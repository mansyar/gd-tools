"""Test runner module for gd-tools.

Orchestrates GUT (Godot Unit Test) via the Godot CLI. Builds the GUT
command line from config, invokes Godot as a subprocess, captures
stdout/stderr, parses JUnit XML output into structured results, and
returns a :class:`TestResult`.
"""

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from junitparser import JUnitXml
from rich.table import Table
from rich.text import Text

from gd_tools import output
from gd_tools.config import GdToolsConfig, TestConfig, find_project_root
from gd_tools.errors import (
    GdToolsError,
    GUTNotInstalledError,
    TestFailureError,
)
from gd_tools.godot import find_godot, run_godot


@dataclass
class TestDetail:
    """Details of a single test case.

    Attributes:
        name: Test method name (e.g., ``"test_addition"``).
        suite: Suite/class name (e.g., ``"TestCalculator"``).
        status: One of ``"pass"``, ``"fail"``, ``"skip"``.
        message: Failure message or empty string on pass/skip.
        duration: Execution time in seconds.
    """

    __test__ = False

    name: str
    suite: str
    status: str
    message: str
    duration: float


@dataclass
class TestResult:
    """Aggregated test results from a GUT run.

    Attributes:
        total: Total number of tests executed.
        passed: Number of passing tests.
        failed: Number of failing tests.
        skipped: Number of skipped tests.
        duration: Total test execution time in seconds.
        junit_xml_path: Path to the JUnit XML file, or None.
        coverage_data_path: Path to coverage data, or None when
            ``--coverage`` not used.
        stdout: GUT stdout (for debugging/surfacing on failure).
        stderr: GUT stderr (for debugging/surfacing on failure).
        test_details: Per-test breakdown.
    """

    __test__ = False

    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
    junit_xml_path: Path | None
    coverage_data_path: Path | None
    stdout: str
    stderr: str
    test_details: list[TestDetail] = field(default_factory=list)


def build_gut_args(
    config: TestConfig,
    project_root: Path,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    coverage: bool = False,
    paths: list[str] | None = None,
) -> list[str]:
    """Build GUT CLI arguments from test configuration.

    Constructs the argument list for invoking GUT via ``run_godot()``.
    The ``--path`` flag is added by ``run_godot()`` itself and is NOT
    included here.

    Args:
        config: Test configuration (test_dirs, prefix, suffix).
        project_root: Path to the Godot project root directory.
        suite: Optional suite/script filter (maps to GUT ``-gselect``).
        test_name: Optional test name filter (maps to GUT
            ``-gunit_test_name``).
        junit_xml: Optional JUnit XML output path. Defaults to
            ``<project_root>/.gd-tools/results.xml``.
        coverage: Whether coverage hooks should be included. When True,
            adds ``-gpre_run_script`` and ``-gpost_run_script`` args.
        paths: Optional test directories that override
            ``config.test_dirs`` for this invocation.

    Returns:
        List of CLI arguments for Godot/GUT.
    """
    args: list[str] = [
        "--headless",
        "-s",
        "addons/gut/gut_cmdln.gd",
        "-gexit",
    ]

    # Test directories (comma-separated per GUT 9.x CLI spec).
    # Use paths override if provided, otherwise fall back to config.
    test_dirs = paths if paths else config.test_dirs
    if test_dirs:
        dirs = ",".join(f"res://{d}/" for d in test_dirs)
        args.append(f"-gdir={dirs}")

    # Prefix/suffix for test file discovery.
    args.append(f"-gprefix={config.prefix}")
    args.append(f"-gsuffix={config.suffix}")

    # Suite/script filter (GUT -gselect: matches against the script
    # filename, not the full res:// path. Strip any res:// prefix
    # and directory components so -gselect receives just the filename.
    if suite:
        select_name = suite
        if select_name.startswith("res://"):
            select_name = select_name[len("res://") :]
        select_name = Path(select_name).name
        args.append(f"-gselect={select_name}")

    # Test name filter (GUT -gunit_test_name: tests containing the
    # specified text will be run, others skipped).
    if test_name:
        args.append(f"-gunit_test_name={test_name}")

    # JUnit XML output path (must be absolute — GUT may treat
    # relative paths as user://-relative).
    if junit_xml:
        xml_path = Path(junit_xml).resolve()
    else:
        xml_path = (project_root / ".gd-tools" / "results.xml").resolve()
    args.append(f"-gjunit_xml_file={xml_path}")

    # Coverage hooks (pre/post run scripts for hybrid coverage system).
    if coverage:
        args.append(
            "-gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd"
        )
        args.append(
            "-gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd"
        )

    return args


def is_gut_installed(project_root: Path) -> bool:
    """Check if GUT is installed in the project.

    Checks for the existence of ``addons/gut/gut.gd`` relative to
    the project root.

    Args:
        project_root: Path to the Godot project root directory.

    Returns:
        True if GUT is installed, False otherwise.
    """
    return (project_root / "addons" / "gut" / "gut.gd").exists()


def check_gut_installed(project_root: Path) -> None:
    """Verify that GUT is installed in the project.

    Checks for the existence of ``addons/gut/gut.gd`` relative to
    the project root. This runs before any subprocess invocation for
    fast, clear failure feedback.

    Args:
        project_root: Path to the Godot project root directory.

    Raises:
        GUTNotInstalledError: If GUT is not installed (exit code 2).
    """
    if not is_gut_installed(project_root):
        raise GUTNotInstalledError(
            "GUT is not installed. Run `gd-tools init` to install it."
        )


def parse_junit_xml(
    path: Path,
) -> tuple[int, int, int, int, float, list[TestDetail]]:
    """Parse a JUnit XML file into structured test results.

    Uses ``junitparser`` to read a JUnit-format XML file (produced by
    GUT's ``-gjunit_xml_file`` flag) and extract aggregate totals plus
    per-test details.

    Args:
        path: Path to the JUnit XML file.

    Returns:
        A tuple of ``(total, passed, failed, skipped, duration,
        test_details)`` where ``duration`` is the summed test-case time
        in seconds and ``test_details`` is a list of
        :class:`TestDetail` objects.

    Raises:
        GdToolsError: If the file is missing, empty, or contains
            malformed XML (exit code 2).
    """
    if not path.exists():
        raise GdToolsError(f"JUnit XML file not found: {path}")

    try:
        xml = JUnitXml.fromfile(str(path))
    except Exception as exc:
        raise GdToolsError(f"Failed to parse JUnit XML file: {path}") from exc

    total = 0
    passed = 0
    failed = 0
    skipped = 0
    duration = 0.0
    test_details: list[TestDetail] = []

    for suite in xml:
        suite_name = suite.name or ""
        for tc in suite:
            total += 1
            tc_time = tc.time if tc.time is not None else 0.0
            duration += tc_time

            results = tc.result
            if tc.is_failure or tc.is_error:
                status = "fail"
                failed += 1
            elif tc.is_skipped:
                status = "skip"
                skipped += 1
            else:
                status = "pass"
                passed += 1

            message = ""
            if results and results[0].message:
                message = str(results[0].message)

            detail = TestDetail(
                name=tc.name or "",
                suite=tc.classname or suite_name,
                status=status,
                message=message,
                duration=tc_time,
            )
            test_details.append(detail)

    return (total, passed, failed, skipped, duration, test_details)


def format_test_results(result: TestResult) -> None:
    """Print a Rich table summarizing test results.

    Always prints a table with total, passed, failed, skipped, and
    duration. When all tests pass, prints a success message. When
    tests fail, prints per-test failure details and GUT's stdout and
    stderr for debugging context (truncated to 5000 characters if
    longer), followed by a summary footer.

    Args:
        result: The :class:`TestResult` to format and print.
    """
    table = Table(title="Test Results")
    table.add_column("Total", justify="right")
    table.add_column("Passed", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Skipped", justify="right", style="yellow")
    table.add_column("Duration", justify="right")
    table.add_row(
        str(result.total),
        str(result.passed),
        str(result.failed),
        str(result.skipped),
        f"{result.duration:.2f}s",
    )
    output.print_table(table)

    if result.failed == 0:
        output.print_success(f"All {result.total} test(s) passed.")
        return

    # Print per-test failure details.
    for detail in result.test_details:
        if detail.status == "fail":
            parts = [
                ("✗ ", "red"),
                (f"{detail.suite}.{detail.name}", ""),
            ]
            if detail.message:
                parts.append((f": {detail.message}", ""))
            output.console.print(Text.assemble(*parts))

    # Surface GUT stdout/stderr for debugging.
    if result.stdout:
        output.console.print("\n--- GUT stdout ---")
        stdout_text = result.stdout
        if len(stdout_text) > 5000:
            stdout_text = stdout_text[:5000] + "\n... (truncated)"
        output.console.print(stdout_text, markup=False)
    if result.stderr:
        output.console.print("\n--- GUT stderr ---")
        stderr_text = result.stderr
        if len(stderr_text) > 5000:
            stderr_text = stderr_text[:5000] + "\n... (truncated)"
        output.console.print(stderr_text, markup=False)

    # Summary footer.
    output.print_summary(
        "fail",
        f"{result.failed} failed, {result.passed} passed, "
        f"{result.skipped} skipped",
    )


def run_tests(
    config: GdToolsConfig,
    coverage: bool = False,
    min_percent: float | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    timeout: int | None = 300,
    paths: list[str] | None = None,
) -> TestResult:
    """Run GUT tests via the Godot CLI.

    Orchestrates the full test lifecycle: checks GUT is installed,
    finds the Godot binary, runs a headless import to register GUT
    class names, builds GUT args, invokes Godot as a subprocess,
    parses the JUnit XML output, and returns a :class:`TestResult`.

    Args:
        config: Project configuration (godot, test, coverage sections).
        coverage: If True, set coverage env vars and add hook script
            args. Hook args are added in ``build_gut_args``.
        min_percent: Coverage threshold. Stored but not enforced
            (enforcement deferred to Phase 3).
        suite: Optional suite/script filter (GUT ``-gselect``).
        test_name: Optional test name filter (GUT
            ``-gunit_test_name``).
        junit_xml: Optional JUnit XML output path. Defaults to
            ``<project_root>/.gd-tools/results.xml``.
        no_exit_code: If True, always return normally even when tests
            fail (for CI pipelines). If False, raises
            :class:`TestFailureError` on test failures.
        timeout: Optional timeout in seconds for the Godot subprocess.
            Defaults to 300 (5 minutes). Pass ``None`` to disable.

    Returns:
        :class:`TestResult` with totals, per-test details, and
        stdout/stderr from the subprocess.

    Raises:
        GUTNotInstalledError: If GUT is not installed (exit code 2).
        GodotNotFoundError: If the Godot binary cannot be found.
        GdToolsError: If the subprocess times out, Godot exits with a
            crash code (>1), or JUnit XML is missing/malformed
            (exit code 2).
        TestFailureError: If tests fail and ``no_exit_code`` is False
            (exit code 1).
    """
    # min_percent is accepted for API compatibility; enforcement deferred to Phase 3.

    project_root = find_project_root()

    # Check GUT is installed before any subprocess invocation.
    check_gut_installed(project_root)

    # Find the Godot binary.
    godot_info = find_godot(config.godot)

    # Run headless import to register GUT class names. Required for
    # fresh projects without a .godot/ cache. Non-zero exit codes are
    # ignored — Godot may emit warnings during import.
    try:
        run_godot(
            godot_info.path,
            project_root,
            ["--headless", "--import"],
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise GdToolsError(f"Godot import timed out after {timeout}s")

    # Ensure .gd-tools/ directory exists for JUnit XML output.
    results_dir = project_root / ".gd-tools"
    results_dir.mkdir(exist_ok=True)

    # Build GUT CLI arguments.
    args = build_gut_args(
        config.test,
        project_root,
        suite=suite,
        test_name=test_name,
        junit_xml=junit_xml,
        coverage=coverage,
        paths=paths,
    )

    # Set up environment variables for coverage.
    env: dict[str, str] | None = None
    if coverage:
        coverage_dir = project_root / config.coverage.output_dir
        coverage_dir.mkdir(parents=True, exist_ok=True)
        plan_path = (coverage_dir / "plan.json").resolve()
        output_path = (coverage_dir / "coverage.json").resolve()
        env = {
            "GD_TOOLS_COVERAGE_PLAN": os.environ.get(
                "GD_TOOLS_COVERAGE_PLAN", str(plan_path)
            ),
            "GD_TOOLS_COVERAGE_OUTPUT": os.environ.get(
                "GD_TOOLS_COVERAGE_OUTPUT", str(output_path)
            ),
        }

    # Run Godot with GUT.
    try:
        result = run_godot(
            godot_info.path,
            project_root,
            args,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise GdToolsError(f"Godot/GUT timed out after {timeout}s")

    # Handle crash exit codes (>1). Exit code 1 means tests ran but
    # some failed — proceed to parse JUnit XML for details.
    if result.returncode > 1:
        raise GdToolsError(
            f"Godot exited with code {result.returncode}: "
            f"{result.stderr.strip()}"
        )

    # Determine the JUnit XML path.
    if junit_xml:
        junit_path = Path(junit_xml).resolve()
    else:
        junit_path = (project_root / ".gd-tools" / "results.xml").resolve()

    # Parse JUnit XML output.
    try:
        total, passed, failed, skipped, duration, test_details = (
            parse_junit_xml(junit_path)
        )
    except GdToolsError:
        if not junit_path.exists():
            # JUnit XML wasn't created — GUT likely crashed before
            # completing. Include Godot output for diagnostics.
            stdout_tail = result.stdout[-2000:] if result.stdout else ""
            stderr_full = result.stderr if result.stderr else ""
            raise GdToolsError(
                f"JUnit XML file not found: {junit_path}\n"
                f"Godot exit code: {result.returncode}\n"
                f"Godot stdout (last 2000 chars):\n{stdout_tail}\n"
                f"Godot stderr:\n{stderr_full}"
            ) from None
        raise

    # Determine coverage data path.
    coverage_data_path: Path | None = None
    if coverage:
        coverage_data_path = (
            project_root / config.coverage.output_dir / "coverage.json"
        )

    # Build TestResult from parsed data and subprocess output.
    test_result = TestResult(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration=duration,
        junit_xml_path=junit_path,
        coverage_data_path=coverage_data_path,
        stdout=result.stdout,
        stderr=result.stderr,
        test_details=test_details,
    )

    # Print Rich summary table (always, on every run).
    format_test_results(test_result)

    # Raise TestFailureError if tests failed and no_exit_code is False.
    if failed > 0 and not no_exit_code:
        raise TestFailureError(f"{failed} test(s) failed")

    return test_result
