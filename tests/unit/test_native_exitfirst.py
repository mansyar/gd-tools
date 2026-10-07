"""Unit tests for the fail-fast (``--exitfirst``) dispatch gate.

The gate stops *dispatching* new suites after the first suite whose final
aggregated result is a failure (test failure or infrastructure error);
in-flight suites drain and are collected, unstarted suites are recorded as
skipped (spec FR1.1-FR1.7).
"""

import itertools
import json
import threading
from contextlib import ExitStack
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.native_test.artifacts import NativeArtifactLayout
from gd_tools.native_test.orchestrator import (
    _SuiteOutcome,
    _kill_process_tree,
    run_native_tests,
)
from gd_tools.native_test.protocol import (
    NativeCoverage,
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
            "protocol_version": 4,
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

    def __init__(self, env, runner, args, abort_event=None):
        self.pid = next(self._counter)
        self._env = env
        self._runner = runner
        self._args = args
        self._abort_event = abort_event
        self.returncode = None

    def communicate(self, timeout=None):
        outcome = self._runner(
            self._args, env=self._env, abort_event=self._abort_event
        )
        if isinstance(outcome, CompletedProcess):
            self.returncode = outcome.returncode
            return outcome.stdout, outcome.stderr
        raise outcome

    def poll(self):
        return self.returncode


def _spawn_adapter(runner):
    """Wrap a fake_run(args, **kwargs) into the _spawn_process seam."""

    def adapt(command, *, env, registry, abort_event=None):
        process = _FakePopen(env, runner, command, abort_event)
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
        return _finish(
            fake_kwargs, _result_for(name, status, **options), status
        )

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
    suites = [
        _suite("ASuite"),
        _suite("BSuite"),
        _suite("CSuite"),
        _suite("DSuite"),
    ]

    result, calls = _run_with_status_map(
        tmp_path,
        suites,
        {"ASuite": _PASS, "BSuite": _FAIL, "CSuite": _PASS, "DSuite": _PASS},
        exitfirst=True,
    )

    assert calls == ["ASuite", "BSuite"]
    assert result.status == "failed"
    assert [
        test.suite for test in result.tests if test.status == "skipped"
    ] == [
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
    calls = []
    lock = threading.Lock()

    def fake_run(args, **fake_kwargs):
        name = fake_kwargs["env"]["GD_TOOLS_SUITE_NAME"]
        with lock:
            calls.append(name)
        abort = fake_kwargs.get("abort_event")
        if name == "ASuite" and abort is not None:
            # Stay in-flight until fail-fast signals the run-level abort
            # event; the drain then collects A without ever spawning C/D/E.
            # The sentinel makes a missing signal a failure, not a silent
            # timeout.
            if not abort.wait(timeout=5):
                raise AssertionError(
                    "fail-fast never signalled abort_event to ASuite"
                )
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
    # Shard hits sum across the drained suites (A wrote 1, B wrote 2).
    assert merged["files"][0]["hits"]["0"] == 3


def _command_patches(tmp_path, native_result):
    """Patch the command seams for run_native_test_command unit tests."""
    return (
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
                NativeSuite(name="ASuite", path="res://test/a_test.gd"),
                NativeSuite(name="BSuite", path="res://test/b_test.gd"),
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
            return_value=native_result,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
    )


def _enter_command(stack, tmp_path, native_result):
    """Enter all command patches; return the run_native_tests mock."""
    run_mock = None
    for item in _command_patches(tmp_path, native_result):
        entered = stack.enter_context(item)
        if item.attribute == "run_native_tests":
            run_mock = entered
    return run_mock


def test_exitfirst_publishes_artifact_index_with_unstarted_suites(tmp_path):
    """The artifact index stays consistent under fail-fast (FR1.6).

    Unstarted suites keep their plan entry, listed with the additive
    ``fail_fast`` marker and no realized artifact paths.
    """
    layout = NativeArtifactLayout.create(tmp_path, "run-ff")
    suites = [_suite("ASuite"), _suite("BSuite"), _suite("CSuite")]

    def fake_execute(index, suite, context):
        context.attempted.append(suite.name)
        return _SuiteOutcome(tests=[], has_failure=index == 1)

    with patch(
        "gd_tools.native_test.orchestrator._execute_suite",
        side_effect=fake_execute,
    ):
        result = run_native_tests(
            tmp_path,
            suites,
            godot_binary="godot",
            artifact_layout=layout,
            exitfirst=True,
        )

    assert result.status == "failed"
    payload = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert [entry["suite"] for entry in payload["suites"]] == [
        "ASuite",
        "BSuite",
        "CSuite",
    ]
    skipped = [entry for entry in payload["suites"] if entry.get("fail_fast")]
    assert [entry["suite"] for entry in skipped] == ["CSuite"]


def test_command_prints_fail_fast_summary_line(capsys, tmp_path):
    """The command layer renders the fail-fast summary line (FR1.6)."""
    from gd_tools.errors import TestFailureError
    from gd_tools.native_test.command import run_native_test_command

    config = MagicMock()
    config.test.test_dirs = ["test"]
    native = NativeRunResult(
        run_id="run-1",
        status="failed",
        tests=[
            NativeTestResult(suite="ASuite", name="test_ok", status="passed"),
            NativeTestResult(suite="BSuite", name="test_bad", status="failed"),
        ],
        fail_fast={"trigger": "BSuite", "skipped": 2, "planned": 4},
    )
    with ExitStack() as stack:
        _enter_command(stack, tmp_path, native)
        with pytest.raises(TestFailureError):
            run_native_test_command(config)

    captured = capsys.readouterr()
    assert (
        "Stopped early: fail-fast after suite BSuite (2 of 4 suites skipped)"
        in captured.out
    )


def test_command_forwards_exitfirst_and_parallel_together(tmp_path):
    """--exitfirst and --parallel reach the orchestrator in one call."""
    from gd_tools.native_test.command import run_native_test_command

    config = MagicMock()
    config.test.test_dirs = ["test"]
    native = NativeRunResult(run_id="run-1", status="passed")
    with ExitStack() as stack:
        run_mock = _enter_command(stack, tmp_path, native)
        run_native_test_command(config, exitfirst=True, parallel=3)

    assert run_mock.call_args.kwargs["exitfirst"] is True
    assert run_mock.call_args.kwargs["parallel"] == 3


def test_command_fail_fast_result_carries_skip_details(tmp_path):
    """The raised TestFailureError carries the fail-fast skip breakdown."""
    from gd_tools.errors import TestFailureError
    from gd_tools.native_test.command import run_native_test_command

    config = MagicMock()
    config.test.test_dirs = ["test"]
    native = NativeRunResult(
        run_id="run-1",
        status="failed",
        tests=[
            NativeTestResult(suite="BSuite", name="test_bad", status="failed"),
            NativeTestResult(
                suite="CSuite",
                name="not_run",
                status="skipped",
                message="Suite not run: fail-fast stopped dispatch after "
                "suite 'BSuite'.",
            ),
        ],
        fail_fast={"trigger": "BSuite", "skipped": 1, "planned": 2},
    )
    with ExitStack() as stack:
        _enter_command(stack, tmp_path, native)
        with pytest.raises(TestFailureError) as excinfo:
            run_native_test_command(config)

    result = excinfo.value.result
    statuses = [detail.status for detail in result.test_details]
    assert "skip" in statuses
