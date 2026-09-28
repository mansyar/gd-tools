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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rich.table import Table
from rich.text import Text

from gd_tools.coverage import plan_generator, reporter
from gd_tools.coverage.plan_generator import CoveragePlan, FilePlan
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileCoverage,
    FileSummary,
    compute_file_summary,
    compute_summary,
)
from gd_tools.errors import CoveragePlanError

_BASELINE_VERSION = 1
_GIT_TIMEOUT_SECONDS = 5
_RATE_EPSILON = 1e-9


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


# --- Diff computation (FR-2) ---


@dataclass
class FileDiff:
    """Per-file coverage comparison between a baseline and the head.

    Metrics are ``None`` on the side the file does not exist on:
    ``new`` files have no base metrics, ``removed`` files have no head
    metrics, and delta fields are ``None`` in both cases.

    Attributes:
        path: ``res://`` path the two sides were matched by.
        classification: One of ``improved``, ``regressed``,
            ``unchanged``, ``new``, ``removed``.
        base_covered_lines / base_total_lines / base_line_rate:
            Baseline line metrics (``None`` for new files).
        head_covered_lines / head_total_lines / head_line_rate:
            Head line metrics (``None`` for removed files).
        base_covered_branches / base_total_branches / base_branch_rate:
            Baseline branch metrics (``None`` for new files).
        head_covered_branches / head_total_branches / head_branch_rate:
            Head branch metrics (``None`` for removed files).
        covered_line_delta: Head minus baseline covered-line count.
        line_rate_delta: Head minus baseline line rate.
        covered_branch_delta: Head minus baseline covered-branch count.
        branch_rate_delta: Head minus baseline branch rate.
        newly_uncovered_lines: Line numbers covered in the baseline but
            not covered in the head (regressed files only).
    """

    path: str
    classification: str
    base_covered_lines: int | None
    base_total_lines: int | None
    base_line_rate: float | None
    head_covered_lines: int | None
    head_total_lines: int | None
    head_line_rate: float | None
    base_covered_branches: int | None
    base_total_branches: int | None
    base_branch_rate: float | None
    head_covered_branches: int | None
    head_total_branches: int | None
    head_branch_rate: float | None
    covered_line_delta: int | None
    line_rate_delta: float | None
    covered_branch_delta: int | None
    branch_rate_delta: float | None
    newly_uncovered_lines: list[int] = field(default_factory=list)


@dataclass
class DiffResult:
    """Result of comparing a baseline snapshot against the head.

    Attributes:
        files: Per-file diffs, sorted by ``res://`` path.
        base_summary: Overall coverage summary of the baseline side.
        head_summary: Overall coverage summary of the head side.
        has_regression: ``True`` when at least one common file's line or
            branch rate decreased relative to the baseline.
    """

    files: list[FileDiff]
    base_summary: CoverageSummary
    head_summary: CoverageSummary
    has_regression: bool


def _covered_line_numbers(
    file_plan: FilePlan, file_data: FileCoverage
) -> set[int]:
    """Return the set of line numbers with at least one hit.

    Args:
        file_plan: The file's instrumentation plan.
        file_data: The file's runtime coverage data.

    Returns:
        Line numbers (1-indexed) whose hit count is positive.
    """
    return {
        line_plan.line
        for line_plan in file_plan.lines
        if file_data.hits.get(str(line_plan.id), 0) > 0
    }


def _side_maps(
    snapshot: BaselineSnapshot,
) -> tuple[dict[str, FileSummary], dict[str, set[int]]]:
    """Compute per-path summaries and covered-line sets for one side.

    Args:
        snapshot: A baseline (or head) plan+data pair.

    Returns:
        A mapping of ``res://`` path to :class:`FileSummary`, and a
        mapping of ``res://`` path to the set of covered line numbers.
    """
    data_by_id = {fc.file_id: fc for fc in snapshot.data.files}
    summaries: dict[str, FileSummary] = {}
    covered: dict[str, set[int]] = {}
    for file_plan in snapshot.plan.files:
        file_data = data_by_id.get(
            file_plan.file_id,
            FileCoverage(file_id=file_plan.file_id, hits={}),
        )
        summaries[file_plan.path] = compute_file_summary(file_plan, file_data)
        covered[file_plan.path] = _covered_line_numbers(file_plan, file_data)
    return summaries, covered


def compute_diff(base: BaselineSnapshot, head: BaselineSnapshot) -> DiffResult:
    """Compare a baseline coverage snapshot against the head snapshot.

    Files are matched by ``res://`` path, never by ``file_id``, so the
    two sides may come from plans generated on different branches. Files
    present only in the head are classified ``new``; files present only
    in the baseline are classified ``removed``. Regression is decided on
    coverage *rates*, not covered counts, so a file that gained covered
    lines but gained even more executable lines still counts as a
    regression.

    Args:
        base: The baseline snapshot (plan + data + advisory metadata).
        head: The head snapshot. Its metadata is ignored.

    Returns:
        A :class:`DiffResult` with per-file diffs sorted by path,
        overall summaries for both sides, and the regression flag.
    """
    base_summaries, base_covered = _side_maps(base)
    head_summaries, head_covered = _side_maps(head)

    files: list[FileDiff] = []
    for path in sorted(set(base_summaries) | set(head_summaries)):
        base_fs = base_summaries.get(path)
        head_fs = head_summaries.get(path)

        if head_fs is None:
            files.append(
                FileDiff(
                    path=path,
                    classification="removed",
                    base_covered_lines=base_fs.covered_lines,
                    base_total_lines=base_fs.total_lines,
                    base_line_rate=base_fs.line_rate,
                    head_covered_lines=None,
                    head_total_lines=None,
                    head_line_rate=None,
                    base_covered_branches=base_fs.covered_branches,
                    base_total_branches=base_fs.total_branches,
                    base_branch_rate=base_fs.branch_rate,
                    head_covered_branches=None,
                    head_total_branches=None,
                    head_branch_rate=None,
                    covered_line_delta=None,
                    line_rate_delta=None,
                    covered_branch_delta=None,
                    branch_rate_delta=None,
                )
            )
            continue

        if base_fs is None:
            files.append(
                FileDiff(
                    path=path,
                    classification="new",
                    base_covered_lines=None,
                    base_total_lines=None,
                    base_line_rate=None,
                    head_covered_lines=head_fs.covered_lines,
                    head_total_lines=head_fs.total_lines,
                    head_line_rate=head_fs.line_rate,
                    base_covered_branches=None,
                    base_total_branches=None,
                    base_branch_rate=None,
                    head_covered_branches=head_fs.covered_branches,
                    head_total_branches=head_fs.total_branches,
                    head_branch_rate=head_fs.branch_rate,
                    covered_line_delta=None,
                    line_rate_delta=None,
                    covered_branch_delta=None,
                    branch_rate_delta=None,
                )
            )
            continue

        line_regressed = head_fs.line_rate < base_fs.line_rate - _RATE_EPSILON
        branch_regressed = (
            head_fs.branch_rate < base_fs.branch_rate - _RATE_EPSILON
        )
        line_improved = head_fs.line_rate > base_fs.line_rate + _RATE_EPSILON
        branch_improved = (
            head_fs.branch_rate > base_fs.branch_rate + _RATE_EPSILON
        )
        # A file with no executable points on either side has no
        # meaningful rates; never let 0/0 vs 0/0 read as a change.
        if (
            base_fs.total_lines == 0
            and head_fs.total_lines == 0
            and base_fs.total_branches == 0
            and head_fs.total_branches == 0
        ):
            classification = "unchanged"
        elif line_regressed or branch_regressed:
            classification = "regressed"
        elif line_improved or branch_improved:
            classification = "improved"
        else:
            classification = "unchanged"

        files.append(
            FileDiff(
                path=path,
                classification=classification,
                base_covered_lines=base_fs.covered_lines,
                base_total_lines=base_fs.total_lines,
                base_line_rate=base_fs.line_rate,
                head_covered_lines=head_fs.covered_lines,
                head_total_lines=head_fs.total_lines,
                head_line_rate=head_fs.line_rate,
                base_covered_branches=base_fs.covered_branches,
                base_total_branches=base_fs.total_branches,
                base_branch_rate=base_fs.branch_rate,
                head_covered_branches=head_fs.covered_branches,
                head_total_branches=head_fs.total_branches,
                head_branch_rate=head_fs.branch_rate,
                covered_line_delta=(
                    head_fs.covered_lines - base_fs.covered_lines
                ),
                line_rate_delta=head_fs.line_rate - base_fs.line_rate,
                covered_branch_delta=(
                    head_fs.covered_branches - base_fs.covered_branches
                ),
                branch_rate_delta=(head_fs.branch_rate - base_fs.branch_rate),
                newly_uncovered_lines=sorted(
                    base_covered[path] - head_covered[path]
                ),
            )
        )

    return DiffResult(
        files=files,
        base_summary=compute_summary(base.plan, base.data),
        head_summary=compute_summary(head.plan, head.data),
        has_regression=any(fd.classification == "regressed" for fd in files),
    )


# --- Rendering (FR-2) ---


def _format_metrics(
    covered: int | None, total: int | None, rate: float | None
) -> str:
    """Format a side's coverage metrics, or ``-`` when the side is absent."""
    if covered is None or total is None or rate is None:
        return "-"
    return f"{covered}/{total} ({rate:.0%})"


def _format_change(fd: FileDiff) -> str:
    """Format the human-readable change column for one file."""
    if fd.classification == "new":
        return "new"
    if fd.classification == "removed":
        return "removed"
    parts: list[str] = []
    if fd.covered_line_delta:
        parts.append(f"{fd.covered_line_delta:+d} lines")
    if fd.covered_branch_delta:
        parts.append(f"{fd.covered_branch_delta:+d} branches")
    return ", ".join(parts) if parts else "-"


def build_diff_table(result: DiffResult, meta: BaselineMeta) -> Table:
    """Build the Rich summary table for a coverage diff.

    Rows are one per file (sorted by path) plus a ``TOTAL`` row. The
    table title carries the baseline's advisory metadata when available.

    Args:
        result: The diff to render.
        meta: The baseline's metadata (may be all-``None``).

    Returns:
        A :class:`rich.table.Table` ready to print via
        ``gd_tools.output.print_table``.
    """
    title = "Coverage diff vs baseline"
    meta_bits: list[str] = []
    if meta.saved_at:
        meta_bits.append(f"saved {meta.saved_at}")
    if meta.git_branch:
        meta_bits.append(f"on {meta.git_branch}")
    if meta.git_commit:
        meta_bits.append(f"@ {meta.git_commit[:7]}")
    if meta_bits:
        title += f" ({' '.join(meta_bits)})"

    table = Table(title=title)
    table.add_column("File", style="dim", no_wrap=True)
    table.add_column("Lines (base)", justify="right")
    table.add_column("Lines (head)", justify="right")
    table.add_column("Branches (base)", justify="right")
    table.add_column("Branches (head)", justify="right")
    table.add_column("Change")

    for fd in result.files:
        style = (
            "red"
            if fd.classification == "regressed"
            else "green" if fd.classification == "improved" else ""
        )
        table.add_row(
            fd.path,
            _format_metrics(
                fd.base_covered_lines, fd.base_total_lines, fd.base_line_rate
            ),
            _format_metrics(
                fd.head_covered_lines, fd.head_total_lines, fd.head_line_rate
            ),
            _format_metrics(
                fd.base_covered_branches,
                fd.base_total_branches,
                fd.base_branch_rate,
            ),
            _format_metrics(
                fd.head_covered_branches,
                fd.head_total_branches,
                fd.head_branch_rate,
            ),
            Text(_format_change(fd), style=style),
        )

    line_delta = (
        result.head_summary.covered_lines - result.base_summary.covered_lines
    )
    branch_delta = (
        result.head_summary.covered_branches
        - result.base_summary.covered_branches
    )
    total_parts: list[str] = []
    if line_delta:
        total_parts.append(f"{line_delta:+d} lines")
    if branch_delta:
        total_parts.append(f"{branch_delta:+d} branches")
    table.add_row(
        "TOTAL",
        _format_metrics(
            result.base_summary.covered_lines,
            result.base_summary.total_lines,
            result.base_summary.line_rate,
        ),
        _format_metrics(
            result.head_summary.covered_lines,
            result.head_summary.total_lines,
            result.head_summary.line_rate,
        ),
        _format_metrics(
            result.base_summary.covered_branches,
            result.base_summary.total_branches,
            result.base_summary.branch_rate,
        ),
        _format_metrics(
            result.head_summary.covered_branches,
            result.head_summary.total_branches,
            result.head_summary.branch_rate,
        ),
        Text(
            ", ".join(total_parts) if total_parts else "-",
            style="red" if line_delta < 0 or branch_delta < 0 else "green",
        ),
    )
    return table


def build_diff_detail(result: DiffResult) -> list[str]:
    """Build newly-uncovered detail lines for regressed files.

    Args:
        result: The diff to render.

    Returns:
        One line per regressed file that lost coverage, e.g.
        ``res://player.gd: newly uncovered lines 3, 4``. Files that did
        not regress contribute nothing.
    """
    detail: list[str] = []
    for fd in result.files:
        if fd.classification == "regressed" and fd.newly_uncovered_lines:
            numbers = ", ".join(str(n) for n in fd.newly_uncovered_lines)
            detail.append(f"{fd.path}: newly uncovered lines {numbers}")
    return detail


def _side_to_json(
    covered: int | None,
    total: int | None,
    rate: float | None,
    covered_branches: int | None,
    total_branches: int | None,
    branch_rate: float | None,
) -> dict[str, int | float] | None:
    """Serialize one side's metrics, or ``None`` when the side is absent."""
    if covered is None or total is None or rate is None:
        return None
    return {
        "covered_lines": covered,
        "total_lines": total,
        "line_rate": rate,
        "covered_branches": covered_branches or 0,
        "total_branches": total_branches or 0,
        "branch_rate": branch_rate or 0.0,
    }


def build_diff_json(result: DiffResult, meta: BaselineMeta) -> dict:
    """Build the machine-readable diff payload (``--report-format json``).

    The structure is deterministic: files are sorted by path and all
    keys are fixed, so two runs over identical inputs serialize
    identically.

    Args:
        result: The diff to serialize.
        meta: The baseline's advisory metadata.

    Returns:
        A JSON-serializable dict with ``baseline_meta``, ``files``
        (per-file metrics, classifications, deltas, and newly-uncovered
        lines), ``totals`` for both sides, and ``has_regression``.
    """

    def file_entry(fd: FileDiff) -> dict:
        return {
            "path": fd.path,
            "classification": fd.classification,
            "base": _side_to_json(
                fd.base_covered_lines,
                fd.base_total_lines,
                fd.base_line_rate,
                fd.base_covered_branches,
                fd.base_total_branches,
                fd.base_branch_rate,
            ),
            "head": _side_to_json(
                fd.head_covered_lines,
                fd.head_total_lines,
                fd.head_line_rate,
                fd.head_covered_branches,
                fd.head_total_branches,
                fd.head_branch_rate,
            ),
            "covered_line_delta": fd.covered_line_delta,
            "line_rate_delta": fd.line_rate_delta,
            "covered_branch_delta": fd.covered_branch_delta,
            "branch_rate_delta": fd.branch_rate_delta,
            "newly_uncovered_lines": fd.newly_uncovered_lines,
        }

    def totals(summary: CoverageSummary) -> dict[str, int | float]:
        return {
            "covered_lines": summary.covered_lines,
            "total_lines": summary.total_lines,
            "line_rate": summary.line_rate,
            "covered_branches": summary.covered_branches,
            "total_branches": summary.total_branches,
            "branch_rate": summary.branch_rate,
        }

    return {
        "baseline_meta": {
            "saved_at": meta.saved_at,
            "git_branch": meta.git_branch,
            "git_commit": meta.git_commit,
        },
        "files": [file_entry(fd) for fd in result.files],
        "totals": {
            "base": totals(result.base_summary),
            "head": totals(result.head_summary),
        },
        "has_regression": result.has_regression,
    }
