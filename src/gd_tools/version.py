"""Version detection for gd-tools components.

This module provides the ``collect_versions()`` function, which gathers
version information for all gd-tools components: gd-tools itself, Godot
Engine, gdtoolkit, and Python.
"""

import importlib.metadata
import sys

from . import __version__
from .config import GodotConfig
from .errors import GodotNotFoundError
from .godot import find_godot


def collect_versions() -> dict[str, str | None]:
    """Collect version strings for all gd-tools components.

    Returns:
        A dictionary mapping component names to version strings.
        Missing components have a value of ``None``. The keys are:
        ``gd-tools``, ``godot``, ``gdtoolkit``, ``python``.
    """
    versions: dict[str, str | None] = {}

    # gd-tools version (always available)
    versions["gd-tools"] = __version__

    # Godot version
    try:
        godot_info = find_godot(GodotConfig())
        versions["godot"] = godot_info.version
    except GodotNotFoundError:
        versions["godot"] = None

    # gdtoolkit version
    try:
        versions["gdtoolkit"] = importlib.metadata.version("gdtoolkit")
    except importlib.metadata.PackageNotFoundError:
        versions["gdtoolkit"] = None

    # Python version (always available)
    versions["python"] = sys.version

    return versions
