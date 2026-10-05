"""Unit tests for the version detection module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from gd_tools.version import collect_versions

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"

pytestmark = pytest.mark.unit


def test_collect_versions_all_found():
    """Test collect_versions when all 4 components are found."""
    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] == "4.5.1-stable"
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
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] is None
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
        patch("importlib.metadata.version", side_effect=mock_version),
    ):
        result = collect_versions()

    assert result["gd-tools"] == "1.2.3"
    assert result["godot"] == "4.5.1-stable"
    assert result["gdtoolkit"] is None
    assert result["python"] == sys.version


def test_collect_versions_return_structure():
    """Test that collect_versions returns a dict with exactly 4 keys."""
    fake_godot_info = MagicMock()
    fake_godot_info.version = "4.5.1-stable"

    with (
        patch("gd_tools.version.__version__", "1.2.3"),
        patch("gd_tools.version.find_godot", return_value=fake_godot_info),
        patch("importlib.metadata.version", return_value="4.5.1"),
    ):
        result = collect_versions()

    assert isinstance(result, dict)
    assert set(result.keys()) == {
        "gd-tools",
        "godot",
        "gdtoolkit",
        "python",
    }


def test_package_version_is_0_7_0():
    """The package version matches the v0.7.0 release being prepared."""
    with PYPROJECT.open("rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["version"] == "0.7.0"
