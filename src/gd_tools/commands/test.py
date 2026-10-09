"""The ``test`` command: run GDScript tests with the native runtime."""

import click

from ..config import ConfigError, load_config
from ..errors import GdToolsError, TestFailureError
from ..native_test.command import run_native_test_command
from ..watch.session import run_watch_mode
from .test_validation import FlagState, RuleStage, validate_test_flags


def _reject_legacy_runtime(source: str) -> None:
    """Reject the removed GUT runtime option with migration guidance."""
    click.echo(
        f"Error: GUT runtime support was removed in v0.6.0 ({source}). "
        "The native runtime is the default. Run `gd-tools migrate` or see "
        "docs/gut-migration.md.",
        err=True,
    )
    ctx = click.get_current_context()
    ctx.exit(2)


def _validate_parallel(
    ctx: click.Context,
    param: click.Parameter,
    value: int | None,
) -> int | None:
    """Validate the --parallel worker count range (1-32)."""
    if value is None:
        return None
    if not 1 <= value <= 32:
        raise click.BadParameter(
            "must be an integer between 1 and 32.",
            ctx=ctx,
            param=param,
        )
    return value


def _validate_durations(
    ctx: click.Context,
    param: click.Parameter,
    value: int | None,
) -> int | None:
    """Validate the --durations count (a non-negative integer)."""
    if value is None:
        return None
    if value < 0:
        raise click.BadParameter(
            "must be a non-negative integer (0 shows all tests).",
            ctx=ctx,
            param=param,
        )
    return value


def _validate_shard(
    ctx: click.Context,
    param: click.Parameter,
    value: str | None,
) -> tuple[int, int] | None:
    """Validate the --shard K/N flag (1-based, 1 <= K <= N)."""
    if value is None:
        return None
    parts = value.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise click.BadParameter(
            "must be of the form K/N (e.g. --shard 2/4).",
            ctx=ctx,
            param=param,
        )
    try:
        k, n = int(parts[0]), int(parts[1])
    except ValueError:
        raise click.BadParameter(
            "must be of the form K/N with integer parts (e.g. --shard 2/4).",
            ctx=ctx,
            param=param,
        ) from None
    if n < 1 or k < 1 or k > n:
        raise click.BadParameter(
            "requires 1 <= K <= N (e.g. --shard 2/4).",
            ctx=ctx,
            param=param,
        )
    return (k, n)


@click.command()
@click.argument("paths", nargs=-1)
@click.option(
    "--runtime",
    type=click.Choice(["native", "gut"]),
    default=None,
    help="Select the test runtime (default: native). 'gut' was removed in "
    "v0.6.0; see docs/gut-migration.md.",
)
@click.option(
    "--parallel",
    type=click.INT,
    is_flag=False,
    flag_value="4",
    default=None,
    callback=_validate_parallel,
    help="Run suites with up to N concurrent workers (1-32). Bare "
    "--parallel defaults to 4 workers. Omit for sequential execution.",
)
@click.option(
    "--durations",
    type=click.INT,
    is_flag=False,
    flag_value="10",
    default=None,
    callback=_validate_durations,
    help="Report the N slowest tests after the run. Bare --durations "
    "defaults to 10; --durations 0 lists every test. Omit to disable.",
)
@click.option("--coverage", is_flag=True, help="Generate coverage report.")
@click.option("--min", type=int, help="Minimum coverage threshold.")
@click.option(
    "--min-branch",
    type=int,
    help="Minimum branch coverage threshold.",
)
@click.option("--suite", help="Specify which test suite to run.")
@click.option("--test", help="Specify which test to run.")
@click.option(
    "--tag",
    "tags",
    multiple=True,
    help="Run native suites matching this class tag (repeatable).",
)
@click.option(
    "--test-timeout",
    type=float,
    help="Per-test timeout in seconds for native tests.",
)
@click.option("--junit-xml", help="Path to write JUnit XML report.")
@click.option(
    "--no-exit-code",
    is_flag=True,
    help="Don't exit with non-zero on test failure.",
)
@click.option(
    "--timeout",
    type=int,
    help="Timeout in seconds for the test run.",
)
@click.option(
    "--show-uncovered",
    is_flag=True,
    help="Show uncovered lines and branches when coverage is below 100%.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Bypass caching: regenerate the coverage plan and re-run the "
    "integration preflight instead of serving cached results.",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Watch .gd files and re-run affected tests on change "
    "(native runtime only, interactive sessions).",
)
@click.option(
    "--changed",
    is_flag=True,
    help="Run only the suites mapped from git-changed files (uncommitted "
    "vs HEAD). A change that maps to no suite runs the full suite.",
)
@click.option(
    "--base",
    help="With --changed: diff from merge-base of this ref and HEAD "
    "instead of the working tree (for CI on pull requests).",
)
@click.option(
    "--snapshot-update",
    is_flag=True,
    help="Rewrite mismatched and malformed snapshots with the rendered "
    "output instead of failing their tests.",
)
@click.option(
    "--exitfirst",
    "-x",
    is_flag=True,
    default=False,
    help="Stop dispatching new suites after the first failing suite "
    "result. In-flight suites finish; unstarted suites are skipped.",
)
@click.option(
    "--shard",
    default=None,
    callback=_validate_shard,
    help="Run only shard K of N suites: suite i of the plan order goes to "
    "shard (i %% N) + 1. For CI matrix splitting, e.g. --shard 2/4.",
)
def test(
    paths,
    runtime,
    parallel,
    durations,
    coverage,
    min,
    min_branch,
    suite,
    test,
    tags,
    test_timeout,
    junit_xml,
    no_exit_code,
    timeout,
    show_uncovered,
    no_cache,
    watch,
    changed,
    base,
    snapshot_update,
    exitfirst,
    shard,
):
    """Run GDScript tests with the native runtime.

    The GUT compatibility bridge was removed in v0.6.0; ``--runtime gut``
    and ``test.runtime = "gut"`` are rejected (see docs/gut-migration.md).
    """
    if runtime == "gut":
        _reject_legacy_runtime("--runtime gut")
    flags = FlagState(
        paths=tuple(paths),
        coverage=coverage,
        min=min,
        show_uncovered=show_uncovered,
        watch=watch,
        changed=changed,
        base=base,
        shard=shard,
    )
    validate_test_flags(flags, stage=RuleStage.PRE_CONFIG)
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    validate_test_flags(flags, stage=RuleStage.POST_CONFIG)

    selected_runtime = runtime
    if selected_runtime is None:
        selected_runtime = getattr(config.test, "runtime", "native")
    if selected_runtime == "gut":
        _reject_legacy_runtime('test.runtime = "gut" in gd-tools.toml')
    if selected_runtime not in {"native", "gut"}:
        selected_runtime = "native"

    effective_parallel = (
        parallel if parallel is not None else config.test.parallel
    )
    effective_durations = (
        durations if durations is not None else config.test.durations
    )

    validate_test_flags(flags, stage=RuleStage.PRE_DISPATCH)

    try:
        if watch:
            ctx = click.get_current_context()
            ctx.exit(
                run_watch_mode(
                    config=config,
                    coverage=coverage,
                    min_percent=min,
                    suite=suite,
                    test_name=test,
                    junit_xml=junit_xml,
                    timeout=timeout,
                    tags=tags,
                    test_timeout=test_timeout,
                    show_uncovered=show_uncovered,
                    no_cache=no_cache,
                    parallel=effective_parallel,
                    durations=effective_durations,
                    snapshot_update=snapshot_update,
                    exitfirst=exitfirst,
                )
            )
        if selected_runtime == "native":
            run_native_test_command(
                config,
                coverage=coverage,
                min_percent=min,
                min_branch_percent=min_branch,
                suite=suite,
                test_name=test,
                junit_xml=junit_xml,
                no_exit_code=no_exit_code,
                timeout=timeout,
                tags=list(tags) if tags else None,
                test_timeout=test_timeout,
                paths=list(paths) if paths else None,
                show_uncovered=show_uncovered,
                no_cache=no_cache,
                parallel=effective_parallel,
                durations=effective_durations,
                changed=changed,
                base=base,
                snapshot_update=snapshot_update,
                exitfirst=exitfirst,
                shard=shard,
            )
    except TestFailureError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)
    except KeyboardInterrupt:
        # The command layer already reported the interrupted run; exit with
        # the conventional SIGINT code instead of a traceback.
        ctx = click.get_current_context()
        ctx.exit(130)
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)

    ctx = click.get_current_context()
    ctx.exit(0)
