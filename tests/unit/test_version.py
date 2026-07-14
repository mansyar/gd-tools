"""Unit tests for the version detection module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.version import collect_versions

pytestmark = pytest.mark.unit


def test_collect_versions_all_found():
    """Test collect_versions when all 5 components are found."""
    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch(
            "gd_tools.version.find_project_root",
            return_value=Path("/fake/project"),
        ),
        patch(
            "gd_tools.version.get_installed_gut_version",
            return_value="7.5.0",
        ),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] == "4.5.1-stable"
    assert result["gut"] == "7.5.0"
    assert result["gdtoolkit"] == "4.5.1"
    assert result["python"] == sys.version


def test_collect_versions_godot_not_found():
    """Test collect_versions when Godot is not detected."""
    from gd_tools.errors import GodotNotFoundError

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch(
            "gd_tools.version.find_godot",
            side_effect=GodotNotFoundError("not found"),
        ),
        patch(
            "gd_tools.version.find_project_root",
            return_value=Path("/fake/project"),
        ),
        patch(
            "gd_tools.version.get_installed_gut_version",
            return_value="7.5.0",
        ),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] is None
    assert result["gut"] == "7.5.0"
    assert result["gdtoolkit"] == "4.5.1"
    assert result["python"] == sys.version


def test_collect_versions_gut_not_installed():
    """Test collect_versions when GUT is not installed (returns None)."""
    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch(
            "gd_tools.version.find_project_root",
            return_value=Path("/fake/project"),
        ),
        patch(
            "gd_tools.version.get_installed_gut_version",
            return_value=None,
        ),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] == "4.5.1-stable"
    assert result["gut"] is None
    assert result["gdtoolkit"] == "4.5.1"
    assert result["python"] == sys.version


def test_collect_versions_gut_no_project_root():
    """Test collect_versions when no project root is found for GUT."""
    from gd_tools.errors import ConfigError

    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch(
            "gd_tools.version.find_project_root",
            side_effect=ConfigError("no project"),
        ),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] == "4.5.1-stable"
    assert result["gut"] is None
    assert result["gdtoolkit"] == "4.5.1"
    assert result["python"] == sys.version


def test_collect_versions_gdtoolkit_not_installed():
    """Test collect_versions when gdtoolkit is not installed."""
    from importlib.metadata import PackageNotFoundError

    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    def mock_version(name):
        if name == "gdtoolkit":
            raise PackageNotFoundError("gdtoolkit")
        return "1.2.3"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch(
            "gd_tools.version.find_project_root",
            return_value=Path("/fake/project"),
        ),
        patch(
            "gd_tools.version.get_installed_gut_version",
            return_value="7.5.0",
        ),
        patch("importlib.metadata.version", side_effect=mock_version),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] == "4.5.1-stable"
    assert result["gut"] == "7.5.0"
    assert result["gdtoolkit"] is None
    assert result["python"] == sys.version


def test_collect_versions_return_structure():
    """Test that collect_versions returns a dict with exactly 5 keys."""
    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch(
            "gd_tools.version.find_project_root",
            return_value=Path("/fake/project"),
        ),
        patch(
            "gd_tools.version.get_installed_gut_version",
            return_value="7.5.0",
        ),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "gd-tools",
        "godot",
        "gut",
        "gdtoolkit",
        "python",
    }
