"""Unit tests for the init command module."""

from pathlib import Path
from unittest.mock import Mock, patch

import zipfile

import pytest
import requests

from gd_tools.config import GdToolsConfig
from gd_tools.errors import GdToolsError, GodotNotFoundError
from gd_tools.godot import GodotInfo
from gd_tools.init import (
    check_gut_installed,
    detect_godot_version,
    download_gut,
    enable_gut_plugin,
    extract_gut,
    get_installed_gut_version,
    install_gut,
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


# --- download_gut ---


def test_download_gut_downloads_zip(tmp_path: Path):
    """Test download_gut downloads the zip and writes it to dest."""
    mock_response = Mock()
    mock_response.content = b"fake zip data"
    mock_response.raise_for_status = Mock()
    dest = tmp_path / "gut.zip"
    with patch(
        "gd_tools.init.requests.get", return_value=mock_response
    ) as mock_get:
        result = download_gut("9.5.0", dest)
    mock_get.assert_called_once_with(
        "https://github.com/bitwes/Gut/archive/refs/tags/v9.5.0.zip",
        timeout=30,
    )
    assert result == dest
    assert dest.read_bytes() == b"fake zip data"


def test_download_gut_fails_with_instructions_on_network_error(
    tmp_path: Path,
):
    """Test download_gut raises GdToolsError with manual install instructions."""
    dest = tmp_path / "gut.zip"
    with patch(
        "gd_tools.init.requests.get",
        side_effect=requests.RequestException("Connection error"),
    ):
        with pytest.raises(GdToolsError) as exc_info:
            download_gut("9.5.0", dest)
    msg = str(exc_info.value)
    assert "Failed to download GUT" in msg
    assert "github.com/bitwes/Gut" in msg
    assert "asset-library" in msg.lower() or "Asset Library" in msg


# --- extract_gut ---


def test_extract_gut_copies_addons_dir(tmp_path: Path):
    """Test extract_gut copies addons/gut/ from the zip to the project."""
    zip_path = tmp_path / "gut.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Gut-9.5.0/addons/gut/gut.gd", "extends Node")
        zf.writestr(
            "Gut-9.5.0/addons/gut/plugin.cfg",
            '[plugin]\nversion="9.5.0"\n',
        )

    project_root = tmp_path / "project"
    project_root.mkdir()

    extract_gut(zip_path, project_root)

    assert (project_root / "addons" / "gut" / "gut.gd").exists()
    assert (project_root / "addons" / "gut" / "plugin.cfg").exists()


def test_extract_gut_cleans_up_temp_dir(tmp_path: Path):
    """Test extract_gut cleans up the temporary extraction directory."""
    zip_path = tmp_path / "gut.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Gut-9.5.0/addons/gut/gut.gd", "extends Node")

    project_root = tmp_path / "project"
    project_root.mkdir()

    temp_dir = tmp_path / "fake_temp"
    temp_dir.mkdir()

    with patch("gd_tools.init.tempfile.mkdtemp", return_value=str(temp_dir)):
        extract_gut(zip_path, project_root)

    assert not temp_dir.exists()


# --- install_gut ---


def test_install_gut_prompts_interactive_yes(tmp_path: Path):
    """Test install_gut prompts in interactive mode and installs on yes."""
    with (
        patch("gd_tools.init.check_gut_installed", return_value=False),
        patch("gd_tools.init.click.confirm", return_value=True),
        patch("gd_tools.init.download_gut") as mock_download,
        patch("gd_tools.init.extract_gut") as mock_extract,
        patch(
            "gd_tools.init.get_gut_version_for_godot",
            return_value="9.5.0",
        ),
    ):
        install_gut(tmp_path, "4.5.1", non_interactive=False)
    mock_download.assert_called_once()
    mock_extract.assert_called_once()


def test_install_gut_non_interactive_assumes_yes(tmp_path: Path):
    """Test install_gut installs without prompting in non-interactive mode."""
    with (
        patch("gd_tools.init.check_gut_installed", return_value=False),
        patch("gd_tools.init.click.confirm") as mock_confirm,
        patch("gd_tools.init.download_gut") as mock_download,
        patch("gd_tools.init.extract_gut") as mock_extract,
        patch(
            "gd_tools.init.get_gut_version_for_godot",
            return_value="9.5.0",
        ),
    ):
        install_gut(tmp_path, "4.5.1", non_interactive=True)
    mock_confirm.assert_not_called()
    mock_download.assert_called_once()
    mock_extract.assert_called_once()


def test_install_gut_user_declines_prints_manual_instructions(
    tmp_path: Path,
):
    """Test install_gut prints manual instructions when user declines."""
    with (
        patch("gd_tools.init.check_gut_installed", return_value=False),
        patch("gd_tools.init.click.confirm", return_value=False),
        patch("gd_tools.init.download_gut") as mock_download,
        patch("gd_tools.init.extract_gut") as mock_extract,
        patch("gd_tools.init.console.print") as mock_print,
    ):
        install_gut(tmp_path, "4.5.1", non_interactive=False)
    mock_download.assert_not_called()
    mock_extract.assert_not_called()
    mock_print.assert_called()
    printed = " ".join(str(c) for c in mock_print.call_args[0])
    assert "manual" in printed.lower() or "install" in printed.lower()


def test_install_gut_version_mismatch_warning(tmp_path: Path):
    """Test install_gut warns when installed GUT version doesn't match."""
    with (
        patch("gd_tools.init.check_gut_installed", return_value=True),
        patch(
            "gd_tools.init.get_installed_gut_version",
            return_value="9.4.0",
        ),
        patch(
            "gd_tools.init.get_gut_version_for_godot",
            return_value="9.5.0",
        ),
        patch("gd_tools.init.console.print") as mock_print,
        patch("gd_tools.init.download_gut") as mock_download,
    ):
        install_gut(tmp_path, "4.5.1", non_interactive=False)
    mock_download.assert_not_called()
    mock_print.assert_called_once()
    call_args = mock_print.call_args[0][0]
    assert "Warning" in call_args or "warning" in call_args
    assert "9.4.0" in call_args
    assert "9.5.0" in call_args


# --- enable_gut_plugin ---


def test_enable_gut_plugin_adds_section_to_empty_file(tmp_path: Path):
    """Test enable_gut_plugin adds [editor_plugins] to a file without it."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text("config_version=5\n")

    enable_gut_plugin(tmp_path)

    content = project_godot.read_text()
    assert "[editor_plugins]" in content
    assert '"res://addons/gut/plugin.gd"' in content


def test_enable_gut_plugin_adds_entry_to_existing_section(
    tmp_path: Path,
):
    """Test enable_gut_plugin adds GUT to existing enabled list."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "config_version=5\n\n"
        "[editor_plugins]\n\n"
        'enabled=PackedStringArray("res://addons/other/plugin.gd")\n'
    )

    enable_gut_plugin(tmp_path)

    content = project_godot.read_text()
    assert '"res://addons/gut/plugin.gd"' in content
    assert '"res://addons/other/plugin.gd"' in content


def test_enable_gut_plugin_idempotent_no_duplicate(tmp_path: Path):
    """Test enable_gut_plugin doesn't duplicate when already enabled."""
    project_godot = tmp_path / "project.godot"
    original = (
        "config_version=5\n\n"
        "[editor_plugins]\n\n"
        'enabled=PackedStringArray("res://addons/gut/plugin.gd")\n'
    )
    project_godot.write_text(original)

    enable_gut_plugin(tmp_path)

    assert project_godot.read_text() == original


def test_enable_gut_plugin_preserves_existing_content(tmp_path: Path):
    """Test enable_gut_plugin preserves all existing content."""
    project_godot = tmp_path / "project.godot"
    original = (
        "config_version=5\n\n"
        "[application]\n\n"
        'config/name="MyGame"\n'
        'config/icon="res://icon.svg"\n'
    )
    project_godot.write_text(original)

    enable_gut_plugin(tmp_path)

    content = project_godot.read_text()
    assert 'config/name="MyGame"' in content
    assert 'config/icon="res://icon.svg"' in content
    assert "[editor_plugins]" in content
    assert '"res://addons/gut/plugin.gd"' in content
