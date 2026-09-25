"""Unit tests for the native test CLI adapter."""

import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gd_tools.errors import (
    ConfigError,
    CoverageThresholdError,
    GdToolsError,
    TestFailureError,
)
from gd_tools.native_test.command import (
    _test_directories,
    run_native_test_command,
)
from gd_tools.native_test.protocol import (
    NativeRunResult,
    NativeSuite,
    NativeTestResult,
)
from gd_tools.test_runner import TestResult

pytestmark = pytest.mark.unit


def _native_result(
    status: str = "passed",
    tests: list[NativeTestResult] | None = None,
) -> NativeRunResult:
    return NativeRunResult(
        run_id="run-1",
        status=status,
        tests=(
            tests
            if tests is not None
            else [
                NativeTestResult(
                    suite="ExampleSuite", name="test_ok", status="passed"
                )
            ]
        ),
    )


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        godot=SimpleNamespace(),
        test=SimpleNamespace(
            test_dirs=["test"],
            timeout_seconds=5.0,
            retries=0,
            tags=[],
        ),
        coverage=SimpleNamespace(
            output_dir=".gd-tools/coverage",
            exclude=[],
            test_dirs=["test"],
            format="text",
        ),
    )


def test_test_directories_preserves_explicit_file_selector(tmp_path):
    """The adapter keeps an explicit file path exact for discovery."""
    selected = tmp_path / "test" / "selected.gd"
    selected.parent.mkdir(parents=True)
    selected.touch()

    assert _test_directories(tmp_path, [str(selected)], _config()) == [
        str(selected)
    ]


def test_to_test_result_normalizes_statuses_and_writes_junit(tmp_path):
    """Native statuses map to the existing TestResult contract and JUnit XML."""
    from gd_tools.native_test.command import _to_test_result

    native = _native_result(
        "failed",
        [
            NativeTestResult(
                suite="ExampleSuite",
                name="test_pass",
                status="passed",
                duration_seconds=0.1,
            ),
            NativeTestResult(
                suite="ExampleSuite",
                name="test_fail",
                status="failed",
                duration_seconds=0.2,
                message="expected true",
            ),
            NativeTestResult(
                suite="ExampleSuite",
                name="test_skip",
                status="skipped",
                duration_seconds=0.0,
            ),
        ],
    )

    result = _to_test_result(native, tmp_path, str(tmp_path / "results.xml"))

    assert isinstance(result, TestResult)
    assert (result.total, result.passed, result.failed, result.skipped) == (
        3,
        1,
        1,
        1,
    )
    assert [detail.status for detail in result.test_details] == [
        "pass",
        "fail",
        "skip",
    ]
    root = ET.parse(tmp_path / "results.xml").getroot()
    assert root.find("testsuite").attrib["tests"] == "3"
    assert root.find("testsuite/testcase/failure") is not None
    assert root.find("testsuite/testcase[3]/skipped") is not None


def test_run_native_command_propagates_filters_and_timeout(tmp_path):
    """The adapter passes discovery filters and the process timeout through."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result()
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=SimpleNamespace(
                path="godot", version="4.7", is_valid=True
            ),
        ),
        patch("gd_tools.native_test.command._import_project"),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[suite],
        ) as discover,
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        result = run_native_test_command(
            _config(),
            suite="ExampleSuite",
            test_name="test_ok",
            tags=["smoke"],
            test_timeout=1.5,
            timeout=42,
        )

    assert result.failed == 0
    discover.assert_called_once_with(
        tmp_path,
        ["test"],
        suite="ExampleSuite",
        test="test_ok",
        tags=["smoke"],
        timeout_seconds=1.5,
        retries=0,
    )
    assert run.call_args.kwargs["process_timeout"] == 42.0
    assert run.call_args.kwargs["coverage"] is None


def test_run_native_command_empty_suites_gives_gut_guidance(tmp_path):
    """A GUT-only or empty project gets actionable runtime guidance."""
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=SimpleNamespace(
                path="godot", version="4.7", is_valid=True
            ),
        ),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[],
        ),
    ):
        with pytest.raises(ConfigError, match=r"--runtime gut"):
            run_native_test_command(_config())


def test_run_native_command_raises_failure_unless_no_exit_code(tmp_path):
    """Test failures preserve the existing exit-code contract."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "failed",
        [
            NativeTestResult(
                suite="ExampleSuite", name="test_fail", status="failed"
            )
        ],
    )
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=SimpleNamespace(
                path="godot", version="4.7", is_valid=True
            ),
        ),
        patch("gd_tools.native_test.command._import_project"),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        with pytest.raises(TestFailureError):
            run_native_test_command(_config())
        result = run_native_test_command(_config(), no_exit_code=True)

    assert result.failed == 1


def test_run_native_command_prioritizes_test_failure_over_coverage_threshold(
    tmp_path,
):
    """A test failure remains the primary error when coverage also fails."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "failed",
        [
            NativeTestResult(
                suite="ExampleSuite", name="test_fail", status="failed"
            )
        ],
    )
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=SimpleNamespace(
                path="godot", version="4.7", is_valid=True
            ),
        ),
        patch("gd_tools.native_test.command._import_project"),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
        patch(
            "gd_tools.native_test.command._generate_native_report",
            side_effect=CoverageThresholdError("below threshold"),
        ),
    ):
        with pytest.raises(TestFailureError):
            run_native_test_command(_config(), coverage=True, min_percent=100)


def test_run_native_command_raises_infrastructure_error(tmp_path):
    """A native runtime error maps to the configuration exit class."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "error",
        [
            NativeTestResult(
                suite="ExampleSuite", name="<process>", status="error"
            )
        ],
    )
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=SimpleNamespace(
                path="godot", version="4.7", is_valid=True
            ),
        ),
        patch("gd_tools.native_test.command._import_project"),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
    ):
        with pytest.raises(GdToolsError, match="infrastructure"):
            run_native_test_command(_config())
