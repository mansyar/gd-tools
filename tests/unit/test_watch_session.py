"""Unit tests for the interactive watch session wiring."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.errors import GdToolsError, TestFailureError
from gd_tools.watch.observer import FileEvent
from gd_tools.watch.session import run_watch_mode

pytestmark = pytest.mark.unit


class FakeClock:
    """Deterministic clock with manual advancement."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeEventSource:
    """Scripted event source; yields queued events then poll ticks."""

    def __init__(self, events) -> None:
        self._events = [
            FileEvent(path, event_type) for path, event_type in events
        ]
        self._stopped = False

    def push(self, event) -> None:
        self._events.append(event)

    def events(self):
        index = 0
        while not self._stopped:
            if index < len(self._events):
                yield self._events[index]
                index += 1
            else:
                yield None
            if self._stopped:
                return

    def stop(self) -> None:
        self._stopped = True


def _project(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "enemy.gd").write_text(
        "extends Node\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "test_enemy.gd").write_text(
        "extends Node\n", encoding="utf-8"
    )
    return tmp_path


def _config(tmp_path):
    config = MagicMock()
    config.test.test_dirs = [str(tmp_path / "tests")]
    config.test.tags = []
    config.test.timeout_seconds = 5.0
    config.test.retries = 0
    return config


def _run_watch(
    tmp_path,
    config,
    fake_native,
    events,
    output,
    clock,
    parallel=None,
    durations=None,
):
    with (
        patch(
            "gd_tools.watch.session.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.watch.session.find_godot",
            return_value=SimpleNamespace(
                is_valid=True, path="godot", version="4.5"
            ),
        ),
        patch(
            "gd_tools.watch.session.run_native_test_command",
            side_effect=fake_native,
        ) as mock_native,
    ):
        code = run_watch_mode(
            config,
            event_source=FakeEventSource(events),
            clock=clock,
            sleep=lambda _seconds: clock.advance(0.5),
            output=output.append,
            parallel=parallel,
            durations=durations,
        )
    return code, mock_native


def test_watch_forwards_durations_to_re_runs(tmp_path):
    """Every watch re-run carries the resolved durations setting."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    fake_native = MagicMock(side_effect=KeyboardInterrupt)
    code, mock_native = _run_watch(
        tmp_path,
        _config(tmp_path),
        fake_native,
        [],
        output,
        clock,
        durations=2,
    )
    assert code == 0
    assert mock_native.call_args.kwargs["durations"] == 2


def test_banner_reports_watched_file_count(tmp_path):
    """The session announces how many files are being watched."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    fake_native = MagicMock(side_effect=KeyboardInterrupt)
    code, mock_native = _run_watch(
        tmp_path, _config(tmp_path), fake_native, [], output, clock
    )
    assert code == 0
    assert "Watching 2 files. Press Ctrl+C to stop." in output
    mock_native.assert_called_once()


def test_run_failure_does_not_abort_watch(tmp_path):
    """A failing test run is reported and the session keeps watching."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    calls = []

    def fake_native(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise TestFailureError("1 test(s) failed")
        raise KeyboardInterrupt

    code, _ = _run_watch(
        tmp_path,
        _config(tmp_path),
        fake_native,
        [("src/enemy.gd", "modified")],
        output,
        clock,
    )
    assert code == 0
    assert any("Run 1: failed" in line for line in output)
    assert len(calls) == 2


def test_infra_error_keeps_watching(tmp_path):
    """A per-run infrastructure error is reported without aborting."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    calls = []

    def fake_native(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise GdToolsError("Godot exploded")
        raise KeyboardInterrupt

    code, _ = _run_watch(
        tmp_path,
        _config(tmp_path),
        fake_native,
        [("src/enemy.gd", "modified")],
        output,
        clock,
    )
    assert code == 0
    assert any("Error: Godot exploded" in line for line in output)
    assert any("Run 1: error" in line for line in output)
    assert len(calls) == 2


def test_startup_godot_error_propagates(tmp_path):
    """Startup failures (bad Godot) propagate as GdToolsError (exit 2)."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    with (
        patch(
            "gd_tools.watch.session.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.watch.session.find_godot",
            return_value=SimpleNamespace(
                is_valid=False, path="godot", version="4.3"
            ),
        ),
    ):
        with pytest.raises(GdToolsError):
            run_watch_mode(
                _config(tmp_path),
                event_source=FakeEventSource([]),
                clock=clock,
                sleep=lambda _seconds: clock.advance(0.5),
                output=output.append,
            )
    assert output == []


def test_screen_cleared_between_runs(tmp_path):
    """Each run starts with a cleared screen."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    calls = []

    def fake_native(*args, **kwargs):
        calls.append(1)
        if len(calls) >= 2:
            raise KeyboardInterrupt
        return MagicMock()

    with patch("click.clear") as mock_clear:
        code, _ = _run_watch(
            tmp_path,
            _config(tmp_path),
            fake_native,
            [("src/enemy.gd", "modified")],
            output,
            clock,
        )
    assert code == 0
    assert mock_clear.call_count == 2


def _suites():
    """Two fake suites so a mapped re-run is a strict subset."""
    return [
        SimpleNamespace(name="EnemySuite", path="res://tests/test_enemy.gd"),
        SimpleNamespace(name="PlayerSuite", path="res://tests/test_player.gd"),
    ]


def test_mapped_rerun_passes_suite_filter(tmp_path):
    """A mapped re-run targets only the affected suite."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    calls = []

    def fake_native(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) >= 2:
            raise KeyboardInterrupt
        return MagicMock()

    with patch(
        "gd_tools.watch.session.discover_native_suites",
        return_value=_suites(),
    ):
        code, mock_native = _run_watch(
            tmp_path,
            _config(tmp_path),
            fake_native,
            [("src/enemy.gd", "modified")],
            output,
            clock,
        )
    assert code == 0
    assert mock_native.call_args_list[0].kwargs.get("suite") is None
    assert mock_native.call_args_list[1].kwargs.get("suite") == "EnemySuite"


def test_fallback_full_run_has_no_suite_filter(tmp_path):
    """A full-suite fallback run keeps every discovered suite."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    calls = []

    def fake_native(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) >= 2:
            raise KeyboardInterrupt
        return MagicMock()

    with patch(
        "gd_tools.watch.session.discover_native_suites",
        return_value=_suites(),
    ):
        code, mock_native = _run_watch(
            tmp_path,
            _config(tmp_path),
            fake_native,
            [("src/helper.gd", "created")],
            output,
            clock,
        )
    assert code == 0
    assert mock_native.call_args_list[0].kwargs.get("suite") is None
    assert mock_native.call_args_list[1].kwargs.get("suite") is None
    assert any("full suite" in line for line in output)


def test_debounce_seconds_is_forwarded_to_the_loop(tmp_path):
    """A custom debounce window reaches the watch loop unchanged."""
    _project(tmp_path)
    with (
        patch(
            "gd_tools.watch.session.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.watch.session.find_godot",
            return_value=SimpleNamespace(
                is_valid=True, path="godot", version="4.5"
            ),
        ),
        patch(
            "gd_tools.watch.session.watch_loop",
            return_value=0,
        ) as mock_loop,
    ):
        code = run_watch_mode(
            _config(tmp_path),
            event_source=FakeEventSource([]),
            debounce_seconds=0.05,
        )
    assert code == 0
    assert mock_loop.call_args.kwargs["debounce_seconds"] == 0.05


def test_watch_runs_inherit_parallel_override(tmp_path):
    """An explicit parallel count reaches every watch-triggered run."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    fake_native = MagicMock(side_effect=KeyboardInterrupt)
    code, mock_native = _run_watch(
        tmp_path,
        _config(tmp_path),
        fake_native,
        [("tests/test_enemy.gd", "modified")],
        output,
        clock,
        parallel=4,
    )
    assert code == 0
    assert mock_native.call_args.kwargs["parallel"] == 4


def test_watch_runs_default_to_sequential(tmp_path):
    """Without a parallel override, watch runs stay on the shared path."""
    _project(tmp_path)
    output = []
    clock = FakeClock()
    fake_native = MagicMock(side_effect=KeyboardInterrupt)
    code, mock_native = _run_watch(
        tmp_path, _config(tmp_path), fake_native, [], output, clock
    )
    assert code == 0
    assert mock_native.call_args.kwargs["parallel"] is None
