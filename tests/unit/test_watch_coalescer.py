"""Unit tests for the watch-mode debounce and run-coalescing state machine."""

import pytest

from gd_tools.watch.coalescer import RunCoalescer

pytestmark = pytest.mark.unit


class FakeClock:
    """Controllable monotonic clock for deterministic debounce tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _coalescer(clock: FakeClock, debounce: float = 0.5) -> RunCoalescer:
    return RunCoalescer(debounce_seconds=debounce, clock=clock)


def test_change_does_not_trigger_run_before_debounce():
    """A single save must not start a run until the debounce window elapses."""
    clock = FakeClock()
    coalescer = _coalescer(clock)

    coalescer.notify_change()
    clock.advance(0.4)

    assert coalescer.should_run() is False


def test_change_triggers_run_after_debounce():
    """A save becomes runnable once 500 ms have passed without another save."""
    clock = FakeClock()
    coalescer = _coalescer(clock)

    coalescer.notify_change()
    clock.advance(0.5)

    assert coalescer.should_run() is True


def test_rapid_saves_coalesce_into_one_run():
    """Saves within the debounce window produce exactly one runnable state."""
    clock = FakeClock()
    coalescer = _coalescer(clock)

    coalescer.notify_change()
    clock.advance(0.3)
    coalescer.notify_change()
    clock.advance(0.3)
    coalescer.notify_change()
    clock.advance(0.5)

    assert coalescer.should_run() is True
    coalescer.start_run()
    assert coalescer.should_run() is False


def test_save_during_run_queues_exactly_one_rerun():
    """A save while a run is in flight schedules one re-run after completion."""
    clock = FakeClock()
    coalescer = _coalescer(clock)

    coalescer.notify_change()
    clock.advance(0.5)
    coalescer.start_run()

    clock.advance(0.4)
    coalescer.notify_change()
    clock.advance(0.5)

    assert coalescer.should_run() is False
    coalescer.finish_run()

    assert coalescer.should_run() is True
    coalescer.start_run()
    coalescer.finish_run()
    assert coalescer.should_run() is False


def test_continuous_saves_during_run_do_not_pile_up():
    """Many saves during a run still yield only a single queued re-run."""
    clock = FakeClock()
    coalescer = _coalescer(clock)

    coalescer.notify_change()
    clock.advance(0.5)
    coalescer.start_run()

    for _ in range(10):
        clock.advance(0.1)
        coalescer.notify_change()

    coalescer.finish_run()
    assert coalescer.should_run() is True

    coalescer.start_run()
    assert coalescer.should_run() is False
    coalescer.finish_run()
    assert coalescer.should_run() is False


def test_no_changes_never_triggers_a_run():
    """The coalescer stays idle when no files change."""
    clock = FakeClock()
    coalescer = _coalescer(clock)

    for _ in range(20):
        clock.advance(1.0)
        assert coalescer.should_run() is False
