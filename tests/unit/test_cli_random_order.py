"""Unit tests for the ``--random-order`` and ``--seed`` flags on ``test``."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import GdToolsConfig, TestConfig

pytestmark = pytest.mark.unit


def _invoke_test(args, config=None, env=None):
    """Invoke `test` with a real config and a patched native command.

    A real :class:`GdToolsConfig` is used rather than a ``MagicMock``
    because the command resolves ``random_order``/``seed`` against the
    config whenever the flags are absent — a mock attribute is always
    truthy and would silently make every assertion pass.

    Returns ``(result, mock_run)``.
    """
    runner = CliRunner()
    cfg = config if config is not None else GdToolsConfig()
    with (
        patch("gd_tools.commands.test.load_config", return_value=cfg),
        patch(
            "gd_tools.commands.test.run_native_test_command",
            return_value=MagicMock(),
        ) as mock_run,
    ):
        result = runner.invoke(cli, args, env=env)
    return result, mock_run


# --- flag surface ---


def test_test_help_exposes_random_order_flags():
    """The test command documents --random-order and --seed."""
    result = CliRunner().invoke(cli, ["test", "--help"])

    assert result.exit_code == 0
    assert "--random-order" in result.output
    assert "--no-random-order" in result.output
    assert "--seed" in result.output


def test_random_order_flag_forwarded():
    """--random-order forwards random_order=True to the native command."""
    result, mock_run = _invoke_test(["test", "--random-order"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is True


def test_random_order_absent_is_false_by_default():
    """With no flag and no config key, ordering is off (opt-in default)."""
    result, mock_run = _invoke_test(["test"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is False
    assert mock_run.call_args.kwargs["seed"] is None


def test_no_random_order_overrides_a_configured_opt_in():
    """--no-random-order unshuffles a project that opted in via config."""
    config = GdToolsConfig(test=TestConfig(random_order=True, seed=4242))
    result, mock_run = _invoke_test(
        ["test", "--no-random-order"], config=config
    )

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is False


def test_no_random_order_alone_stays_off():
    """--no-random-order on an unconfigured project changes nothing."""
    result, mock_run = _invoke_test(["test", "--no-random-order"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is False


def test_no_random_order_wins_over_a_seed():
    """An explicit disable beats the ordering a --seed would imply."""
    result, mock_run = _invoke_test(
        ["test", "--seed", "1234", "--no-random-order"]
    )

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is False


def test_seed_implies_random_order():
    """A bare --seed implies random ordering (FR-3)."""
    result, mock_run = _invoke_test(["test", "--seed", "1234"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is True
    assert mock_run.call_args.kwargs["seed"] == 1234


@pytest.mark.parametrize("value", ["-1", "abc"])
def test_seed_rejects_invalid_values(value):
    """A negative or non-integer seed exits 2 without dispatching.

    The assertion is on the *value* error text rather than only the exit
    code: an undefined ``--seed`` option also exits 2 ("No such option"),
    so an exit-code-only assertion would pass before the flag exists.
    """
    result, mock_run = _invoke_test(["test", f"--seed={value}"])

    assert result.exit_code == 2
    assert "Invalid value" in result.output
    assert "No such option" not in result.output
    assert not mock_run.called


def test_seed_error_message_names_accepted_range():
    """The negative-seed rejection states the accepted range."""
    result, _ = _invoke_test(["test", "--seed=-1"])

    assert result.exit_code == 2
    assert "--seed" in result.output
    assert "0" in result.output


# --- config resolution ---


def test_config_random_order_used_when_flag_absent():
    """[test] random_order opts a project in without any CLI flag."""
    config = GdToolsConfig(test=TestConfig(random_order=True))
    result, mock_run = _invoke_test(["test"], config=config)

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is True


def test_config_seed_used_when_flag_absent():
    """[test] seed pins the project's order."""
    config = GdToolsConfig(test=TestConfig(random_order=True, seed=4242))
    result, mock_run = _invoke_test(["test"], config=config)

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["seed"] == 4242


def test_cli_seed_overrides_config_seed():
    """--seed takes precedence over [test] seed."""
    config = GdToolsConfig(test=TestConfig(random_order=True, seed=4242))
    result, mock_run = _invoke_test(["test", "--seed", "99"], config=config)

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["seed"] == 99


def test_config_seed_implies_random_order():
    """A configured seed implies random ordering too."""
    config = GdToolsConfig(test=TestConfig(seed=7))
    result, mock_run = _invoke_test(["test"], config=config)

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is True
    assert mock_run.call_args.kwargs["seed"] == 7


# --- composition ---


def test_random_order_accepted_with_shard():
    """--random-order and --shard compose; no flag-conflict rule (FR-19).

    Shard membership stays a function of the deterministic discovery
    order, so rejecting the combination would remove the only way to
    shuffle execution inside a CI shard.
    """
    result, mock_run = _invoke_test(
        ["test", "--random-order", "--shard", "2/4"]
    )

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["random_order"] is True
    assert mock_run.call_args.kwargs["shard"] == (2, 4)


def test_random_order_forwarded_to_watch_mode():
    """--random-order is forwarded into the watch session."""
    runner = CliRunner()
    with (
        patch(
            "gd_tools.commands.test.load_config",
            return_value=GdToolsConfig(),
        ),
        patch(
            "gd_tools.commands.test.run_watch_mode", return_value=0
        ) as mock_watch,
    ):
        result = runner.invoke(
            cli, ["test", "--random-order", "--watch"], env={"CI": ""}
        )

    assert result.exit_code == 0
    assert mock_watch.call_args.kwargs["random_order"] is True
