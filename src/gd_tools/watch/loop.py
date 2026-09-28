"""Watch loop orchestrating event observation, coalescing and test runs."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path

from gd_tools.native_test.protocol import NativeRunResult, NativeSuite
from gd_tools.watch.coalescer import RunCoalescer
from gd_tools.watch.mapping import map_changed_file
from gd_tools.watch.observer import FileEvent
from gd_tools.watch.scope import WatchAction, classify_event


def watch_loop(
    project_root: Path,
    *,
    discover: Callable[[], list[NativeSuite]],
    runner: Callable[[list[NativeSuite]], NativeRunResult],
    event_source: object,
    clock: Callable[[], float],
    sleep: Callable[[float], None] = time.sleep,
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
        output: Status-line sink.

    Returns:
        The process exit code: always ``0`` for a watch session.
    """
    coalescer = RunCoalescer(clock=clock)
    run_number = 0
    last_changed: str | None = None

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
                    if last_changed is not None:
                        mapped = map_changed_file(
                            project_root / last_changed, project_root, suites
                        )
                        if mapped is None:
                            output(
                                f"No suite mapped for '{last_changed}';"
                                " running full suite."
                            )
                            run(suites)
                        else:
                            run(
                                [
                                    suite
                                    for suite in suites
                                    if suite.path == mapped
                                ]
                            )
                    else:
                        run(suites)
                    last_changed = None
                    coalescer.finish_run()
            else:
                if classify_event(event.event_type) is WatchAction.RUN:
                    coalescer.notify_change()
                    last_changed = event.path
    except KeyboardInterrupt:
        pass
    finally:
        event_source.stop()
    return 0
