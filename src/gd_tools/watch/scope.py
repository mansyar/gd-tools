"""Watched-scope resolution and file-event classification for watch mode."""

from __future__ import annotations

import os
from enum import Enum, auto
from pathlib import Path

from gd_tools.file_discovery import discover_gd_files

# Standard watch excludes. Unlike the project-wide DEFAULT_EXCLUDES (which
# prunes the whole ``addons`` tree), watch mode only skips the gd-tools
# deployed addons so user addon code stays watchable. The tool-state
# directory also covers the artifact index (``.gd-tools/artifacts/``).
WATCH_EXCLUDES: list[str] = [
    ".godot",
    ".gd-tools",
    ".git",
    "addons/gd-tools-coverage",
    "addons/gd-tools-test",
]


class WatchAction(Enum):
    """Action the watch loop takes for a file-system event."""

    RUN = auto()
    IGNORE = auto()


def resolve_watched_files(project_root: Path) -> list[str]:
    """Return the ``.gd`` files that make up the watch scope.

    Scans the project root using the standard watch excludes. Called
    (re-)each time the watch loop needs a current snapshot, so files created
    after the initial scan are picked up automatically.

    Args:
        project_root: Root directory of the Godot project.

    Returns:
        List of ``.gd`` file paths relative to ``project_root`` (as strings).
    """
    root = str(project_root)
    return [
        os.path.relpath(file_path, root).replace(os.sep, "/")
        for file_path in discover_gd_files(root, WATCH_EXCLUDES)
    ]


def classify_event(event_type: str) -> WatchAction:
    """Classify a file-system event into the action the watch loop takes.

    Args:
        event_type: Raw event kind reported by the observer layer
            (e.g. ``modified``, ``created``, ``deleted``).

    Returns:
        :attr:`WatchAction.RUN` for events that should schedule a test run,
        :attr:`WatchAction.IGNORE` for everything else.
    """
    if event_type in ("modified", "created"):
        return WatchAction.RUN
    return WatchAction.IGNORE
