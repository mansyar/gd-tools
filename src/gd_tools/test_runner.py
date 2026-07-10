"""Test runner module for gd-tools.

Orchestrates GUT (Godot Unit Test) via the Godot CLI. Builds the GUT
command line from config, invokes Godot as a subprocess, captures
stdout/stderr, parses JUnit XML output into structured results, and
returns a :class:`TestResult`.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from junitparser import JUnitXml
from rich.console import Console
from rich.table import Table

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

    Returns:
        List of CLI arguments for Godot/GUT.
    """
    args: list[str] = [
        "-s",
        "addons/gut/gut_cmdln.gd",
        "-d",
        "-gexit",
    ]

    # Test directories (comma-separated per GUT 9.x CLI spec).
    if config.test_dirs:
        dirs = ",".join(f"res://{d}/" for d in config.test_dirs)
        args.append(f"-gdir={dirs}")

    # Prefix/suffix for test file discovery.
    args.append(f"-gprefix={config.prefix}")
    args.append(f"-gsuffix={config.suffix}")

    # Suite/script filter (GUT -gselect: scripts containing the
    # specified string in their filename will be run).
    if suite:
        args.append(f"-gselect={suite}")

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


def check_gut_installed(project_root: Path) -> None:
    """Verify that GUT is installed in the project.

    Checks for the existence of ``addons/gut/gut_cmdln.gd`` relative to
    the project root. This runs before any subprocess invocation for
    fast, clear failure feedback.

    Args:
        project_root: Path to the Godot project root directory.

    Raises:
        GUTNotInstalledError: If GUT is not installed (exit code 2).
    """
    gut_script = project_root / "addons" / "gut" / "gut_cmdln.gd"
    if not gut_script.exists():
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
    duration. When tests fail, also prints GUT's stdout and stderr
    for debugging context (truncated to 5000 characters if longer).

    Args:
        result: The :class:`TestResult` to format and print.
    """
    console = Console(force_terminal=True)
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
    console.print(table)

    # On failure, surface GUT stdout/stderr for debugging.
    if result.failed > 0:
        if result.stdout:
            console.print("\n--- GUT stdout ---")
            stdout_text = result.stdout
            if len(stdout_text) > 5000:
                stdout_text = stdout_text[:5000] + "\n... (truncated)"
            console.print(stdout_text)
        if result.stderr:
            console.print("\n--- GUT stderr ---")
            stderr_text = result.stderr
            if len(stderr_text) > 5000:
                stderr_text = stderr_text[:5000] + "\n... (truncated)"
            console.print(stderr_text)


def run_tests(
    config: GdToolsConfig,
    coverage: bool = False,
    min_percent: float | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    timeout: int | None = None,
) -> TestResult:
    """Run GUT tests via the Godot CLI.

    Orchestrates the full test lifecycle: checks GUT is installed,
    finds the Godot binary, builds GUT args, invokes Godot as a
    subprocess, parses the JUnit XML output, and returns a
    :class:`TestResult`.

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

    Returns:
        :class:`TestResult` with totals, per-test details, and
        stdout/stderr from the subprocess.

    Raises:
        GUTNotInstalledError: If GUT is not installed (exit code 2).
        GodotNotFoundError: If the Godot binary cannot be found.
        GdToolsError: If the subprocess times out, Godot exits
            non-zero, or JUnit XML is missing/malformed (exit code 2).
        TestFailureError: If tests fail and ``no_exit_code`` is False
            (exit code 1).
    """
    del min_percent  # Enforcement deferred to Phase 3

    project_root = find_project_root()

    # Check GUT is installed before any subprocess invocation.
    check_gut_installed(project_root)

    # Find the Godot binary.
    godot_info = find_godot(config.godot)

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
    )

    # Set up environment variables for coverage (Phase 3 infrastructure).
    env: dict[str, str] | None = None
    if coverage:
        env = {"GD_TOOLS_COVERAGE_ACTIVE": "1"}

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

    # Handle non-zero exit codes (crash, not test failure).
    if result.returncode != 0:
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
    total, passed, failed, skipped, duration, test_details = parse_junit_xml(
        junit_path
    )

    # Determine coverage data path (Phase 3 infrastructure).
    coverage_data_path: Path | None = None
    if coverage:
        coverage_data_path = (
            project_root / ".gd-tools" / "coverage" / "coverage.json"
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
