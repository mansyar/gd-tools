"""Integration tests for the format command.

Tests the full CLI flow: load_config → run_format → render output → exit code.
Uses fixture .gd files from tests/fixtures/ and the real run_format function
(only load_config is mocked since no project.godot exists in the test env).

Also verifies gdformatrc integration: generate_gdformatrc() creates a valid
file whose exclude list matches the config, and format respects those excludes.
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import DEFAULT_EXCLUDES, GdToolsConfig, generate_gdformatrc

pytestmark = pytest.mark.integration

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _copy_fixture(tmp_path: Path, name: str, dest_name: str | None = None):
    """Copy a fixture file into tmp_path, optionally renaming it."""
    src = FIXTURES_DIR / name
    dst = tmp_path / (dest_name or name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    return dst


# --- Full format runs (default mode) ---


def test_format_full_run_default_mode(tmp_path):
    """Full format run in default mode formats unformatted files in place."""
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    clean_file = _copy_fixture(tmp_path, "clean.gd")
    original_bad = bad_file.read_text()

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    assert "Formatted 1 of 2 file(s)" in result.output
    # bad.gd was reformatted (content changed)
    assert bad_file.read_text() != original_bad
    # clean.gd was not changed
    assert clean_file.read_text() == "extends Node\n"


def test_format_full_run_all_formatted(tmp_path):
    """Full format run when all files are already formatted."""
    _copy_fixture(tmp_path, "clean.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    assert "already formatted" in result.output


# --- Full format runs (--check mode) ---


def test_format_full_run_check_needs_formatting(tmp_path):
    """Full format --check run reports files needing formatting, exit 1."""
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    _copy_fixture(tmp_path, "clean.gd")
    original_bad = bad_file.read_text()

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", "--check", str(tmp_path)])

    assert result.exit_code == 1
    assert "bad.gd" in result.output
    assert "1 file(s) need formatting" in result.output
    assert "2 files checked" in result.output
    # Files not modified in check mode
    assert bad_file.read_text() == original_bad


def test_format_full_run_check_all_formatted(tmp_path):
    """Full format --check run when all files are formatted, exit 0."""
    _copy_fixture(tmp_path, "clean.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", "--check", str(tmp_path)])

    assert result.exit_code == 0
    assert "All 1 file(s) are formatted" in result.output


# --- Full format runs (--diff mode) ---


def test_format_full_run_diff_mode(tmp_path):
    """Full format --diff run shows diffs, does not modify files."""
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    original_bad = bad_file.read_text()

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", "--diff", str(tmp_path)])

    assert result.exit_code == 0
    # Diff output contains the changed content (diff headers use full
    # paths which rich Console may truncate, so assert on diff body)
    assert "BadFunctionName" in result.output
    # File not modified in diff mode
    assert bad_file.read_text() == original_bad


# --- Excludes ---


def test_format_excludes_addons_directory(tmp_path):
    """Files in excluded directories (addons/) are not formatted."""
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    addon_file = _copy_fixture(tmp_path, "addons/plugin.gd")
    original_bad = bad_file.read_text()
    original_addon = addon_file.read_text()

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    # Only bad.gd was checked (addons excluded by default)
    assert "Formatted 1 of 1 file(s)" in result.output
    # bad.gd was reformatted
    assert bad_file.read_text() != original_bad
    # addons/plugin.gd was NOT touched
    assert addon_file.read_text() == original_addon


# --- Syntax error handling ---


def test_format_syntax_error_skipped(tmp_path):
    """Syntax-error files are skipped, other files are still formatted."""
    broken_file = _copy_fixture(tmp_path, "broken.gd")
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    original_broken = broken_file.read_text()
    original_bad = bad_file.read_text()

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    # 1 file checked (1 skipped), 1 formatted
    assert "Formatted 1 of 1 file(s)" in result.output
    # Syntax error reported with file path
    assert "broken.gd" in result.output
    assert "Warning" in result.output
    # broken.gd not modified (syntax error, skipped)
    assert broken_file.read_text() == original_broken
    # bad.gd was reformatted
    assert bad_file.read_text() != original_bad


# --- No files found ---


def test_format_no_files_found(tmp_path):
    """Format on empty directory prints graceful message, exit 0."""
    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    assert "No .gd files found" in result.output


# --- gdformatrc integration ---


def test_gdformatrc_generated_matches_config_excludes(tmp_path):
    """generate_gdformatrc creates a file whose excludes match the config."""
    config = GdToolsConfig()
    generate_gdformatrc(config, project_root=tmp_path)

    rc_file = tmp_path / "gdformatrc"
    assert rc_file.is_file()

    content = rc_file.read_text(encoding="utf-8")
    excludes_in_file = [
        line for line in content.strip().split("\n") if line.strip()
    ]
    assert excludes_in_file == list(DEFAULT_EXCLUDES)


def test_format_respects_same_excludes_as_gdformatrc(tmp_path):
    """Format runner respects the same excludes that gdformatrc contains."""
    # Generate gdformatrc in tmp_path
    config = GdToolsConfig()
    generate_gdformatrc(config, project_root=tmp_path)

    # Create an unformatted file in addons/ (excluded)
    addon_file = _copy_fixture(tmp_path, "addons/plugin.gd")
    original_addon = addon_file.read_text()

    # Create an unformatted file at root (not excluded)
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    original_bad = bad_file.read_text()

    runner = CliRunner()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    # Only bad.gd checked (addons excluded)
    assert "Formatted 1 of 1 file(s)" in result.output
    # addons file untouched
    assert addon_file.read_text() == original_addon
    # root file formatted
    assert bad_file.read_text() != original_bad
