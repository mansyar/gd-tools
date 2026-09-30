"""Unit tests for the gd_tools CLI skeleton."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner
from rich.console import Console

from gd_tools.cli import cli
from gd_tools.doctor import CheckResult, DoctorResult
from gd_tools.verbosity import Verbosity, get_verbosity
from gd_tools.errors import (
    ConfigError,
    CoveragePlanError,
    CoveragePlaytestError,
    CoverageThresholdError,
    GdToolsError,
    TestFailureError,
)
from gd_tools.format_runner import FormatResult
from gd_tools.lint_runner import LintIssue, LintResult
from gd_tools.test_runner import TestResult

pytestmark = pytest.mark.unit


def test_cli_is_group():
    """Test that cli is a Click group."""
    assert isinstance(cli, click.Group)


def test_version():
    """Test --version outputs the correct version."""
    from gd_tools import __version__

    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert f"gd-tools {__version__}" in result.output


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
    result = runner.invoke(cli, ["test", "--runtime", "gut", "--help"])
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


def test_lint_help_shows_path_report_format_and_fix():
    """Test lint --help shows PATH argument, --report-format, and --fix."""
    runner = CliRunner()
    result = runner.invoke(cli, ["lint", "--help"])
    assert result.exit_code == 0
    assert "PATH" in result.output
    assert "--report-format" in result.output
    assert "--fix" in result.output


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


def test_test_config_error_exit_code_2():
    """Test test exits with code 2 when config loading fails."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("project.godot not found"),
    ):
        result = runner.invoke(cli, ["test"])
    assert result.exit_code == 2


def _native_result() -> TestResult:
    return TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.1,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )


def test_test_forwards_selection_options_to_native():
    """Suite, test, junit-xml, and path selectors reach the native adapter."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_native_result(),
        ) as mock_run,
    ):
        result = runner.invoke(
            cli,
            [
                "test",
                "--suite",
                "MySuite",
                "--test",
                "MyTest",
                "--junit-xml",
                "/path/to.xml",
                "dir_a",
                "dir_b",
            ],
        )
    assert result.exit_code == 0
    kwargs = mock_run.call_args.kwargs
    assert kwargs["suite"] == "MySuite"
    assert kwargs["test_name"] == "MyTest"
    assert kwargs["junit_xml"] == "/path/to.xml"
    assert kwargs["paths"] == ["dir_a", "dir_b"]


def test_test_forwards_coverage_options_to_native():
    """Coverage-related flags reach the native adapter unchanged."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_native_result(),
        ) as mock_run,
    ):
        result = runner.invoke(
            cli,
            [
                "test",
                "--coverage",
                "--min",
                "80",
                "--show-uncovered",
                "--no-cache",
                "--no-exit-code",
                "--timeout",
                "120",
            ],
        )
    assert result.exit_code == 0
    kwargs = mock_run.call_args.kwargs
    assert kwargs["coverage"] is True
    assert kwargs["min_percent"] == 80
    assert kwargs["show_uncovered"] is True
    assert kwargs["no_cache"] is True
    assert kwargs["no_exit_code"] is True
    assert kwargs["timeout"] == 120


def test_test_min_without_coverage_warns():
    """--min without --coverage prints a warning and proceeds with native."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_native_result(),
        ) as mock_run,
    ):
        result = runner.invoke(cli, ["test", "--min", "80"])
    assert result.exit_code == 0
    assert "--min is only valid with --coverage" in result.output
    mock_run.assert_called_once()


def test_test_show_uncovered_without_coverage_warns():
    """--show-uncovered without --coverage warns and proceeds with native."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_native_result(),
        ) as mock_run,
    ):
        result = runner.invoke(cli, ["test", "--show-uncovered"])
    assert result.exit_code == 0
    assert "--show-uncovered is only valid with --coverage" in result.output
    mock_run.assert_called_once()


def test_test_test_failure_exit_code_1():
    """TestFailureError from the native adapter exits with code 1."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            side_effect=TestFailureError("2 test(s) failed"),
        ),
    ):
        result = runner.invoke(cli, ["test"])
    assert result.exit_code == 1


def test_test_coverage_threshold_error_exit_1():
    """CoverageThresholdError from the native adapter exits with code 1."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            side_effect=CoverageThresholdError("Coverage below threshold"),
        ),
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    assert result.exit_code == 1


def test_test_coverage_plan_error_exit_2():
    """CoveragePlanError from the native adapter exits with code 2."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_native_test_command",
            side_effect=CoveragePlanError("Missing plan"),
        ),
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    assert result.exit_code == 2


def test_lint_exit_code_2_config_error():
    """Test lint exits with code 2 when config loading fails."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("project.godot not found"),
    ):
        result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 2


def test_lint_default_path():
    """Test lint command defaults to '.' when no path is given."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=0, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_config, [], "text")


def test_lint_report_format_json():
    """Test lint --report-format json produces JSON output."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=1, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["lint", "--report-format", "json"])
    assert result.exit_code == 0
    assert '"files_checked"' in result.output
    assert '"errors"' in result.output
    assert '"warnings"' in result.output


def test_lint_report_format_text_default():
    """Test lint defaults to text format."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=1, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 0
    assert "[OK]" in result.output


def test_lint_fix_flag_warning():
    """Test --fix flag prints warning that gdlint is read-only."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=0, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["lint", "--fix"])
    assert "gdlint is read-only" in result.output
    assert "--fix has no effect" in result.output


def test_lint_exit_code_0_clean():
    """Test lint exits 0 when no errors found."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=2, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 0


def test_lint_exit_code_1_errors():
    """Test lint exits 1 when lint errors are found."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(
        files_checked=1,
        errors=[
            LintIssue(
                file="test.gd",
                line=1,
                column=1,
                rule="test-rule",
                message="test error",
                severity="error",
            )
        ],
        warnings=[],
    )
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["lint"])
    assert result.exit_code == 1


def test_lint_wired_to_run_lint():
    """Test lint command calls run_lint with config and path."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=0, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(
            cli, ["lint", "some/path", "--report-format", "json"]
        )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_config, ["some/path"], "json")


def test_format_config_error_exit_2():
    """Test format exits with code 2 when config loading fails."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("project.godot not found"),
    ):
        result = runner.invoke(cli, ["format", "some_path"])
    assert result.exit_code == 2


def test_format_default_mode():
    """Test format command in default mode formats files."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=3, files_formatted=2)
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["format", "some/path"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        mock_config, ["some/path"], check=False, diff=False
    )
    assert "Formatted 2 of 3 file(s)" in result.output
    assert "3 files checked" in result.output


def test_format_default_path():
    """Test format command defaults to '.' when no path is given."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=0)
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["format"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_config, [], check=False, diff=False)


def test_format_default_all_formatted():
    """Test format reports all files already formatted."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=2, files_formatted=0)
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "some/path"])
    assert result.exit_code == 0
    assert "already formatted" in result.output
    assert "[OK]" in result.output


def test_format_check_needs_formatting():
    """Test format --check exits 1 when files need formatting."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(
        files_checked=3,
        files_needing_format=2,
        files_needing_format_paths=["a.gd", "b.gd"],
    )
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "--check", "some/path"])
    assert result.exit_code == 1
    assert "a.gd" in result.output
    assert "b.gd" in result.output
    assert "2 file(s) need formatting" in result.output
    assert "3 files checked" in result.output


def test_format_check_all_formatted():
    """Test format --check exits 0 when all files are formatted."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=2, files_needing_format=0)
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "--check", "some/path"])
    assert result.exit_code == 0
    assert "All 2 file(s) are formatted" in result.output
    assert "[OK]" in result.output


def test_format_diff_renders_diffs():
    """Test format --diff renders unified diffs with file path headers."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(
        files_checked=1,
        diffs=[
            "--- test.gd\n+++ test.gd\n@@ -1,3 +1,4 @@\n"
            "-extends Node\n+extends Node\n"
        ],
    )
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "--diff", "some/path"])
    assert result.exit_code == 0
    assert "test.gd" in result.output


def test_format_check_diff_conflict():
    """Test format --check --diff exits 2 with error message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["format", "--check", "--diff", "some/path"])
    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_format_no_files_found():
    """Test format exits 0 with graceful message when no .gd files found."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=0)
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "some/path"])
    assert result.exit_code == 0
    assert "No .gd files found" in result.output


def test_format_diff_no_diffs():
    """Test format --diff shows success message when no diffs found."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=2, diffs=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "--diff", "some/path"])
    assert result.exit_code == 0
    assert "[OK]" in result.output
    assert "already formatted" in result.output


def test_format_check_dim_file_paths(monkeypatch):
    """Test format --check renders file paths with dim style."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(
        files_checked=2,
        files_needing_format=1,
        files_needing_format_paths=["test.gd"],
    )
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["format", "--check", "some/path"])
    assert result.exit_code == 1
    assert "test.gd" in result.output
    # ANSI dim code (\x1b[2m) should be present when terminal is forced
    assert "\x1b[2m" in result.output


def test_cli_init_calls_run_init():
    """Test invoking init calls run_init."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_init") as mock_run:
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    mock_run.assert_called_once()


def test_cli_init_passes_non_interactive_flag():
    """Test invoking init with --non-interactive passes the flag."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_init") as mock_run:
        result = runner.invoke(cli, ["init", "--non-interactive"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(non_interactive=True, with_gut=False)


def test_cli_init_exits_zero_on_success():
    """Test init exits with code 0 on success."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_init"):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0


def test_cli_doctor_calls_run_doctor():
    """Test invoking doctor calls run_doctor."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["doctor"])
    mock_run.assert_called_once()
    assert result.exit_code == 0


def test_cli_doctor_prints_table():
    """Test doctor command prints the table with check names."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(
            checks=[
                CheckResult(name="Godot Binary", passed=True, message="Found"),
            ],
            all_passed=True,
        )
        result = runner.invoke(cli, ["doctor"])
    assert "Godot Binary" in result.output


def test_cli_doctor_exits_zero_when_all_pass():
    """Test doctor exits with code 0 when all checks pass."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(
            checks=[
                CheckResult(name="Test", passed=True, message="OK"),
            ],
            all_passed=True,
        )
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0


def test_cli_doctor_exits_one_when_any_fails():
    """Test doctor exits with code 1 when any check fails."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(
            checks=[
                CheckResult(
                    name="Test",
                    passed=False,
                    message="Failed",
                    severity="critical",
                ),
            ],
            all_passed=False,
        )
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 1


def test_coverage_report_calls_orchestrator():
    """Test coverage report calls generate_coverage_report."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.generate_coverage_report",
            return_value=mock_result,
        ) as mock_report,
    ):
        result = runner.invoke(cli, ["coverage", "report"])
    assert result.exit_code == 0
    mock_report.assert_called_once()


def test_coverage_report_format_override():
    """Test --format lcov passes format to orchestrator."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.generate_coverage_report",
            return_value=mock_result,
        ) as mock_report,
    ):
        result = runner.invoke(cli, ["coverage", "report", "--format", "lcov"])
    assert result.exit_code == 0
    _, kwargs = mock_report.call_args
    assert kwargs["report_format"] == "lcov"


def test_coverage_report_output_dir_override():
    """Test --output-dir passes output_dir to orchestrator."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.generate_coverage_report",
            return_value=mock_result,
        ) as mock_report,
    ):
        result = runner.invoke(
            cli, ["coverage", "report", "--output-dir", "/tmp/reports"]
        )
    assert result.exit_code == 0
    _, kwargs = mock_report.call_args
    assert kwargs["output_dir"] == "/tmp/reports"


def test_coverage_report_plan_error_exit_2():
    """Test coverage report exits 2 when CoveragePlanError is raised."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.generate_coverage_report",
            side_effect=CoveragePlanError("missing"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "report"])
    assert result.exit_code == 2


def test_coverage_report_success_exit_0():
    """Test coverage report exits 0 on success and prints output path."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = MagicMock()
    mock_result.output_path = Path("/tmp/reports/report.html")
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.generate_coverage_report",
            return_value=mock_result,
        ),
    ):
        result = runner.invoke(cli, ["coverage", "report"])
    assert result.exit_code == 0
    assert "report.html" in result.output


def test_coverage_merge_calls_orchestrator():
    """Test coverage merge calls merge_coverage_files with list of Paths."""
    runner = CliRunner()
    mock_result = MagicMock()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.merge_coverage_files",
            return_value=mock_result,
        ) as mock_merge,
    ):
        result = runner.invoke(
            cli, ["coverage", "merge", "file1.json", "file2.json"]
        )
    assert result.exit_code == 0
    mock_merge.assert_called_once()
    args, _ = mock_merge.call_args
    files_arg = args[0]
    assert len(files_arg) == 2
    assert all(isinstance(f, Path) for f in files_arg)


def test_coverage_merge_output_override():
    """Test --output passes output path to orchestrator."""
    runner = CliRunner()
    mock_result = MagicMock()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.merge_coverage_files",
            return_value=mock_result,
        ) as mock_merge,
    ):
        result = runner.invoke(
            cli, ["coverage", "merge", "file1.json", "--output", "merged.json"]
        )
    assert result.exit_code == 0
    args, kwargs = mock_merge.call_args
    output_arg = args[1] if len(args) > 1 else kwargs.get("output")
    assert output_arg == Path("merged.json")


def test_coverage_merge_no_files_exit_2():
    """Test coverage merge exits 2 when no files provided."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "merge"])
    assert result.exit_code == 2


def test_coverage_merge_success_exit_0():
    """Test coverage merge exits 0 on success."""
    runner = CliRunner()
    mock_result = MagicMock()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.merge_coverage_files",
            return_value=mock_result,
        ),
    ):
        result = runner.invoke(cli, ["coverage", "merge", "file1.json"])
    assert result.exit_code == 0


def test_coverage_show_calls_orchestrator():
    """Test coverage show calls show_coverage_summary."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_summary = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.show_coverage_summary",
            return_value=mock_summary,
        ) as mock_show,
    ):
        result = runner.invoke(cli, ["coverage", "show"])
    assert result.exit_code == 0
    mock_show.assert_called_once()


def test_coverage_show_min_passed_to_orchestrator():
    """Test --min 80 passes min_percent=80 to orchestrator."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_summary = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.show_coverage_summary",
            return_value=mock_summary,
        ) as mock_show,
    ):
        result = runner.invoke(cli, ["coverage", "show", "--min", "80"])
    assert result.exit_code == 0
    _, kwargs = mock_show.call_args
    assert kwargs["min_percent"] == 80


def test_coverage_show_threshold_error_exit_1():
    """Test coverage show exits 1 when CoverageThresholdError is raised."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.show_coverage_summary",
            side_effect=CoverageThresholdError("below threshold"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "show", "--min", "90"])
    assert result.exit_code == 1


def test_coverage_show_plan_error_exit_2():
    """Test coverage show exits 2 when CoveragePlanError is raised."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.show_coverage_summary",
            side_effect=CoveragePlanError("missing"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "show"])
    assert result.exit_code == 2


def test_cli_group_not_implemented_error_exit_2():
    """Test GdToolsGroup catches NotImplementedError and exits 2."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_init", side_effect=NotImplementedError()):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 2


def test_cli_init_gdtools_error_exit_code():
    """Test init exits with GdToolsError.exit_code when run_init raises."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.run_init",
        side_effect=GdToolsError("init failed", exit_code=3),
    ):
        result = runner.invoke(cli, ["init"])
    assert result.exit_code == 3


def test_coverage_report_config_error_exit_2():
    """Test coverage report exits 2 when load_config raises ConfigError."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("project.godot not found"),
    ):
        result = runner.invoke(cli, ["coverage", "report"])
    assert result.exit_code == 2


def test_coverage_merge_config_error_exit_2():
    """Test coverage merge exits 2 when load_config raises ConfigError."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("project.godot not found"),
    ):
        result = runner.invoke(cli, ["coverage", "merge", "file1.json"])
    assert result.exit_code == 2


def test_coverage_merge_gdtools_error_exit_code():
    """Test coverage merge exits with GdToolsError.exit_code when merge fails."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.merge_coverage_files",
            side_effect=GdToolsError("merge failed", exit_code=3),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "merge", "file1.json"])
    assert result.exit_code == 3


def test_coverage_show_config_error_exit_2():
    """Test coverage show exits 2 when load_config raises ConfigError."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("project.godot not found"),
    ):
        result = runner.invoke(cli, ["coverage", "show"])
    assert result.exit_code == 2


# ---------------------------------------------------------------------------
# Update notification tests
# ---------------------------------------------------------------------------


def test_update_notification_printed_when_update_available():
    """Notification appears on stderr when a newer PyPI version exists."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.check_for_update", return_value="1.0.0"),
        patch("gd_tools.cli.__version__", "0.1.0"),
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert (
        "A new version of gd-tools is available: 1.0.0 (you have 0.1.0)"
        in result.output
    )
    assert "pip install --upgrade gd-tools-cli" in result.output


def test_no_notification_when_no_update_available():
    """No notification when check_for_update returns None."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "A new version of gd-tools" not in result.output


def test_notification_does_not_affect_exit_code():
    """Update notification does not affect the exit code."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.check_for_update", return_value="1.0.0"),
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0


def test_env_var_disables_notification_in_cli(mock_requests_get, monkeypatch):
    """GD_TOOLS_NO_UPDATE_CHECK=1 disables the update check entirely."""
    from gd_tools.update_check import check_for_update as real_check_for_update

    monkeypatch.setenv("GD_TOOLS_NO_UPDATE_CHECK", "1")
    runner = CliRunner()
    with (
        patch("gd_tools.cli.check_for_update", new=real_check_for_update),
        mock_requests_get(json_data={"info": {"version": "1.0.0"}}) as mock_get,
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "A new version of gd-tools" not in result.output
    mock_get.assert_not_called()


# --- Multi-path CLI tests (FR-4, FR-5, FR-6) ---


def test_lint_multiple_paths():
    """Test lint accepts multiple path arguments."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = LintResult(files_checked=0, errors=[], warnings=[])
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_lint", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["lint", "path_a", "path_b"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(mock_config, ["path_a", "path_b"], "text")


def test_format_multiple_paths():
    """Test format accepts multiple path arguments."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = FormatResult(files_checked=2, files_formatted=1)
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_format", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["format", "path_a", "path_b"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        mock_config, ["path_a", "path_b"], check=False, diff=False
    )


def test_cli_version_table_output():
    """Test version command renders Rich table with all component names."""
    runner = CliRunner()
    with patch("gd_tools.cli.collect_versions") as mock_collect:
        mock_collect.return_value = {
            "gd-tools": "0.3.0",
            "godot": "4.5.1",
            "gut": "9.2.0",
            "gdtoolkit": "4.5.0",
            "python": "3.13.5",
        }
        result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "gd-tools" in result.output
    assert "godot" in result.output
    assert "gut" in result.output
    assert "gdtoolkit" in result.output
    assert "python" in result.output


def test_cli_version_json_output():
    """Test --json flag outputs valid JSON with null for missing."""
    runner = CliRunner()
    with patch("gd_tools.cli.collect_versions") as mock_collect:
        mock_collect.return_value = {
            "gd-tools": "0.3.0",
            "godot": None,
            "gut": None,
            "gdtoolkit": "4.5.0",
            "python": "3.13.5",
        }
        result = runner.invoke(cli, ["version", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gd-tools"] == "0.3.0"
    assert data["godot"] is None
    assert data["gut"] is None
    assert data["gdtoolkit"] == "4.5.0"
    assert data["python"] == "3.13.5"


def test_cli_version_exit_zero_with_missing():
    """Test version exits 0 even when components are missing."""
    runner = CliRunner()
    with patch("gd_tools.cli.collect_versions") as mock_collect:
        mock_collect.return_value = {
            "gd-tools": "0.3.0",
            "godot": None,
            "gut": None,
            "gdtoolkit": None,
            "python": "3.13.5",
        }
        result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0


def test_cli_version_missing_display():
    """Test missing components show 'not detected' or 'not installed'."""
    runner = CliRunner()
    with patch("gd_tools.cli.collect_versions") as mock_collect:
        mock_collect.return_value = {
            "gd-tools": "0.3.0",
            "godot": None,
            "gut": None,
            "gdtoolkit": None,
            "python": "3.13.5",
        }
        result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "not detected" in result.output
    assert "not installed" in result.output


# ---------------------------------------------------------------------------
# Verbosity global flags: --verbose/-v and --quiet/-q
# ---------------------------------------------------------------------------


def test_verbose_long_flag_sets_verbosity():
    """--verbose sets verbosity to VERBOSE."""
    runner = CliRunner()
    runner.invoke(cli, ["--verbose", "version"])
    assert get_verbosity() == Verbosity.VERBOSE


def test_verbose_short_flag_sets_verbosity():
    """-v sets verbosity to VERBOSE."""
    runner = CliRunner()
    runner.invoke(cli, ["-v", "version"])
    assert get_verbosity() == Verbosity.VERBOSE


def test_quiet_long_flag_sets_verbosity():
    """--quiet sets verbosity to QUIET."""
    runner = CliRunner()
    runner.invoke(cli, ["--quiet", "version"])
    assert get_verbosity() == Verbosity.QUIET


def test_quiet_short_flag_sets_verbosity():
    """-q sets verbosity to QUIET."""
    runner = CliRunner()
    runner.invoke(cli, ["-q", "version"])
    assert get_verbosity() == Verbosity.QUIET


def test_no_flag_defaults_to_default_verbosity():
    """No verbosity flag leaves verbosity at DEFAULT."""
    runner = CliRunner()
    runner.invoke(cli, ["version"])
    assert get_verbosity() == Verbosity.DEFAULT


def test_verbose_and_quiet_mutual_exclusion():
    """--verbose --quiet exits with code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--verbose", "--quiet", "version"])
    assert result.exit_code == 2


def test_verbose_short_and_quiet_short_mutual_exclusion():
    """-v -q exits with code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["-v", "-q", "version"])
    assert result.exit_code == 2


def test_verbose_flag_shown_in_help():
    """--help shows --verbose option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output


def test_quiet_flag_shown_in_help():
    """--help shows --quiet option."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "--quiet" in result.output


# ---------------------------------------------------------------------------
# Quiet mode: suppress update and addon version checks
# ---------------------------------------------------------------------------


def test_quiet_suppresses_update_and_addon_checks():
    """--quiet flag suppresses both check_for_update and check_addon_version."""
    runner = CliRunner()
    with (
        patch(
            "gd_tools.cli.check_for_update", return_value=None
        ) as mock_update,
        patch("gd_tools.cli.check_addon_version") as mock_addon,
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["--quiet", "doctor"])
    assert result.exit_code == 0
    mock_update.assert_not_called()
    mock_addon.assert_not_called()


def test_quiet_short_flag_suppresses_update_and_addon_checks():
    """-q flag suppresses both check_for_update and check_addon_version."""
    runner = CliRunner()
    with (
        patch(
            "gd_tools.cli.check_for_update", return_value=None
        ) as mock_update,
        patch("gd_tools.cli.check_addon_version") as mock_addon,
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["-q", "doctor"])
    assert result.exit_code == 0
    mock_update.assert_not_called()
    mock_addon.assert_not_called()


def test_default_mode_calls_update_and_addon_checks():
    """Without --quiet, both check_for_update and check_addon_version are called."""
    runner = CliRunner()
    with (
        patch(
            "gd_tools.cli.check_for_update", return_value=None
        ) as mock_update,
        patch("gd_tools.cli.check_addon_version") as mock_addon,
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    mock_update.assert_called_once()
    mock_addon.assert_called_once()


def test_quiet_suppresses_update_notification_when_available():
    """--quiet suppresses update notification even when an update is available."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.check_for_update", return_value="1.0.0"),
        patch("gd_tools.cli.__version__", "0.1.0"),
        patch("gd_tools.cli.check_addon_version"),
        patch("gd_tools.cli.run_doctor") as mock_run,
    ):
        mock_run.return_value = DoctorResult(checks=[], all_passed=True)
        result = runner.invoke(cli, ["--quiet", "doctor"])
    assert result.exit_code == 0
    assert "A new version of gd-tools" not in result.output


# ---------------------------------------------------------------------------
# Quiet mode: suppress init/doctor details
# ---------------------------------------------------------------------------


def test_doctor_quiet_shows_one_line_pass():
    """--quiet doctor shows only a one-line pass status, no table."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(
            checks=[
                CheckResult(name="Godot Binary", passed=True, message="Found"),
            ],
            all_passed=True,
        )
        result = runner.invoke(cli, ["--quiet", "doctor"])
    assert result.exit_code == 0
    assert "Godot Binary" not in result.output
    assert "OK" in result.output


def test_doctor_quiet_shows_one_line_fail():
    """--quiet doctor shows only a one-line fail status, no table."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(
            checks=[
                CheckResult(
                    name="Godot Binary",
                    passed=False,
                    message="Not found",
                ),
            ],
            all_passed=False,
        )
        result = runner.invoke(cli, ["--quiet", "doctor"])
    assert result.exit_code == 1
    assert "Godot Binary" not in result.output
    assert "FAIL" in result.output


def test_doctor_default_shows_table():
    """Without --quiet, doctor shows the full table with check names."""
    runner = CliRunner()
    with patch("gd_tools.cli.run_doctor") as mock_run:
        mock_run.return_value = DoctorResult(
            checks=[
                CheckResult(name="Godot Binary", passed=True, message="Found"),
            ],
            all_passed=True,
        )
        result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Godot Binary" in result.output


# ---------------------------------------------------------------------------
# coverage save-baseline
# ---------------------------------------------------------------------------


def test_coverage_save_baseline_is_registered():
    """Test coverage save-baseline is registered in the coverage group."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "save-baseline", "--help"])
    assert result.exit_code == 0


def test_coverage_save_baseline_calls_orchestrator():
    """Test save-baseline delegates to save_coverage_baseline with config."""
    runner = CliRunner()
    mock_config = MagicMock()
    baseline_path = Path(".gd-tools") / "coverage" / "baseline.json"
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.save_coverage_baseline",
            return_value=baseline_path,
        ) as mock_save,
    ):
        result = runner.invoke(cli, ["coverage", "save-baseline"])
    assert result.exit_code == 0
    mock_save.assert_called_once_with(mock_config)
    assert "baseline.json" in result.output


def test_coverage_save_baseline_missing_data_exit_2():
    """Test save-baseline exits 2 when coverage data is missing."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.save_coverage_baseline",
            side_effect=CoveragePlanError("Coverage data file not found"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "save-baseline"])
    assert result.exit_code == 2


# --- coverage diff ---


def test_coverage_diff_is_registered():
    """Test coverage diff --help shows the command and its options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "diff", "--help"])
    assert result.exit_code == 0
    assert "--base" in result.output
    assert "--fail-on-regression" in result.output
    assert "--show-lines" in result.output
    assert "--report-format" in result.output


def test_coverage_diff_requires_base_option():
    """Test coverage diff without --base is a usage error (exit 2)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "diff"])
    assert result.exit_code == 2


def test_coverage_diff_calls_orchestrator():
    """Test coverage diff delegates to diff_coverage with defaults."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.diff_coverage", return_value=None) as mock_diff,
    ):
        result = runner.invoke(cli, ["coverage", "diff", "--base", "b.json"])
    assert result.exit_code == 0
    mock_diff.assert_called_once_with(
        mock_config,
        "b.json",
        show_lines=False,
        report_format="text",
        fail_on_regression=False,
    )


def test_coverage_diff_flags_passed_to_orchestrator():
    """Test coverage diff forwards --show-lines/--report-format/gating flags."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.diff_coverage", return_value=None) as mock_diff,
    ):
        result = runner.invoke(
            cli,
            [
                "coverage",
                "diff",
                "--base",
                "b.json",
                "--show-lines",
                "--report-format",
                "json",
                "--fail-on-regression",
            ],
        )
    assert result.exit_code == 0
    mock_diff.assert_called_once_with(
        mock_config,
        "b.json",
        show_lines=True,
        report_format="json",
        fail_on_regression=True,
    )


def test_coverage_diff_plan_error_exit_2():
    """Test missing/malformed baseline or current data exits 2."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.diff_coverage",
            side_effect=CoveragePlanError("Baseline file not found"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "diff", "--base", "b.json"])
    assert result.exit_code == 2


def test_coverage_diff_regression_gate_exit_1():
    """Test a gated regression raises CoverageThresholdError mapped to exit 1."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.diff_coverage",
            side_effect=CoverageThresholdError("Coverage regressed"),
        ),
    ):
        result = runner.invoke(
            cli,
            ["coverage", "diff", "--base", "b.json", "--fail-on-regression"],
        )
    assert result.exit_code == 1


# --- coverage run (playtest coverage) ---


def test_coverage_run_is_registered():
    """Test coverage --help lists the run subcommand."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "--help"])
    assert result.exit_code == 0
    assert "run" in result.output


def test_coverage_run_help_shows_flags():
    """Test coverage run --help shows --scene, --timeout, --min, --report-format."""
    runner = CliRunner()
    result = runner.invoke(cli, ["coverage", "run", "--help"])
    assert result.exit_code == 0
    assert "--scene" in result.output
    assert "--timeout" in result.output
    assert "--min" in result.output
    assert "--report-format" in result.output


def test_coverage_run_calls_orchestrator():
    """Flags reach run_playtest_coverage unchanged."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = MagicMock()
    mock_result.output_path = Path("report.txt")
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_playtest_coverage",
            return_value=mock_result,
        ) as mock_run,
    ):
        result = runner.invoke(
            cli,
            [
                "coverage",
                "run",
                "--scene",
                "res://scenes/level1.tscn",
                "--timeout",
                "60",
                "--min",
                "50",
                "--report-format",
                "json",
            ],
        )
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        mock_config,
        scene="res://scenes/level1.tscn",
        timeout=60,
        min_percent=50,
        report_format="json",
    )


def test_coverage_run_success_exit_0():
    """A completed playtest session echoes the report path and exits 0."""
    runner = CliRunner()
    mock_result = MagicMock()
    mock_result.output_path = Path("coverage_report.txt")
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch("gd_tools.cli.run_playtest_coverage", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["coverage", "run"])
    assert result.exit_code == 0
    assert "Report written to: coverage_report.txt" in result.output


def test_coverage_run_config_error_exit_2():
    """Test coverage run exits 2 when load_config raises ConfigError."""
    runner = CliRunner()
    with patch(
        "gd_tools.cli.load_config",
        side_effect=ConfigError("Invalid config"),
    ):
        result = runner.invoke(cli, ["coverage", "run"])
    assert result.exit_code == 2


def test_coverage_run_threshold_error_exit_1():
    """A --min gate failure raises CoverageThresholdError mapped to exit 1."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.run_playtest_coverage",
            side_effect=CoverageThresholdError("Coverage below minimum"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "run", "--min", "80"])
    assert result.exit_code == 1


def test_coverage_run_playtest_error_exit_2():
    """Invalid scene / missing project / launch failure exits 2."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.run_playtest_coverage",
            side_effect=CoveragePlaytestError("No main scene configured"),
        ),
    ):
        result = runner.invoke(cli, ["coverage", "run"])
    assert result.exit_code == 2
