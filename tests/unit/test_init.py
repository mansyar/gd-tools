"""Unit tests for the init command module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.errors import GodotNotFoundError
from gd_tools.godot import GodotInfo
from gd_tools.init import (
    check_gut_installed,
    detect_godot_version,
    get_installed_gut_version,
)

# --- detect_godot_version ---


def test_detect_godot_version_returns_version():
    """Test detect_godot_version returns the version from GodotInfo."""
    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)
    with patch("gd_tools.init.find_godot", return_value=mock_info):
        result = detect_godot_version(config)
    assert result == "4.5.1"


def test_detect_godot_version_raises_godot_not_found():
    """Test detect_godot_version propagates GodotNotFoundError."""
    config = GdToolsConfig()
    with patch(
        "gd_tools.init.find_godot",
        side_effect=GodotNotFoundError("Godot not found"),
    ):
        with pytest.raises(GodotNotFoundError):
            detect_godot_version(config)


def test_detect_godot_version_warns_if_invalid_version():
    """Test detect_godot_version prints warning when version is invalid."""
    config = GdToolsConfig()
    mock_info = GodotInfo(
        path="/usr/bin/godot", version="4.4.0", is_valid=False
    )
    with (
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.console.print") as mock_print,
    ):
        result = detect_godot_version(config)
    assert result == "4.4.0"
    mock_print.assert_called_once()
    call_args = mock_print.call_args[0][0]
    assert "Warning" in call_args or "warning" in call_args


# --- check_gut_installed ---


def test_check_gut_installed_returns_true_when_present(tmp_path: Path):
    """Test check_gut_installed returns True when gut.gd exists."""
    gut_dir = tmp_path / "addons" / "gut"
    gut_dir.mkdir(parents=True)
    (gut_dir / "gut.gd").touch()
    assert check_gut_installed(tmp_path) is True


def test_check_gut_installed_returns_false_when_absent(tmp_path: Path):
    """Test check_gut_installed returns False when gut.gd does not exist."""
    assert check_gut_installed(tmp_path) is False


# --- get_installed_gut_version ---


def test_get_installed_gut_version_reads_plugin_cfg(tmp_path: Path):
    """Test get_installed_gut_version reads version from plugin.cfg."""
    gut_dir = tmp_path / "addons" / "gut"
    gut_dir.mkdir(parents=True)
    plugin_cfg = gut_dir / "plugin.cfg"
    plugin_cfg.write_text(
        '[plugin]\nname="GUT"\ndescription="Unit Testing"\nauthor="Butch Wesley"\nversion="9.5.0"\nscript="plugin.gd"\n'
    )
    assert get_installed_gut_version(tmp_path) == "9.5.0"


def test_get_installed_gut_version_returns_none_if_no_cfg(tmp_path: Path):
    """Test get_installed_gut_version returns None when plugin.cfg is missing."""
    assert get_installed_gut_version(tmp_path) is None


def test_get_installed_gut_version_returns_none_if_no_version_key(
    tmp_path: Path,
):
    """Test get_installed_gut_version returns None when version key is absent."""
    gut_dir = tmp_path / "addons" / "gut"
    gut_dir.mkdir(parents=True)
    plugin_cfg = gut_dir / "plugin.cfg"
    plugin_cfg.write_text('[plugin]\nname="GUT"\n')
    assert get_installed_gut_version(tmp_path) is None
