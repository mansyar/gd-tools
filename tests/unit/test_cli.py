"""Unit tests for the gd_tools CLI skeleton."""

import click
from click.testing import CliRunner

from gd_tools.cli import cli


def test_cli_is_group():
    """Test that cli is a Click group."""
    assert isinstance(cli, click.Group)


def test_version():
    """Test --version outputs gd-tools 0.1.0."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "gd-tools 0.1.0" in result.output


def test_help_shows_all_commands():
    """Test --help exits 0 and shows all command names."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ["init", "doctor", "test", "lint", "format", "coverage"]:
        assert cmd in result.output


def test_init_help_shows_non_interactive():
    """Test init --help shows --non-interactive option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "--non-interactive" in result.output


def test_test_help_shows_options():
    """Test test --help shows all required options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["test", "--help"])
    assert result.exit_code == 0
    for opt in [
        "--coverage",
        "--min",
        "--suite",
        "--test",
        "--junit-xml",
        "--no-exit-code",
    ]:
        assert opt in result.output


def test_lint_help_shows_path_and_report_format():
    """Test lint --help shows PATH argument and --report-format option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--help"])
    assert result.exit_code == 0
    assert "PATH" in result.output
    assert "--report-format" in result.output


def test_format_help_shows_path_check_diff():
    """Test format --help shows PATH, --check, --diff."""
    runner = CliRunner()
    result = runner.invoke(cli, ["format", "--help"])
    assert result.exit_code == 0
    assert "PATH" in result.output
    assert "--check" in result.output
    assert "--diff" in result.output


def test_coverage_help_shows_subcommands():
    """Test coverage --help shows subcommands report, merge, show."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "--help"])
    assert result.exit_code == 0
    for sub in ["report", "merge", "show"]:
        assert sub in result.output


def test_coverage_report_help_shows_format_and_output_dir():
    """Test coverage report --help shows --format and --output-dir."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "report", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output
    assert "--output-dir" in result.output


def test_coverage_merge_help_shows_files_and_output():
    """Test coverage merge --help shows files argument and --output."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "merge", "--help"])
    assert result.exit_code == 0
    assert "files" in result.output
    assert "--output" in result.output


def test_coverage_show_help_shows_min():
    """Test coverage show --help shows --min option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "show", "--help"])
    assert result.exit_code == 0
    assert "--min" in result.output


def test_test_stub_exit_code_2():
    """Test invoking test raises error with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["test"])
    assert result.exit_code == 2


def test_lint_stub_exit_code_2():
    """Test invoking lint raises error with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "some_path"])
    assert result.exit_code == 2


def test_format_stub_exit_code_2():
    """Test invoking format raises error with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["format", "some_path"])
    assert result.exit_code == 2


def test_init_stub_exit_code_2():
    """Test invoking init raises error with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 2


def test_doctor_stub_exit_code_2():
    """Test invoking doctor raises error with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 2


def test_coverage_report_stub_exit_code_2():
    """Test invoking coverage report raises error with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "report"])
    assert result.exit_code == 2
