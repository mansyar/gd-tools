"""Unit tests for the ``--changed`` / ``--base`` flags on the ``test`` command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit


def test_base_without_changed_exits_2():
    """``--base`` only modifies ``--changed``; alone it is an error."""
    runner = CliRunner()
    with patch("gd_tools.commands.test.load_config", return_value=MagicMock()):
        result = runner.invoke(cli, ["test", "--base", "main"])
    assert result.exit_code == 2
    assert "--changed" in result.output


def test_changed_with_watch_exits_2():
    """``--changed`` and ``--watch`` both drive selection; combining is an error."""
    runner = CliRunner()
    with (
        patch("gd_tools.commands.test.load_config", return_value=MagicMock()),
        patch("gd_tools.commands.test.run_native_test_command") as run,
    ):
        result = runner.invoke(
            cli, ["test", "--changed", "--watch"], env={"CI": ""}
        )
    assert result.exit_code == 2
    run.assert_not_called()


def test_changed_passes_flags_to_command():
    """``--changed``/``--base`` are forwarded to the native test command."""
    runner = CliRunner()
    with (
        patch("gd_tools.commands.test.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.commands.test.run_native_test_command",
            return_value=MagicMock(),
        ) as run,
    ):
        result = runner.invoke(cli, ["test", "--changed", "--base", "main"])
    assert result.exit_code == 0
    kwargs = run.call_args.kwargs
    assert kwargs["changed"] is True
    assert kwargs["base"] == "main"
