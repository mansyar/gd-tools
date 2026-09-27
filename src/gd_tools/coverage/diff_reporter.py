"""Coverage diff reporter module.

Implements the Coverage Diff track (Roadmap Track 33): baseline snapshot
persistence and, in later phases, coverage comparison between a baseline
and the current run.

A baseline is a single self-contained JSON document that nests the two
existing coverage formats verbatim — the ``plan.json`` payload and the
``coverage.json`` payload — plus an advisory ``baseline_meta`` block. The
nested payloads keep their exact on-disk shapes, so baseline loading can
reuse the existing plan and data loaders without a parallel schema.

The baseline is deliberately self-sufficient across branches: the diff
never assumes the head plan equals the baseline plan, because plans change
whenever tracked lines change.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from gd_tools.coverage import plan_generator, reporter
from gd_tools.coverage.plan_generator import CoveragePlan
from gd_tools.coverage.reporter import CoverageData
from gd_tools.errors import CoveragePlanError

_BASELINE_VERSION = 1
_GIT_TIMEOUT_SECONDS = 5


@dataclass
class BaselineMeta:
    """Advisory metadata stamped into a baseline document.

    The diff computation never depends on these fields; they exist to
    give humans context about where a baseline came from.

    Attributes:
        saved_at: UTC ISO timestamp of when the baseline was saved.
        git_branch: Branch name at save time, when detectable.
        git_commit: Full commit SHA at save time, when detectable.
    """

    saved_at: str | None = None
    git_branch: str | None = None
    git_commit: str | None = None


@dataclass
class BaselineSnapshot:
    """A loaded baseline: plan, data, and advisory metadata.

    Attributes:
        plan: The baseline's instrumentation plan.
        data: The baseline's runtime coverage data.
        meta: Advisory metadata from the baseline document.
    """

    plan: CoveragePlan
    data: CoverageData
    meta: BaselineMeta


def _git_output(args: list[str]) -> str | None:
    """Run a git query and return its stripped stdout, or None on failure.

    Git detection is best-effort by design: a baseline saved outside a
    repository (or with git missing) simply carries no git metadata.

    Args:
        args: Arguments to pass to ``git`` (without the program name).

    Returns:
        Stripped stdout on success, otherwise ``None``.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _collect_baseline_meta() -> BaselineMeta:
    """Stamp the advisory metadata block for a new baseline.

    Returns:
        A :class:`BaselineMeta` with the current UTC timestamp and, when
        detectable, the current git branch and commit.
    """
    return BaselineMeta(
        saved_at=datetime.now(timezone.utc).isoformat(),
        git_branch=_git_output(["rev-parse", "--abbrev-ref", "HEAD"]),
        git_commit=_git_output(["rev-parse", "HEAD"]),
    )


def save_baseline(
    plan_path: Path, data_path: Path, baseline_path: Path
) -> BaselineMeta:
    """Persist the current run's coverage as a baseline document.

    Reads the plan and data via the existing loaders (which also validates
    them), nests their raw JSON payloads verbatim, and stamps advisory
    metadata. The baseline is written only after both inputs validate, so
    a failed save never leaves a half-written file behind.

    Args:
        plan_path: Path to the run's ``plan.json``.
        data_path: Path to the run's ``coverage.json``.
        baseline_path: Where to write the baseline document.

    Returns:
        The :class:`BaselineMeta` stamped into the document.

    Raises:
        CoveragePlanError: If either input file is missing or malformed.
    """
    # Validate through the existing loaders first; both raise
    # CoveragePlanError with actionable messages on missing/malformed
    # inputs, which maps to exit code 2 at the CLI boundary.
    plan_generator.read_plan_json(str(plan_path))
    reporter.read_coverage_json(Path(data_path))

    plan_payload = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    data_payload = json.loads(Path(data_path).read_text(encoding="utf-8"))

    meta = _collect_baseline_meta()
    document = {
        "version": _BASELINE_VERSION,
        "baseline_meta": {
            "saved_at": meta.saved_at,
            "git_branch": meta.git_branch,
            "git_commit": meta.git_commit,
        },
        "plan": plan_payload,
        "data": data_payload,
    }
    baseline_path = Path(baseline_path)
    baseline_path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return meta


def load_baseline(path: Path) -> BaselineSnapshot:
    """Load a baseline document into plan, data, and metadata objects.

    The nested payloads are validated through the existing loaders by
    round-tripping them through a temporary directory. This keeps a single
    source of truth for plan and data validation — a malformed baseline
    fails with exactly the same diagnostics as a malformed live run.

    Args:
        path: Path to the baseline JSON document.

    Returns:
        A :class:`BaselineSnapshot` with the loaded plan, data, and
        advisory metadata.

    Raises:
        CoveragePlanError: If the file is missing, contains invalid JSON,
            lacks a required payload, or its nested payloads fail
            validation.
    """
    baseline_path = Path(path)
    if not baseline_path.exists():
        raise CoveragePlanError(
            f"[Error] Baseline file not found: {path}\n"
            f"  Cause: The baseline file does not exist at the specified "
            "path.\n"
            f"  Fix: Create one with 'gd-tools coverage save-baseline' or "
            "pass the correct path via --base."
        )

    try:
        document = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CoveragePlanError(
            "[Error] Invalid JSON in baseline file\n"
            f"  Cause: {exc}\n"
            f"  Fix: Ensure the file is a baseline created by "
            "'gd-tools coverage save-baseline'."
        ) from exc

    if not isinstance(document, dict):
        raise CoveragePlanError(
            "[Error] Baseline must be a JSON object\n"
            "  Cause: The top-level JSON value is not an object.\n"
            "  Fix: Ensure the file is a baseline created by "
            "'gd-tools coverage save-baseline'."
        )

    for key in ("plan", "data"):
        if key not in document:
            raise CoveragePlanError(
                f"[Error] Missing required field: {key}\n"
                f"  Cause: The baseline document does not contain a "
                f"'{key}' payload.\n"
                f"  Fix: Ensure the file is a baseline created by "
                "'gd-tools coverage save-baseline'."
            )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_plan = Path(tmp) / "plan.json"
        tmp_data = Path(tmp) / "coverage.json"
        tmp_plan.write_text(json.dumps(document["plan"]), encoding="utf-8")
        tmp_data.write_text(json.dumps(document["data"]), encoding="utf-8")
        plan = plan_generator.read_plan_json(str(tmp_plan))
        data = reporter.read_coverage_json(tmp_data)

    raw_meta = document.get("baseline_meta")
    if not isinstance(raw_meta, dict):
        raw_meta = {}
    meta = BaselineMeta(
        saved_at=raw_meta.get("saved_at"),
        git_branch=raw_meta.get("git_branch"),
        git_commit=raw_meta.get("git_commit"),
    )
    return BaselineSnapshot(plan=plan, data=data, meta=meta)
