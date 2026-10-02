"""Unit tests for the test runner module.

Tests the result models (TestDetail, TestResult) and CLI result
formatting (format_test_results).
"""

from pathlib import Path

import pytest

from rich.console import Console

from gd_tools.test_runner import (
    TestDetail,
    TestResult,
    format_test_results,
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
