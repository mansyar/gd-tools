"""Coverage orchestrator module.

Coordinates the full coverage flow by wiring together the plan generator,
test runner, and reporter modules.  This is the orchestration layer mandated
by NFR-1 — CLI commands delegate to these functions rather than embedding
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
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileSummary,
    ReportResult,
)
from gd_tools.errors import (
    CoveragePlanError,
    CoverageThresholdError,
    TestFailureError,
)
from gd_tools.test_runner import TestResult, run_tests

if TYPE_CHECKING:
    from gd_tools.coverage.plan_generator import CoveragePlan


def run_coverage_test(
    config: GdToolsConfig,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    min_percent: int | None = None,
    timeout: int | None = None,
    paths: list[str] | None = None,
    show_uncovered: bool = False,
) -> TestResult:
    """Run tests with coverage instrumentation and generate reports.

    Orchestrates the full coverage flow:

    1. Generate an instrumentation plan.
    2. Write the plan to ``<output_dir>/plan.json``.
    3. Run tests with coverage enabled.
    4. Read the coverage data produced by the runtime hooks.
    5. Generate reports in the configured format.

    Error precedence (NFR-2): ``TestFailureError`` is re-raised before
    ``CoverageThresholdError`` when both occur.

    Args:
        config: Project configuration.
        suite: Optional test suite filter.
        test_name: Optional specific test to run.
        junit_xml: Optional JUnit XML output path.
        no_exit_code: If True, test failures do not raise
            :class:`TestFailureError`.
        min_percent: Minimum coverage percentage (0-100). If set and
            coverage is below this, raises
            :class:`CoverageThresholdError`.
        timeout: Optional test timeout in seconds.
        show_uncovered: If True, print per-file uncovered lines and
            branches when coverage is below 100%.

    Returns:
        The :class:`TestResult` from running tests.

    Raises:
        TestFailureError: If tests fail (unless ``no_exit_code`` is True).
        CoverageThresholdError: If coverage is below ``min_percent``.
    """
    project_root = find_project_root()
    output_dir = project_root / config.coverage.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate and write instrumentation plan.
    plan = plan_generator.generate_plan(
        str(project_root),
        config.coverage.exclude,
        config.coverage.test_dirs,
    )
    plan_generator.write_plan_json(plan, str(output_dir / "plan.json"))

    # Run tests with coverage enabled.
    test_error: TestFailureError | None = None
    result: TestResult | None = None
    try:
        result = run_tests(
            config,
            coverage=True,
            min_percent=min_percent,
            suite=suite,
            test_name=test_name,
            junit_xml=junit_xml,
            no_exit_code=no_exit_code,
            timeout=timeout,
            paths=paths,
        )
    except TestFailureError as exc:
        test_error = exc

    # Read coverage data and generate reports (even if tests failed).
    # If tests failed AND coverage data is missing (e.g., GUT crashed
    # before writing coverage.json), re-raise the TestFailureError
    # instead of the CoveragePlanError — the test failure is the root
    # cause and the missing file is just a side effect.
    try:
        data = reporter.read_coverage_json(output_dir / "coverage.json")
        plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))
    except CoveragePlanError:
        if test_error is not None:
            raise test_error
        raise

    min_threshold = min_percent / 100 if min_percent is not None else None
    try:
        report_result = reporter.generate_report(
            plan,
            data,
            output_dir,
            config.coverage.format,
            min_threshold=min_threshold,
        )
    except CoverageThresholdError as exc:
        if exc.report_result is not None:
            _print_coverage_inline(
                exc.report_result.summary,
                min_percent,
                show_uncovered=show_uncovered,
                file_summaries=exc.report_result.file_summaries,
                plan=plan,
            )
        if test_error is not None:
            raise test_error
        raise

    if test_error is not None:
        raise test_error

    # Print coverage inline summary on success.
    _print_coverage_inline(
        report_result.summary,
        min_percent,
        show_uncovered=show_uncovered,
        file_summaries=report_result.file_summaries,
        plan=plan,
    )

    if result is None:
        raise CoveragePlanError(
            "Coverage generation returned no result — "
            "run_tests() returned None without raising TestFailureError. "
            "This should not happen; please report as a bug."
        )
    return result


def generate_coverage_report(
    config: GdToolsConfig,
    report_format: str | None = None,
    output_dir: str | None = None,
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
    return reporter.generate_report(plan, data, output_path, effective_format)


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


def _print_coverage_table(
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


def _print_threshold_footer(
    summary: CoverageSummary, min_percent: int | None = None
) -> None:
    """Print a summary footer with threshold pass/fail status.

    Args:
        summary: The coverage summary to display.
        min_percent: Optional minimum coverage percentage (0-100).
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


def _print_coverage_inline(
    summary: CoverageSummary,
    min_percent: int | None = None,
    show_uncovered: bool = False,
    file_summaries: list[FileSummary] | None = None,
    plan: CoveragePlan | None = None,
) -> None:
    """Print a one-line coverage summary.

    Used by :func:`run_coverage_test` to show coverage after test
    results.  Prints the line and branch coverage percentages followed
    by a summary footer indicating whether the threshold was met.
    When ``show_uncovered`` is True and coverage is below 100%,
    per-file uncovered detail panels are printed below the summary.

    Args:
        summary: The coverage summary to display.
        min_percent: Optional minimum coverage percentage (0-100).
        show_uncovered: If True, print per-file uncovered lines and
            branches panels when coverage is below 100%.
        file_summaries: Per-file summaries for uncovered detail.
            Required when ``show_uncovered`` is True.
        plan: Coverage plan for branch type lookup.  Required when
            ``show_uncovered`` is True.
    """
    line_pct = summary.line_rate * 100
    branch_pct = summary.branch_rate * 100

    output.print_info(
        f"Coverage: {line_pct:.1f}% lines, {branch_pct:.1f}% branches"
    )
    _print_threshold_footer(summary, min_percent)

    if show_uncovered and file_summaries is not None and plan is not None:
        panels = reporter.render_uncovered_panels(file_summaries, plan)
        if panels is not None:
            output.console.print(panels)


def show_coverage_summary(
    config: GdToolsConfig,
    min_percent: int | None = None,
) -> CoverageSummary:
    """Display a terminal summary table of coverage results.

    Reads existing ``plan.json`` and ``coverage.json``, computes a
    summary, prints a Rich table, and optionally enforces a minimum
    threshold.  Per-file uncovered detail panels are always printed
    below the summary when coverage is below 100%.

    Args:
        config: Project configuration.
        min_percent: Minimum coverage percentage (0-100). If set and
            coverage is below this, raises
            :class:`CoverageThresholdError`.

    Returns:
        The :class:`CoverageSummary`.

    Raises:
        CoverageThresholdError: If ``min_percent`` is set and line
            coverage is below the threshold.
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
    _print_coverage_table(summary, min_percent)

    # Print summary footer with threshold status.
    _print_threshold_footer(summary, min_percent)

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

    return summary
