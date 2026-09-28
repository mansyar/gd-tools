"""Debounce and run-coalescing for the watch loop."""

from __future__ import annotations

from collections.abc import Callable

DEFAULT_DEBOUNCE_SECONDS = 0.5


class RunCoalescer:
    """Coalesce file-change events into the minimum number of runs.

    The coalescer tracks two pieces of state: whether at least one change is
    waiting to be run (``pending``), and whether a run is currently in flight.
    A run becomes due once the debounce window has elapsed since the most
    recent change. Changes that arrive while a run is in flight mark the
    session dirty; when the run finishes, exactly one further run is due —
    never one per save.
    """

    def __init__(
        self,
        *,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
        clock: Callable[[], float],
    ) -> None:
        """Create a coalescer.

        Args:
            debounce_seconds: Quiet period required after the latest change
                before a run is due.
            clock: Zero-argument callable returning the current monotonic
                time; injectable so tests can control time deterministically.
        """
        self._debounce_seconds = debounce_seconds
        self._clock = clock
        self._pending = False
        self._running = False
        self._dirty_during_run = False
        self._due_immediately = False
        self._last_change: float | None = None

    def notify_change(self) -> None:
        """Record a file change at the current time."""
        self._last_change = self._clock()
        if self._running:
            self._dirty_during_run = True
        else:
            self._pending = True

    def should_run(self) -> bool:
        """Return whether a run is due right now."""
        if self._running:
            return False
        if not self._pending or self._last_change is None:
            return False
        if self._due_immediately:
            return True
        return self._clock() - self._last_change >= self._debounce_seconds

    def start_run(self) -> None:
        """Mark a run as started, consuming any pending state."""
        self._pending = False
        self._dirty_during_run = False
        self._due_immediately = False
        self._running = True

    def finish_run(self) -> None:
        """Mark the in-flight run as finished.

        If changes arrived while the run was executing, exactly one further
        run becomes pending and is due immediately: the run's own duration
        already coalesced the burst of saves, so no extra debounce wait is
        applied.
        """
        self._running = False
        if self._dirty_during_run:
            self._dirty_during_run = False
            self._pending = True
            self._due_immediately = True