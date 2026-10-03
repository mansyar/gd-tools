"""Coverage orchestrator module.

Coordinates coverage plan generation, data merging, and reporting. The
coverage CLI commands delegate to these functions rather than embedding
business logic directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.table import Table
from rich.text import Text

from gd_tools import output
from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.coverage import plan_generator, reporter
import json

from gd_tools.coverage.diff_reporter import (
    BaselineMeta,
    BaselineSnapshot,
    DiffResult,
    build_diff_detail,
    build_diff_json,
    build_diff_table,
    compute_diff,
    load_baseline,
    save_baseline,
)
from gd_tools.coverage.omissions import (
    OmissionReport,
    omission_gate_message,
    reconcile_omissions,
)
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileSummary,
    ReportResult,
)
from gd_tools.errors import (
    CoverageThresholdError,
)

if TYPE_CHECKING:
    from gd_tools.coverage.plan_generator import CoveragePlan


def generate_coverage_report(
    config: GdToolsConfig,
    report_format: str | None = None,
    output_dir: str | None = None,
    annotate_min_percent: int | None = None,
) -> ReportResult:
    """Regenerate reports from existing coverage data without re-running tests.

    Reads existing ``plan.json`` and ``coverage.json`` from the output
    directory and regenerates reports in the specified format.

    Args:
        config: Project configuration.
        report_format: Report format override (e.g., ``"html"``, ``"lcov"``,
            ``"cobertura"``, ``"text"``).  If ``None``, uses
            ``config.coverage.format``.
        output_dir: Output directory override.  If ``None``, uses
            ``config.coverage.output_dir``.
        annotate_min_percent: Line-coverage percentage (0-100) used by the
            ``github-actions`` format to emit per-file ``::warning``
            annotations for files below the threshold.  Only used by that
            format; ``None`` disables annotations.

    Returns:
        The :class:`ReportResult` from report generation.

    Raises:
        CoveragePlanError: If ``plan.json`` or ``coverage.json`` is
            missing or invalid.
    """
    project_root = find_project_root()

    # Resolve effective output_dir: flag > config > default.
    effective_output_dir = (
        output_dir if output_dir is not None else config.coverage.output_dir
    )
    output_path = project_root / effective_output_dir

    # Resolve effective format: flag > config > default.
    effective_format = (
        report_format if report_format is not None else config.coverage.format
    )

    # Read existing plan and coverage data.
    plan = plan_generator.read_plan_json(str(output_path / "plan.json"))
    data = reporter.read_coverage_json(output_path / "coverage.json")

    # Generate report.
    return reporter.generate_report(
        plan,
        data,
        output_path,
        effective_format,
        annotate_min_percent=annotate_min_percent,
    )


def merge_coverage_files(
    files: list[Path],
    output_path: Path | None = None,
    config: GdToolsConfig | None = None,
) -> CoverageData:
    """Merge multiple coverage data files into one.

    Delegates to :func:`reporter.merge_coverage_data` to sum hit
    counts, then writes the merged result as JSON.

    Args:
        files: List of paths to coverage data JSON files.
        output_path: Path for the merged output file. If ``None``,
            defaults to ``<output_dir>/coverage.json`` (resolved via
            ``find_project_root`` and ``config.coverage.output_dir``
            when ``config`` is provided, or ``.gd-tools/coverage/
            coverage.json`` relative to the current working directory
            otherwise).
        config: Optional project configuration for resolving the
            default output path.

    Returns:
        The merged :class:`CoverageData`.
    """
    if output_path is None:
        if config is not None:
            project_root = find_project_root()
            output_path = (
                project_root / config.coverage.output_dir / "coverage.json"
            )
        else:
            output_path = (
                Path.cwd() / ".gd-tools" / "coverage" / "coverage.json"
            )

    merged = reporter.merge_coverage_data(files)

    reporter.write_coverage_json(merged, output_path)

    output.console.print(
        f"Merged {len(files)} file(s) → {len(merged.files)} file(s) "
        f"in output. Written to: {output_path}"
    )

    return merged


def print_coverage_table(
    summary: CoverageSummary, min_percent: int | None = None
) -> None:
    """Print a Rich coverage summary table to stdout.

    Renders a table with Lines and Branches rows, showing Found,
    Hit, and Rate columns.  Rate cells are color-coded based on the
    minimum threshold: green when at or above the threshold, red when
    below.  Uses the shared output module for consistent rendering.

    Args:
        summary: The coverage summary to display.
        min_percent: Optional minimum coverage percentage (0-100).
            When set, rate cells are color-coded green if at or above
            the threshold, red if below.
    """
    table = Table(title="Coverage Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Found", justify="right")
    table.add_column("Hit", justify="right")
    table.add_column("Rate", justify="right")

    line_pct = summary.line_rate * 100
    branch_pct = summary.branch_rate * 100

    if min_percent is not None:
        line_style = "green" if line_pct >= min_percent else "red"
        branch_style = "green" if branch_pct >= min_percent else "red"
    else:
        line_style = "green"
        branch_style = "green"

    table.add_row(
        "Lines",
        str(summary.total_lines),
        str(summary.covered_lines),
        Text(f"{line_pct:.1f}%", style=line_style),
    )
    table.add_row(
        "Branches",
        str(summary.total_branches),
        str(summary.covered_branches),
        Text(f"{branch_pct:.1f}%", style=branch_style),
    )

    output.print_table(table)


def print_threshold_footer(
    summary: CoverageSummary,
    min_percent: int | None = None,
    min_branch_percent: int | None = None,
) -> None:
    """Print a summary footer with threshold pass/fail status.

    Args:
        summary: The coverage summary to display.
        min_percent: Optional minimum line coverage percentage (0-100).
        min_branch_percent: Optional minimum branch coverage percentage
            (0-100).
    """
    line_pct = summary.line_rate * 100
    if min_percent is not None:
        status = "pass" if line_pct >= min_percent else "fail"
        output.print_summary(
            status,
            f"{line_pct:.1f}% line coverage (threshold: {min_percent}%)",
        )
    else:
        output.print_summary("pass", f"{line_pct:.1f}% line coverage")

    if min_branch_percent is not None:
        if summary.total_branches == 0:
            output.print_summary(
                "pass",
                "Branch coverage: no branch points; "
                "--min-branch gate not applied.",
            )
        else:
            branch_pct = summary.branch_rate * 100
            status = "pass" if branch_pct >= min_branch_percent else "fail"
            output.print_summary(
                status,
                f"{branch_pct:.1f}% branch coverage "
                f"(threshold: {min_branch_percent}%)",
            )


def _report_coverage(
    plan: CoveragePlan,
    data: CoverageData,
    summary: CoverageSummary,
    min_percent: int | None,
    *,
    show_uncovered: bool,
    file_summaries: list[FileSummary] | None,
    min_branch_percent: int | None = None,
) -> None:
    """Reconcile the run against its plan, print it, and gate on it.

    The single wiring point for the coverage contract (spec R5, R6, R7).
    Both runtimes reach this through :func:`_print_coverage_inline`; the
    reconciliation and the gate live here so the two can never diverge.

    Args:
        plan: The instrumentation plan.
        data: The runtime coverage data.
        summary: The plan-wide coverage summary.
        min_percent: The ``--min`` threshold, or None.
        show_uncovered: Whether to print per-file uncovered panels.
        file_summaries: Per-file summaries for uncovered detail.

    Raises:
        CoverageThresholdError: With exit code 2, when ``--min`` was
            requested and the measurement turned out to be partial. A gate
            reporting success over a knowingly incomplete measurement is
            not a gate, so this is deliberately separate from the
            percentage threshold.
    """
    omissions = reconcile_omissions(plan, data)
    instrumented_summary = None
    if omissions.has_omissions:
        excluded = frozenset(t.file_id for t in omissions.omitted)
        instrumented_summary = reporter.compute_summary(
            plan, data, exclude_ids=excluded
        )

    _print_coverage_inline(
        summary,
        min_percent,
        show_uncovered=show_uncovered,
        file_summaries=file_summaries,
        min_branch_percent=min_branch_percent,
        plan=plan,
        omissions=omissions,
        instrumented_summary=instrumented_summary,
    )

    gate = omission_gate_message(omissions, min_percent)
    if gate is not None:
        raise CoverageThresholdError(gate, exit_code=2)


def _print_coverage_inline(
    summary: CoverageSummary,
    min_percent: int | None = None,
    show_uncovered: bool = False,
    file_summaries: list[FileSummary] | None = None,
    min_branch_percent: int | None = None,
    plan: CoveragePlan | None = None,
    *,
    omissions: OmissionReport | None = None,
    instrumented_summary: CoverageSummary | None = None,
) -> None:
    """Print a one-line coverage summary.

    Used by :func:`show_coverage_summary` to show coverage after test
    results.  Prints the line and branch coverage percentages followed
    by a summary footer indicating whether the threshold was met.
    When ``show_uncovered`` is True and coverage is below 100%,
    per-file uncovered detail panels are printed below the summary.

    When ``omissions`` reports skipped targets, the run was partial. The
    plan-wide figure is then labelled as such and the instrumented-set
    figure is shown beside it, because a percentage whose denominator
    excludes failing files would otherwise look like a whole-project
    result (spec R6).

    Args:
        summary: The plan-wide coverage summary to display.
        min_percent: Optional minimum coverage percentage (0-100).
        show_uncovered: If True, print per-file uncovered lines and
            branches panels when coverage is below 100%.
        file_summaries: Per-file summaries for uncovered detail.
            Required when ``show_uncovered`` is True.
        plan: Coverage plan for branch type lookup.  Required when
            ``show_uncovered`` is True.
        omissions: Reconciliation result, when the run skipped any target.
        instrumented_summary: The instrumented-set summary. Shown beside
            the plan-wide figure when the two differ.
    """
    line_pct = summary.line_rate * 100
    branch_pct = summary.branch_rate * 100

    partial = omissions is not None and omissions.has_omissions

    if partial:
        assert instrumented_summary is not None
        inst_line_pct = instrumented_summary.line_rate * 100
        inst_branch_pct = instrumented_summary.branch_rate * 100
        output.print_info(
            f"Coverage: {inst_line_pct:.1f}% lines, "
            f"{inst_branch_pct:.1f}% branches "
            f"(of {omissions.instrumented_count}/{omissions.plan_count} "
            f"instrumented; {line_pct:.1f}% lines of the whole plan)"
        )
    else:
        output.print_info(
            f"Coverage: {line_pct:.1f}% lines, {branch_pct:.1f}% branches"
        )

    print_threshold_footer(summary, min_percent, min_branch_percent)

    if partial:
        assert omissions is not None
        output.print_warning(
            f"Coverage is partial: {len(omissions.omitted)} of "
            f"{omissions.plan_count} plan targets could not be instrumented."
        )
        for target in omissions.omitted:
            detail = f"  {target.path}\n    Cause: {target.reason}"
            if target.fix:
                detail += f"\n    Fix:   {target.fix}"
            output.print_warning(detail)

    if show_uncovered and file_summaries is not None and plan is not None:
        panels = reporter.render_uncovered_panels(file_summaries, plan)
        if panels is not None:
            output.console.print(panels)


def show_coverage_summary(
    config: GdToolsConfig,
    min_percent: int | None = None,
    min_branch_percent: int | None = None,
) -> CoverageSummary:
    """Display a terminal summary table of coverage results.

    Reads existing ``plan.json`` and ``coverage.json``, computes a
    summary, prints a Rich table, and optionally enforces a minimum
    threshold.  Per-file uncovered detail panels are always printed
    below the summary when coverage is below 100%.

    Args:
        config: Project configuration.
        min_percent: Minimum coverage percentage (0-100). If set and
            line coverage is below this, raises
            :class:`CoverageThresholdError`.
        min_branch_percent: Minimum branch coverage percentage (0-100).
            If set and branch coverage is below this, raises
            :class:`CoverageThresholdError`.

    Returns:
        The :class:`CoverageSummary`.

    Raises:
        CoverageThresholdError: If ``min_percent`` is set and line
            coverage is below the threshold, or ``min_branch_percent``
            is set and branch coverage is below the threshold.
        CoveragePlanError: If ``plan.json`` or ``coverage.json`` is
            missing or invalid.
    """
    project_root = find_project_root()
    output_dir = project_root / config.coverage.output_dir

    # Read plan and coverage data.
    plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))
    data = reporter.read_coverage_json(output_dir / "coverage.json")

    # Compute summary.
    summary = reporter.compute_summary(plan, data)

    # Compute per-file summaries for uncovered detail.
    coverage_by_id = {fc.file_id: fc for fc in data.files}
    file_summaries: list[FileSummary] = []
    for file_plan in plan.files:
        file_data = coverage_by_id.get(
            file_plan.file_id,
            reporter.FileCoverage(file_id=file_plan.file_id, hits={}),
        )
        file_summaries.append(
            reporter.compute_file_summary(file_plan, file_data)
        )

    # Print Rich terminal table with color-coded rates.
    print_coverage_table(summary, min_percent)

    # Print summary footer with threshold status.
    print_threshold_footer(summary, min_percent, min_branch_percent)

    # Print uncovered detail panels (always shown for coverage show).
    panels = reporter.render_uncovered_panels(file_summaries, plan)
    if panels is not None:
        output.console.print(panels)

    # Threshold check.
    if min_percent is not None and summary.line_rate * 100 < min_percent:
        raise CoverageThresholdError(
            f"[Error] Line coverage {summary.line_rate * 100:.1f}% is "
            f"below minimum threshold {min_percent}%\n"
            f"  Cause: Only {summary.covered_lines} of "
            f"{summary.total_lines} lines were executed.\n"
            f"  Fix: Add tests to cover uncovered lines or lower the "
            "--min threshold."
        )
    if (
        min_branch_percent is not None
        and summary.total_branches > 0
        and summary.branch_rate * 100 < min_branch_percent
    ):
        raise CoverageThresholdError(
            f"[Error] Branch coverage {summary.branch_rate * 100:.1f}% is "
            f"below minimum threshold {min_branch_percent}%\n"
            f"  Cause: Only {summary.covered_branches} of "
            f"{summary.total_branches} branches were executed.\n"
            f"  Fix: Add tests to cover uncovered branches or lower the "
            "--min-branch threshold."
        )

    return summary


def save_coverage_baseline(config: GdToolsConfig) -> Path:
    """Save the latest coverage run as the diff baseline.

    Reads ``plan.json`` and ``coverage.json`` from the coverage output
    directory and writes them as a self-contained baseline document at
    ``<output_dir>/baseline.json`` (see ``diff_reporter.save_baseline``).

    Args:
        config: Resolved project configuration.

    Returns:
        Path to the written baseline file.

    Raises:
        CoveragePlanError: If the plan or coverage data is missing or
            malformed (exit code 2 at the CLI boundary).
    """
    project_root = find_project_root()
    output_dir = project_root / config.coverage.output_dir
    baseline_path = output_dir / "baseline.json"
    save_baseline(
        output_dir / "plan.json",
        output_dir / "coverage.json",
        baseline_path,
    )
    return baseline_path


def diff_coverage(
    config: GdToolsConfig,
    base: str,
    *,
    show_lines: bool = False,
    report_format: str = "text",
    fail_on_regression: bool = False,
) -> DiffResult:
    """Compare current coverage against a baseline and report the diff.

    Loads the baseline document and the current plan/data pair from the
    coverage output directory, computes the per-file diff, and renders
    it as a terminal table or machine-readable JSON.

    Args:
        config: Resolved project configuration.
        base: Path to the baseline file written by ``save-baseline``.
        show_lines: List newly-uncovered line numbers for regressed files.
        report_format: ``"text"`` for the terminal table, ``"json"`` for
            deterministic machine-readable output.
        fail_on_regression: Raise :class:`CoverageThresholdError` when any
            file regressed (exit code 1 at the CLI boundary).

    Returns:
        The computed :class:`DiffResult`.

    Raises:
        CoveragePlanError: If the baseline or the current plan/data pair
            is missing or malformed (exit code 2 at the CLI boundary).
        CoverageThresholdError: If ``fail_on_regression`` is set and any
            file regressed (exit code 1 at the CLI boundary).
    """
    baseline = load_baseline(base)

    project_root = find_project_root()
    output_dir = project_root / config.coverage.output_dir
    plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))
    data = reporter.read_coverage_json(output_dir / "coverage.json")
    head = BaselineSnapshot(plan=plan, data=data, meta=BaselineMeta())

    result = compute_diff(baseline, head)

    if report_format == "json":
        # Plain print (not the Rich console) so piped output is never
        # line-wrapped and stays valid, deterministic JSON.
        print(json.dumps(build_diff_json(result, baseline.meta), indent=2))
    else:
        output.print_table(build_diff_table(result, baseline.meta))
        if show_lines:
            for detail_line in build_diff_detail(result):
                output.console.print(Text(detail_line, style="red"))

    if fail_on_regression and result.has_regression:
        regressed = [
            fd.path for fd in result.files if fd.classification == "regressed"
        ]
        raise CoverageThresholdError(
            "[Error] Coverage regression detected\n"
            f"  Cause: {len(regressed)} file(s) have lower coverage "
            f"than the baseline: {', '.join(regressed)}\n"
            "  Fix: Add tests to restore coverage, or rerun without "
            "--fail-on-regression."
        )

    return result
