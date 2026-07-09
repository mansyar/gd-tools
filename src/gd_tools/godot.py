"""Godot binary detection and invocation module.

Resolves the Godot binary path via a 5-level priority chain, detects
and validates the Godot version, maps Godot versions to compatible
GUT versions, and provides a subprocess wrapper for invoking Godot.
"""

from dataclasses import dataclass


@dataclass
class GodotInfo:
    """Information about a detected Godot binary.

    Attributes:
        path: Resolved binary path.
        version: Parsed version string (e.g., "4.5.1").
        is_valid: True if version >= 4.5.0.
    """

    path: str
    version: str
    is_valid: bool
