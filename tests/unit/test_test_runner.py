"""Unit tests for the test runner module.

Covers TestResult/TestDetail dataclasses, build_gut_args argument
construction, GUT installation check, JUnit XML parsing, run_tests
orchestration, coverage flag infrastructure, and Rich output.
"""

import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig, TestConfig
from gd_tools.errors import (
    GdToolsError,
    GUTNotInstalledError,
    GodotNotFoundError,
    TestFailureError,
)
from rich.console import Console

from gd_tools.godot import GodotInfo
from gd_tools.test_runner import (
    TestDetail,
    TestResult,
    build_gut_args,
    check_gut_installed,
    format_test_results,
    parse_junit_xml,
    run_tests,
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


@pytest.mark.unit
def test_build_gut_args_base_command():
    """Test base command args: --headless, -s, -d, -gexit present."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"))
    assert "--headless" in args
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
def test_build_gut_args_suite_strips_res_prefix():
    """build_gut_args strips res:// prefix and directory from suite."""
    config = TestConfig()
    args = build_gut_args(
        config,
        Path("/fake/project"),
        suite="res://test/test_calculator.gd",
    )
    assert "-gselect=test_calculator.gd" in args


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


# --- parse_junit_xml ---


@pytest.mark.unit
def test_parse_junit_xml_valid_totals():
    """Test parsing valid JUnit XML returns correct totals."""
    total, passed, failed, skipped, duration, details = parse_junit_xml(
        FIXTURE_JUNIT_XML
    )
    assert total == 3
    assert passed == 1
    assert failed == 1
    assert skipped == 1
    assert duration == pytest.approx(0.3)
    assert len(details) == 3


@pytest.mark.unit
def test_parse_junit_xml_valid_details():
    """Test parsing valid JUnit XML returns correct per-test details."""
    _, _, _, _, _, details = parse_junit_xml(FIXTURE_JUNIT_XML)

    # First test: passing
    assert details[0].name == "test_addition"
    assert details[0].suite == "TestCalculator"
    assert details[0].status == "pass"
    assert details[0].message == ""
    assert details[0].duration == pytest.approx(0.1)

    # Second test: failing
    assert details[1].name == "test_subtraction"
    assert details[1].suite == "TestCalculator"
    assert details[1].status == "fail"
    assert "Expected 3 but got 2" in details[1].message
    assert details[1].duration == pytest.approx(0.2)

    # Third test: skipped
    assert details[2].name == "test_skipped"
    assert details[2].suite == "TestCalculator"
    assert details[2].status == "skip"
    assert "Not implemented yet" in details[2].message
    assert details[2].duration == pytest.approx(0.0)


@pytest.mark.unit
def test_parse_junit_xml_missing_file(tmp_path):
    """Test that GdToolsError is raised for a missing JUnit XML file."""
    missing_path = tmp_path / "nonexistent.xml"
    with pytest.raises(GdToolsError) as exc_info:
        parse_junit_xml(missing_path)
    assert exc_info.value.exit_code == 2
    assert (
        "not found" in str(exc_info.value).lower()
        or "missing" in str(exc_info.value).lower()
    )


@pytest.mark.unit
def test_parse_junit_xml_malformed(tmp_path):
    """Test that GdToolsError is raised for malformed JUnit XML."""
    malformed_path = tmp_path / "malformed.xml"
    malformed_path.write_text("this is not valid xml <<<<", encoding="utf-8")
    with pytest.raises(GdToolsError) as exc_info:
        parse_junit_xml(malformed_path)
    assert exc_info.value.exit_code == 2
    assert (
        "parse" in str(exc_info.value).lower()
        or "xml" in str(exc_info.value).lower()
    )


@pytest.mark.unit
def test_parse_junit_xml_empty_suite(tmp_path):
    """Test parsing JUnit XML with zero test cases returns zeroed fields."""
    empty_path = tmp_path / "empty.xml"
    empty_path.write_text(
        "<testsuites>\n"
        '  <testsuite name="EmptySuite" tests="0"'
        ' failures="0" errors="0" skipped="0" time="0.0">\n'
        "  </testsuite>\n"
        "</testsuites>\n",
        encoding="utf-8",
    )
    total, passed, failed, skipped, duration, details = parse_junit_xml(
        empty_path
    )
    assert total == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert duration == pytest.approx(0.0)
    assert details == []


# --- run_tests ---


def _make_completed_process(returncode=0, stdout="", stderr=""):
    """Helper: create a CompletedProcess for mocking run_godot."""
    return CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _make_godot_info():
    """Helper: create a GodotInfo for mocking find_godot."""
    return GodotInfo(path="/fake/godot", version="4.5.1", is_valid=True)


@pytest.fixture
def gut_project(tmp_path):
    """Fixture: tmp_path with GUT installed (addons/gut/gut_cmdln.gd)."""
    gut_path = tmp_path / "addons" / "gut" / "gut_cmdln.gd"
    gut_path.parent.mkdir(parents=True)
    gut_path.touch()
    return tmp_path


@pytest.mark.unit
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_gut_not_installed(mock_find_root, tmp_path):
    """run_tests raises GUTNotInstalledError when GUT is missing."""
    mock_find_root.return_value = tmp_path
    config = GdToolsConfig()
    with pytest.raises(GUTNotInstalledError) as exc_info:
        run_tests(config)
    assert exc_info.value.exit_code == 2


@pytest.mark.unit
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_godot_not_found(
    mock_find_root, mock_find_godot, gut_project
):
    """run_tests raises GodotNotFoundError when Godot binary is missing."""
    mock_find_root.return_value = gut_project
    mock_find_godot.side_effect = GodotNotFoundError("Godot not found")
    config = GdToolsConfig()
    with pytest.raises(GodotNotFoundError):
        run_tests(config)


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_calls_run_godot_with_correct_args(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests calls run_godot with correct binary, project, and GUT args."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        stdout="All tests passed", stderr=""
    )
    mock_parse.return_value = (1, 1, 0, 0, 0.1, [])

    run_tests(GdToolsConfig())

    # Two calls: (1) headless import, (2) GUT test run.
    assert mock_run_godot.call_count == 2

    # First call is the headless import.
    import_args = mock_run_godot.call_args_list[0].args
    assert import_args[0] == "/fake/godot"
    assert import_args[1] == gut_project
    assert import_args[2] == ["--headless", "--import"]

    # Second call is the GUT test run.
    gut_args = mock_run_godot.call_args_list[1].args
    assert gut_args[0] == "/fake/godot"
    assert gut_args[1] == gut_project
    assert "--headless" in gut_args[2]
    assert "-s" in gut_args[2]
    assert "addons/gut/gut_cmdln.gd" in gut_args[2]
    assert "-gexit" in gut_args[2]


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_import_nonzero_exit_ignored(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests ignores non-zero exit from the headless import step."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.side_effect = [
        _make_completed_process(
            returncode=1, stdout="", stderr="import warnings"
        ),
        _make_completed_process(returncode=0, stdout="", stderr=""),
    ]
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    result = run_tests(GdToolsConfig())
    assert result is not None


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_captures_stdout_stderr(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests captures stdout and stderr from the subprocess."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        stdout="GUT output here", stderr="Some warnings"
    )
    mock_parse.return_value = (1, 1, 0, 0, 0.1, [])

    result = run_tests(GdToolsConfig())
    assert result.stdout == "GUT output here"
    assert result.stderr == "Some warnings"


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_assembles_test_result(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests assembles TestResult from parsed JUnit data + subprocess."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        stdout="Running tests...", stderr=""
    )
    details = [
        TestDetail(
            name="test_one",
            suite="Suite",
            status="pass",
            message="",
            duration=0.1,
        )
    ]
    mock_parse.return_value = (1, 1, 0, 0, 0.1, details)

    result = run_tests(GdToolsConfig())
    assert result.total == 1
    assert result.passed == 1
    assert result.failed == 0
    assert result.skipped == 0
    assert result.duration == 0.1
    assert result.stdout == "Running tests..."
    assert len(result.test_details) == 1
    assert result.test_details[0].name == "test_one"
    assert result.junit_xml_path is not None


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_all_pass_no_error(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests with all passing tests does not raise TestFailureError."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        stdout="All passed", stderr=""
    )
    mock_parse.return_value = (3, 3, 0, 0, 0.3, [])

    result = run_tests(GdToolsConfig())
    assert result.failed == 0
    assert result.passed == 3


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_failures_raise_test_failure_error(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests raises TestFailureError when tests fail and no_exit_code=False."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        stdout="Tests ran", stderr=""
    )
    mock_parse.return_value = (3, 2, 1, 0, 0.3, [])

    with pytest.raises(TestFailureError) as exc_info:
        run_tests(GdToolsConfig())
    assert exc_info.value.exit_code == 1


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_failures_no_exit_code_true(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests with no_exit_code=True does not raise on test failures."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        stdout="Tests ran", stderr=""
    )
    mock_parse.return_value = (3, 2, 1, 0, 0.3, [])

    result = run_tests(GdToolsConfig(), no_exit_code=True)
    assert result.failed == 1
    assert result.passed == 2


@pytest.mark.unit
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_timeout_raises_gdtools_error(
    mock_find_root, mock_find_godot, mock_run_godot, gut_project
):
    """run_tests raises GdToolsError when Godot subprocess times out."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.side_effect = subprocess.TimeoutExpired(
        cmd=["godot"], timeout=30
    )

    with pytest.raises(GdToolsError) as exc_info:
        run_tests(GdToolsConfig(), timeout=30)
    assert exc_info.value.exit_code == 2
    assert (
        "timeout" in str(exc_info.value).lower()
        or "timed out" in str(exc_info.value).lower()
    )


@pytest.mark.unit
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_nonzero_exit_raises_gdtools_error(
    mock_find_root, mock_find_godot, mock_run_godot, gut_project
):
    """run_tests raises GdToolsError when Godot exits with crash code (>1)."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(
        returncode=2, stdout="", stderr="Godot crashed"
    )

    with pytest.raises(GdToolsError) as exc_info:
        run_tests(GdToolsConfig())
    assert exc_info.value.exit_code == 2


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_creates_gd_tools_dir(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests creates .gd-tools/ directory if it doesn't exist."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(stdout="", stderr="")
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    run_tests(GdToolsConfig())
    assert (gut_project / ".gd-tools").is_dir()


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_sets_junit_xml_path(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """run_tests sets junit_xml_path in TestResult to the resolved XML path."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(stdout="", stderr="")
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    result = run_tests(GdToolsConfig())
    expected_path = (gut_project / ".gd-tools" / "results.xml").resolve()
    assert result.junit_xml_path == expected_path


# --- coverage flag infrastructure ---


@pytest.mark.unit
def test_build_gut_args_coverage_adds_pre_run_script():
    """coverage=True adds -gpre_run_script to GUT args."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"), coverage=True)
    assert any(
        a == "-gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd"
        for a in args
    )


@pytest.mark.unit
def test_build_gut_args_coverage_adds_post_run_script():
    """coverage=True adds -gpost_run_script to GUT args."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"), coverage=True)
    assert any(
        a == "-gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd"
        for a in args
    )


@pytest.mark.unit
def test_build_gut_args_no_coverage_no_hook_scripts():
    """coverage=False does not add hook script args."""
    config = TestConfig()
    args = build_gut_args(config, Path("/fake/project"), coverage=False)
    assert not any(a.startswith("-gpre_run_script") for a in args)
    assert not any(a.startswith("-gpost_run_script") for a in args)


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_coverage_sets_env_var(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """coverage=True sets GD_TOOLS_COVERAGE_ACTIVE=1 in subprocess env."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(stdout="", stderr="")
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    run_tests(GdToolsConfig(), coverage=True)

    call_args = mock_run_godot.call_args
    env = call_args.kwargs.get("env")
    assert env is not None
    assert env.get("GD_TOOLS_COVERAGE_ACTIVE") == "1"


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_no_coverage_no_env_var(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """coverage=False does not set coverage env vars."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(stdout="", stderr="")
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    run_tests(GdToolsConfig(), coverage=False)

    call_args = mock_run_godot.call_args
    env = call_args.kwargs.get("env")
    assert env is None


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_coverage_sets_coverage_data_path(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """coverage=True sets coverage_data_path in TestResult."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(stdout="", stderr="")
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    result = run_tests(GdToolsConfig(), coverage=True)
    expected_path = gut_project / ".gd-tools" / "coverage" / "coverage.json"
    assert result.coverage_data_path == expected_path


@pytest.mark.unit
@patch("gd_tools.test_runner.parse_junit_xml")
@patch("gd_tools.test_runner.run_godot")
@patch("gd_tools.test_runner.find_godot")
@patch("gd_tools.test_runner.find_project_root")
def test_run_tests_no_coverage_coverage_data_path_none(
    mock_find_root,
    mock_find_godot,
    mock_run_godot,
    mock_parse,
    gut_project,
):
    """coverage=False sets coverage_data_path to None."""
    mock_find_root.return_value = gut_project
    mock_find_godot.return_value = _make_godot_info()
    mock_run_godot.return_value = _make_completed_process(stdout="", stderr="")
    mock_parse.return_value = (0, 0, 0, 0, 0.0, [])

    result = run_tests(GdToolsConfig(), coverage=False)
    assert result.coverage_data_path is None


# --- format_test_results ---


@pytest.mark.unit
def test_format_test_results_all_pass(capsys):
    """format_test_results with all-passing tests shows table, no GUT output."""
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
    # Should NOT print GUT stdout/stderr when no failures.
    assert "GUT stdout" not in captured.out
    assert "Running tests" not in captured.out


@pytest.mark.unit
def test_format_test_results_with_failures(capsys):
    """format_test_results with failures shows table + GUT output."""
    result = TestResult(
        total=3,
        passed=2,
        failed=1,
        skipped=0,
        duration=0.5,
        junit_xml_path=Path("/fake/results.xml"),
        coverage_data_path=None,
        stdout="Some output from GUT",
        stderr="Some error from GUT",
        test_details=[],
    )
    format_test_results(result)
    captured = capsys.readouterr()
    assert "Some output from GUT" in captured.out
    assert "Some error from GUT" in captured.out


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
def test_format_test_results_zero_tests(capsys):
    """format_test_results with zero tests shows 0/0/0/0."""
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


@pytest.mark.unit
def test_format_test_results_color_coding(capsys):
    """format_test_results uses ANSI color codes for pass/fail."""
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
    format_test_results(result, console=Console(force_terminal=True))
    captured = capsys.readouterr()
    # ANSI escape codes should be present (force_terminal=True).
    assert "\x1b[" in captured.out
