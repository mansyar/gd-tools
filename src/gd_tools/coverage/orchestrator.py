"""Coverage orchestrator module.

Coordinates the full coverage flow by wiring together the plan generator,
test runner, and reporter modules.  This is the orchestration layer mandated
by NFR-1 — CLI commands delegate to these functions rather than embedding
business logic directly.
"""

from __future__ import annotations

from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.coverage import plan_generator, reporter
from gd_tools.errors import CoverageThresholdError, TestFailureError
from gd_tools.test_runner import TestResult, run_tests


def run_coverage_test(
    config: GdToolsConfig,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    min_percent: int | None = None,
    timeout: int | None = None,
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
        None,
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
        )
    except TestFailureError as exc:
        test_error = exc

    # Read coverage data and generate reports (even if tests failed).
    data = reporter.read_coverage_json(output_dir / "coverage.json")
    plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))

    min_threshold = min_percent / 100 if min_percent is not None else None
    try:
        reporter.generate_report(
            plan,
            data,
            output_dir,
            config.coverage.format,
            min_threshold=min_threshold,
        )
    except CoverageThresholdError:
        if test_error is not None:
            raise test_error
        raise

    if test_error is not None:
        raise test_error

    assert result is not None  # test_error is None implies run_tests succeeded
    return result
