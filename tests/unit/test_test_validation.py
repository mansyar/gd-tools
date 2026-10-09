"""Unit tests for the declarative test-command flag-conflict table."""

import contextlib
import io
from collections.abc import Callable

import click
import pytest
from rich.console import Console

from gd_tools.commands.test_validation import (
    RuleStage,
    FlagState,
    validate_test_flags,
)

pytestmark = pytest.mark.unit


def _state(**overrides: object) -> FlagState:
    """Build a flag state, defaulting to a clean, conflict-free run."""
    defaults: dict[str, object] = {
        "paths": (),
        "coverage": False,
        "min": None,
        "show_uncovered": False,
        "watch": False,
        "changed": False,
        "base": None,
        "shard": None,
    }
    defaults.update(overrides)
    return FlagState(**defaults)


def _stderr_of(validate: Callable[[], None]) -> tuple[str, int | None]:
    """Run ``validate`` inside a click context; return (stderr, exit code)."""
    err = io.StringIO()
    exit_code: int | None = None
    with click.Context(click.Command("test")):
        with contextlib.redirect_stderr(err):
            try:
                validate()
            except click.exceptions.Exit as e:
                exit_code = e.exit_code
    return err.getvalue(), exit_code


def test_base_without_changed_errors() -> None:
    """--base without --changed errors with exit code 2."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(base="main"), stage=RuleStage.PRE_CONFIG
        )
    )

    assert exit_code == 2
    assert "Error: --base requires --changed." in stderr


def test_changed_with_watch_errors() -> None:
    """--changed and --watch together error with exit code 2."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(changed=True, watch=True), stage=RuleStage.PRE_CONFIG
        )
    )

    assert exit_code == 2
    assert (
        "Error: --changed and --watch cannot be combined; --watch "
        "already selects suites per change." in stderr
    )


def test_shard_with_watch_errors() -> None:
    """--shard and --watch together error with exit code 2."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(shard="2/4", watch=True), stage=RuleStage.PRE_CONFIG
        )
    )

    assert exit_code == 2
    assert (
        "Error: --shard and --watch cannot be combined; --shard is a "
        "CI concern and --watch is a dev-loop concern." in stderr
    )


def test_watch_with_ci_true_errors() -> None:
    """--watch under CI=true errors with exit code 2."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(watch=True),
            stage=RuleStage.PRE_DISPATCH,
            env={"CI": "true"},
        )
    )

    assert exit_code == 2
    assert (
        "Error: --watch is interactive and cannot run with CI=true." in stderr
    )


def test_watch_with_ci_true_is_case_insensitive() -> None:
    """A CI=true check matches case-insensitively, as before."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(watch=True),
            stage=RuleStage.PRE_DISPATCH,
            env={"CI": "TRUE"},
        )
    )

    assert exit_code == 2
    assert (
        "Error: --watch is interactive and cannot run with CI=true." in stderr
    )


def test_watch_with_paths_errors() -> None:
    """--watch with path arguments errors with exit code 2."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(watch=True, paths=("tests/",)),
            stage=RuleStage.PRE_DISPATCH,
            env={},
        )
    )

    assert exit_code == 2
    assert (
        "Error: --watch does not accept path arguments; it watches the "
        "whole project scope." in stderr
    )


def test_min_without_coverage_warns_only() -> None:
    """--min without --coverage prints a warning and does not exit."""
    sink = io.StringIO()
    console = Console(file=sink, width=120, legacy_windows=False)

    result = validate_test_flags(
        _state(min=80),
        stage=RuleStage.POST_CONFIG,
        console=console,
    )

    assert result is None
    assert (
        "Warning: --min is only valid with --coverage; ignoring."
        in sink.getvalue()
    )


def test_show_uncovered_without_coverage_warns_only() -> None:
    """--show-uncovered without --coverage prints a warning and does not exit."""
    sink = io.StringIO()
    console = Console(file=sink, width=120, legacy_windows=False)

    result = validate_test_flags(
        _state(show_uncovered=True),
        stage=RuleStage.POST_CONFIG,
        console=console,
    )

    assert result is None
    assert (
        "Warning: --show-uncovered is only valid with --coverage; ignoring."
        in sink.getvalue()
    )


def test_pre_config_stage_skips_later_stage_rules() -> None:
    """Later-stage rules do not fire during the pre-config pass."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(watch=True, paths=("tests/",), min=80),
            stage=RuleStage.PRE_CONFIG,
            env={"CI": "true"},
        )
    )

    assert exit_code is None
    assert stderr == ""


def test_post_config_stage_skips_other_stage_rules() -> None:
    """Pre-config and pre-dispatch rules do not fire post-config."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(base="main", watch=True, paths=("tests/",)),
            stage=RuleStage.POST_CONFIG,
            env={"CI": "true"},
        )
    )

    assert exit_code is None
    assert stderr == ""


def test_pre_dispatch_stage_skips_other_stage_rules() -> None:
    """Pre-config rules do not fire during the pre-dispatch pass."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(base="main"),
            stage=RuleStage.PRE_DISPATCH,
        )
    )

    assert exit_code is None
    assert stderr == ""


def test_first_violation_wins_in_table_order() -> None:
    """With multiple violations, the earliest table rule fires first."""
    stderr, exit_code = _stderr_of(
        lambda: validate_test_flags(
            _state(base="main", shard="2/4", watch=True),
            stage=RuleStage.PRE_CONFIG,
        )
    )

    assert exit_code == 2
    assert "Error: --base requires --changed." in stderr
    assert "--shard and --watch cannot be combined" not in stderr


def test_clean_state_passes_silently() -> None:
    """A conflict-free state produces no output and no exit."""
    for stage in RuleStage:
        stderr, exit_code = _stderr_of(
            lambda stage=stage: validate_test_flags(_state(), stage=stage)
        )

        assert exit_code is None
        assert stderr == ""
