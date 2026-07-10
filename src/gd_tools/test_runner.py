"""Test runner module for gd-tools.

Orchestrates GUT (Godot Unit Test) via the Godot CLI. Builds the GUT
command line from config, invokes Godot as a subprocess, captures
stdout/stderr, parses JUnit XML output into structured results, and
returns a :class:`TestResult`.
"""

from dataclasses import dataclass, field
from pathlib import Path


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
