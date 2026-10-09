"""Declarative flag-conflict validation for the ``test`` command.

The rules in :data:`TEST_FLAG_RULES` replace the hand-written pairwise
checks that used to live inline in ``cli.py``. Every entry is data;
:func:`validate_test_flags` interprets them in table order, preserving
the original check ordering so behavior (messages, exit codes,
first-violation-wins) stays identical.

The table is split into three stages that mirror the original evaluation
order relative to config loading and runtime selection:

* ``PRE_CONFIG`` — hard conflicts checked before ``load_config()``.
* ``POST_CONFIG`` — soft warnings, checked after ``load_config()`` but
  before runtime selection (so a legacy ``test.runtime`` rejection still
  fires after any warning, as before).
* ``PRE_DISPATCH`` — environment and positional-argument checks, checked
  after runtime selection, immediately before dispatch.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

import click
from rich.console import Console


class RuleStage(Enum):
    """When a rule is evaluated relative to config loading."""

    PRE_CONFIG = "pre_config"
    POST_CONFIG = "post_config"
    PRE_DISPATCH = "pre_dispatch"


class RuleSeverity(Enum):
    """What happens when a rule is violated."""

    ERROR = "error"
    WARNING = "warning"


class RuleKind(Enum):
    """Shape of the condition a rule checks."""

    REQUIRES = "requires"
    EXCLUSIVE = "exclusive"
    FORBIDDEN_ENV = "forbidden_env"
    FORBIDDEN_ARGS = "forbidden_args"


@dataclass(frozen=True)
class FlagState:
    """The subset of ``test`` flags the rule table reads."""

    paths: tuple[str, ...] = ()
    coverage: bool = False
    min: int | None = None
    show_uncovered: bool = False
    watch: bool = False
    changed: bool = False
    base: str | None = None
    shard: str | None = None


@dataclass(frozen=True)
class FlagRule:
    """One declarative validation rule for the ``test`` command.

    ``message`` is the detail line without the ``Error: ``/``Warning: ``
    prefix; the validator adds the prefix appropriate to ``severity`` so
    the rendered output matches the original hand-written checks exactly.
    """

    kind: RuleKind
    severity: RuleSeverity
    stage: RuleStage
    flag: str
    message: str
    other: str | None = None
    env_key: str | None = None
    env_value: str | None = None


TEST_FLAG_RULES: tuple[FlagRule, ...] = (
    FlagRule(
        kind=RuleKind.REQUIRES,
        severity=RuleSeverity.ERROR,
        stage=RuleStage.PRE_CONFIG,
        flag="base",
        other="changed",
        message="--base requires --changed.",
    ),
    FlagRule(
        kind=RuleKind.EXCLUSIVE,
        severity=RuleSeverity.ERROR,
        stage=RuleStage.PRE_CONFIG,
        flag="changed",
        other="watch",
        message=(
            "--changed and --watch cannot be combined; --watch "
            "already selects suites per change."
        ),
    ),
    FlagRule(
        kind=RuleKind.EXCLUSIVE,
        severity=RuleSeverity.ERROR,
        stage=RuleStage.PRE_CONFIG,
        flag="shard",
        other="watch",
        message=(
            "--shard and --watch cannot be combined; --shard is a "
            "CI concern and --watch is a dev-loop concern."
        ),
    ),
    FlagRule(
        kind=RuleKind.REQUIRES,
        severity=RuleSeverity.WARNING,
        stage=RuleStage.POST_CONFIG,
        flag="min",
        other="coverage",
        message="--min is only valid with --coverage; ignoring.",
    ),
    FlagRule(
        kind=RuleKind.REQUIRES,
        severity=RuleSeverity.WARNING,
        stage=RuleStage.POST_CONFIG,
        flag="show_uncovered",
        other="coverage",
        message="--show-uncovered is only valid with --coverage; ignoring.",
    ),
    FlagRule(
        kind=RuleKind.FORBIDDEN_ENV,
        severity=RuleSeverity.ERROR,
        stage=RuleStage.PRE_DISPATCH,
        flag="watch",
        env_key="CI",
        env_value="true",
        message="--watch is interactive and cannot run with CI=true.",
    ),
    FlagRule(
        kind=RuleKind.FORBIDDEN_ARGS,
        severity=RuleSeverity.ERROR,
        stage=RuleStage.PRE_DISPATCH,
        flag="watch",
        message=(
            "--watch does not accept path arguments; it watches the "
            "whole project scope."
        ),
    ),
)


def _is_set(state: FlagState, flag: str) -> bool:
    """Return whether ``flag`` carries a user-provided, truthy value."""
    return bool(getattr(state, flag))


def _violated(
    rule: FlagRule, state: FlagState, environ: Mapping[str, str]
) -> bool:
    """Evaluate one rule against the flag state."""
    if rule.kind is RuleKind.REQUIRES and rule.other is not None:
        return _is_set(state, rule.flag) and not _is_set(state, rule.other)
    if rule.kind is RuleKind.EXCLUSIVE and rule.other is not None:
        return _is_set(state, rule.flag) and _is_set(state, rule.other)
    if rule.kind is RuleKind.FORBIDDEN_ENV and rule.env_key is not None:
        value = environ.get(rule.env_key, "").lower()
        return _is_set(state, rule.flag) and value == (rule.env_value or "")
    if rule.kind is RuleKind.FORBIDDEN_ARGS:
        return _is_set(state, rule.flag) and bool(state.paths)
    return False


def validate_test_flags(
    state: FlagState,
    *,
    stage: RuleStage,
    env: Mapping[str, str] | None = None,
    console: Console | None = None,
) -> None:
    """Evaluate the rule table for ``stage`` against ``state``.

    Rules fire in table order; the first ``ERROR`` violation reports to
    stderr and exits with code 2. ``WARNING`` violations print a yellow
    note on ``console`` and execution continues.

    Args:
        state: The resolved ``test`` flag values.
        stage: Which pass to evaluate; rules for other stages are skipped.
        env: Environment mapping for ``FORBIDDEN_ENV`` rules; defaults to
            ``os.environ``.
        console: Output sink for warnings; defaults to a fresh ``Console``.

    Raises:
        click.exceptions.Exit: With code 2 on the first ``ERROR`` violation.
    """
    environ = os.environ if env is None else env
    sink = console if console is not None else Console()
    for rule in TEST_FLAG_RULES:
        if rule.stage is not stage or not _violated(rule, state, environ):
            continue
        if rule.severity is RuleSeverity.ERROR:
            click.echo(f"Error: {rule.message}", err=True)
            ctx = click.get_current_context()
            ctx.exit(2)
        sink.print(f"[yellow]Warning: {rule.message}[/yellow]")
