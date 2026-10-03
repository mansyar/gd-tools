"""Test result models shared by the test runtimes.

Defines :class:`TestDetail` and :class:`TestResult`, the result models the
native test runtime maps its protocol results into for CLI reporting.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.table import Table
from rich.text import Text

from gd_tools import output


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
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Aggregated test results from a test run.

    Attributes:
        total: Total number of tests executed.
        passed: Number of passing tests.
        failed: Number of failing tests.
        skipped: Number of skipped tests.
        duration: Total test execution time in seconds.
        junit_xml_path: Path to the JUnit XML file, or None.
        coverage_data_path: Path to coverage data, or None when
            ``--coverage`` not used.
        artifact_index_path: Path to the published native run artifact index,
            or None for runtimes without run artifacts.
        stdout: Test-runner stdout (for debugging/surfacing on failure).
        stderr: Test-runner stderr (for debugging/surfacing on failure).
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
    artifact_index_path: Path | None = None


def format_test_results(result: TestResult) -> None:
    """Print a Rich table summarizing test results.

    Always prints a table with total, passed, failed, skipped, and
    duration. When no test fails, prints a success message that counts
    skipped tests separately rather than folding them into the passed
    total. When tests fail, prints per-test failure details and the
    test runner's stdout and stderr for debugging context (truncated to
    5000 characters if longer), followed by a summary footer.

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

    if result.artifact_index_path is not None:
        output.console.print(
            Text.assemble(
                ("Run artifacts: ", "dim"),
                (str(result.artifact_index_path), "cyan"),
            )
        )

    if result.failed == 0:
        # A skipped test did not run, so counting it as passed would report a
        # suite as fully green when part of it never executed.
        if result.skipped:
            output.print_success(
                f"All {result.passed} test(s) passed, {result.skipped} skipped."
            )
        else:
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
            if detail.diagnostics:
                parts.append(
                    (
                        "\nDiagnostics: "
                        + json.dumps(detail.diagnostics, sort_keys=True),
                        "dim",
                    )
                )
            output.console.print(Text.assemble(*parts))

    # Surface the Godot process output for debugging.
    if result.stdout:
        output.console.print("\n--- Godot stdout ---")
        stdout_text = result.stdout
        if len(stdout_text) > 5000:
            stdout_text = stdout_text[:5000] + "\n... (truncated)"
        output.console.print(stdout_text, markup=False)
    if result.stderr:
        output.console.print("\n--- Godot stderr ---")
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
