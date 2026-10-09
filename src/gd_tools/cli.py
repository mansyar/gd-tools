"""CLI entry point for gd-tools."""

import sys
from pathlib import Path
from typing import Any

import click
from click.shell_completion import (
    BashComplete,
    add_completion_class,
)

from . import __version__
from .commands.clean import clean
from .commands.completion import create_completion_command
from .commands.config import config
from .commands.coverage import coverage
from .commands.doctor import doctor
from .commands.format import format
from .commands.init import init
from .commands.install_hooks import install_hooks
from .commands.lint import lint
from .commands.migrate import migrate
from .commands.test_validation import FlagState, RuleStage, validate_test_flags
from .commands.version import version
from .config import ConfigError, load_config, set_explicit_project_root
from .errors import GdToolsError, TestFailureError
from .native_test.command import run_native_test_command
from .watch.session import run_watch_mode
from .addon_check import check_addon_version
from .update_check import check_for_update
from .verbosity import Verbosity, set_verbosity


def _configure_windows_utf8() -> None:
    """Reconfigure stdout/stderr to UTF-8 on Windows.

    Windows defaults to the system codepage (e.g. cp1252) for console
    output, which cannot encode Unicode characters used by Rich (✓, ✗,
    ⚠). This reconfigures the standard streams to UTF-8, matching the
    effect of setting PYTHONUTF8=1.
    """
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


_configure_windows_utf8()


_SOURCE_POWERSHELL = """Register-ArgumentCompleter -Native -CommandName %(prog_name)s -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $words = $commandAst.CommandElements | ForEach-Object { $_.ToString() }
    $env:COMP_WORDS = $words -join ' '
    $commandElements = $commandAst.CommandElements
    $env:COMP_CWORD = $commandElements.Count
    for ($i = 0; $i -lt $commandElements.Count; $i++) {
        if ($cursorPosition -le $commandElements[$i].Extent.StartOffset) {
            $env:COMP_CWORD = $i
            break
        }
    }

    $env:%(complete_var)s = "powershell_complete"
    %(prog_name)s | ForEach-Object {
        $values = $_.Split(",")
        if ($values[0] -eq "dir") {
            [System.Management.Automation.CompletionResult]::new($values[1], $values[1], "ParameterValue", $values[1])
        } elseif ($values[0] -eq "file") {
            [System.Management.Automation.CompletionResult]::new($values[1], $values[1], "ParameterValue", $values[1])
        } else {
            $help = if ($values[2] -eq "_") { "" } else { $values[2] }
            [System.Management.Automation.CompletionResult]::new($values[1], $values[1], "ParameterValue", $help)
        }
    }

    $env:COMP_WORDS = $null
    $env:COMP_CWORD = 0
    $env:%(complete_var)s = $null
}
"""


class PowerShellComplete(BashComplete):
    """Shell completion for PowerShell.

    Click 8.2.x does not include a PowerShell completion class.
    This subclass reuses BashComplete's completion args and
    format_completion, providing a PowerShell-compatible source
    template using Register-ArgumentCompleter.
    """

    name = "powershell"
    source_template = _SOURCE_POWERSHELL


add_completion_class(PowerShellComplete)


class GdToolsGroup(click.Group):
    """Custom Click group that converts NotImplementedError to exit code 2.

    Stub commands raise ``NotImplementedError`` to indicate they are not
    yet implemented. This class catches that exception and exits with
    code 2 (configuration/usage error), consistent with the gd-tools
    error convention.
    """

    def invoke(self, ctx) -> Any:
        """Invoke the group, catching NotImplementedError as exit code 2.

        Performs an update check before dispatching to the subcommand.
        If a newer version is available, a notification is printed to
        stderr. The check fails silently and never blocks execution.

        In quiet mode (``--quiet``/``-q``), both the update check and
        the addon version check are skipped entirely.

        Args:
            ctx: The Click context for this invocation.

        Returns:
            The result of the underlying command invocation.

        Raises:
            SystemExit: With code 2 if a command raises
                NotImplementedError.
        """
        # Use raw ctx.params here — set_verbosity() runs inside the group
        # callback (invoked by super().invoke below), so get_verbosity()
        # is not yet set at this point.
        quiet = ctx.params.get("quiet", False)
        if not quiet:
            latest = check_for_update()
            if latest is not None:
                click.echo(
                    f"A new version of gd-tools is available: {latest} "
                    f"(you have {__version__}).\n"
                    f"Run `pip install --upgrade gd-tools-cli` to update.",
                    err=True,
                )
            check_addon_version()
        try:
            return super().invoke(ctx)
        except NotImplementedError:
            click.echo(
                "Error: This command is not yet implemented.",
                err=True,
            )
            ctx.exit(2)


@click.group(cls=GdToolsGroup)
@click.version_option(
    version=__version__,
    prog_name="gd-tools",
    message="%(prog)s %(version)s",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show verbose output including underlying commands and timing.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress non-essential output (update checks, progress info).",
)
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to the Godot project root. Defaults to discovery from "
    "the current working directory.",
)
def cli(verbose: bool, quiet: bool, project_path: Path | None):
    """gd-tools: A modern development workflow CLI for GDScript."""
    set_explicit_project_root(project_path)
    if verbose and quiet:
        click.echo(
            "Error: --verbose and --quiet are mutually exclusive.", err=True
        )
        ctx = click.get_current_context()
        ctx.exit(2)
    if verbose:
        set_verbosity(Verbosity.VERBOSE)
    elif quiet:
        set_verbosity(Verbosity.QUIET)
    else:
        set_verbosity(Verbosity.DEFAULT)


# Register the extracted commands, preserving the original help order:
# init, doctor, version, clean, install-hooks, test, migrate, lint,
# format, coverage, config, completion.
cli.add_command(init)
cli.add_command(doctor)
cli.add_command(version)
cli.add_command(clean)
cli.add_command(install_hooks)


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


@cli.command()
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


# Commands defined after `test` keep their original registration order.
cli.add_command(migrate)
cli.add_command(lint)
cli.add_command(format)
cli.add_command(coverage)
cli.add_command(config)
cli.add_command(create_completion_command(cli))
