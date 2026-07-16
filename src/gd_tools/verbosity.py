"""Verbosity context module for global output level control.

Provides a ``Verbosity`` enum and module-level accessors
``get_verbosity()`` / ``set_verbosity()`` that store and retrieve the
active verbosity level.  The level is set once by the CLI group callback
and read by output helpers and runner modules throughout the package.
"""

from __future__ import annotations

from enum import Enum


class Verbosity(Enum):
    """Global output verbosity level.

    Attributes:
        QUIET: Suppress non-essential output (info, warnings, update
            checks, progress messages).
        DEFAULT: Normal output — the pre-verbosity behavior.
        VERBOSE: Show underlying commands and timing information in
            addition to normal output.
    """

    QUIET = 0
    DEFAULT = 1
    VERBOSE = 2


# Module-level active verbosity level.
_active: Verbosity = Verbosity.DEFAULT


def get_verbosity() -> Verbosity:
    """Return the currently active verbosity level.

    Returns:
        The active :class:`Verbosity` (defaults to ``Verbosity.DEFAULT``).
    """
    return _active


def set_verbosity(level: Verbosity) -> None:
    """Set the active verbosity level.

    Args:
        level: The :class:`Verbosity` level to activate.
    """
    global _active
    _active = level
