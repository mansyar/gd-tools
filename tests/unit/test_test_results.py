"""Unit tests for the test runner module.

Tests the result models (TestDetail, TestResult) and CLI result
formatting (format_test_results).
"""

from pathlib import Path

import pytest

from rich.console import Console

from gd_tools.test_results import (
    SnapshotSummary,
    TestDetail,
    TestResult,
    build_snapshot_summary,
    format_test_results,
    print_durations_table,
)

# Path to the fixture JUnit XML file.
FIXTURE_JUNIT_XML = (
    Path(__file__).parent.parent / "fixtures" / "junit" / "sample_results.xml"
)

# --- TestDetail dataclass ---


@pytest.mark.unit
def test_test_detail_construction_pass():
    """Test TestDetail construction with status='pass'."""
    detail = TestDetail(
        name="test_addition",
        suite="TestCalculator",
        status="pass",
        message="",
        duration=0.025,
    )
    assert detail.name == "test_addition"
    assert detail.suite == "TestCalculator"
    assert detail.status == "pass"
    assert detail.message == ""
    assert detail.duration == 0.025


@pytest.mark.unit
def test_test_detail_construction_fail():
    """Test TestDetail construction with status='fail' and message."""
    detail = TestDetail(
        name="test_subtraction",
        suite="TestCalculator",
        status="fail",
        message="Expected 5 but got 3",
        duration=0.010,
    )
    assert detail.name == "test_subtraction"
    assert detail.suite == "TestCalculator"
    assert detail.status == "fail"
    assert detail.message == "Expected 5 but got 3"
    assert detail.duration == 0.010


@pytest.mark.unit
def test_test_detail_construction_skip():
    """Test TestDetail construction with status='skip'."""
    detail = TestDetail(
        name="test_skipped",
        suite="TestCalculator",
        status="skip",
        message="Skipped: not implemented yet",
        duration=0.0,
    )
    assert detail.status == "skip"
    assert detail.message == "Skipped: not implemented yet"


# --- TestResult dataclass ---


@pytest.mark.unit
def test_test_result_construction_all_fields():
    """Test TestResult construction with all fields populated."""
    details = [
        TestDetail(
            name="test_one",
            suite="SuiteA",
            status="pass",
            message="",
            duration=0.01,
        ),
        TestDetail(
            name="test_two",
            suite="SuiteA",
            status="fail",
            message="Assertion failed",
            duration=0.02,
        ),
    ]
    result = TestResult(
        total=2,
        passed=1,
        failed=1,
        skipped=0,
        duration=0.03,
        junit_xml_path=Path("/tmp/results.xml"),
        coverage_data_path=Path("/tmp/coverage.json"),
        stdout="Running tests...\nDone.",
        stderr="Warning: something minor.",
        test_details=details,
    )
    assert result.total == 2
    assert result.passed == 1
    assert result.failed == 1
    assert result.skipped == 0
    assert result.duration == 0.03
    assert result.junit_xml_path == Path("/tmp/results.xml")
    assert result.coverage_data_path == Path("/tmp/coverage.json")
    assert result.stdout == "Running tests...\nDone."
    assert result.stderr == "Warning: something minor."
    assert len(result.test_details) == 2
    assert result.test_details[0].name == "test_one"
    assert result.test_details[1].status == "fail"


@pytest.mark.unit
def test_test_result_with_none_paths():
    """Test TestResult with None for junit_xml_path and coverage_data_path."""
    result = TestResult(
        total=0,
        passed=0,
        failed=0,
        skipped=0,
        duration=0.0,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    assert result.junit_xml_path is None
    assert result.coverage_data_path is None
    assert result.test_details == []


@pytest.mark.unit
def test_test_result_holds_multiple_details():
    """Test TestResult can hold multiple TestDetail objects."""
    details = [
        TestDetail(
            name=f"test_{i}",
            suite="Suite",
            status="pass" if i % 2 == 0 else "fail",
            message="" if i % 2 == 0 else "err",
            duration=float(i),
        )
        for i in range(5)
    ]
    result = TestResult(
        total=5,
        passed=3,
        failed=2,
        skipped=0,
        duration=1.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=details,
    )
    assert len(result.test_details) == 5
    assert result.test_details[0].status == "pass"
    assert result.test_details[1].status == "fail"


# --- build_gut_args ---


# --- check_gut_installed ---


# --- parse_junit_xml ---


# --- coverage flag infrastructure ---


# --- format_test_results ---


@pytest.mark.unit
def test_format_test_results_all_pass(capsys):
    """format_test_results with all-passing tests shows table + [OK] message."""
    result = TestResult(
        total=3,
        passed=3,
        failed=0,
        skipped=0,
        duration=0.5,
        junit_xml_path=Path("/fake/results.xml"),
        coverage_data_path=None,
        stdout="Running tests...",
        stderr="",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "3" in captured.out
    assert "[OK]" in captured.out
    assert "All 3 test(s) passed." in captured.out
    # Should NOT print Godot stdout/stderr when no failures.
    assert "Godot stdout" not in captured.out
    assert "Running tests" not in captured.out


@pytest.mark.unit
def test_format_test_results_counts_skipped_separately(capsys):
    """format_test_results must not report skipped tests as passed."""
    result = TestResult(
        total=4,
        passed=1,
        failed=0,
        skipped=3,
        duration=0.5,
        junit_xml_path=Path("/fake/results.xml"),
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "All 4 test(s) passed." not in captured.out
    assert "1 test(s) passed, 3 skipped." in captured.out


@pytest.mark.unit
def test_format_test_results_with_failures(capsys):
    """format_test_results with failures shows table + details + Godot output."""
    result = TestResult(
        total=3,
        passed=2,
        failed=1,
        skipped=0,
        duration=0.5,
        junit_xml_path=Path("/fake/results.xml"),
        coverage_data_path=None,
        stdout="Some output from Godot",
        stderr="Some error from Godot",
        test_details=[
            TestDetail(
                name="test_fail",
                suite="TestSuite",
                status="fail",
                message="assertion failed",
                duration=0.1,
            ),
        ],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "Some output from Godot" in captured.out
    assert "Some error from Godot" in captured.out
    # Per-test failure details.
    assert "✗" in captured.out
    assert "TestSuite.test_fail" in captured.out
    assert "assertion failed" in captured.out
    # Summary footer.
    assert "1 failed" in captured.out


@pytest.mark.unit
def test_format_test_results_truncates_long_output(capsys):
    """format_test_results truncates stdout/stderr > 5000 chars."""
    long_stdout = "x" * 6000
    long_stderr = "y" * 6000
    result = TestResult(
        total=1,
        passed=0,
        failed=1,
        skipped=0,
        duration=0.1,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout=long_stdout,
        stderr=long_stderr,
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "truncated" in captured.out.lower()
    # The full output should NOT be present.
    assert long_stdout not in captured.out


@pytest.mark.unit
def test_format_test_results_reports_artifact_location(capsys):
    """The run artifact index location is discoverable from CLI output."""
    result = TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.1,
        junit_xml_path=None,
        coverage_data_path=None,
        artifact_index_path=Path(
            "C:/project/.gd-tools/artifacts/run-1/artifacts.json"
        ),
        stdout="",
        stderr="",
        test_details=[],
    )

    format_test_results(result)

    output = capsys.readouterr().out
    assert "artifacts.json" in output
    assert "run-1" in output


@pytest.mark.unit
def test_format_test_results_omits_artifact_line_without_index(capsys):
    """Runs without a published index print no artifact line."""
    result = TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.1,
        junit_xml_path=None,
        coverage_data_path=None,
        artifact_index_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )

    format_test_results(result)

    assert "artifacts.json" not in capsys.readouterr().out


@pytest.mark.unit
def test_format_test_results_zero_tests(capsys):
    """format_test_results with zero tests shows 0/0/0/0 and [OK] message."""
    result = TestResult(
        total=0,
        passed=0,
        failed=0,
        skipped=0,
        duration=0.0,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "Test Results" in captured.out
    assert "0" in captured.out
    assert "[OK]" in captured.out


@pytest.mark.unit
def test_format_test_results_color_coding(capsys, monkeypatch):
    """format_test_results uses ANSI color codes for pass/fail."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    result = TestResult(
        total=3,
        passed=2,
        failed=1,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    # ANSI escape codes should be present (force_terminal=True).
    assert "\x1b[" in captured.out


@pytest.mark.unit
def test_format_test_results_failure_details(capsys):
    """format_test_results shows per-test failure details when tests fail."""
    result = TestResult(
        total=2,
        passed=1,
        failed=1,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[
            TestDetail(
                name="test_addition",
                suite="TestCalculator",
                status="pass",
                message="",
                duration=0.1,
            ),
            TestDetail(
                name="test_subtraction",
                suite="TestCalculator",
                status="fail",
                message="Expected 5 but got 3",
                duration=0.2,
            ),
        ],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    # Should show failure details with ✗ marker, suite.name, and message.
    assert "✗" in captured.out
    assert "TestCalculator.test_subtraction" in captured.out
    assert "Expected 5 but got 3" in captured.out
    # Should NOT show passing test details in failure section.
    assert "✗ TestCalculator.test_addition" not in captured.out


@pytest.mark.unit
def test_format_test_results_success_color(capsys, monkeypatch):
    """format_test_results prints [OK] in green when all tests pass."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    result = TestResult(
        total=3,
        passed=3,
        failed=0,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "\x1b[32" in captured.out  # green ANSI code


# --- Verbose mode: command display ---


# --- Verbose mode: timing display ---


# --- Snapshot summary ---


@pytest.mark.unit
def test_snapshot_summary_aggregates_diagnostics(tmp_path):
    """Snapshot counts aggregate across every test's diagnostics."""
    details = [
        TestDetail(
            name="test_first_run_writes_and_passes",
            suite="SuiteA",
            status="pass",
            message="",
            duration=0.1,
            diagnostics={
                "snapshots_written": [
                    "SuiteA/test_first_run_writes_and_passes/s_1"
                ],
            },
        ),
        TestDetail(
            name="test_second",
            suite="SuiteA",
            status="pass",
            message="",
            duration=0.1,
            diagnostics={"snapshots_matched": 2},
        ),
        TestDetail(
            name="test_mismatch",
            suite="SuiteB",
            status="fail",
            message="Snapshot mismatch",
            duration=0.1,
            diagnostics={
                "snapshots_updated": ["SuiteB/test_mismatch/m"],
                "failures": [
                    {
                        "assertion": "assert_snapshot",
                        "message": "Snapshot mismatch",
                    }
                ],
            },
        ),
    ]
    summary = build_snapshot_summary(details, tmp_path)
    assert summary == SnapshotSummary(
        written=1,
        updated=1,
        matched=2,
        failed=1,
        obsolete=[],
    )


@pytest.mark.unit
def test_snapshot_summary_detects_obsolete_snapshots(tmp_path):
    """Stored snapshots whose suite/test no longer ran are obsolete."""
    snapshots_dir = tmp_path / ".gd-tools" / "snapshots"
    kept = snapshots_dir / "SuiteA" / "test_kept"
    kept.mkdir(parents=True)
    (kept / "kept.snap").write_text(
        "# gd-tools snapshot v1\n", encoding="utf-8"
    )
    orphan = snapshots_dir / "SuiteA" / "test_gone"
    orphan.mkdir(parents=True)
    (orphan / "orphan.snap").write_text(
        "# gd-tools snapshot v1\n", encoding="utf-8"
    )
    other_suite = snapshots_dir / "SuiteNeverRan" / "test_x"
    other_suite.mkdir(parents=True)
    (other_suite / "x.snap").write_text(
        "# gd-tools snapshot v1\n", encoding="utf-8"
    )
    details = [
        TestDetail(
            name="test_kept",
            suite="SuiteA",
            status="pass",
            message="",
            duration=0.1,
        ),
    ]
    summary = build_snapshot_summary(details, tmp_path)
    assert summary is not None
    assert summary.obsolete == ["SuiteA/test_gone/orphan.snap"]


@pytest.mark.unit
def test_snapshot_summary_none_without_snapshot_activity(tmp_path):
    """No snapshot diagnostics and no stored snapshots means no summary."""
    details = [
        TestDetail(
            name="test_plain",
            suite="SuiteA",
            status="pass",
            message="",
            duration=0.1,
        ),
    ]
    assert build_snapshot_summary(details, tmp_path) is None


@pytest.mark.unit
def test_format_test_results_prints_snapshot_summary(capsys, tmp_path):
    """Snapshot activity renders as a summary line with obsolete paths."""
    snapshots_dir = (
        tmp_path / ".gd-tools" / "snapshots" / "SuiteA" / "test_gone"
    )
    snapshots_dir.mkdir(parents=True)
    (snapshots_dir / "orphan.snap").write_text(
        "# gd-tools snapshot v1\n", encoding="utf-8"
    )
    details = [
        TestDetail(
            name="test_a",
            suite="SuiteA",
            status="pass",
            message="",
            duration=0.1,
            diagnostics={
                "snapshots_written": ["SuiteA/test_a/a_1"],
                "snapshots_matched": 1,
            },
        ),
    ]
    summary = build_snapshot_summary(details, tmp_path)
    result = TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=details,
        snapshot_summary=summary,
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert (
        "Snapshots: 1 written, 0 updated, 1 matched, 0 failed" in captured.out
    )
    assert "SuiteA/test_gone/orphan.snap" in captured.out


@pytest.mark.unit
def test_format_test_results_omits_snapshot_summary_when_none(capsys):
    """No snapshot activity means no snapshot summary line."""
    result = TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "Snapshots:" not in captured.out


# --- durations table ---


def _durations_result(details):
    """Build a TestResult whose counts derive from the given details."""
    return TestResult(
        total=len(details),
        passed=sum(d.status == "pass" for d in details),
        failed=sum(d.status == "fail" for d in details),
        skipped=sum(d.status == "skip" for d in details),
        duration=sum(d.duration for d in details),
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=list(details),
    )


def _detail(name, duration, status="pass", suite="SuiteA"):
    """Build a TestDetail with terse defaults."""
    return TestDetail(
        name=name,
        suite=suite,
        status=status,
        message="" if status != "fail" else "boom",
        duration=duration,
    )


@pytest.mark.unit
def test_print_durations_table_sorted_slowest_first(capsys):
    """Rows are ordered slowest-first regardless of input order."""
    details = [
        _detail("test_fast", 0.1),
        _detail("test_slowest", 2.0),
        _detail("test_middle", 0.5),
    ]
    print_durations_table(_durations_result(details), 10)
    captured = capsys.readouterr()
    slowest = captured.out.index("test_slowest")
    middle = captured.out.index("test_middle")
    fast = captured.out.index("test_fast")
    assert slowest < middle < fast


@pytest.mark.unit
def test_print_durations_table_truncates_to_n(capsys):
    """--durations N shows only the N slowest tests."""
    details = [_detail(f"test_{i}", float(5 - i)) for i in range(5)]
    print_durations_table(_durations_result(details), 3)
    captured = capsys.readouterr()
    assert "test_0" in captured.out
    assert "test_1" in captured.out
    assert "test_2" in captured.out
    assert "test_3" not in captured.out
    assert "test_4" not in captured.out


@pytest.mark.unit
def test_print_durations_table_zero_lists_all(capsys):
    """--durations 0 lists every executed test, slowest-first."""
    details = [_detail(f"test_{i}", float(i)) for i in range(4)]
    print_durations_table(_durations_result(details), 0)
    captured = capsys.readouterr()
    for i in range(4):
        assert f"test_{i}" in captured.out


@pytest.mark.unit
def test_print_durations_table_shows_all_outcomes(capsys):
    """Pass, fail, and skip rows all appear with their outcome."""
    details = [
        _detail("test_ok", 1.0, status="pass"),
        _detail("test_bad", 2.0, status="fail"),
        _detail("test_skipped", 0.0, status="skip"),
    ]
    print_durations_table(_durations_result(details), 0)
    captured = capsys.readouterr()
    assert "test_ok" in captured.out
    assert "test_bad" in captured.out
    assert "test_skipped" in captured.out
    assert "pass" in captured.out
    assert "fail" in captured.out
    assert "skip" in captured.out


@pytest.mark.unit
def test_print_durations_table_formats_durations(capsys):
    """Durations render as seconds with two decimals."""
    details = [_detail("test_timed", 1.234)]
    print_durations_table(_durations_result(details), 10)
    captured = capsys.readouterr()
    assert "1.23s" in captured.out


@pytest.mark.unit
def test_print_durations_table_no_details_prints_nothing(capsys):
    """A run with no per-test details prints no durations table."""
    print_durations_table(_durations_result([]), 10)
    captured = capsys.readouterr()
    assert "Slowest" not in captured.out


@pytest.mark.unit
def test_print_durations_table_retries_summed_duration(capsys):
    """A retried test's duration (sum of all attempts) renders as-is.

    The native runner already sums per-attempt durations into
    TestDetail.duration; the renderer must display that value unchanged.
    """
    details = [_detail("test_retried", 3.6)]
    print_durations_table(_durations_result(details), 10)
    captured = capsys.readouterr()
    assert "3.60s" in captured.out


@pytest.mark.unit
def test_format_test_results_durations_disabled_by_default(capsys):
    """Without the durations argument the default output is unchanged."""
    details = [_detail("test_only", 0.4)]
    format_test_results(_durations_result(details))
    captured = capsys.readouterr()
    assert "Slowest" not in captured.out


@pytest.mark.unit
def test_format_test_results_durations_before_success_line(capsys):
    """The durations table prints before the success message."""
    details = [_detail("test_only", 0.4)]
    format_test_results(_durations_result(details), 10)
    captured = capsys.readouterr()
    assert captured.out.index("Slowest") < captured.out.index("passed")


@pytest.mark.unit
def test_format_test_results_durations_before_summary_footer(capsys):
    """The durations table prints after failure details, before the footer."""
    details = [
        _detail("test_bad", 2.0, status="fail"),
        _detail("test_ok", 0.1),
    ]
    format_test_results(_durations_result(details), 10)
    captured = capsys.readouterr()
    assert captured.out.index("Slowest") < captured.out.index(
        "1 failed, 1 passed"
    )
