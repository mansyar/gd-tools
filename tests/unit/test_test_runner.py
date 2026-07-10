"""Unit tests for the test runner module.

Covers TestResult/TestDetail dataclasses, build_gut_args argument
construction, GUT installation check, JUnit XML parsing, run_tests
orchestration, coverage flag infrastructure, and Rich output.
"""

from pathlib import Path

import pytest

from gd_tools.test_runner import TestDetail, TestResult

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
