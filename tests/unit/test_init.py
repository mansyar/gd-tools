"""Unit tests for the init command module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import zipfile

import pytest
import requests

from gd_tools.config import GdToolsConfig
from gd_tools.errors import GdToolsError, GodotNotFoundError
from gd_tools.godot import GodotInfo
from gd_tools.test_runner import is_gut_installed
from gd_tools.init import (
    create_config_file,
    create_data_dir,
    detect_godot_version,
    download_gut,
    enable_gut_plugin,
    extract_gut,
    generate_lint_format_rcs,
    get_installed_gut_version,
    install_coverage_addon,
    install_gut,
    print_summary,
    register_coverage_autoload,
    run_init,
    update_gutconfig,
)

pytestmark = pytest.mark.unit

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
    """Test is_gut_installed returns True when gut.gd exists."""
    gut_dir = tmp_path / "addons" / "gut"
    gut_dir.mkdir(parents=True)
    (gut_dir / "gut.gd").touch()
    assert is_gut_installed(tmp_path) is True


def test_check_gut_installed_returns_false_when_absent(tmp_path: Path):
    """Test is_gut_installed returns False when gut.gd does not exist."""
    assert is_gut_installed(tmp_path) is False


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
        patch("gd_tools.init.is_gut_installed", return_value=False),
        patch("gd_tools.init.click.confirm", return_value=True),
        patch("gd_tools.init.download_gut") as mock_download,
        patch("gd_tools.init.extract_gut") as mock_extract,
        patch(
            "gd_tools.init.get_gut_version_for_godot",
            return_value="9.5.0",
        ),
    ):
        result = install_gut(tmp_path, "4.5.1", non_interactive=False)
    assert result is True
    mock_download.assert_called_once()
    mock_extract.assert_called_once()


def test_install_gut_non_interactive_assumes_yes(tmp_path: Path):
    """Test install_gut installs without prompting in non-interactive mode."""
    with (
        patch("gd_tools.init.is_gut_installed", return_value=False),
        patch("gd_tools.init.click.confirm") as mock_confirm,
        patch("gd_tools.init.download_gut") as mock_download,
        patch("gd_tools.init.extract_gut") as mock_extract,
        patch(
            "gd_tools.init.get_gut_version_for_godot",
            return_value="9.5.0",
        ),
    ):
        result = install_gut(tmp_path, "4.5.1", non_interactive=True)
    assert result is True
    mock_confirm.assert_not_called()
    mock_download.assert_called_once()
    mock_extract.assert_called_once()


def test_install_gut_user_declines_prints_manual_instructions(
    tmp_path: Path,
):
    """Test install_gut prints manual instructions when user declines."""
    with (
        patch("gd_tools.init.is_gut_installed", return_value=False),
        patch("gd_tools.init.click.confirm", return_value=False),
        patch("gd_tools.init.download_gut") as mock_download,
        patch("gd_tools.init.extract_gut") as mock_extract,
        patch("gd_tools.init.console.print") as mock_print,
    ):
        result = install_gut(tmp_path, "4.5.1", non_interactive=False)
    assert result is False
    mock_download.assert_not_called()
    mock_extract.assert_not_called()
    mock_print.assert_called()
    printed = " ".join(str(c) for c in mock_print.call_args[0])
    assert "manual" in printed.lower() or "install" in printed.lower()


def test_install_gut_version_mismatch_warning(tmp_path: Path):
    """Test install_gut warns when installed GUT version doesn't match."""
    with (
        patch("gd_tools.init.is_gut_installed", return_value=True),
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
        result = install_gut(tmp_path, "4.5.1", non_interactive=False)
    assert result is True
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


# --- register_coverage_autoload ---


def test_register_coverage_autoload_creates_section_when_missing(
    tmp_path: Path,
):
    """Test register_coverage_autoload adds [autoload] section to a file
    without it."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text("config_version=5\n\n[application]\n\n")

    register_coverage_autoload(tmp_path)

    content = project_godot.read_text()
    assert "[autoload]" in content
    assert (
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"' in content
    )


def test_register_coverage_autoload_idempotent(tmp_path: Path):
    """Test register_coverage_autoload doesn't duplicate when already
    registered."""
    project_godot = tmp_path / "project.godot"
    original = (
        "config_version=5\n\n"
        "[autoload]\n\n"
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"\n'
    )
    project_godot.write_text(original)

    register_coverage_autoload(tmp_path)

    assert project_godot.read_text() == original


def test_register_coverage_autoload_replaces_wrong_path(tmp_path: Path):
    """Test register_coverage_autoload replaces an existing entry with a
    different path instead of creating a duplicate."""
    project_godot = tmp_path / "project.godot"
    original = (
        "config_version=5\n\n"
        "[autoload]\n\n"
        '_GDTCoverage="*res://addons/gd-tools-coverage/tracker.gd"\n'
    )
    project_godot.write_text(original)

    register_coverage_autoload(tmp_path)

    content = project_godot.read_text()
    assert (
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"' in content
    )
    assert "tracker.gd" not in content
    # Ensure no duplicate _GDTCoverage entries.
    assert content.count("_GDTCoverage=") == 1


def test_register_coverage_autoload_preserves_existing_autoloads(
    tmp_path: Path,
):
    """Test register_coverage_autoload preserves existing autoload entries."""
    project_godot = tmp_path / "project.godot"
    original = (
        "config_version=5\n\n"
        "[autoload]\n\n"
        'GlobalSignals="*res://autoloads/global_signals.gd"\n'
        'PlayerData="*res://autoloads/player_data.gd"\n'
    )
    project_godot.write_text(original)

    register_coverage_autoload(tmp_path)

    content = project_godot.read_text()
    assert 'GlobalSignals="*res://autoloads/global_signals.gd"' in content
    assert 'PlayerData="*res://autoloads/player_data.gd"' in content
    assert (
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"' in content
    )


def test_register_coverage_autoload_handles_no_trailing_newline(
    tmp_path: Path,
):
    """Test register_coverage_autoload handles content without trailing
    newline."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text('config_version=5\n\n[application]\n\nname="Test"')

    register_coverage_autoload(tmp_path)

    content = project_godot.read_text()
    assert "[autoload]" in content
    assert (
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"' in content
    )


# --- install_coverage_addon ---


def test_install_coverage_addon_copies_all_files(tmp_path: Path):
    """Test install_coverage_addon copies all 3 .gd files to project."""
    install_coverage_addon(tmp_path)

    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    assert (target_dir / "coverage.gd").exists()
    assert (target_dir / "pre_run_hook.gd").exists()
    assert (target_dir / "post_run_hook.gd").exists()


def test_install_coverage_addon_overwrites_stale_files(tmp_path: Path):
    """Test install_coverage_addon overwrites existing stale files."""
    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True)
    for gd_file in ["coverage.gd", "pre_run_hook.gd", "post_run_hook.gd"]:
        (target_dir / gd_file).write_text("old stale content")

    install_coverage_addon(tmp_path)

    for gd_file in ["coverage.gd", "pre_run_hook.gd", "post_run_hook.gd"]:
        content = (target_dir / gd_file).read_text()
        assert content != "old stale content"


def test_install_coverage_addon_creates_target_dir(tmp_path: Path):
    """Test install_coverage_addon creates the target directory."""
    assert not (tmp_path / "addons" / "gd-tools-coverage").exists()

    install_coverage_addon(tmp_path)

    assert (tmp_path / "addons" / "gd-tools-coverage").is_dir()


def test_install_coverage_addon_deploys_real_implementation(tmp_path: Path):
    """Test install_coverage_addon deploys real coverage.gd (not placeholder)."""
    install_coverage_addon(tmp_path)

    coverage_gd = (
        tmp_path / "addons" / "gd-tools-coverage" / "coverage.gd"
    ).read_text()
    # Placeholder had a TODO comment; real implementation must not.
    assert "TODO" not in coverage_gd
    # Key markers of the real implementation.
    assert "var _hits" in coverage_gd
    assert "func _ready()" in coverage_gd
    assert "func hit(" in coverage_gd
    assert "func reset()" in coverage_gd
    assert "func set_active(" in coverage_gd
    assert "func is_active()" in coverage_gd


# --- update_gutconfig ---


def test_update_gutconfig_creates_new_with_template(tmp_path: Path):
    """Test update_gutconfig creates .gutconfig.json from template if missing."""
    config = GdToolsConfig()
    update_gutconfig(tmp_path, config)

    gutconfig = tmp_path / ".gutconfig.json"
    assert gutconfig.exists()
    data = json.loads(gutconfig.read_text())
    assert data["dirs"] == ["res://test/", "res://tests/"]
    assert data["include_subdirs"] is True
    assert data["prefix"] == "test_"
    assert data["suffix"] == ".gd"
    assert data["should_exit"] is True
    assert data["junit_xml_file"] == ".gd-tools/results.xml"
    assert (
        data["pre_run_script"]
        == "res://addons/gd-tools-coverage/pre_run_hook.gd"
    )
    assert (
        data["post_run_script"]
        == "res://addons/gd-tools-coverage/post_run_hook.gd"
    )


def test_update_gutconfig_merges_existing_preserves_user_keys(
    tmp_path: Path,
):
    """Test update_gutconfig preserves user's dirs/prefix/suffix/include_subdirs."""
    gutconfig = tmp_path / ".gutconfig.json"
    existing = {
        "dirs": ["res://my_tests/"],
        "include_subdirs": False,
        "prefix": "spec_",
        "suffix": ".gd",
        "should_exit": False,
        "junit_xml_file": "old/path.xml",
        "pre_run_script": "old/pre.gd",
        "post_run_script": "old/post.gd",
    }
    gutconfig.write_text(json.dumps(existing))

    config = GdToolsConfig()
    update_gutconfig(tmp_path, config)

    data = json.loads(gutconfig.read_text())
    # User keys preserved
    assert data["dirs"] == ["res://my_tests/"]
    assert data["include_subdirs"] is False
    assert data["prefix"] == "spec_"
    assert data["suffix"] == ".gd"
    # Hook keys overwritten
    assert data["should_exit"] is True
    assert data["junit_xml_file"] == ".gd-tools/results.xml"
    assert (
        data["pre_run_script"]
        == "res://addons/gd-tools-coverage/pre_run_hook.gd"
    )
    assert (
        data["post_run_script"]
        == "res://addons/gd-tools-coverage/post_run_hook.gd"
    )


def test_update_gutconfig_overwrites_hook_keys(tmp_path: Path):
    """Test update_gutconfig always overwrites hook-related keys."""
    gutconfig = tmp_path / ".gutconfig.json"
    existing = {
        "dirs": ["res://test/"],
        "include_subdirs": True,
        "prefix": "test_",
        "suffix": ".gd",
        "should_exit": False,
        "junit_xml_file": "custom/results.xml",
        "pre_run_script": "custom/pre.gd",
        "post_run_script": "custom/post.gd",
    }
    gutconfig.write_text(json.dumps(existing))

    config = GdToolsConfig()
    update_gutconfig(tmp_path, config)

    data = json.loads(gutconfig.read_text())
    assert data["should_exit"] is True
    assert data["junit_xml_file"] == ".gd-tools/results.xml"
    assert (
        data["pre_run_script"]
        == "res://addons/gd-tools-coverage/pre_run_hook.gd"
    )
    assert (
        data["post_run_script"]
        == "res://addons/gd-tools-coverage/post_run_hook.gd"
    )


def test_update_gutconfig_preserves_custom_dirs(tmp_path: Path):
    """Test update_gutconfig preserves custom dirs from existing config."""
    gutconfig = tmp_path / ".gutconfig.json"
    existing = {
        "dirs": ["res://unit/", "res://integration/"],
        "include_subdirs": True,
        "prefix": "test_",
        "suffix": ".gd",
    }
    gutconfig.write_text(json.dumps(existing))

    config = GdToolsConfig()
    update_gutconfig(tmp_path, config)

    data = json.loads(gutconfig.read_text())
    assert data["dirs"] == ["res://unit/", "res://integration/"]
    # Hook keys should be added
    assert "should_exit" in data
    assert "junit_xml_file" in data
    assert "pre_run_script" in data
    assert "post_run_script" in data


# --- create_config_file ---


def test_create_config_file_creates_defaults_if_missing(tmp_path: Path):
    """Test create_config_file creates gd-tools.toml with defaults if missing."""
    config = GdToolsConfig()
    create_config_file(tmp_path, config)

    config_file = tmp_path / "gd-tools.toml"
    assert config_file.exists()
    # Verify it's valid TOML with expected structure
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    with open(config_file, "rb") as f:
        data = tomllib.load(f)
    assert "godot" in data
    assert "test" in data
    assert "lint" in data
    assert "format" in data
    assert "coverage" in data


def test_create_config_file_preserves_existing(tmp_path: Path):
    """Test create_config_file does not overwrite existing gd-tools.toml."""
    config_file = tmp_path / "gd-tools.toml"
    original_content = (
        "[godot]\nbinary = '/custom/godot'\n\n"
        "[test]\ntest_dirs = ['my_tests']\n"
    )
    config_file.write_text(original_content)

    config = GdToolsConfig()
    create_config_file(tmp_path, config)

    assert config_file.read_text() == original_content


# --- generate_lint_format_rcs ---


def test_generate_rcs_generates_if_missing(tmp_path: Path):
    """Test generate_lint_format_rcs creates gdlintrc and gdformatrc if missing."""
    config = GdToolsConfig()
    generate_lint_format_rcs(tmp_path, config)

    assert (tmp_path / "gdlintrc").exists()
    assert (tmp_path / "gdformatrc").exists()
    # Verify content is non-empty
    assert (tmp_path / "gdlintrc").read_text().strip()
    assert (tmp_path / "gdformatrc").read_text().strip()


def test_generate_rcs_warns_if_differs(tmp_path: Path):
    """Test generate_lint_format_rcs warns but does not overwrite when content differs."""
    # Create files with wrong content
    (tmp_path / "gdlintrc").write_text("wrong content\n")
    (tmp_path / "gdformatrc").write_text("also wrong\n")

    config = GdToolsConfig()
    with patch("gd_tools.init.console.print") as mock_print:
        generate_lint_format_rcs(tmp_path, config)

    # Files should NOT be overwritten
    assert (tmp_path / "gdlintrc").read_text() == "wrong content\n"
    assert (tmp_path / "gdformatrc").read_text() == "also wrong\n"
    # Warning should have been printed
    assert mock_print.called


def test_generate_rcs_skips_if_matches(tmp_path: Path):
    """Test generate_lint_format_rcs does nothing when files already match."""
    # Generate correct files using existing functions
    from gd_tools.config import generate_gdlintrc, generate_gdformatrc

    config = GdToolsConfig()
    generate_gdlintrc(config, tmp_path)
    generate_gdformatrc(config, tmp_path)

    original_lint = (tmp_path / "gdlintrc").read_text()
    original_format = (tmp_path / "gdformatrc").read_text()

    with patch("gd_tools.init.console.print") as mock_print:
        generate_lint_format_rcs(tmp_path, config)

    # Files should be unchanged
    assert (tmp_path / "gdlintrc").read_text() == original_lint
    assert (tmp_path / "gdformatrc").read_text() == original_format
    # No warning should be printed
    assert not mock_print.called


# --- create_data_dir ---


def test_create_data_dir_creates_directory(tmp_path: Path):
    """Test create_data_dir creates the .gd-tools directory."""
    create_data_dir(tmp_path)
    assert (tmp_path / ".gd-tools").is_dir()


def test_create_data_dir_adds_to_gitignore(tmp_path: Path):
    """Test create_data_dir appends .gd-tools/ to existing .gitignore."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.tmp\nbuild/\n", encoding="utf-8")
    create_data_dir(tmp_path)
    content = gitignore.read_text(encoding="utf-8")
    assert ".gd-tools/" in content
    assert "*.tmp" in content
    assert "build/" in content


def test_create_data_dir_gitignore_idempotent(tmp_path: Path):
    """Test create_data_dir does not add duplicate .gd-tools/ entries."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".gd-tools/\n*.tmp\n", encoding="utf-8")
    create_data_dir(tmp_path)
    content = gitignore.read_text(encoding="utf-8")
    assert content.count(".gd-tools/") == 1


def test_create_data_dir_creates_gitignore_if_missing(tmp_path: Path):
    """Test create_data_dir creates .gitignore if it does not exist."""
    create_data_dir(tmp_path)
    gitignore = tmp_path / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert ".gd-tools/" in content


# --- print_summary ---


def test_print_summary_lists_actions(tmp_path: Path):
    """Test print_summary lists all actions taken."""
    actions = [
        "Created .gd-tools/ directory",
        "Installed GUT v9.5.0",
        "Enabled GUT plugin in project.godot",
    ]
    with patch("gd_tools.init.console.print") as mock_print:
        print_summary(tmp_path, actions)
    # Verify all actions appear in the output
    printed_text = " ".join(
        str(call.args[0]) for call in mock_print.call_args_list
    )
    for action in actions:
        assert action in printed_text


def test_print_summary_prints_next_steps(tmp_path: Path):
    """Test print_summary prints next steps guidance."""
    actions = ["Created .gd-tools/ directory"]
    with patch("gd_tools.init.console.print") as mock_print:
        print_summary(tmp_path, actions)
    printed_text = " ".join(
        str(call.args[0]) for call in mock_print.call_args_list
    )
    assert "gd-tools test" in printed_text


# --- run_init ---


def test_run_init_full_flow_with_mocks(tmp_path: Path):
    """Test run_init calls all steps in the correct order."""
    # Create a project.godot so find_project_root works
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.is_gut_installed", return_value=True),
        patch("gd_tools.init.get_installed_gut_version", return_value="9.5.0"),
        patch("gd_tools.init.install_gut") as mock_install,
        patch("gd_tools.init.enable_gut_plugin") as mock_enable,
        patch("gd_tools.init.install_coverage_addon") as mock_cov,
        patch("gd_tools.init.update_gutconfig") as mock_gutconfig,
        patch("gd_tools.init.create_config_file") as mock_create_config,
        patch("gd_tools.init.generate_lint_format_rcs") as mock_gen_rcs,
        patch("gd_tools.init.create_data_dir") as mock_data_dir,
        patch("gd_tools.init.print_summary") as mock_summary,
    ):
        run_init()

    # All functions should be called
    mock_install.assert_called_once()
    mock_enable.assert_called_once()
    mock_cov.assert_called_once()
    mock_gutconfig.assert_called_once()
    mock_create_config.assert_called_once()
    mock_gen_rcs.assert_called_once()
    mock_data_dir.assert_called_once()
    mock_summary.assert_called_once()


def test_run_init_non_interactive_skips_prompts(tmp_path: Path):
    """Test run_init passes non_interactive to install_gut."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.is_gut_installed", return_value=False),
        patch("gd_tools.init.install_gut") as mock_install,
        patch("gd_tools.init.enable_gut_plugin"),
        patch("gd_tools.init.install_coverage_addon"),
        patch("gd_tools.init.update_gutconfig"),
        patch("gd_tools.init.create_config_file"),
        patch("gd_tools.init.generate_lint_format_rcs"),
        patch("gd_tools.init.create_data_dir"),
        patch("gd_tools.init.print_summary"),
    ):
        run_init(non_interactive=True)

    # install_gut should be called with non_interactive=True
    _, kwargs = mock_install.call_args
    assert (
        kwargs.get("non_interactive") is True
        or mock_install.call_args.args[-1] is True
    )


def test_run_init_collects_actions_list(tmp_path: Path):
    """Test run_init collects actions and passes them to print_summary."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.is_gut_installed", return_value=False),
        patch("gd_tools.init.install_gut"),
        patch("gd_tools.init.enable_gut_plugin"),
        patch("gd_tools.init.install_coverage_addon"),
        patch("gd_tools.init.update_gutconfig"),
        patch("gd_tools.init.create_config_file"),
        patch("gd_tools.init.generate_lint_format_rcs"),
        patch("gd_tools.init.create_data_dir"),
        patch("gd_tools.init.print_summary") as mock_summary,
    ):
        run_init()

    # print_summary should be called with a non-empty actions list
    call_args = mock_summary.call_args
    actions = (
        call_args.args[1] if call_args.args else call_args.kwargs.get("actions")
    )
    assert isinstance(actions, list)
    assert len(actions) > 0


def test_run_init_exits_when_user_declines_gut(tmp_path: Path):
    """Test run_init exits when user declines GUT installation."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.is_gut_installed", return_value=False),
        patch("gd_tools.init.install_gut", return_value=False),
        patch("gd_tools.init.enable_gut_plugin") as mock_enable,
        patch("gd_tools.init.print_summary") as mock_summary,
    ):
        with pytest.raises(SystemExit) as exc_info:
            run_init()

    assert exc_info.value.code == 1
    mock_enable.assert_not_called()
    mock_summary.assert_not_called()


def test_extract_gut_no_addons_gut_dir_raises(tmp_path: Path):
    """extract_gut raises GdToolsError when archive has no addons/gut/."""
    zip_path = tmp_path / "gut.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Gut-9.5.0/README.md", "no addons here")

    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(GdToolsError, match="addons/gut/ directory not found"):
        extract_gut(zip_path, project_root)


def test_extract_gut_removes_existing_dest(tmp_path: Path):
    """extract_gut removes existing addons/gut/ before copying (stale cleanup)."""
    zip_path = tmp_path / "gut.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Gut-9.5.0/addons/gut/gut.gd", "extends Node")

    project_root = tmp_path / "project"
    project_root.mkdir()
    stale_gut = project_root / "addons" / "gut"
    stale_gut.mkdir(parents=True)
    (stale_gut / "old_file.gd").write_text("extends Node")

    extract_gut(zip_path, project_root)

    assert not (stale_gut / "old_file.gd").exists()
    assert (stale_gut / "gut.gd").exists()


def test_enable_gut_plugin_inserts_before_next_section(tmp_path: Path):
    """enable_gut_plugin inserts enabled= before next section header."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "config_version=5\n\n"
        "[editor_plugins]\n\n"
        "[application]\n\n"
        'config/name="MyGame"\n'
    )

    enable_gut_plugin(tmp_path)

    content = project_godot.read_text()
    assert '"res://addons/gut/plugin.gd"' in content
    # enabled= should appear before [application]
    enabled_idx = content.index("enabled=PackedStringArray")
    app_idx = content.index("[application]")
    assert enabled_idx < app_idx


def test_enable_gut_plugin_appends_at_end(tmp_path: Path):
    """enable_gut_plugin appends enabled= at end when no next section."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text("config_version=5\n\n" "[editor_plugins]\n")

    enable_gut_plugin(tmp_path)

    content = project_godot.read_text()
    assert '"res://addons/gut/plugin.gd"' in content
    assert "enabled=PackedStringArray" in content


def test_run_init_gut_installed_version_unknown(tmp_path: Path):
    """run_init reports 'version unknown' when GUT installed but version is None."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.is_gut_installed", return_value=True),
        patch("gd_tools.init.get_installed_gut_version", return_value=None),
        patch("gd_tools.init.install_gut"),
        patch("gd_tools.init.enable_gut_plugin"),
        patch("gd_tools.init.install_coverage_addon"),
        patch("gd_tools.init.update_gutconfig"),
        patch("gd_tools.init.create_config_file"),
        patch("gd_tools.init.generate_lint_format_rcs"),
        patch("gd_tools.init.create_data_dir"),
        patch("gd_tools.init.print_summary") as mock_summary,
    ):
        run_init()

    call_args = mock_summary.call_args
    actions = (
        call_args.args[1] if call_args.args else call_args.kwargs.get("actions")
    )
    assert isinstance(actions, list)
    assert any("version unknown" in a for a in actions)


# --- install_coverage_addon version file ---


def test_install_coverage_addon_writes_version_file(tmp_path: Path):
    """Test install_coverage_addon writes _version.txt to the addon directory."""
    install_coverage_addon(tmp_path)

    version_file = (
        tmp_path / "addons" / "gd-tools-coverage" / "_version.txt"
    )
    assert version_file.exists()


def test_install_coverage_addon_version_file_content(tmp_path: Path):
    """Test _version.txt content matches __version__ with trailing newline."""
    from gd_tools import __version__

    install_coverage_addon(tmp_path)

    version_file = (
        tmp_path / "addons" / "gd-tools-coverage" / "_version.txt"
    )
    content = version_file.read_text(encoding="utf-8")
    assert content == f"{__version__}\n"


def test_install_coverage_addon_overwrites_existing_version_file(
    tmp_path: Path,
):
    """Test re-running init overwrites an existing version file with current
    version."""
    from gd_tools import __version__

    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True)
    (target_dir / "_version.txt").write_text("0.0.1\n", encoding="utf-8")

    install_coverage_addon(tmp_path)

    content = (target_dir / "_version.txt").read_text(encoding="utf-8")
    assert content == f"{__version__}\n"
    assert content != "0.0.1\n"


# --- run_init version file action summary ---


def test_run_init_action_summary_includes_version_file_entry(
    tmp_path: Path,
):
    """Test run_init action summary includes a version file entry."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(
        path="/usr/bin/godot", version="4.5.1", is_valid=True
    )

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.is_gut_installed", return_value=True),
        patch(
            "gd_tools.init.get_installed_gut_version", return_value="9.5.0"
        ),
        patch("gd_tools.init.install_gut"),
        patch("gd_tools.init.enable_gut_plugin"),
        patch("gd_tools.init.install_coverage_addon"),
        patch("gd_tools.init.update_gutconfig"),
        patch("gd_tools.init.create_config_file"),
        patch("gd_tools.init.generate_lint_format_rcs"),
        patch("gd_tools.init.create_data_dir"),
        patch("gd_tools.init.print_summary") as mock_summary,
        patch("gd_tools.init.__version__", "0.3.0"),
    ):
        run_init()

    call_args = mock_summary.call_args
    actions = (
        call_args.args[1] if call_args.args else call_args.kwargs.get("actions")
    )
    assert isinstance(actions, list)
    assert any("version file" in a.lower() for a in actions)
    assert any("v0.3.0" in a for a in actions)
