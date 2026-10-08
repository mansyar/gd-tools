"""Patch coverage computation for ``coverage diff --patch``.

Computes coverage restricted to the lines changed relative to a base
ref: changed-line ranges from :mod:`gd_tools.changes` are intersected
with the coverage plan's executable line points, then classified as
covered or uncovered using the current run's coverage data.

Files whose changed ranges contain no executable plan lines are
excluded from the metrics entirely and never fail the gate, matching
the strict edge semantics of the track specification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.table import Table

from gd_tools.coverage.plan_generator import CoveragePlan, FilePlan
from gd_tools.coverage.reporter import CoverageData


@dataclass
class PatchFileMetric:
    """Patch coverage metrics for one changed file.

    Attributes:
        path: Repo-relative path as reported by git (forward slashes).
        changed: Executable plan lines that fall inside changed ranges.
        covered: Changed executable lines with at least one hit.
        uncovered: Changed executable lines with zero hits.
        rate: Covered / changed as a fraction; 0.0 when changed is 0.
    """

    path: str
    changed: int
    covered: int
    uncovered: int
    rate: float


@dataclass
class PatchCoverageResult:
    """Aggregate patch coverage across all changed files.

    Attributes:
        files: Per-file metrics, sorted by path. Files with no changed
            executable plan lines are omitted.
        covered: Total covered changed executable lines.
        total: Total changed executable lines across all files.
        rate: Overall covered / total as a fraction; 0.0 when total
            is 0 (an empty patch never fails the gate).
    """

    files: list[PatchFileMetric] = field(default_factory=list)
    covered: int = 0
    total: int = 0
    rate: float = 0.0


def _normalize_plan_path(path: str) -> str:
    """Convert a plan ``res://`` path to a forward-slash repo path."""
    stripped = path.removeprefix("res://")
    return stripped.replace("\\", "/")


def compute_patch_coverage(
    plan: CoveragePlan,
    data: CoverageData,
    changed: dict[Path, list[tuple[int, int]]],
) -> PatchCoverageResult:
    """Compute coverage over the lines changed relative to a base ref.

    Args:
        plan: The coverage instrumentation plan for the current tree.
        data: The current run's coverage data (may be empty).
        changed: Mapping of repo-relative ``.gd`` paths to inclusive
            ``(start, end)`` added-line ranges, as returned by
            :func:`gd_tools.changes.collect_changed_lines`.

    Returns:
        A :class:`PatchCoverageResult` with per-file metrics and
        aggregate totals. Files with no changed executable plan lines
        are excluded from ``files``.
    """
    hits_by_file_id: dict[int, dict[str, int]] = {
        entry.file_id: entry.hits for entry in data.files
    }
    plans_by_path: dict[str, FilePlan] = {
        _normalize_plan_path(fp.path): fp for fp in plan.files
    }

    metrics: list[PatchFileMetric] = []
    total_covered = 0
    total_changed = 0

    for path in sorted(changed, key=lambda p: p.as_posix()):
        file_plan = plans_by_path.get(path.as_posix())
        if file_plan is None:
            continue

        changed_lines: set[int] = set()
        for start, end in changed[path]:
            changed_lines.update(range(start, end + 1))
        executable_changed = sorted(
            {lp.line for lp in file_plan.lines} & changed_lines
        )
        if not executable_changed:
            continue

        lines_by_line = {lp.line: lp for lp in file_plan.lines}
        hits = hits_by_file_id.get(file_plan.file_id, {})
        covered_count = sum(
            1
            for line_number in executable_changed
            if hits.get(str(lines_by_line[line_number].id), 0) > 0
        )
        changed_count = len(executable_changed)
        metrics.append(
            PatchFileMetric(
                path=path.as_posix(),
                changed=changed_count,
                covered=covered_count,
                uncovered=changed_count - covered_count,
                rate=covered_count / changed_count,
            )
        )
        total_covered += covered_count
        total_changed += changed_count

    return PatchCoverageResult(
        files=metrics,
        covered=total_covered,
        total=total_changed,
        rate=total_covered / total_changed if total_changed > 0 else 0.0,
    )


def patch_verdict(result: PatchCoverageResult, threshold: float | None) -> str:
    """Classify a patch coverage result against an optional threshold.

    Args:
        result: The computed patch coverage.
        threshold: Minimum required patch coverage percentage
            (``--patch-fail-under``), or ``None`` for informational mode.

    Returns:
        ``"pass"`` when the gate holds (an empty patch always passes),
        ``"fail"`` when below the threshold, or ``"informational"``
        when no threshold is configured.
    """
    if threshold is None:
        return "informational"
    if result.total == 0:
        return "pass"
    return "pass" if result.rate * 100 >= threshold else "fail"


def build_patch_table(
    result: PatchCoverageResult, threshold: float | None
) -> Table:
    """Build the Rich summary table for patch coverage.

    Rows are one per file (sorted by path) plus a ``TOTAL`` row. The
    caption carries the gate verdict: ``PASS``/``FAIL`` against the
    threshold, ``informational`` without one, or a no-changed-lines
    notice for an empty patch (which never fails the gate).

    Args:
        result: The computed patch coverage.
        threshold: Gate threshold percentage, or ``None``.

    Returns:
        A :class:`rich.table.Table` ready to print via
        ``gd_tools.output.print_table``.
    """
    table = Table(title="Patch coverage vs base")
    table.add_column("File", style="dim", no_wrap=True)
    table.add_column("Changed", justify="right")
    table.add_column("Covered", justify="right")
    table.add_column("Uncovered", justify="right")
    table.add_column("Coverage", justify="right")

    for fm in result.files:
        table.add_row(
            fm.path,
            str(fm.changed),
            str(fm.covered),
            str(fm.uncovered),
            f"{fm.covered}/{fm.changed} ({fm.rate:.0%})",
        )

    table.add_row(
        "TOTAL",
        str(result.total),
        str(result.covered),
        str(result.total - result.covered),
        f"{result.covered}/{result.total} ({result.rate:.0%})",
    )

    if result.total == 0:
        table.caption = "No changed executable lines"
    else:
        verdict = patch_verdict(result, threshold)
        if verdict == "informational":
            table.caption = "Patch coverage gate: informational (no threshold)"
        else:
            label = "PASS" if verdict == "pass" else "FAIL"
            table.caption = (
                f"Patch coverage gate: {label} "
                f"({result.rate:.0%} vs {threshold:.0f}% required)"
            )
    return table


def build_patch_json(
    result: PatchCoverageResult, threshold: float | None
) -> dict:
    """Build the machine-readable patch payload (``--report-format json``).

    The structure is deterministic: files are sorted by path (as in
    :func:`compute_patch_coverage`) and all keys are fixed.

    Args:
        result: The computed patch coverage.
        threshold: Gate threshold percentage, or ``None``.

    Returns:
        A JSON-serializable dict with ``files``, ``totals``,
        ``threshold``, ``verdict``, and ``empty``.
    """
    return {
        "files": [
            {
                "path": fm.path,
                "changed": fm.changed,
                "covered": fm.covered,
                "uncovered": fm.uncovered,
                "rate": fm.rate,
            }
            for fm in result.files
        ],
        "totals": {
            "covered": result.covered,
            "total": result.total,
            "rate": result.rate,
        },
        "threshold": threshold,
        "verdict": patch_verdict(result, threshold),
        "empty": result.total == 0,
    }
