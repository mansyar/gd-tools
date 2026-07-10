"""Test runner module for gd-tools.

Orchestrates GUT (Godot Unit Test) via the Godot CLI. Builds the GUT
command line from config, invokes Godot as a subprocess, captures
stdout/stderr, parses JUnit XML output into structured results, and
returns a :class:`TestResult`.
"""

from dataclasses import dataclass, field
from pathlib import Path

from junitparser import JUnitXml

from gd_tools.config import TestConfig
from gd_tools.errors import GdToolsError, GUTNotInstalledError


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
        coverage: Whether coverage hooks should be included. Currently
            unused (Phase 3 infrastructure).

    Returns:
        List of CLI arguments for Godot/GUT.
    """
    del coverage  # Phase 3 will implement coverage hook args

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
