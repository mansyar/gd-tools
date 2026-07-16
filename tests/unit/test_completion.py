"""Unit tests for the gd-tools completion command."""

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit


def test_completion_bash():
    """Test `completion bash` outputs a valid bash completion script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "bash"])
    assert result.exit_code == 0
    assert "_gd_tools_completion" in result.output
    assert "complete -o nosort" in result.output
    assert "gd-tools" in result.output


def test_completion_zsh():
    """Test `completion zsh` outputs a valid zsh completion script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "zsh"])
    assert result.exit_code == 0
    assert "#compdef gd-tools" in result.output
    assert "_gd_tools_completion" in result.output


def test_completion_fish():
    """Test `completion fish` outputs a valid fish completion script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "fish"])
    assert result.exit_code == 0
    assert "function _gd_tools_completion" in result.output
    assert "complete --no-files --command gd-tools" in result.output


def test_completion_powershell():
    """Test `completion powershell` outputs a valid PowerShell completion script."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "powershell"])
    assert result.exit_code == 0
    assert "Register-ArgumentCompleter" in result.output
    assert "gd-tools" in result.output


def test_completion_invalid_shell():
    """Test `completion <invalid>` exits with code 2 and an error message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "tcsh"])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_completion_help_shows_shell_choices():
    """Test `completion --help` shows the shell argument and choices."""
    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--help"])
    assert result.exit_code == 0
    for shell in ["bash", "zsh", "fish", "powershell"]:
        assert shell in result.output
