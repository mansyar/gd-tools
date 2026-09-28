"""Unit tests for the ``--watch`` flag on the ``test`` command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit


def test_watch_with_gut_runtime_exits_2():
    """``--watch`` is native-only; combining it with GUT exits 2."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch("gd_tools.cli.run_watch_mode") as mock_watch,
    ):
        result = runner.invoke(cli, ["test", "--watch", "--runtime", "gut"])
    assert result.exit_code == 2
    assert "native" in result.output
    mock_watch.assert_not_called()


def test_watch_with_ci_env_exits_2():
    """Watch mode is interactive; CI=true makes it a hard error (exit 2)."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch("gd_tools.cli.run_watch_mode") as mock_watch,
    ):
        result = runner.invoke(cli, ["test", "--watch"], env={"CI": "true"})
    assert result.exit_code == 2
    assert "CI" in result.output
    mock_watch.assert_not_called()


def test_watch_with_path_arguments_exits_2():
    """Watch mode ignores positional paths; it must reject them instead."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch("gd_tools.cli.run_watch_mode") as mock_watch,
    ):
        result = runner.invoke(
            cli, ["test", "tests/", "--watch"], env={"CI": ""}
        )
    assert result.exit_code == 2
    assert "path" in result.output
    mock_watch.assert_not_called()


def test_watch_passes_filters_and_coverage_to_session():
    """Filters and --coverage are passed through to the watch session."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.run_watch_mode", return_value=0) as mock_watch,
    ):
        result = runner.invoke(
            cli,
            [
                "test",
                "--watch",
                "--coverage",
                "--suite",
                "EnemySuite",
                "--test",
                "test_health",
                "--tag",
                "smoke",
            ],
            env={"CI": ""},
        )
    assert result.exit_code == 0
    mock_watch.assert_called_once()
    kwargs = mock_watch.call_args.kwargs
    assert kwargs["config"] is mock_config
    assert kwargs["coverage"] is True
    assert kwargs["suite"] == "EnemySuite"
    assert kwargs["test_name"] == "test_health"
    assert kwargs["tags"] == ("smoke",)
