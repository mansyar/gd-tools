"""Unit tests for the config show/validate CLI commands."""

import json
from unittest.mock import patch

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import GdToolsConfig
from gd_tools.errors import ConfigError

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# config show tests
# ---------------------------------------------------------------------------


def test_config_show_table_default():
    """config show prints Rich table with all sections by default."""
    runner = CliRunner()
    config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    for section in ["godot", "test", "lint", "format", "coverage"]:
        assert section in result.output


def test_config_show_format_toml():
    """config show --format toml prints valid TOML."""
    runner = CliRunner()
    config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(cli, ["config", "show", "--format", "toml"])
    assert result.exit_code == 0
    parsed = tomllib.loads(result.output)
    assert "test" in parsed
    assert "lint" in parsed


def test_config_show_json():
    """config show --json prints valid JSON."""
    runner = CliRunner()
    config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(cli, ["config", "show", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert "godot" in parsed
    assert "test" in parsed
    assert "lint" in parsed
    assert "format" in parsed
    assert "coverage" in parsed


def test_config_show_no_config_file_shows_defaults():
    """config show with no config file shows defaults (exit 0)."""
    runner = CliRunner()
    config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0
    assert "test" in result.output
    assert "test_dirs" in result.output


def test_config_show_format_and_json_mutually_exclusive():
    """config show --format toml --json produces error and exit code 2."""
    runner = CliRunner()
    config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(
            cli, ["config", "show", "--format", "toml", "--json"]
        )
    assert result.exit_code == 2


def test_config_show_exit_0_on_success():
    """config show exits 0 on success."""
    runner = CliRunner()
    config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=config):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 0


def test_config_show_config_error_exit_2():
    """config show exits 2 on config load error."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config", side_effect=ConfigError("bad config")
    ):
        result = runner.invoke(cli, ["config", "show"])
    assert result.exit_code == 2


def test_config_show_help():
    """config show --help shows usage and options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--json" in result.output


def test_config_group_help():
    """config --help shows show and validate subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "validate" in result.output


# ---------------------------------------------------------------------------
# config validate tests
# ---------------------------------------------------------------------------


def _create_default_dirs(path):
    """Create directories matching default config to avoid path warnings."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (path / d).mkdir(exist_ok=True)


def test_config_validate_valid_config(tmp_path, monkeypatch):
    """config validate with a valid config exits 0 and prints success."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text(
        '[test]\ntest_dirs = ["test", "tests"]\n'
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_config_validate_invalid_toml(tmp_path, monkeypatch):
    """config validate with invalid TOML exits 1 and reports error."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text("= invalid toml\n")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 1


def test_config_validate_unknown_key(tmp_path, monkeypatch):
    """config validate with unknown key exits 1 and reports it."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text('[test]\nunknown_key = "value"\n')
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 1
    assert "unknown_key" in result.output


def test_config_validate_nonexistent_test_dir(tmp_path, monkeypatch):
    """config validate with nonexistent test dir exits 0, warns."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text(
        '[test]\ntest_dirs = ["nonexistent_dir"]\n'
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 0
    assert "nonexistent_dir" in result.output


def test_config_validate_nonexistent_godot_binary(tmp_path, monkeypatch):
    """config validate with nonexistent godot.binary exits 0, warns."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text(
        '[godot]\nbinary = "nonexistent_godot"\n'
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 0
    assert "nonexistent_godot" in result.output


def test_config_validate_nonexistent_exclude_dir(tmp_path, monkeypatch):
    """config validate with nonexistent exclude dir exits 0, warns."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text(
        "[lint]\nexclude = "
        '["addons", ".godot", ".gd-tools", ".git", "nonexistent"]\n'
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 0
    assert "nonexistent" in result.output


def test_config_validate_deprecated_setting(tmp_path, monkeypatch):
    """config validate with deprecated setting exits 1, warns."""
    from gd_tools import config as config_module
    from gd_tools.config import DeprecatedField

    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    (tmp_path / "gd-tools.toml").write_text(
        '[test]\ntest_dirs = ["test", "tests"]\n'
        "[coverage]\nold_field = true\n"
    )
    monkeypatch.chdir(tmp_path)

    config_module._DEPRECATED_FIELDS["coverage.old_field"] = DeprecatedField(
        field_path="coverage.old_field",
        since_version="1.0.0",
        replacement="coverage.min_percent",
        migration_message="Replace old_field with min_percent.",
    )

    try:
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "validate"])
        assert result.exit_code == 1
        assert "coverage.old_field" in result.output
        assert "deprecated" in result.output.lower()
    finally:
        config_module._DEPRECATED_FIELDS.pop("coverage.old_field", None)


def test_config_validate_no_config_file(tmp_path, monkeypatch):
    """config validate with no config file exits 0, prints defaults."""
    (tmp_path / "project.godot").write_text("")
    _create_default_dirs(tmp_path)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "validate"])
    assert result.exit_code == 0
    assert "default" in result.output.lower()
