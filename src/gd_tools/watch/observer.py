"""Watchdog-backed file event source for watch mode."""

from __future__ import annotations

import queue
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from gd_tools.watch.scope import is_watched_path

_POLL_TIMEOUT_SECONDS = 0.1


class FileEvent(NamedTuple):
    """A single observed file-system event inside the watch scope.

    Attributes:
        path: Project-relative posix path of the affected file.
        event_type: One of ``"modified"``, ``"created"`` or ``"deleted"``.
    """

    path: str
    event_type: str


def _relative_posix(src_path: str, project_root: Path) -> str | None:
    """Resolve a watchdog path to a project-relative posix path.

    Returns ``None`` when the path cannot be resolved inside the project
    root. Windows extended-length (``\\\\?\\``) prefixes, as emitted by
    some file-system activity, are stripped before resolving.

    Args:
        src_path: Absolute path reported by the file system.
        project_root: Root directory of the watched project.

    Returns:
        The project-relative posix path, or ``None`` when the path lies
        outside the project root or cannot be resolved.
    """
    raw = src_path
    if raw.startswith("\\\\?\\"):
        raw = raw[4:]
    try:
        return (
            Path(raw).resolve().relative_to(project_root.resolve()).as_posix()
        )
    except ValueError:
        return None


class WatchdogEventSource:
    """File event source backed by a watchdog observer.

    Yields :class:`FileEvent` records for watched ``.gd`` files, with paths
    relative to the project root. Events outside the watch scope (non-.gd
    files and standard excludes) are filtered out.
    """

    def __init__(self, project_root: Path) -> None:
        """Create the source and start the underlying watchdog observer.

        Args:
            project_root: Root directory of the Godot project to watch.
        """
        self._project_root = project_root
        self._queue: queue.Queue[FileEvent | None] = queue.Queue()
        self._stopped = False
        self._observer = Observer()
        self._observer.schedule(
            self._handler(), str(project_root), recursive=True
        )
        self._observer.start()

    def _handler(self) -> FileSystemEventHandler:
        """Build the watchdog event handler mapping events onto the queue."""
        source = self

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event: FileSystemEvent) -> None:
                # An observer callback must never raise: an exception here
                # kills the watchdog emitter thread and silently stalls
                # the event stream.
                try:
                    source._enqueue(event)
                except Exception:  # noqa: BLE001 - protect the emitter
                    return

        return _Handler()

    def _enqueue(self, watchdog_event: FileSystemEvent) -> None:
        """Filter and queue a watchdog event, if it is in scope."""
        if self._stopped:
            return
        if watchdog_event.event_type not in ("modified", "created", "deleted"):
            return
        relative_posix = _relative_posix(
            str(watchdog_event.src_path), self._project_root
        )
        if relative_posix is None or not is_watched_path(relative_posix):
            return
        self._queue.put(
            FileEvent(relative_posix, str(watchdog_event.event_type))
        )

    def events(self) -> Iterator[FileEvent | None]:
        """Yield file events as they arrive.

        Yields :class:`FileEvent` records for in-scope activity, or ``None``
        as a poll tick when no event arrived within the polling window, so
        consumers can interleave waiting with their own periodic checks
        (e.g. coalescer state). The generator terminates after
        :meth:`stop` is called.
        """
        while not self._stopped:
            try:
                event = self._queue.get(timeout=_POLL_TIMEOUT_SECONDS)
            except queue.Empty:
                yield None
                continue
            yield event

    def stop(self) -> None:
        """Stop the watchdog observer and terminate the event stream."""
        self._stopped = True
        self._observer.stop()
        self._observer.join(timeout=2.0)
