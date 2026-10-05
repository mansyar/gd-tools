"""Unit tests for the fail-fast (``--exitfirst``) dispatch gate.

The gate stops *dispatching* new suites after the first suite whose final
aggregated result is a failure (test failure or infrastructure error);
in-flight suites drain and are collected, unstarted suites are recorded as
skipped (spec FR1.1-FR1.7).
"""

import itertools
import json
import threading
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from gd_tools.native_test.orchestrator import (
    _kill_process_tree,
    run_native_tests,
)
from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeSuite,
    NativeTest,
)

pytestmark = pytest.mark.unit


def _suite(name: str) -> NativeSuite:
    return NativeSuite(
        name=name,
        path=f"res://test/{name.lower()}_test.gd",
        tests=[NativeTest(name="test_example")],
    )


def _result_for(
    suite_name: str,
    status: str = "passed",
    *,
    attempts: int = 1,
    with_skip: bool = False,
) -> str:
    """Build a protocol v3 result JSON the runner would produce."""
    tests = [
        {
            "suite": suite_name,
            "name": "test_example",
            "status": status,
            "duration_seconds": 0.01,
            "attempts": attempts,
            "message": "",
            "diagnostics": {},
        }
    ]
    if with_skip:
        tests.append(
            {
                "suite": suite_name,
                "name": "test_skipped",
                "status": "skipped",
                "duration_seconds": 0.0,
                "attempts": 1,
                "message": "",
                "diagnostics": {},
            }
        )
    return json.dumps(
        {
            "protocol_version": 3,
            "run_id": "test-run",
            "status": status,
            "engine_warnings": [],
            "diagnostics": {},
            "tests": tests,
        }
    )


_RETURN_CODES = {"passed": 0, "failed": 1, "error": 2, "cancelled": 1}


def _finish(kwargs, body: str, status: str) -> CompletedProcess:
    result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
    result_path.write_text(body, encoding="utf-8")
    args = kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]
    return CompletedProcess(args, _RETURN_CODES[status], "stdout", "stderr")


class _FakePopen:
    """Adapts the existing CompletedProcess-style fakes to the Popen seam."""

    _counter = itertools.count(2000)

    def __init__(self, env, runner, args):
        self.pid = next(self._counter)
        self._env = env
        self._runner = runner
        self._args = args
        self.returncode = None

    def communicate(self, timeout=None):
        outcome = self._runner(self._args, env=self._env)
        if isinstance(outcome, CompletedProcess):
            self.returncode = outcome.returncode
            return outcome.stdout, outcome.stderr
        raise outcome

    def poll(self):
        return self.returncode


def _spawn_adapter(runner):
    """Wrap a fake_run(args, **kwargs) into the _spawn_process seam."""

    def adapt(command, *, env, registry, abort_event=None):
        process = _FakePopen(env, runner, command)
        registry.add(process)
        if abort_event is not None and abort_event.is_set():
            _kill_process_tree(process.pid)
            registry.remove(process)
        return process

    return adapt


def _run_with_status_map(tmp_path, suites, statuses, *, exitfirst, **kwargs):
    """Run run_native_tests with per-suite fake statuses.

    ``statuses`` maps suite name -> (result status, kwargs for _result_for).
    Returns ``(result, calls)`` where ``calls`` lists spawned suite names in
    spawn order.
    """
    calls = []
    lock = threading.Lock()

    def fake_run(args, **fake_kwargs):
        name = fake_kwargs["env"]["GD_TOOLS_SUITE_NAME"]
        with lock:
            calls.append(name)
        status, options = statuses[name]
        return _finish(fake_kwargs, _result_for(name, status, **options), status)

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            suites,
            godot_binary="godot",
            exitfirst=exitfirst,
            **kwargs,
        )
    return result, calls


_PASS = ("passed", {})
_FAIL = ("failed", {})
_ERROR = ("error", {})


def test_exitfirst_stops_dispatch_after_failing_suite(tmp_path):
    """Sequential: dispatch stops after the first failing suite result."""
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite"), _suite("DSuite")]

    result, calls = _run_with_status_map(
        tmp_path,
        suites,
        {"ASuite": _PASS, "BSuite": _FAIL, "CSuite": _PASS, "DSuite": _PASS},
        exitfirst=True,
    )

    assert calls == ["ASuite", "BSuite"]
    assert result.status == "failed"
    assert [test.suite for test in result.tests if test.status == "skipped"] == [
        "CSuite",
        "DSuite",
    ]
    assert result.fail_fast == {"trigger": "BSuite", "skipped": 2, "planned": 4}


def test_exitfirst_triggers_on_infrastructure_error(tmp_path):
    """A suite that errors (not just fails tests) stops dispatch."""
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite")]

    result, calls = _run_with_status_map(
        tmp_path,
        suites,
        {"ASuite": _PASS, "BSuite": _ERROR, "CSuite": _PASS},
        exitfirst=True,
    )

    assert calls == ["ASuite", "BSuite"]
    assert result.status == "error"
    assert result.fail_fast == {"trigger": "BSuite", "skipped": 1, "planned": 3}


def test_exitfirst_ignores_skips_and_passes(tmp_path):
    """Passes and skips never trigger the gate."""
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite")]

    result, calls = _run_with_status_map(
        tmp_path,
        suites,
        {
            "ASuite": _PASS,
            "BSuite": ("passed", {"with_skip": True}),
            "CSuite": _PASS,
        },
        exitfirst=True,
    )

    assert calls == ["ASuite", "BSuite", "CSuite"]
    assert result.status == "passed"
    assert result.fail_fast is None


def test_exitfirst_respects_final_result_after_retry(tmp_path):
    """A suite whose final result passes after a retry does not trigger."""
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite")]

    result, calls = _run_with_status_map(
        tmp_path,
        suites,
        {
            "ASuite": _PASS,
            "BSuite": ("passed", {"attempts": 2}),
            "CSuite": _PASS,
        },
        exitfirst=True,
    )

    assert calls == ["ASuite", "BSuite", "CSuite"]
    assert result.fail_fast is None


def test_exitfirst_parallel_stops_dispatch_and_drains_inflight(tmp_path):
    """Parallel: queued suites are not started; in-flight suites drain.

    ``ASuite`` is still running when ``BSuite`` fails fast; ``ASuite`` is
    collected and C/D/E are never spawned. Aggregation stays in discovery
    order with the synthetic skips appended at the end.
    """
    suites = [
        _suite("ASuite"),
        _suite("BSuite"),
        _suite("CSuite"),
        _suite("DSuite"),
        _suite("ESuite"),
    ]
    release = threading.Event()
    calls = []
    lock = threading.Lock()

    def fake_run(args, **fake_kwargs):
        name = fake_kwargs["env"]["GD_TOOLS_SUITE_NAME"]
        with lock:
            calls.append(name)
        if name == "ASuite":
            release.wait(timeout=5)
        return _finish(
            fake_kwargs,
            _result_for(name, "failed" if name == "BSuite" else "passed"),
            "failed" if name == "BSuite" else "passed",
        )

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            suites,
            godot_binary="godot",
            parallel=2,
            exitfirst=True,
        )
        release.set()

    assert sorted(calls) == ["ASuite", "BSuite"]
    assert result.status == "failed"
    assert [test.suite for test in result.tests] == [
        "ASuite",
        "BSuite",
        "CSuite",
        "DSuite",
        "ESuite",
    ]
    assert [test.status for test in result.tests] == [
        "passed",
        "failed",
        "skipped",
        "skipped",
        "skipped",
    ]
    assert result.fail_fast == {"trigger": "BSuite", "skipped": 3, "planned": 5}


def test_without_exitfirst_all_suites_run(tmp_path):
    """Regression guard: without the flag, dispatch is unchanged."""
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite")]

    result, calls = _run_with_status_map(
        tmp_path,
        suites,
        {"ASuite": _PASS, "BSuite": _FAIL, "CSuite": _PASS},
        exitfirst=False,
    )

    assert calls == ["ASuite", "BSuite", "CSuite"]
    assert result.status == "failed"
    assert result.fail_fast is None
    assert not [test for test in result.tests if test.status == "skipped"]


def test_exitfirst_still_merges_coverage_from_drained_suites(tmp_path):
    """Coverage shards from completed suites are merged into the report."""
    final_coverage = tmp_path / "coverage.json"
    plan_path = tmp_path / "plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite")]
    calls = []

    def fake_run(args, **fake_kwargs):
        name = fake_kwargs["env"]["GD_TOOLS_SUITE_NAME"]
        calls.append(name)
        manifest = json.loads(
            Path(fake_kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
        )
        status = "failed" if name == "BSuite" else "passed"
        shard_path = Path(manifest["coverage"]["output_path"])
        shard_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "test",
                    "files": [{"file_id": 0, "hits": {"0": len(calls)}}],
                }
            ),
            encoding="utf-8",
        )
        return _finish(fake_kwargs, _result_for(name, status), status)

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            suites,
            godot_binary="godot",
            exitfirst=True,
            coverage=NativeCoverage(
                enabled=True,
                plan_path=plan_path,
                output_path=final_coverage,
            ),
        )

    assert calls == ["ASuite", "BSuite"]
    assert result.status == "failed"
    assert result.coverage_data_path == final_coverage
    merged = json.loads(final_coverage.read_text(encoding="utf-8"))
    assert merged["files"][0]["hits"]["0"] == 2


def test_command_prints_fail_fast_summary_line(capsys, tmp_path):
    """The command layer renders the fail-fast summary line (FR1.6)."""
    from unittest.mock import MagicMock, patch

    from gd_tools.errors import TestFailureError
    from gd_tools.native_test.command import run_native_test_command
    from gd_tools.native_test.protocol import NativeRunResult, NativeTestResult

    config = MagicMock()
    config.test.test_dirs = ["test"]
    native = NativeRunResult(
        run_id="run-1",
        status="failed",
        tests=[
            NativeTestResult(suite="ASuite", name="test_ok", status="passed"),
            NativeTestResult(
                suite="BSuite", name="test_bad", status="failed"
            ),
        ],
        fail_fast={"trigger": "BSuite", "skipped": 2, "planned": 4},
    )
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=MagicMock(path="godot", version="4.7", is_valid=True),
        ),
        patch("gd_tools.native_test.command._import_project"),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[
                NativeSuite(
                    name="ASuite", path="res://test/a_test.gd"
                ),
                NativeSuite(
                    name="BSuite", path="res://test/b_test.gd"
                ),
            ],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda root, manifest, **_: MagicMock(
                status="ok", suites=list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
    ):
        with pytest.raises(TestFailureError):
            run_native_test_command(config)

    captured = capsys.readouterr()
    assert (
        "Stopped early: fail-fast after suite BSuite (2 of 4 suites skipped)"
        in captured.out
    )