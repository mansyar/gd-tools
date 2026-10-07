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
from gd_tools.verbosity import Verbosity, get_verbosity
from gd_tools.native_test.flaky import is_flaky


@dataclass
class SnapshotSummary:
    """Aggregated snapshot activity for one test run.

    Attributes:
        written: Number of snapshots auto-written on first sight.
        updated: Number of snapshots rewritten by update mode.
        matched: Number of snapshot comparisons that matched.
        failed: Number of snapshot assertions that failed.
        obsolete: Stored snapshots with no owning test in the run,
            as ``suite/test/name`` paths.
    """

    written: int
    updated: int
    matched: int
    failed: int
    obsolete: list[str]


@dataclass
class TestDetail:
    """Details of a single test case.

    Attributes:
        name: Test method name (e.g., ``"test_addition"``).
        suite: Suite/class name (e.g., ``"TestCalculator"``).
        status: One of ``"pass"``, ``"fail"``, ``"skip"``.
        message: Failure message or empty string on pass/skip.
        duration: Execution time in seconds.
        attempts: Retry attempts the native runtime spent on the test.
        first_failure_message: The first failing attempt's message
            (empty when the test passed on its first attempt).
    """

    __test__ = False

    name: str
    suite: str
    status: str
    message: str
    duration: float
    diagnostics: dict[str, Any] = field(default_factory=dict)
    attempts: int = 1
    first_failure_message: str = ""


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
    snapshot_summary: SnapshotSummary | None = None


def build_snapshot_summary(
    test_details: list[TestDetail],
    project_root: Path,
) -> SnapshotSummary | None:
    """Aggregate snapshot activity from test diagnostics and disk state.

    Counts come from the runner's per-test diagnostics: lists under
    ``snapshots_written`` / ``snapshots_updated``, integers under
    ``snapshots_matched``, and snapshot failures among the recorded
    ``failures`` (assertion ``"assert_snapshot"``). Obsolete snapshots are
    stored files under ``.gd-tools/snapshots/<suite>/<test>/`` whose owning
    suite ran but whose owning test did not.

    Args:
        test_details: Per-test breakdown of the finished run.
        project_root: Project root containing the snapshots directory.

    Returns:
        A :class:`SnapshotSummary`, or ``None`` when the run shows no
        snapshot activity and no obsolete snapshots.
    """
    written = 0
    updated = 0
    matched = 0
    failed = 0
    run_keys: set[tuple[str, str]] = set()
    for detail in test_details:
        run_keys.add((detail.suite, detail.name))
        diagnostics = detail.diagnostics
        written += len(diagnostics.get("snapshots_written", []))
        updated += len(diagnostics.get("snapshots_updated", []))
        matched += int(diagnostics.get("snapshots_matched", 0))
        for failure in diagnostics.get("failures", []):
            if failure.get("assertion") == "assert_snapshot":
                failed += 1

    obsolete = _find_obsolete_snapshots(test_details, project_root)
    if (
        not written
        and not updated
        and not matched
        and not failed
        and not obsolete
    ):
        return None
    return SnapshotSummary(
        written=written,
        updated=updated,
        matched=matched,
        failed=failed,
        obsolete=obsolete,
    )


def _find_obsolete_snapshots(
    test_details: list[TestDetail],
    project_root: Path,
) -> list[str]:
    """List stored snapshots whose owning test did not run.

    Only suites that ran in this run are scanned: snapshots of suites the
    run never touched are simply unvisited, not obsolete.

    Args:
        test_details: Per-test breakdown of the finished run.
        project_root: Project root containing the snapshots directory.

    Returns:
        Obsolete snapshot paths as ``suite/test/name``, sorted.
    """
    snapshots_dir = project_root / ".gd-tools" / "snapshots"
    if not snapshots_dir.is_dir():
        return []
    run_keys = {(detail.suite, detail.name) for detail in test_details}
    ran_suites = {detail.suite for detail in test_details}
    obsolete: list[str] = []
    for suite_dir in sorted(snapshots_dir.iterdir()):
        if not suite_dir.is_dir() or suite_dir.name not in ran_suites:
            continue
        for test_dir in sorted(suite_dir.iterdir()):
            if (
                not test_dir.is_dir()
                or (suite_dir.name, test_dir.name) in run_keys
            ):
                continue
            for snapshot_file in sorted(test_dir.glob("*.snap")):
                obsolete.append(
                    f"{suite_dir.name}/{test_dir.name}/{snapshot_file.name}"
                )
    return obsolete


def _print_snapshot_summary(summary: SnapshotSummary) -> None:
    """Print the snapshot activity line and any obsolete snapshot paths.

    Mirrors the ``Run artifacts:`` dim/cyan rendering so snapshot reporting
    blends into the existing summary block.

    Args:
        summary: Aggregated snapshot counts for the finished run.
    """
    counts = (
        f"{summary.written} written, {summary.updated} updated, "
        f"{summary.matched} matched, {summary.failed} failed"
    )
    output.console.print(
        Text.assemble(("Snapshots: ", "dim"), (counts, "cyan"))
    )
    if summary.obsolete:
        output.console.print(
            Text.assemble(
                ("Obsolete snapshots (not touched by this run):\n", "yellow"),
                ("\n".join(summary.obsolete), "yellow"),
            )
        )


_STATUS_STYLES = {
    "pass": "green",
    "fail": "red",
    "skip": "yellow",
}


def _collapse_message(message: str, limit: int = 120) -> str:
    """Collapse a failure message to its first line, truncated.

    Args:
        message: The raw (possibly multi-line) failure message.
        limit: Maximum rendered length; longer lines are cut and
            closed with an ellipsis.

    Returns:
        The single-line, truncated message (empty when the message is
        blank).
    """
    lines = message.splitlines()
    first_line = lines[0].strip() if lines else ""
    if not first_line:
        return ""
    if len(first_line) > limit:
        return first_line[: limit - 1] + "\u2026"
    return first_line


def _print_flaky_panel(test_details: list[TestDetail]) -> None:
    """Print the flaky-test panel when the run had flaky tests.

    A test is flaky when it ultimately passed but needed more than one
    attempt.  The panel is suppressed entirely when no test qualifies,
    and under QUIET verbosity.

    Args:
        test_details: The run's per-test details.
    """
    flaky = [
        detail
        for detail in test_details
        if is_flaky(detail.status, detail.attempts)
    ]
    if not flaky:
        return
    if get_verbosity() == Verbosity.QUIET:
        return
    output.console.print(
        Text.assemble(
            ("Flaky tests ", "yellow"),
            (f"({len(flaky)}):", "yellow"),
        )
    )
    for detail in flaky:
        output.console.print(
            Text.assemble(
                (f"  {detail.suite}.{detail.name}", ""),
                (f" passed on attempt {detail.attempts}", "dim"),
            )
        )
        message = _collapse_message(detail.first_failure_message)
        if message:
            output.console.print(f"    {message}", markup=False)


def print_durations_table(result: TestResult, n: int) -> None:
    """Print a Rich table of the slowest tests from a finished run.

    Rows cover every executed test (pass, fail, and skip) sorted
    slowest-first. ``n`` limits the table to the N slowest tests;
    ``0`` lists every test. Prints nothing when the run carried no
    per-test details.
    """
    details = sorted(
        result.test_details,
        key=lambda detail: detail.duration,
        reverse=True,
    )
    if n > 0:
        details = details[:n]
    if not details:
        return
    table = Table(title="Slowest Tests")
    table.add_column("Status")
    table.add_column("Suite")
    table.add_column("Test")
    table.add_column("Duration", justify="right")
    for detail in details:
        style = _STATUS_STYLES.get(detail.status, "")
        table.add_row(
            Text(detail.status, style=style),
            detail.suite,
            detail.name,
            f"{detail.duration:.2f}s",
        )
    output.print_table(table)


def format_test_results(
    result: TestResult, durations: int | None = None
) -> None:
    """Print a Rich table summarizing test results.

    Always prints a table with total, passed, failed, skipped, and
    duration. When no test fails, prints a success message that counts
    skipped tests separately rather than folding them into the passed
    total. When tests fail, prints per-test failure details and the
    test runner's stdout and stderr for debugging context (truncated to
    5000 characters if longer), followed by a summary footer.

    Args:
        result: The :class:`TestResult` to format and print.
        durations: Optional count of slowest tests to report near the
            end of the run summary (after failure details when tests
            fail, before the success line otherwise); 0 lists every
            executed test, None disables the durations report.
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

    if result.snapshot_summary is not None:
        _print_snapshot_summary(result.snapshot_summary)

    _print_flaky_panel(result.test_details)

    if result.failed == 0:
        # A skipped test did not run, so counting it as passed would report a
        # suite as fully green when part of it never executed.
        if durations is not None:
            print_durations_table(result, durations)
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

    # Durations report comes after failure details, before the footer.
    if durations is not None:
        print_durations_table(result, durations)

    # Summary footer.
    output.print_summary(
        "fail",
        f"{result.failed} failed, {result.passed} passed, "
        f"{result.skipped} skipped",
    )
