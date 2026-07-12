"""Unit tests for the gd_tools CLI skeleton."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.doctor import CheckResult, DoctorResult
from gd_tools.errors import (
    ConfigError,
    CoveragePlanError,
    CoverageThresholdError,
    GUTNotInstalledError,
    TestFailureError,
)
from gd_tools.format_runner import FormatResult
from gd_tools.lint_runner import LintIssue, LintResult
from gd_tools.test_runner import TestResult


import pytest
pytestmark = pytest.mark.unit

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


def test_test_calls_run_tests_with_correct_args():
    """Test test command calls run_tests with config and default flags."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
        total=3,
        passed=3,
        failed=0,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["test"])
    assert result.exit_code == 0
    mock_run.assert_called_once_with(
        mock_config,
        coverage=False,
        min_percent=None,
        suite=None,
        test_name=None,
        junit_xml=None,
        no_exit_code=False,
    )


def test_test_suite_flag():
    """Test --suite passes suite to run_tests."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["test", "--suite", "MySuite"])
    assert result.exit_code == 0
    _, kwargs = mock_run.call_args
    assert kwargs["suite"] == "MySuite"


def test_test_name_flag():
    """Test --test passes test_name to run_tests."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["test", "--test", "MyTest"])
    assert result.exit_code == 0
    _, kwargs = mock_run.call_args
    assert kwargs["test_name"] == "MyTest"


def test_test_coverage_calls_orchestrator():
    """Test --coverage calls orchestrator.run_coverage_test, not run_tests."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_coverage_test",
            return_value=mock_result,
        ) as mock_orch,
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    assert result.exit_code == 0
    mock_orch.assert_called_once()


def test_test_coverage_min_passed_to_orchestrator():
    """Test --coverage --min 80 passes min_percent=80 to orchestrator."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_coverage_test",
            return_value=mock_result,
        ) as mock_orch,
    ):
        result = runner.invoke(cli, ["test", "--coverage", "--min", "80"])
    assert result.exit_code == 0
    _, kwargs = mock_orch.call_args
    assert kwargs["min_percent"] == 80


def test_test_no_coverage_calls_run_tests_directly():
    """Test test without --coverage calls run_tests directly (regression guard)."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result) as mock_run,
        patch("gd_tools.cli.run_coverage_test") as mock_orch,
    ):
        result = runner.invoke(cli, ["test"])
    assert result.exit_code == 0
    mock_run.assert_called_once()
    mock_orch.assert_not_called()


def test_test_coverage_test_failure_exit_1():
    """Test TestFailureError from orchestrator exits with code 1."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_coverage_test",
            side_effect=TestFailureError("2 test(s) failed"),
        ),
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    assert result.exit_code == 1


def test_test_coverage_threshold_error_exit_1():
    """Test CoverageThresholdError from orchestrator exits with code 1."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_coverage_test",
            side_effect=CoverageThresholdError("Coverage below threshold"),
        ),
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    assert result.exit_code == 1


def test_test_coverage_plan_error_exit_2():
    """Test CoveragePlanError from orchestrator exits with code 2."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_coverage_test",
            side_effect=CoveragePlanError("Missing plan"),
        ),
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    assert result.exit_code == 2


def test_test_coverage_no_exit_code_propagated():
    """Test --no-exit-code flag is propagated to orchestrator."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_coverage_test",
            return_value=mock_result,
        ) as mock_orch,
    ):
        result = runner.invoke(cli, ["test", "--coverage", "--no-exit-code"])
    assert result.exit_code == 0
    _, kwargs = mock_orch.call_args
    assert kwargs["no_exit_code"] is True


def test_test_junit_xml_flag():
    """Test --junit-xml passes junit_xml to run_tests."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["test", "--junit-xml", "/path/to.xml"])
    assert result.exit_code == 0
    _, kwargs = mock_run.call_args
    assert kwargs["junit_xml"] == "/path/to.xml"


def test_test_no_exit_code_flag():
    """Test --no-exit-code passes no_exit_code=True to run_tests."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
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
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result) as mock_run,
    ):
        result = runner.invoke(cli, ["test", "--no-exit-code"])
    assert result.exit_code == 0
    _, kwargs = mock_run.call_args
    assert kwargs["no_exit_code"] is True


def test_test_all_pass_exit_code_0():
    """Test test command exits 0 when all tests pass."""
    runner = CliRunner()
    mock_config = MagicMock()
    mock_result = TestResult(
        total=3,
        passed=3,
        failed=0,
        skipped=0,
        duration=0.5,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=[],
    )
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_tests", return_value=mock_result),
    ):
        result = runner.invoke(cli, ["test"])
    assert result.exit_code == 0


def test_test_failures_exit_code_1():
    """Test test command exits 1 when tests fail."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_tests",
            side_effect=TestFailureError("2 test(s) failed"),
        ),
    ):
        result = runner.invoke(cli, ["test"])
    assert result.exit_code == 1


def test_test_gut_not_installed_exit_code_2():
    """Test test command exits 2 when GUT is not installed."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.run_tests",
            side_effect=GUTNotInstalledError("GUT is not installed"),
        ),
    ):
        result = runner.invoke(cli, ["test"])
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
    mock_run.assert_called_once_with(mock_config, ".", "text")


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
    mock_run.assert_called_once_with(mock_config, "some/path", "json")


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
        mock_config, "some/path", check=False, diff=False
    )
    assert "Formatted 2 of 3 file(s)" in result.output


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
    mock_run.assert_called_once_with(mock_config, ".", check=False, diff=False)


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
    mock_run.assert_called_once_with(non_interactive=True)


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
