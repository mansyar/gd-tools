"""Unit tests for native suite process orchestration."""

import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.protocol import NativeSuite, NativeTest

pytestmark = pytest.mark.unit


def _suite(name: str) -> NativeSuite:
    return NativeSuite(
        name=name,
        path=f"res://test/{name.lower()}_test.gd",
        tests=[NativeTest(name="test_example")],
    )


def _write_result(result_path: Path, status: str = "passed") -> None:
    result_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "run_id": "test-run",
                "status": status,
                "tests": [
                    {
                        "suite": "ExampleSuite",
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


def test_run_native_tests_uses_one_process_per_suite(tmp_path):
    """Each suite gets its own manifest and Godot process."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        manifest = json.loads(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
        )
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        assert len(manifest["suites"]) == 1
        return CompletedProcess(args, 0, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
        )

    assert len(calls) == 2
    assert result.status == "passed"
    assert len(result.tests) == 2


def test_run_native_tests_continues_after_process_failure(tmp_path):
    """A suite process failure is recorded and later suites still run."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            return CompletedProcess(args, 2, "startup failed", "missing runner")

        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("BrokenSuite"), _suite("WorkingSuite")],
            godot_binary="godot",
        )

    assert len(calls) == 2
    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert result.tests[1].status == "passed"
    assert "startup failed" in result.tests[0].message


def test_run_native_tests_rejects_inconsistent_process_result(tmp_path):
    """A nonzero process code cannot be masked by a passing result file."""

    def fake_run(args, **kwargs):
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 1, "test failed", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("InconsistentSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "process exit code 1" in result.tests[0].message


def test_run_native_tests_records_subprocess_timeout(tmp_path):
    """A subprocess timeout becomes an infrastructure result."""
    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=TimeoutError("process timeout"),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("TimeoutSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "process timeout" in result.tests[0].message
