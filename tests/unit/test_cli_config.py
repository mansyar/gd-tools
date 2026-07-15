"""Unit tests for the config show/validate CLI commands."""

import json
import tomllib
from unittest.mock import patch

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
