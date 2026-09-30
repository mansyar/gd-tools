"""Unit tests for actionable exit-2 diagnostics on native test failures."""

import json
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gd_tools.errors import GdToolsError
from gd_tools.native_test.command import (
    _raise_for_native_error,
    run_native_test_command,
)
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.protocol import (
    NativeRunResult,
    NativeSuite,
    NativeTest,
    NativeTestResult,
)

pytestmark = pytest.mark.unit


def _suite(name: str) -> NativeSuite:
    return NativeSuite(
        name=name,
        path=f"res://test/{name.lower()}_test.gd",
        tests=[NativeTest(name="test_example")],
    )


def _write_result(result_path: Path) -> None:
    """Write a minimal protocol v2 result JSON the runner would produce."""
    result_path.write_text(
        json.dumps(
            {
                "protocol_version": 2,
                "run_id": "test-run",
                "status": "passed",
                "engine_warnings": [],
                "diagnostics": {},
                "tests": [
                    {
                        "suite": "FirstSuite",
                        "name": "test_example",
                        "status": "passed",
                        "duration_seconds": 0.01,
                        "attempts": 1,
                        "message": "",
                        "diagnostics": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _diagnostic(test) -> dict:
    """Return the structured diagnostics of the single process-error test."""
    process_tests = [t for t in test if t.name == "<process>"]
    assert len(process_tests) == 1
    return process_tests[0].diagnostics


def test_timeout_diagnostic_names_suite_and_remedy(tmp_path):
    """A suite timeout states the limit and how to raise it."""
    attempts = []

    def fake_run(args, **kwargs):
        attempts.append(args)
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs["timeout"])

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("SlowSuite")],
            godot_binary="godot",
            process_timeout=12.0,
        )

    assert result.status == "error"
    diagnostic = _diagnostic(result.tests)
    assert "SlowSuite" in result.tests[0].message
    assert "12" in result.tests[0].message
    assert diagnostic["expected"] == "completion within 12s"
    assert diagnostic["found"] == "timeout"
    assert "timeout" in diagnostic["remedy"]


def test_missing_result_diagnostic_points_to_engine_log(tmp_path):
    """A crashed engine run directs the user to the artifact engine log."""

    def fake_run(args, **kwargs):
        return CompletedProcess(args, 3, "engine stdout", "engine stderr")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("CrashSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    diagnostic = _diagnostic(result.tests)
    assert diagnostic["kind"] == "engine"
    assert "log" in diagnostic["remedy"]


def test_invalid_result_diagnostic_is_protocol(tmp_path):
    """An unparseable result file is reported as a protocol failure."""

    def fake_run(args, **kwargs):
        target = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        target.write_text("{not json", encoding="utf-8")
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("BrokenSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    diagnostic = _diagnostic(result.tests)
    assert diagnostic["kind"] == "protocol"
    assert "protocol" in diagnostic["remedy"]


def test_returncode_mismatch_states_expected_and_found(tmp_path):
    """A runner/exit-code disagreement reports both sides explicitly."""

    def fake_run(args, **kwargs):
        target = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(target)
        return CompletedProcess(args, 1, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("MismatchSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    diagnostic = _diagnostic(result.tests)
    assert diagnostic["expected"] == "exit code 0 for status 'passed'"
    assert diagnostic["found"] == "exit code 1"


def test_godot_version_error_names_remedy(tmp_path):
    """An unsupported Godot version suggests the configuration fix."""

    def invalid_godot(config):
        return SimpleNamespace(path="godot", version="4.3", is_valid=False)

    with patch(
        "gd_tools.native_test.command.find_godot", side_effect=invalid_godot
    ):
        with patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ):
            with pytest.raises(GdToolsError) as excinfo:
                run_native_test_command(_config())

    message = str(excinfo.value)
    assert "4.5+" in message
    assert "gd-tools.toml" in message or "install" in message.lower()


def test_error_summary_includes_remedy():
    """The aggregate exit-2 error carries the first actionable remedy."""
    result = NativeRunResult(
        run_id="run-1",
        status="error",
        tests=[
            _process_error_with_remedy(
                "Godot process timed out", "raise --timeout"
            )
        ],
        coverage_data_path=None,
        artifact_index_path=None,
        engine_warnings=[],
        diagnostics={},
        stdout="",
        stderr="",
    )

    with pytest.raises(GdToolsError) as excinfo:
        _raise_for_native_error(result)

    assert "Remedy:" in str(excinfo.value)
    assert "raise --timeout" in str(excinfo.value)


def _config():
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


def _process_error_with_remedy(message: str, remedy: str):
    return NativeTestResult(
        suite="ExampleSuite",
        name="<process>",
        status="error",
        message=message,
        diagnostics={"kind": "process", "remedy": remedy},
    )
