"""Unit tests for the test runner module.

Covers TestResult/TestDetail dataclasses, build_gut_args argument
construction, GUT installation check, JUnit XML parsing, run_tests
orchestration, coverage flag infrastructure, and Rich output.
"""

from pathlib import Path

import pytest

from gd_tools.config import TestConfig
from gd_tools.errors import GUTNotInstalledError
from gd_tools.test_runner import (
    TestDetail,
    TestResult,
    build_gut_args,
    check_gut_installed,
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


@pytest.mark.unit
def test_build_gut_args_base_command():
    """Test base command args: -s, -d, -gexit present."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"))
    assert "-s" in args
    idx = args.index("-s")
    assert args[idx + 1] == "addons/gut/gut_cmdln.gd"
    assert "-d" in args
    assert "-gexit" in args


@pytest.mark.unit
def test_build_gut_args_no_path_flag():
    """Test that --path is NOT in args (handled by run_godot)."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"))
    assert "--path" not in args


@pytest.mark.unit
def test_build_gut_args_test_dirs():
    """Test test dir args: -gdir=res://<dir>/ conversion from config."""
    config = TestConfig(test_dirs=["test"])
    args = build_gut_args(config, Path("/fake/project"))
    assert "-gdir=res://test/" in args


@pytest.mark.unit
def test_build_gut_args_multiple_test_dirs():
    """Test multiple test dirs as comma-separated value."""
    config = TestConfig(test_dirs=["test", "tests"])
    args = build_gut_args(config, Path("/fake/project"))
    assert "-gdir=res://test/,res://tests/" in args


@pytest.mark.unit
def test_build_gut_args_prefix_suffix():
    """Test prefix and suffix args."""
    config = TestConfig(prefix="test_", suffix=".gd")
    args = build_gut_args(config, Path("/fake/project"))
    assert "-gprefix=test_" in args
    assert "-gsuffix=.gd" in args


@pytest.mark.unit
def test_build_gut_args_suite_filter():
    """Test suite filter arg when suite provided."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"), suite="MySuite")
    assert "-gselect=MySuite" in args


@pytest.mark.unit
def test_build_gut_args_no_suite_filter():
    """Test no suite filter when suite not provided."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"))
    assert not any(a.startswith("-gselect") for a in args)


@pytest.mark.unit
def test_build_gut_args_test_name_filter():
    """Test name filter arg when test_name provided."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"), test_name="MyTest")
    assert "-gunit_test_name=MyTest" in args


@pytest.mark.unit
def test_build_gut_args_no_test_name_filter():
    """Test no name filter when test_name not provided."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"))
    assert not any(a.startswith("-gunit_test_name") for a in args)


@pytest.mark.unit
def test_build_gut_args_junit_xml_custom_path(tmp_path):
    """Test custom JUnit XML path is absolute."""
    config = TestConfig()
    custom_path = str(tmp_path / "custom_results.xml")
    args = build_gut_args(config, tmp_path, junit_xml=custom_path)
    junit_args = [a for a in args if a.startswith("-gjunit_xml_file=")]
    assert len(junit_args) == 1
    path_str = junit_args[0].split("=", 1)[1]
    assert Path(path_str).is_absolute()
    assert path_str.endswith("custom_results.xml")


@pytest.mark.unit
def test_build_gut_args_default_junit_xml_path(tmp_path):
    """Test default JUnit XML path is .gd-tools/results.xml under project_root."""
    config = TestConfig()
    args = build_gut_args(config, tmp_path)
    junit_args = [a for a in args if a.startswith("-gjunit_xml_file=")]
    assert len(junit_args) == 1
    path_str = junit_args[0].split("=", 1)[1]
    xml_path = Path(path_str)
    assert xml_path.is_absolute()
    assert ".gd-tools" in xml_path.parts
    assert xml_path.name == "results.xml"


# --- check_gut_installed ---


@pytest.mark.unit
def test_check_gut_installed_present(tmp_path):
    """Test that no error is raised when GUT is installed."""
    gut_path = tmp_path / "addons" / "gut" / "gut_cmdln.gd"
    gut_path.parent.mkdir(parents=True)
    gut_path.touch()
    result = check_gut_installed(tmp_path)
    assert result is None


@pytest.mark.unit
def test_check_gut_installed_missing(tmp_path):
    """Test that GUTNotInstalledError is raised when GUT is not installed."""
    with pytest.raises(GUTNotInstalledError) as exc_info:
        check_gut_installed(tmp_path)
    assert exc_info.value.exit_code == 2
    assert "GUT is not installed" in str(exc_info.value)
    assert "gd-tools init" in str(exc_info.value)
