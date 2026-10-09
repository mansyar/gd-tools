"""Unit tests for the ``--exitfirst`` and ``--shard k/N`` flags on ``test``."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit


def _invoke_test(args, env=None):
    """Invoke `test` with a mock config and a patched native command.

    Returns (result, mock_run) with run_native_test_command patched.
    """
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.commands.test.load_config", return_value=mock_config),
        patch(
            "gd_tools.commands.test.run_native_test_command",
            return_value=MagicMock(),
        ) as mock_run,
    ):
        result = runner.invoke(cli, args, env=env)
    return result, mock_run


# --- --exitfirst flag ---


def test_exitfirst_flag_forwarded():
    """--exitfirst forwards exitfirst=True to the native test command."""
    result, mock_run = _invoke_test(["test", "--exitfirst"])
    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["exitfirst"] is True


def test_exitfirst_short_alias_forwarded():
    """-x is the pytest-compatible short alias of --exitfirst."""
    result, mock_run = _invoke_test(["test", "-x"])
    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["exitfirst"] is True


def test_exitfirst_absent_is_false():
    """Without the flag, exitfirst is False (v0.7.0 default behavior)."""
    result, mock_run = _invoke_test(["test"])
    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["exitfirst"] is False


def test_exitfirst_accepted_with_watch():
    """--exitfirst composes with --watch; it is forwarded to the session."""
    runner = CliRunner()
    with (
        patch("gd_tools.commands.test.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.commands.test.run_watch_mode", return_value=0
        ) as mock_watch,
    ):
        result = runner.invoke(
            cli, ["test", "--exitfirst", "--watch"], env={"CI": ""}
        )
    assert result.exit_code == 0
    assert mock_watch.call_args.kwargs["exitfirst"] is True


# --- --shard k/N flag ---


def test_shard_parses_to_tuple():
    """--shard k/N forwards a (k, N) integer tuple to the command."""
    result, mock_run = _invoke_test(["test", "--shard", "2/4"])
    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["shard"] == (2, 4)


def test_shard_one_of_one_forwarded():
    """--shard 1/1 is valid and equivalent to no sharding."""
    result, mock_run = _invoke_test(["test", "--shard", "1/1"])
    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["shard"] == (1, 1)


def test_shard_absent_is_none():
    """Without the flag, shard is None (full plan, no shard selection)."""
    result, mock_run = _invoke_test(["test"])
    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["shard"] is None


@pytest.mark.parametrize("value", ["4/3", "0/3", "3", "a/b", "2/0", "2/"])
def test_shard_invalid_forms_exit_2(value):
    """Malformed or out-of-range --shard exits 2 with a fix hint."""
    result, mock_run = _invoke_test(["test", "--shard", value])
    assert result.exit_code == 2
    assert "--shard" in result.output
    mock_run.assert_not_called()


def test_shard_with_watch_exits_2():
    """--shard is a CI concern; combining it with --watch is an error."""
    result, mock_run = _invoke_test(
        ["test", "--shard", "1/2", "--watch"], env={"CI": ""}
    )
    assert result.exit_code == 2
    assert "--watch" in result.output
    mock_run.assert_not_called()


def test_shard_and_exitfirst_compose():
    """--shard and --exitfirst are accepted together and both forwarded."""
    result, mock_run = _invoke_test(["test", "--shard", "1/2", "--exitfirst"])
    assert result.exit_code == 0
    kwargs = mock_run.call_args.kwargs
    assert kwargs["shard"] == (1, 2)
    assert kwargs["exitfirst"] is True
