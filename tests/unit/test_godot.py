"""Unit tests for the Godot binary detection and invocation module.

Covers GodotInfo dataclass, binary resolution chain, version
detection/validation, GUT version mapping, and the subprocess wrapper.
"""

import pytest

from gd_tools.godot import GodotInfo

# --- GodotInfo dataclass ---


@pytest.mark.unit
def test_godot_info_construction_valid():
    """Test GodotInfo construction with valid path, version, is_valid."""
    info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)
    assert info.path == "/usr/bin/godot"
    assert info.version == "4.5.1"
    assert info.is_valid is True


@pytest.mark.unit
def test_godot_info_construction_unknown_version():
    """Test GodotInfo with version='unknown' and is_valid=False."""
    info = GodotInfo(path="/some/path", version="unknown", is_valid=False)
    assert info.path == "/some/path"
    assert info.version == "unknown"
    assert info.is_valid is False
