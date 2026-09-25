"""Unit tests for native and legacy test CLI dispatch."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.test_runner import TestResult

pytestmark = pytest.mark.unit


def _result() -> TestResult:
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


def test_init_help_exposes_optional_gut_install():
    """Init exposes the explicit legacy installation switch."""
    result = CliRunner().invoke(cli, ["init", "--help"])

    assert result.exit_code == 0
    assert "--with-gut" in result.output


def test_init_with_gut_passes_opt_in_flag():
    """The init command forwards the explicit GUT option."""
    with patch("gd_tools.cli.run_init") as run:
        result = CliRunner().invoke(cli, ["init", "--with-gut"])

    assert result.exit_code == 0
    run.assert_called_once_with(non_interactive=False, with_gut=True)


def test_test_help_exposes_native_runtime_selector():
    """The public test command exposes the native/GUT runtime choice."""
    result = CliRunner().invoke(cli, ["test", "--help"])

    assert result.exit_code == 0
    assert "--runtime" in result.output
    assert "--tag" in result.output
    assert "--test-timeout" in result.output
    assert "native" in result.output
    assert "gut" in result.output


def test_test_defaults_to_native_runtime_dispatch():
    """The default command routes to the native runner."""
    config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_result(),
        ) as native_run,
        patch("gd_tools.cli.run_tests") as legacy_run,
    ):
        result = CliRunner().invoke(cli, ["test"])

    assert result.exit_code == 0
    native_run.assert_called_once()
    legacy_run.assert_not_called()


def test_test_explicit_native_and_no_exit_dispatch_native_options():
    """Explicit native selection forwards suppression to the native adapter."""
    config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_result(),
        ) as native_run,
    ):
        result = CliRunner().invoke(
            cli, ["test", "--runtime", "native", "--no-exit-code"]
        )

    assert result.exit_code == 0
    assert native_run.call_args.kwargs["no_exit_code"] is True


def test_test_forwards_native_tags_and_test_timeout():
    """Native tag and per-test timeout options reach the adapter."""
    config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=config),
        patch(
            "gd_tools.cli.run_native_test_command",
            return_value=_result(),
        ) as native_run,
    ):
        result = CliRunner().invoke(
            cli,
            [
                "test",
                "--tag",
                "smoke",
                "--tag",
                "fast",
                "--test-timeout",
                "1.5",
            ],
        )

    assert result.exit_code == 0
    assert native_run.call_args.kwargs["tags"] == ["smoke", "fast"]
    assert native_run.call_args.kwargs["test_timeout"] == 1.5


def test_test_runtime_gut_dispatches_legacy_runner():
    """Explicit GUT selection preserves the existing runner."""
    config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=config),
        patch("gd_tools.cli.run_tests", return_value=_result()) as legacy_run,
        patch("gd_tools.cli.run_native_test_command") as native_run,
    ):
        result = CliRunner().invoke(cli, ["test", "--runtime", "gut"])

    assert result.exit_code == 0
    legacy_run.assert_called_once()
    native_run.assert_not_called()


def test_test_invalid_runtime_exits_2():
    """Unknown runtime names are configuration errors."""
    result = CliRunner().invoke(cli, ["test", "--runtime", "pytest"])

    assert result.exit_code == 2
