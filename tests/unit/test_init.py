"""Unit tests for the init command module."""

import shutil
from pathlib import Path
from unittest.mock import patch


import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.errors import GodotNotFoundError
from gd_tools.godot import GodotInfo
from gd_tools.init import (
    EDITOR_PLUGIN_FILES,
    NATIVE_TEST_ADDON_FILES,
    create_config_file,
    create_data_dir,
    detect_godot_version,
    generate_lint_format_rcs,
    install_coverage_addon,
    install_editor_plugin,
    install_native_test_addon,
    print_summary,
    register_coverage_autoload,
    run_init,
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


def test_register_coverage_autoload_prepends_before_existing(tmp_path: Path):
    """_GDTCoverage must be the FIRST entry in [autoload], before existing
    autoloads."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "config_version=5\n\n"
        "[autoload]\n\n"
        'GlobalSignals="*res://autoloads/global_signals.gd"\n'
        'PlayerData="*res://autoloads/player_data.gd"\n'
    )

    register_coverage_autoload(tmp_path)

    content = project_godot.read_text()
    lines = content.split("\n")
    # Collect autoload entry keys in order.
    in_autoload = False
    entry_order: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_autoload = stripped == "[autoload]"
            continue
        if in_autoload and stripped and "=" in stripped:
            entry_order.append(stripped.split("=")[0])

    assert entry_order[0] == "_GDTCoverage"
    assert "GlobalSignals" in entry_order
    assert "PlayerData" in entry_order


def test_register_coverage_autoload_moves_to_first_when_not_first(
    tmp_path: Path,
):
    """When _GDTCoverage is registered but not in position 0, it gets
    moved to position 0."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "config_version=5\n\n"
        "[autoload]\n\n"
        'GlobalSignals="*res://autoloads/global_signals.gd"\n'
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"\n'
    )

    register_coverage_autoload(tmp_path)

    content = project_godot.read_text()
    # Parse autoload entry order.
    lines = content.split("\n")
    in_autoload = False
    entry_order: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_autoload = stripped == "[autoload]"
            continue
        if in_autoload and stripped and "=" in stripped:
            entry_order.append(stripped.split("=")[0])

    assert entry_order[0] == "_GDTCoverage"
    assert "GlobalSignals" in entry_order
    # No duplicate _GDTCoverage entries.
    assert content.count("_GDTCoverage=") == 1


def test_register_coverage_autoload_warns_when_moving(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    """A warning is printed to stderr when _GDTCoverage is moved to
    first position."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "config_version=5\n\n"
        "[autoload]\n\n"
        'GlobalSignals="*res://autoloads/global_signals.gd"\n'
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"\n'
    )

    register_coverage_autoload(tmp_path)

    captured = capsys.readouterr()
    assert "Moved _GDTCoverage to first autoload position" in captured.err


def test_register_coverage_autoload_no_warning_when_already_first(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    """No warning printed when _GDTCoverage is already in position 0."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "config_version=5\n\n"
        "[autoload]\n\n"
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"\n'
        'GlobalSignals="*res://autoloads/global_signals.gd"\n'
    )

    register_coverage_autoload(tmp_path)

    captured = capsys.readouterr()
    assert "Moved _GDTCoverage" not in captured.err
    assert "Moved _GDTCoverage" not in captured.out


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
    """Test install_coverage_addon copies the coverage .gd file to project."""
    install_coverage_addon(tmp_path)

    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    assert (target_dir / "coverage.gd").exists()


def test_install_coverage_addon_overwrites_stale_files(tmp_path: Path):
    """Test install_coverage_addon overwrites existing stale files.

    Stale content differs from the bundled version, so a backup must be
    created for each file before overwriting.
    """
    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True)
    for gd_file in ["coverage.gd"]:
        (target_dir / gd_file).write_text("old stale content")

    install_coverage_addon(tmp_path)

    backups_dir = target_dir / ".backups"
    for gd_file in ["coverage.gd"]:
        content = (target_dir / gd_file).read_text()
        assert content != "old stale content"
        # Backup must exist with the user's modified content
        bak = backups_dir / f"{gd_file}.bak"
        assert bak.exists()
        assert bak.read_text() == "old stale content"


def test_smart_backup_first_install_no_backups(tmp_path: Path):
    """First-time install (no existing addon files) creates no .bak files."""
    install_coverage_addon(tmp_path)

    backups_dir = tmp_path / "addons" / "gd-tools-coverage" / ".backups"
    # No backups should exist on first install
    assert not backups_dir.exists() or not any(backups_dir.iterdir())


def test_smart_backup_unchanged_files_no_backups(tmp_path: Path):
    """Re-init with unmodified files (identical to bundled) creates no .bak."""
    # First install to get the bundled files in place
    install_coverage_addon(tmp_path)

    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    # Capture the bundled content
    bundled_content = {
        gd_file: (target_dir / gd_file).read_bytes()
        for gd_file in ["coverage.gd"]
    }

    # Remove any .backups dir from first install (shouldn't exist, but be safe)
    backups_dir = target_dir / ".backups"
    if backups_dir.exists():
        shutil.rmtree(backups_dir)

    # Re-run init — files are identical to bundled, so no backups
    install_coverage_addon(tmp_path)

    # No .bak files should exist
    assert not backups_dir.exists() or not any(backups_dir.iterdir())
    # Files should still match bundled content
    for gd_file, content in bundled_content.items():
        assert (target_dir / gd_file).read_bytes() == content


def test_smart_backup_modified_coverage_file(tmp_path: Path):
    """Re-init with modified coverage.gd creates backup and warns."""
    # First install
    install_coverage_addon(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-coverage"

    # Modify coverage.gd
    modified_content = "# user customization\n"
    (target_dir / "coverage.gd").write_text(modified_content)

    with patch("gd_tools.init.console.print") as mock_print:
        install_coverage_addon(tmp_path)

    # Backup should exist with the user's modified content
    bak = target_dir / ".backups" / "coverage.gd.bak"
    assert bak.exists()
    assert bak.read_text() == modified_content

    # The target file should now have the bundled content (not the modified)
    source_dir = (
        Path(__file__).parent.parent.parent
        / "src"
        / "gd_tools"
        / "addons"
        / "gd-tools-coverage"
    )
    bundled = (source_dir / "coverage.gd").read_bytes()
    assert (target_dir / "coverage.gd").read_bytes() == bundled

    # A yellow warning should have been printed
    assert mock_print.called
    printed = " ".join(str(c) for c in mock_print.call_args[0])
    assert "coverage.gd" in printed
    assert ".bak" in printed
    assert "yellow" in printed.lower()


def test_smart_backup_modified_coverage_gd(tmp_path: Path):
    """Re-init with modified coverage.gd creates backup and warns."""
    install_coverage_addon(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-coverage"

    modified_content = "# user customization\n"
    (target_dir / "coverage.gd").write_text(modified_content)

    with patch("gd_tools.init.console.print") as mock_print:
        install_coverage_addon(tmp_path)

    bak = target_dir / ".backups" / "coverage.gd.bak"
    assert bak.exists()
    assert bak.read_text() == modified_content

    source_dir = (
        Path(__file__).parent.parent.parent
        / "src"
        / "gd_tools"
        / "addons"
        / "gd-tools-coverage"
    )
    bundled = (source_dir / "coverage.gd").read_bytes()
    assert (target_dir / "coverage.gd").read_bytes() == bundled

    assert mock_print.called
    printed = " ".join(str(c) for c in mock_print.call_args[0])
    assert "coverage.gd" in printed
    assert ".bak" in printed
    assert "yellow" in printed.lower()


def test_smart_backup_creates_backups_dir(tmp_path: Path):
    """The .backups/ subdirectory is auto-created if it does not exist."""
    install_coverage_addon(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-coverage"

    # Modify a file so a backup will be triggered
    (target_dir / "coverage.gd").write_text("modified\n")

    # Ensure .backups does not exist yet
    backups_dir = target_dir / ".backups"
    assert not backups_dir.exists()

    install_coverage_addon(tmp_path)

    # .backups should now exist and contain the backup
    assert backups_dir.is_dir()
    assert (backups_dir / "coverage.gd.bak").exists()


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


def test_print_summary_quiet_shows_one_line_status(tmp_path: Path, capsys):
    """In quiet mode, print_summary shows only a one-line status."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.QUIET)
    actions = ["Created .gd-tools/ directory", "Installed GUT v9.5.0"]
    print_summary(tmp_path, actions)
    captured = capsys.readouterr()
    # Should NOT show detailed output
    assert "Actions taken" not in captured.out
    assert "Next steps" not in captured.out
    assert "gd-tools init complete" not in captured.out
    # Should show a one-line status
    assert "OK" in captured.out
    assert "Initialized" in captured.out


# --- install_native_test_addon ---


def test_install_native_test_addon_copies_bundled_files(tmp_path: Path):
    """Native initialization deploys all managed runtime files."""
    install_native_test_addon(tmp_path)

    target_dir = tmp_path / "addons" / "gd-tools-test"
    assert (target_dir / "gd_tools_test.gd").is_file()
    assert (target_dir / "gd_tools_test_runner.gd").is_file()
    assert (target_dir / "gd_tools_native_coverage.gd").is_file()
    assert (target_dir / "_version.txt").is_file()


def test_install_native_test_addon_backs_up_modified_files(tmp_path: Path):
    """Reinitializing preserves user-modified native files before replacement."""
    install_native_test_addon(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-test"
    modified = "# user customization\n"
    (target_dir / "gd_tools_test.gd").write_text(modified, encoding="utf-8")

    with patch("gd_tools.init.console.print") as mock_print:
        install_native_test_addon(tmp_path)

    backup = target_dir / ".backups" / "gd_tools_test.gd.bak"
    assert backup.read_text(encoding="utf-8") == modified
    assert (target_dir / "gd_tools_test.gd").read_text(
        encoding="utf-8"
    ) != modified
    assert "Backed up" in " ".join(
        str(call.args[0]) for call in mock_print.call_args_list
    )


def test_install_native_test_addon_does_not_backup_unchanged_files(
    tmp_path: Path,
):
    """A repeated native install does not create unnecessary backups."""
    install_native_test_addon(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-test"
    backups_dir = target_dir / ".backups"
    if backups_dir.exists():
        shutil.rmtree(backups_dir)

    install_native_test_addon(tmp_path)

    assert not backups_dir.exists() or not any(backups_dir.iterdir())


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
        patch("gd_tools.init.install_native_test_addon") as mock_native,
        patch("gd_tools.init.install_coverage_addon") as mock_cov,
        patch("gd_tools.init.create_config_file") as mock_create_config,
        patch("gd_tools.init.generate_lint_format_rcs") as mock_gen_rcs,
        patch("gd_tools.init.create_data_dir") as mock_data_dir,
        patch("gd_tools.init.print_summary") as mock_summary,
    ):
        run_init()

    # All functions should be called
    mock_native.assert_called_once_with(tmp_path)
    mock_cov.assert_called_once()
    mock_create_config.assert_called_once()
    mock_gen_rcs.assert_called_once()
    mock_data_dir.assert_called_once()
    mock_summary.assert_called_once()


def test_run_init_collects_actions_list(tmp_path: Path):
    """Test run_init collects actions and passes them to print_summary."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.install_coverage_addon"),
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


# --- install_coverage_addon version file ---


def test_install_coverage_addon_writes_version_file(tmp_path: Path):
    """Test install_coverage_addon writes _version.txt to the addon directory."""
    install_coverage_addon(tmp_path)

    version_file = tmp_path / "addons" / "gd-tools-coverage" / "_version.txt"
    assert version_file.exists()


def test_install_coverage_addon_version_file_content(tmp_path: Path):
    """Test _version.txt content matches __version__ with trailing newline."""
    from gd_tools import __version__

    install_coverage_addon(tmp_path)

    version_file = tmp_path / "addons" / "gd-tools-coverage" / "_version.txt"
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


def test_install_native_test_addon_copies_runtime_files(tmp_path: Path):
    """Native init deploys the bundled test addon and version marker."""
    install_native_test_addon(tmp_path)

    addon_dir = tmp_path / "addons" / "gd-tools-test"
    assert (addon_dir / "gd_tools_test.gd").is_file()
    assert (addon_dir / "gd_tools_test_runner.gd").is_file()
    assert (addon_dir / "gd_tools_native_coverage.gd").is_file()
    assert (addon_dir / "_version.txt").read_text(encoding="utf-8")


def test_install_native_test_addon_deploys_integration_files(
    tmp_path: Path,
):
    """Native init deploys the preflight and integration context scripts."""
    install_native_test_addon(tmp_path)

    addon_dir = tmp_path / "addons" / "gd-tools-test"
    assert (addon_dir / "gd_tools_test_preflight.gd").is_file()
    assert (addon_dir / "gd_tools_test_context.gd").is_file()


def test_install_native_test_addon_deploys_mock_module(tmp_path: Path):
    """Native init deploys the bundled mock module used by double()/stub()."""
    install_native_test_addon(tmp_path)

    addon_dir = tmp_path / "addons" / "gd-tools-test"
    assert (addon_dir / "gd_tools_mock.gd").is_file()


def test_install_native_test_addon_lists_every_bundled_script() -> None:
    """Every bundled native addon script is part of the managed file list."""
    addon_source = Path(__file__).parent.parent.parent.joinpath(
        "src", "gd_tools", "addons", "gd-tools-test"
    )
    bundled = {
        path.name
        for path in addon_source.glob("*.gd")
        if not path.name.startswith("_")
    }

    assert bundled == set(NATIVE_TEST_ADDON_FILES)


# --- run_init version file action summary ---


def test_run_init_action_summary_includes_version_file_entry(
    tmp_path: Path,
):
    """Test run_init action summary includes a version file entry."""
    (tmp_path / "project.godot").write_text("config_version=5\n")

    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.install_coverage_addon"),
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


# --- install_editor_plugin ---


def test_install_editor_plugin_copies_bundled_files(tmp_path: Path):
    """Editor plugin init deploys all managed plugin files."""
    from gd_tools import __version__

    install_editor_plugin(tmp_path)

    target_dir = tmp_path / "addons" / "gd-tools-editor"
    assert (target_dir / "plugin.cfg").is_file()
    assert (target_dir / "plugin.gd").is_file()
    assert (target_dir / "dock.gd").is_file()
    assert (target_dir / "coverage_overlay.gd").is_file()
    version = (target_dir / "_version.txt").read_text(encoding="utf-8")
    assert version == f"{__version__}\n"


def test_install_editor_plugin_backs_up_modified_files(tmp_path: Path):
    """Reinitializing preserves user-modified editor files before replacement."""
    install_editor_plugin(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-editor"
    modified = "# user customization\n"
    (target_dir / "dock.gd").write_text(modified, encoding="utf-8")

    with patch("gd_tools.init.console.print") as mock_print:
        install_editor_plugin(tmp_path)

    backup = target_dir / ".backups" / "dock.gd.bak"
    assert backup.read_text(encoding="utf-8") == modified
    assert (target_dir / "dock.gd").read_text(encoding="utf-8") != modified
    assert "Backed up" in " ".join(
        str(call.args[0]) for call in mock_print.call_args_list
    )


def test_install_editor_plugin_does_not_backup_unchanged_files(tmp_path: Path):
    """A repeated editor plugin install does not create unnecessary backups."""
    install_editor_plugin(tmp_path)
    target_dir = tmp_path / "addons" / "gd-tools-editor"
    backups_dir = target_dir / ".backups"
    if backups_dir.exists():
        shutil.rmtree(backups_dir)

    install_editor_plugin(tmp_path)

    assert not backups_dir.exists() or not any(backups_dir.iterdir())


def test_install_editor_plugin_lists_every_bundled_script() -> None:
    """Every bundled editor plugin script is part of the managed file list."""
    addon_source = Path(__file__).parent.parent.parent.joinpath(
        "src", "gd_tools", "addons", "gd-tools-editor"
    )
    bundled = {
        path.name
        for path in addon_source.glob("*.gd")
        if not path.name.startswith("_")
    }

    assert bundled == {"plugin.gd", "dock.gd", "coverage_overlay.gd"}


def test_install_editor_plugin_covers_all_declared_files(tmp_path: Path):
    """The managed file list covers every bundled editor addon file."""
    addon_source = Path(__file__).parent.parent.parent.joinpath(
        "src", "gd_tools", "addons", "gd-tools-editor"
    )
    bundled = {
        path.name
        for path in addon_source.iterdir()
        if path.is_file() and not path.name.startswith("_")
    }

    assert bundled == set(EDITOR_PLUGIN_FILES)


def test_run_init_deploys_editor_plugin(tmp_path: Path):
    """Native init deploys the editor plugin addon by default."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    config = GdToolsConfig()
    mock_info = GodotInfo(path="/usr/bin/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.load_config", return_value=config),
        patch("gd_tools.init.find_godot", return_value=mock_info),
        patch("gd_tools.init.install_native_test_addon"),
        patch("gd_tools.init.install_editor_plugin"),
        patch("gd_tools.init.register_coverage_autoload"),
        patch("gd_tools.init.install_coverage_addon"),
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
    assert any("editor plugin" in a.lower() for a in actions)


def test_pyproject_package_data_includes_editor_addon():
    """Wheel packaging ships the bundled editor plugin files."""
    import sys

    if sys.version_info >= (3, 11):
        import tomllib
    else:  # pragma: no cover
        import tomli as tomllib

    pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    package_data = data["tool"]["setuptools"]["package-data"]
    patterns = [
        pattern for values in package_data.values() for pattern in values
    ]
    assert any("gd-tools-editor" in pattern for pattern in patterns)


def test_install_coverage_addon_removes_stale_hook_files(tmp_path: Path):
    """Re-init removes GUT hook files gd-tools no longer deploys.

    The hooks extended the removed ``GutHookScript`` base class, so a
    stale copy is dead weight. init moves them into ``.backups/``
    before deleting and reports the cleanup.
    """
    target_dir = tmp_path / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True)
    (target_dir / "pre_run_hook.gd").write_text("# stale pre-run hook\n")
    (target_dir / "post_run_hook.gd").write_text("# stale post-run hook\n")

    with patch("gd_tools.init.console.print") as mock_print:
        install_coverage_addon(tmp_path)

    assert not (target_dir / "pre_run_hook.gd").exists()
    assert not (target_dir / "post_run_hook.gd").exists()
    assert (target_dir / "coverage.gd").exists()

    backups_dir = target_dir / ".backups"
    assert (
        backups_dir / "pre_run_hook.gd.bak"
    ).read_text() == "# stale pre-run hook\n"
    assert (
        backups_dir / "post_run_hook.gd.bak"
    ).read_text() == "# stale post-run hook\n"

    printed = " ".join(
        str(call.args[0]) for call in mock_print.call_args_list if call.args
    )
    assert "pre_run_hook.gd" in printed
    assert "post_run_hook.gd" in printed


def test_stale_hook_cleanup_is_a_noop_when_files_are_absent(tmp_path: Path):
    """First-time install prints nothing about removed hook files."""
    with patch("gd_tools.init.console.print") as mock_print:
        install_coverage_addon(tmp_path)

    printed = " ".join(
        str(call.args[0]) for call in mock_print.call_args_list if call.args
    )
    assert "Removed" not in printed
