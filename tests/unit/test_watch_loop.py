"""Unit tests for the watch loop orchestration."""

from pathlib import Path

import pytest
from gd_tools.native_test.protocol import NativeRunResult, NativeSuite

from gd_tools.watch.loop import watch_loop
from gd_tools.watch.observer import FileEvent

pytestmark = pytest.mark.unit

SUITE = NativeSuite(name="test_enemy", path="res://tests/test_enemy.gd")


class FakeClock:
    """Controllable monotonic clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeEventSource:
    """Scripted event source supporting mid-run pushes."""

    def __init__(self, *events) -> None:
        self._events = list(events)
        self._index = 0
        self.stopped = False

    def push(self, event) -> None:
        self._events.append(event)

    def events(self):
        while not self.stopped:
            if self._index < len(self._events):
                event = self._events[self._index]
                self._index += 1
                yield event
            else:
                yield None

    def stop(self) -> None:
        self.stopped = True


class FakeRunner:
    """Records run invocations; hooks fire before each run returns."""

    def __init__(self, on_call=None) -> None:
        self.calls: list[list[str]] = []
        self._on_call = on_call

    def __call__(self, suites):
        self.calls.append([s.path for s in suites])
        if self._on_call is not None:
            self._on_call(len(self.calls))
        return NativeRunResult(
            run_id=f"r{len(self.calls)}", status="passed", tests=[]
        )


def _run_loop(source, discover, runner, clock, output):
    return watch_loop(
        Path(".").resolve(),
        discover=discover,
        runner=runner,
        event_source=source,
        clock=clock,
        sleep=lambda seconds: clock.advance(0.5),
        output=output.append,
    )


def test_initial_full_run_then_mapped_rerun():
    """The loop runs the full suite once, then re-runs the mapped suite."""
    clock = FakeClock()
    source = FakeEventSource(FileEvent("src/enemy.gd", "modified"))
    discover_calls: list[int] = []

    def discover():
        discover_calls.append(1)
        return [SUITE]

    def on_call(n):
        if n >= 2:
            source.stop()

    runner = FakeRunner(on_call)
    output: list[str] = []

    exit_code = _run_loop(source, discover, runner, clock, output)

    assert exit_code == 0
    assert len(runner.calls) == 2
    assert runner.calls[0] == ["res://tests/test_enemy.gd"]
    assert runner.calls[1] == ["res://tests/test_enemy.gd"]
    assert len(discover_calls) == 2
    assert source.stopped is True


def test_no_match_falls_back_to_full_run_with_explicit_status():
    """A changed file with no mapped suite re-runs everything, with a note."""
    clock = FakeClock()
    source = FakeEventSource(FileEvent("src/player.gd", "modified"))
    discover_calls: list[int] = []

    def discover():
        discover_calls.append(1)
        return [SUITE]

    def on_call(n):
        if n >= 2:
            source.stop()

    runner = FakeRunner(on_call)
    output: list[str] = []

    _run_loop(source, discover, runner, clock, output)

    assert runner.calls[1] == ["res://tests/test_enemy.gd"]
    assert any("full suite" in line for line in output)
    assert any("src/player.gd" in line for line in output)


def test_events_during_run_queue_exactly_one_rerun():
    """Bursts of saves during a run produce one further run, not many."""
    clock = FakeClock()
    source = FakeEventSource()
    discover_calls: list[int] = []

    def discover():
        discover_calls.append(1)
        return [SUITE]

    def on_call(n):
        if n == 1:
            source.push(FileEvent("src/enemy.gd", "modified"))
            source.push(FileEvent("src/enemy.gd", "modified"))
        elif n == 2:
            source.push(FileEvent("src/enemy.gd", "modified"))
            source.push(FileEvent("src/enemy.gd", "created"))
        else:
            source.stop()

    runner = FakeRunner(on_call)
    output: list[str] = []

    _run_loop(source, discover, runner, clock, output)

    assert len(runner.calls) == 3
    assert len(discover_calls) == 3
    assert runner.calls[1] == ["res://tests/test_enemy.gd"]
    assert runner.calls[2] == ["res://tests/test_enemy.gd"]


def test_keyboard_interrupt_exits_cleanly():
    """Ctrl+C during the watch phase stops the source and exits 0."""
    clock = FakeClock()

    class InterruptingSource:
        def __init__(self) -> None:
            self.stopped = False

        def events(self):
            raise KeyboardInterrupt
            yield  # pragma: no cover - makes this a generator

        def stop(self) -> None:
            self.stopped = True

    source = InterruptingSource()
    discover_calls: list[int] = []

    def discover():
        discover_calls.append(1)
        return [SUITE]

    runner = FakeRunner()
    output: list[str] = []

    exit_code = _run_loop(source, discover, runner, clock, output)

    assert exit_code == 0
    assert source.stopped is True
    assert len(runner.calls) == 1


def test_output_reports_run_status_lines():
    """Each run prints a status line with the run outcome."""
    clock = FakeClock()
    source = FakeEventSource(FileEvent("src/enemy.gd", "modified"))
    discover_calls: list[int] = []

    def discover():
        discover_calls.append(1)
        return [SUITE]

    def on_call(n):
        if n >= 2:
            source.stop()

    runner = FakeRunner(on_call)
    output: list[str] = []

    _run_loop(source, discover, runner, clock, output)

    assert len([line for line in output if "passed" in line]) == 2


def test_coalesced_batch_reruns_all_mapped_suites():
    """Multiple changed files map to all affected suites in one run."""
    clock = FakeClock()
    source = FakeEventSource(
        FileEvent("src/enemy.gd", "modified"),
        FileEvent("src/player.gd", "modified"),
    )
    suites = [
        SUITE,
        NativeSuite(name="test_player", path="res://tests/test_player.gd"),
    ]

    def discover():
        return list(suites)

    def on_call(n):
        if n >= 2:
            source.stop()

    runner = FakeRunner(on_call)
    output: list[str] = []

    _run_loop(source, discover, runner, clock, output)

    assert runner.calls[1] == [
        "res://tests/test_enemy.gd",
        "res://tests/test_player.gd",
    ]


def test_batch_with_any_unmapped_file_falls_back_to_full_suite():
    """One unmapped file in a batch forces a full-suite fallback run."""
    clock = FakeClock()
    source = FakeEventSource(
        FileEvent("src/enemy.gd", "modified"),
        FileEvent("src/helper.gd", "modified"),
    )

    def discover():
        return [SUITE]

    def on_call(n):
        if n >= 2:
            source.stop()

    runner = FakeRunner(on_call)
    output: list[str] = []

    _run_loop(source, discover, runner, clock, output)

    assert runner.calls[1] == ["res://tests/test_enemy.gd"]
    assert any("src/helper.gd" in line for line in output)
