"""Unit tests for interrupted native test runs (crash recovery)."""

import itertools
import json
import signal
from contextlib import ExitStack
from pathlib import Path
from subprocess import CompletedProcess
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.errors import NativeInterruptError
from gd_tools.native_test.artifacts import NativeArtifactLayout
from gd_tools.native_test.command import (
    _raise_interrupt,
    run_native_test_command,
)
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.preflight import NativePreflightResult
from gd_tools.native_test.protocol import NativeSuite, NativeTest

pytestmark = pytest.mark.unit

_POPEN_IDS = itertools.count(700)


class _FakePopen:
    """Minimal Popen stand-in driving a fake runner through communicate()."""

    def __init__(self, command, runner, env):
        self.pid = next(_POPEN_IDS)
        self._runner = runner
        self._args = command
        self._env = env
        self.returncode = None

    def communicate(self, timeout=None):
        result = self._runner(self._args, env=self._env)
        self.returncode = result.returncode
        return result.stdout, result.stderr

    def poll(self):
        return self.returncode


def _spawn_adapter(runner):
    """Adapt a ``CompletedProcess``-style fake to the Popen spawn seam."""

    def adapt(command, *, env, registry, abort_event=None):
        process = _FakePopen(command, runner, env)
        registry.add(process)
        return process

    return adapt


def _suite(name: str) -> NativeSuite:
    return NativeSuite(
        name=name,
        path=f"res://test/{name.lower()}_test.gd",
        tests=[NativeTest(name="test_example")],
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


def _write_result(result_path: Path, status: str = "passed") -> None:
    result_path.write_text(
        json.dumps(
            {
                "protocol_version": 4,
                "run_id": "test-run",
                "status": status,
                "engine_warnings": [],
                "diagnostics": {},
                "tests": [
                    {
                        "suite": "ExampleSuite",
                        "name": "test_example",
                        "status": status,
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


def test_interrupt_publishes_incomplete_index_and_stops(tmp_path):
    """An interrupted run marks the artifacts incomplete and spawns no more.

    The in-flight Godot child is killed through the process-tree killer and
    the orchestrator must publish an artifact index whose status says the
    run never finished, then raise ``NativeInterruptError`` so the CLI can
    exit 130.
    """
    attempts = []
    killed = []

    def fake_run(args, **kwargs):
        attempts.append(args)
        raise KeyboardInterrupt

    layout = NativeArtifactLayout.create(tmp_path, "interrupt-1")
    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch(
            "gd_tools.native_test.orchestrator._kill_process_tree",
            side_effect=lambda pid, **kwargs: killed.append(pid),
        ),
    ):
        with pytest.raises(NativeInterruptError) as excinfo:
            run_native_tests(
                tmp_path,
                [_suite("FirstSuite"), _suite("SecondSuite")],
                godot_binary="godot",
                artifact_layout=layout,
            )

    assert excinfo.value.exit_code == 130
    assert len(attempts) == 1
    assert len(killed) == 1
    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert index["status"] == "incomplete"
    assert [entry["suite"] for entry in index["suites"]] == ["FirstSuite"]


def test_interrupt_after_completed_suite_keeps_attempted_suites(tmp_path):
    """Suites attempted before the interrupt stay listed in the index."""
    attempts = []

    def fake_run(args, **kwargs):
        attempts.append(args)
        if len(attempts) == 1:
            result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
            _write_result(result_path)
            return CompletedProcess(args, 0, "stdout", "stderr")
        raise KeyboardInterrupt

    layout = NativeArtifactLayout.create(tmp_path, "interrupt-2")
    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree"),
    ):
        with pytest.raises(NativeInterruptError):
            run_native_tests(
                tmp_path,
                [_suite("FirstSuite"), _suite("SecondSuite")],
                godot_binary="godot",
                artifact_layout=layout,
            )

    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert index["status"] == "incomplete"
    assert [entry["suite"] for entry in index["suites"]] == [
        "FirstSuite",
        "SecondSuite",
    ]


def test_completed_run_is_never_marked_incomplete(tmp_path):
    """Regression: a run that finishes publishes its real status."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 0, "stdout", "stderr")

    layout = NativeArtifactLayout.create(tmp_path, "complete-1")
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("OnlySuite")],
            godot_binary="godot",
            artifact_layout=layout,
        )

    assert result.status == "passed"
    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert index["status"] == "passed"


def _command_patches(suite: NativeSuite):
    """Return the standard command-layer patch context managers."""
    return (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=suite.root,
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
            return_value=[suite.suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=NativePreflightResult(
                status="ok", suites=[suite.suite]
            ),
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    )


def _enter_command_patches(stack: ExitStack, holder: SimpleNamespace) -> None:
    """Enter the standard command-layer patches into an ExitStack."""
    for patcher in _command_patches(holder):
        stack.enter_context(patcher)


def test_interrupt_prints_human_notice(tmp_path):
    """An interrupted run tells the user where the incomplete artifacts are."""
    holder = SimpleNamespace(
        root=tmp_path,
        suite=NativeSuite(name="ExampleSuite", path="res://test/example.gd"),
    )
    with ExitStack() as stack:
        _enter_command_patches(stack, holder)
        stack.enter_context(
            patch(
                "gd_tools.native_test.command.run_native_tests",
                side_effect=KeyboardInterrupt,
            )
        )
        notice = stack.enter_context(patch("gd_tools.output.print_error"))
        with pytest.raises(KeyboardInterrupt):
            run_native_test_command(_config())

    text = " ".join(
        str(call.args[0]) for call in notice.call_args_list if call.args
    )
    assert "incomplete" in text


def test_interrupt_before_orchestrator_publishes_incomplete_index(tmp_path):
    """An interrupt during preflight still leaves an incomplete index."""
    holder = SimpleNamespace(
        root=tmp_path,
        suite=NativeSuite(name="ExampleSuite", path="res://test/example.gd"),
    )
    with ExitStack() as stack:
        _enter_command_patches(stack, holder)
        stack.enter_context(
            patch(
                "gd_tools.native_test.command.run_preflight_cached",
                side_effect=KeyboardInterrupt,
            )
        )
        stack.enter_context(patch("gd_tools.output.print_error"))
        with pytest.raises(KeyboardInterrupt):
            run_native_test_command(_config())

    indexes = list(
        (tmp_path / ".gd-tools" / "artifacts").glob("*/artifacts.json")
    )
    assert len(indexes) == 1
    index = json.loads(indexes[0].read_text(encoding="utf-8"))
    assert index["status"] == "incomplete"


def test_sigterm_handler_registered_and_restored(tmp_path):
    """SIGTERM converts to the interrupt cleanup path and is restored."""
    holder = SimpleNamespace(
        root=tmp_path,
        suite=NativeSuite(name="ExampleSuite", path="res://test/example.gd"),
    )
    previous = signal.getsignal(signal.SIGTERM)
    with ExitStack() as stack:
        _enter_command_patches(stack, holder)
        stack.enter_context(
            patch(
                "gd_tools.native_test.command.run_native_tests",
                return_value=SimpleNamespace(
                    run_id="run-1",
                    status="passed",
                    tests=[],
                    coverage_data_path=None,
                    artifact_index_path=None,
                    fail_fast=None,
                    engine_warnings=[],
                    diagnostics={},
                    stdout="",
                    stderr="",
                ),
            )
        )
        sig = stack.enter_context(
            patch("gd_tools.native_test.command.signal.signal")
        )
        sig.return_value = previous
        run_native_test_command(_config())

    registrations = [
        call for call in sig.call_args_list if call.args[0] == signal.SIGTERM
    ]
    assert len(registrations) == 2
    assert registrations[0].args[1] is _raise_interrupt
    assert registrations[1].args[1] == previous


def test_cli_interrupted_test_run_exits_130():
    """Ctrl+C during `gd-tools test` exits with the SIGINT code 130."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.run_native_test_command",
            side_effect=KeyboardInterrupt,
        ),
    ):
        result = runner.invoke(cli, ["test"])

    assert result.exit_code == 130
