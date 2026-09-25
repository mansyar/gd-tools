"""Tests for the gd_tools package."""

import pytest

pytestmark = pytest.mark.unit


def test_version():
    """Test that __version__ is defined and is a non-empty string."""
    from gd_tools import __version__

    assert isinstance(__version__, str)
    assert __version__ != ""


def test_native_test_addon_is_bundled():
    """The native Godot runtime ships with the Python package."""
    from pathlib import Path

    import gd_tools

    addon = Path(gd_tools.__file__).parent / "addons" / "gd-tools-test"
    assert (addon / "gd_tools_test.gd").is_file()
    assert (addon / "gd_tools_test_runner.gd").is_file()
    assert (addon / "gd_tools_native_coverage.gd").is_file()
    assert (addon / "gd_tools_test_preflight.gd").is_file()
    assert (addon / "gd_tools_test_context.gd").is_file()
