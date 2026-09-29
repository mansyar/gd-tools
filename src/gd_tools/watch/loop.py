"""Watch loop orchestrating event observation, coalescing and test runs."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol

from gd_tools.native_test.protocol import NativeRunResult, NativeSuite
from gd_tools.watch.coalescer import DEFAULT_DEBOUNCE_SECONDS, RunCoalescer
from gd_tools.watch.mapping import map_changed_file
from gd_tools.watch.observer import FileEvent
from gd_tools.watch.scope import WatchAction, classify_event


class EventSource(Protocol):
    """Minimal interface the watch loop needs from an event source."""

    def events(self) -> Iterator[FileEvent | None]:
        """Yield file events, with ``None`` poll ticks between arrivals."""
        ...

    def stop(self) -> None:
        """Terminate the event stream."""
        ...


def watch_loop(
    project_root: Path,
    *,
    discover: Callable[[], list[NativeSuite]],
    runner: Callable[[list[NativeSuite]], NativeRunResult],
    event_source: EventSource,
    clock: Callable[[], float],
    sleep: Callable[[float], None] = time.sleep,
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    output: Callable[[str], None] = print,
) -> int:
    """Run the watch session until interrupted.

    Performs one full-suite run up front, then observes file events: each
    coalesced change re-runs the suite mapped from the changed file, or the
    full suite when no mapping exists. The session ends on Ctrl+C (or when
    the event source stops) with exit code 0 regardless of the last run's
    outcome.

    Args:
        project_root: Godot project root.
        discover: Returns the currently runnable suites; invoked once per
            run so new files and active filters are re-applied each time.
        runner: Executes the given suites and returns the run result.
        event_source: Object exposing ``events()`` (yields
            :class:`FileEvent` or ``None`` ticks) and ``stop()``.
        clock: Monotonic time callable for the coalescer.
        sleep: Wait between poll ticks; injectable for tests.
        debounce_seconds: Quiet period after the latest change before a
            run becomes due; injectable for tests and fast e2e.
        output: Status-line sink.

    Returns:
        The process exit code: always ``0`` for a watch session.
    """
    coalescer = RunCoalescer(clock=clock, debounce_seconds=debounce_seconds)
    run_number = 0
    changed: set[str] = set()

    def run(suites: list[NativeSuite]) -> None:
        nonlocal run_number
        run_number += 1
        result = runner(suites)
        output(f"Run {run_number}: {result.status} ({len(result.tests)} tests)")

    try:
        run(discover())
        event_stream: Iterator[FileEvent | None] = event_source.events()
        for event in event_stream:
            if event is None:
                sleep(0.05)
                if coalescer.should_run():
                    coalescer.start_run()
                    suites = discover()
                    mapped_paths: set[str] = set()
                    unmapped: list[str] = []
                    for path in sorted(changed):
                        mapped = map_changed_file(
                            project_root / path, project_root, suites
                        )
                        if mapped is None:
                            unmapped.append(path)
                        else:
                            mapped_paths.add(mapped)
                    if unmapped:
                        for path in unmapped:
                            output(
                                f"No suite mapped for '{path}';"
                                " running full suite."
                            )
                        run(suites)
                    else:
                        run(
                            [
                                suite
                                for suite in suites
                                if suite.path in mapped_paths
                            ]
                        )
                    changed.clear()
                    coalescer.finish_run()
            else:
                if classify_event(event.event_type) is WatchAction.RUN:
                    coalescer.notify_change()
                    changed.add(event.path)
    except KeyboardInterrupt:
        pass
    finally:
        event_source.stop()
    return 0
