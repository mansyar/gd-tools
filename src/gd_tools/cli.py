"""CLI entry point for gd-tools."""

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

import click
from click.shell_completion import (
    BashComplete,
    add_completion_class,
    get_completion_class,
)
from pydantic import ValidationError
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from . import __version__, output
from .clean import (
    STATUS_ABSENT,
    STATUS_FAILED,
    STATUS_NOTHING,
    STATUS_PRESENT,
    STATUS_REMOVED,
    STATUS_SUBSUMED,
    STATUS_WOULD_REMOVE,
    CleanResult,
    run_clean,
)
from .pre_commit import (
    STATUS_ADDED,
    STATUS_NOTHING_TO_DO,
    InstallResult,
    install_hooks as run_install_hooks,
)
from .config import (
    check_deprecated_settings,
    find_project_root,
    format_config_json,
    format_config_table,
    format_config_toml,
    load_config,
    set_explicit_project_root,
    validate_paths,
    GdToolsConfig,
)
from .schema import generate_schema_text
from .coverage.orchestrator import (
    diff_coverage,
    generate_coverage_report,
    merge_coverage_files,
    save_coverage_baseline,
    show_coverage_summary,
)
from .coverage.playtest import run_playtest_coverage
from .doctor import format_doctor_table, run_doctor
from .errors import (
    ConfigError,
    CoveragePlaytestError,
    CoverageThresholdError,
    GdToolsError,
    TestFailureError,
)
from .format_runner import run_format
from .init import run_init
from .lint_runner import format_lint_json, format_lint_text, run_lint
from .migration.apply import apply_migration, plan_rewrites
from .migration.rewrite import generate_diff
from .migration.reporter import render_migration_report
from .migration.scan import MigrationScanError, build_migration_report
from .migration.gutconfig import translate_gutconfig
from .native_test.command import run_native_test_command
from .native_test.discovery import discover_native_suites
from .watch.session import run_watch_mode
from .update_check import check_for_update
from .addon_check import check_addon_version
from .verbosity import Verbosity, get_verbosity, set_verbosity
from .version import collect_versions

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


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


@cli.command()
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Run without interactive prompts.",
)
def init(non_interactive):
    """Initialize a new gd-tools configuration."""
    try:
        run_init(non_interactive=non_interactive)
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)

    ctx = click.get_current_context()
    ctx.exit(0)


@cli.command()
def doctor():
    """Check the environment for required tools."""
    result = run_doctor()
    if get_verbosity() == Verbosity.QUIET:
        if result.all_passed:
            output.print_success("All checks passed")
        else:
            output.print_error("Some checks failed")
    else:
        console = Console()
        console.print(format_doctor_table(result))
    ctx = click.get_current_context()
    ctx.exit(0 if result.all_passed else 1)


@cli.command()
@click.option(
    "--json", "as_json", is_flag=True, help="Output versions as JSON."
)
def version(as_json):
    """Display version information for all components."""
    versions = collect_versions()
    if as_json:
        click.echo(json.dumps(versions))
    else:
        table = Table(title="gd-tools Component Versions")
        table.add_column("Component")
        table.add_column("Version")
        for component, ver in versions.items():
            if ver is None:
                display = (
                    "not detected" if component == "godot" else "not installed"
                )
            else:
                display = ver
            table.add_row(component, display)
        console = Console()
        console.print(table)
    ctx = click.get_current_context()
    ctx.exit(0)


def _humanize_bytes(num_bytes: int) -> str:
    """Format a byte count for display (e.g., ``150 B``, ``4.2 KB``)."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _clean_target_label(name: str) -> str:
    """Return the user-facing path label for a clean target name."""
    labels = {
        "coverage": ".gd-tools/coverage",
        "artifacts": ".gd-tools/artifacts",
        "baselines": ".gd-tools/coverage/baseline.json",
        "cache": ".gd-tools/native",
    }
    return labels.get(name, name)


def _render_clean(result: CleanResult, inventory: bool, dry_run: bool) -> None:
    """Render the outcome of a clean run.

    Args:
        result: The :class:`CleanResult` returned by ``run_clean``.
        inventory: Whether this was a no-flag inventory run.
        dry_run: Whether deletion was suppressed.
    """
    if inventory:
        output.print_info("gd-tools artifacts inventory (.gd-tools/):")
        for entry in result.targets:
            if entry.status == STATUS_PRESENT:
                click.echo(
                    f"  {_clean_target_label(entry.name)}: "
                    f"{_humanize_bytes(entry.freed_bytes)}"
                )
            elif entry.status == STATUS_ABSENT:
                click.echo(
                    f"  {_clean_target_label(entry.name)}: nothing present"
                )
        output.print_info(
            "Hint: run `gd-tools clean --coverage` (or --artifacts, "
            "--baselines, --cache) to remove a target, or `gd-tools clean "
            "--all` to remove everything. Nothing was deleted."
        )
        return

    for entry in result.targets:
        label = _clean_target_label(entry.name)
        if entry.status == STATUS_REMOVED:
            output.print_success(
                f"removed {label} ({_humanize_bytes(entry.freed_bytes)} freed)"
            )
        elif entry.status == STATUS_WOULD_REMOVE:
            output.print_info(
                f"would remove {label} ({_humanize_bytes(entry.freed_bytes)})"
            )
        elif entry.status == STATUS_NOTHING:
            output.print_verbose(f"nothing to remove at {label}")
            click.echo(f"  {label}: nothing to remove")
        elif entry.status == STATUS_SUBSUMED:
            output.print_verbose(
                f"{label} covered by a broader target selection"
            )
        elif entry.status == STATUS_FAILED:
            click.echo(f"Error: {entry.error}")

    freed = _humanize_bytes(result.freed_bytes)
    if dry_run:
        output.print_summary(
            "warning", f"dry run: {freed} would be freed (nothing deleted)"
        )
    elif result.failed:
        output.print_summary(
            "fail", f"cleaning failed; {freed} freed before failure"
        )
    elif result.freed_bytes:
        output.print_summary("pass", f"{freed} freed")
    else:
        output.print_summary("pass", "nothing to remove")


@cli.command()
@click.option(
    "--coverage",
    is_flag=True,
    help=(
        "Remove the coverage output directory (.gd-tools/coverage, "
        "including the plan cache and baseline.json)."
    ),
)
@click.option(
    "--artifacts",
    is_flag=True,
    help="Remove native test artifacts (.gd-tools/artifacts).",
)
@click.option(
    "--baselines",
    is_flag=True,
    help=(
        "Remove only the saved coverage baseline "
        "(.gd-tools/coverage/baseline.json)."
    ),
)
@click.option(
    "--cache",
    is_flag=True,
    help="Remove the native worker scratch directory (.gd-tools/native).",
)
@click.option(
    "--all",
    "clean_all",
    is_flag=True,
    help="Remove every target directory (overrides individual flags).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Report what would be removed without deleting anything.",
)
def clean(coverage, artifacts, baselines, cache, clean_all, dry_run):
    """Remove generated artifacts under .gd-tools (inventory only with no flags)."""
    try:
        project_root = find_project_root()
    except ConfigError:
        project_root = Path.cwd()
    result = run_clean(
        coverage=coverage,
        artifacts=artifacts,
        baselines=baselines,
        cache=cache,
        all=clean_all,
        dry_run=dry_run,
        project_root=project_root,
    )
    inventory = not (coverage or artifacts or baselines or cache or clean_all)
    _render_clean(result, inventory=inventory, dry_run=dry_run)
    ctx = click.get_current_context()
    ctx.exit(2 if result.failed else 0)


_HOOK_NAMES = ("format", "lint", "test")


def _stdin_is_tty() -> bool:
    """Return True when stdin is an interactive terminal."""
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _render_install_hooks(result: InstallResult) -> None:
    """Render the install-hooks result via the shared output helpers.

    Args:
        result: The :class:`~gd_tools.pre_commit.InstallResult` to render.
    """
    if result.status == STATUS_NOTHING_TO_DO:
        output.print_warning("No hooks selected; nothing to install.")
        return
    for hook in result.hooks:
        if hook.status == STATUS_ADDED:
            output.print_success(f"Added {hook.id} ({hook.name}).")
        else:
            output.print_info(f"Updated {hook.id} ({hook.name}).")
    if result.deselected_present:
        names = ", ".join(result.deselected_present)
        output.print_warning(
            f"Present but not selected: {names} (left in "
            ".pre-commit-config.yaml; remove manually if unwanted)."
        )
    output.print_success(f"Wrote {result.hooks_file.name}")
    output.print_success(f"Merged {result.config_file.name}")


@cli.command("install-hooks")
@click.option(
    "--all",
    "install_all",
    is_flag=True,
    help="Enable every hook (format, lint, and test).",
)
@click.option(
    "--hooks",
    default=None,
    is_flag=False,
    flag_value="",
    metavar="HOOKS",
    help="Comma-separated hook selection, e.g. --hooks format,lint. "
    "An empty selection does nothing (exit 1).",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Never prompt; install the default pair (format and lint) "
    "unless overridden with --all or --hooks.",
)
def install_hooks(install_all, hooks, non_interactive):
    """Install pre-commit hooks for gd-tools in the current project.

    Generates .pre-commit-hooks.yaml and merges gd-tools hook entries
    into .pre-commit-config.yaml. Existing hooks and foreign entries
    are preserved; re-runs update gd-tools entries in place.
    """
    if install_all:
        selection: tuple[str, ...] = _HOOK_NAMES
    elif hooks is not None:
        names = tuple(
            dict.fromkeys(h.strip() for h in hooks.split(",") if h.strip())
        )
        for name in names:
            if name not in _HOOK_NAMES:
                raise click.BadParameter(
                    f"unknown hook {name!r}; choose from "
                    f"{', '.join(_HOOK_NAMES)}."
                )
        selection = names
    elif non_interactive or not _stdin_is_tty():
        selection = ("format", "lint")
    else:
        defaults = (True, True, False)
        selection = tuple(
            name
            for name, default in zip(_HOOK_NAMES, defaults)
            if click.confirm(f"Install the {name} hook?", default=default)
        )
    try:
        project_root = find_project_root()
    except ConfigError:
        project_root = Path.cwd()
    try:
        result = run_install_hooks(
            selection=selection, project_root=project_root
        )
    except GdToolsError as e:
        output.print_error(str(e))
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)
    _render_install_hooks(result)
    ctx = click.get_current_context()
    ctx.exit(0 if result.status != STATUS_NOTHING_TO_DO else 1)


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
@click.option("--coverage", is_flag=True, help="Generate coverage report.")
@click.option("--min", type=int, help="Minimum coverage threshold.")
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
def test(
    paths,
    runtime,
    parallel,
    coverage,
    min,
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
):
    """Run GDScript tests with the native runtime.

    The GUT compatibility bridge was removed in v0.6.0; ``--runtime gut``
    and ``test.runtime = "gut"`` are rejected (see docs/gut-migration.md).
    """
    if runtime == "gut":
        _reject_legacy_runtime("--runtime gut")
    if base is not None and not changed:
        click.echo(
            "Error: --base requires --changed.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)
    if changed and watch:
        click.echo(
            "Error: --changed and --watch cannot be combined; --watch "
            "already selects suites per change.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    if min is not None and not coverage:
        console = Console()
        console.print(
            "[yellow]Warning: --min is only valid with --coverage; "
            "ignoring.[/yellow]"
        )

    if show_uncovered and not coverage:
        console = Console()
        console.print(
            "[yellow]Warning: --show-uncovered is only valid with "
            "--coverage; ignoring.[/yellow]"
        )

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

    if watch and os.environ.get("CI", "").lower() == "true":
        click.echo(
            "Error: --watch is interactive and cannot run with CI=true.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)
    if watch and paths:
        click.echo(
            "Error: --watch does not accept path arguments; it watches the "
            "whole project scope.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)

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
                )
            )
        if selected_runtime == "native":
            run_native_test_command(
                config,
                coverage=coverage,
                min_percent=min,
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
                changed=changed,
                base=base,
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


@cli.command()
@click.argument(
    "path",
    required=False,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply the proposed rewrites and config translation.",
)
@click.option(
    "--config-only",
    is_flag=True,
    help="Only translate .gutconfig.json into gd-tools.toml; never "
    "rewrite suites.",
)
def migrate(path, apply, config_only):
    """Migrate GUT suites to the native runtime.

    Without flags, prints a read-only migration report with proposed
    rewrites (exit 1 when items are found, nothing is written). See
    docs/gut-migration.md.
    """
    ctx = click.get_current_context()
    project_root = Path(path) if path is not None else find_project_root()
    try:
        config = load_config(project_root)
        suites = discover_native_suites(
            project_root,
            list(config.test.test_dirs),
            timeout_seconds=config.test.timeout_seconds,
            retries=config.test.retries,
            allow_legacy=True,
        )
        report = build_migration_report(project_root, suites)
    except (ConfigError, MigrationScanError) as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(2)

    options: dict[str, object] = {}
    translation = None
    if report.gutconfig_path is not None:
        gutconfig_file = project_root / ".gutconfig.json"
        try:
            parsed = json.loads(gutconfig_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            click.echo(f"Error: Cannot read .gutconfig.json: {e}", err=True)
            ctx.exit(2)
        if not isinstance(parsed, dict):
            click.echo(
                "Error: .gutconfig.json must contain a JSON object.",
                err=True,
            )
            ctx.exit(2)
        options = parsed
        translation = translate_gutconfig(options)

    findings = bool(report.suites) or report.gutconfig_path is not None
    if not findings:
        output.print_success(
            "Nothing to migrate: no GUT suites and no .gutconfig.json found."
        )
        ctx.exit(0)
        return

    diffs: dict[str, str] = {}
    if not config_only:
        try:
            plans = plan_rewrites(project_root, report)
        except MigrationScanError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(2)
        diffs = {
            suite_path: generate_diff(suite_path, old, new)
            for suite_path, (_file_path, old, new) in plans.items()
        }

    output.console.print(
        render_migration_report(report, translation, diffs or None)
    )

    if not apply and not config_only:
        ctx.exit(1)
        return

    if report.gutconfig_path is None and config_only:
        click.echo("No .gutconfig.json found; nothing to translate.")

    try:
        result = apply_migration(
            project_root, report, options, config_only=config_only
        )
    except MigrationScanError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(2)

    if result.rewritten:
        output.print_success(
            f"Renamed base class in {len(result.rewritten)} suite(s)."
        )
    dirty_count = sum(1 for suite in report.suites if not suite.is_clean)
    if dirty_count:
        output.print_warning(
            f"{dirty_count} suite(s) still need manual migration; "
            "see the report above."
        )
    if result.config_updated:
        output.print_success("Updated gd-tools.toml with translated settings.")
    if result.skipped:
        for gut_key, target in result.skipped:
            output.print_warning(
                f"Kept existing {target}; .gutconfig.json '{gut_key}' "
                "was not applied (merge, never clobber)."
            )
    for flag, value in result.cli_flags:
        output.print_info(f"Suggested flag: {flag} {value}")

    ctx.exit(0)


@cli.command()
@click.argument("paths", nargs=-1)
@click.option(
    "--report-format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for the lint report.",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to fix lint issues (no-op for gdlint).",
)
def lint(paths, report_format, fix):
    """Lint GDScript files."""
    if fix:
        click.echo(
            "Warning: gdlint is read-only; --fix has no effect.", err=True
        )

    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    result = run_lint(config, list(paths), report_format)

    if report_format == "json":
        click.echo(format_lint_json(result))
    else:
        format_lint_text(result)

    ctx = click.get_current_context()
    if result.errors:
        ctx.exit(1)
    ctx.exit(0)


@cli.command()
@click.argument("paths", nargs=-1)
@click.option("--check", is_flag=True, help="Check only, don't modify files.")
@click.option("--diff", is_flag=True, help="Show diff of changes.")
def format(paths, check, diff):
    """Format GDScript files."""
    if check and diff:
        click.echo("Error: --check and --diff are mutually exclusive", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    result = run_format(config, list(paths), check=check, diff=diff)

    ctx = click.get_current_context()
    if result.files_checked == 0:
        output.print_info("No .gd files found.")
        ctx.exit(0)

    if check:
        if result.files_needing_format > 0:
            for file_path in result.files_needing_format_paths:
                output.console.print(f"[dim]{file_path}[/dim]")
            output.print_summary(
                "fail",
                f"{result.files_needing_format} file(s) need formatting",
                result.files_checked,
            )
            ctx.exit(1)
        else:
            output.print_success(
                f"All {result.files_checked} file(s) are formatted."
            )
            ctx.exit(0)
    elif diff:
        if result.diffs:
            for diff_str in result.diffs:
                syntax = Syntax(diff_str, "diff", theme="ansi_dark")
                output.console.print(syntax)
        else:
            output.print_success(
                f"All {result.files_checked} file(s) already formatted."
            )
        ctx.exit(0)
    else:
        if result.files_formatted > 0:
            output.print_summary(
                "pass",
                f"Formatted {result.files_formatted} of "
                f"{result.files_checked} file(s)",
                result.files_checked,
            )
        else:
            output.print_success(
                f"All {result.files_checked} file(s) already formatted."
            )
        ctx.exit(0)


@cli.group()
def coverage():
    """Coverage reporting commands."""


@coverage.command()
@click.option("--format", help="Output format for the report.")
@click.option("--output-dir", help="Directory to write the report to.")
def report(format, output_dir):
    """Generate a coverage report."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        result = generate_coverage_report(
            config, report_format=format, output_dir=output_dir
        )
        click.echo(f"Report written to: {result.output_path}")
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)


@coverage.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--output", help="Path for the merged output file.")
def merge(files, output):
    """Merge multiple coverage files."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        merge_coverage_files(
            [Path(f) for f in files],
            Path(output) if output else None,
            config=config,
        )
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)


@coverage.command()
@click.option("--min", type=int, help="Minimum coverage threshold.")
def show(min):
    """Show coverage summary."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        show_coverage_summary(config, min_percent=min)
    except CoverageThresholdError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)


@coverage.command(name="save-baseline")
def save_baseline_cmd():
    """Save the latest coverage run as the diff baseline."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        baseline_path = save_coverage_baseline(config)
        click.echo(f"Baseline saved to: {baseline_path}")
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)


@coverage.command(name="diff")
@click.option(
    "--base",
    required=True,
    help="Path to the baseline file written by 'coverage save-baseline'.",
)
@click.option(
    "--show-lines",
    is_flag=True,
    default=False,
    help="List newly-uncovered line numbers for regressed files.",
)
@click.option(
    "--report-format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (default: text).",
)
@click.option(
    "--fail-on-regression",
    is_flag=True,
    default=False,
    help="Exit 1 when any file has lower coverage than the baseline.",
)
def diff_cmd(base, show_lines, report_format, fail_on_regression):
    """Compare current coverage against a baseline."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        diff_coverage(
            config,
            base,
            show_lines=show_lines,
            report_format=report_format.lower(),
            fail_on_regression=fail_on_regression,
        )
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)


@coverage.command()
@click.option(
    "--scene",
    help="Scene to launch for the playtest session "
    "(default: the project's main scene).",
)
@click.option(
    "--timeout",
    type=int,
    help="Automatically close the game after N seconds.",
)
@click.option(
    "--min",
    "min_percent",
    type=int,
    help="Exit 1 when line coverage falls below this percentage.",
)
@click.option(
    "--report-format",
    type=click.Choice(["text", "html", "lcov", "cobertura", "json"]),
    help="Report format (default: the configured coverage format).",
)
def run(scene, timeout, min_percent, report_format):
    """Collect coverage during a manual playtest session."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        result = run_playtest_coverage(
            config,
            scene=scene,
            timeout=timeout,
            min_percent=min_percent,
            report_format=report_format,
        )
        click.echo(f"Report written to: {result.output_path}")
    except CoverageThresholdError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)
    except CoveragePlaytestError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)


@cli.group()
def config():
    """Configuration management commands."""


@config.command(name="show")
@click.option(
    "--format",
    type=click.Choice(["toml"]),
    default=None,
    help="Output format (currently only 'toml').",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
def config_show(format, as_json):
    """Show the resolved configuration.

    By default, prints a Rich table of all configuration sections.
    Use ``--format toml`` for TOML output or ``--json`` for JSON
    output. These two options are mutually exclusive.
    """
    if format is not None and as_json:
        click.echo(
            "Error: --format and --json are mutually exclusive.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        resolved_config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    if as_json:
        click.echo(format_config_json(resolved_config))
    elif format == "toml":
        click.echo(format_config_toml(resolved_config))
    else:
        console = Console()
        console.print(format_config_table(resolved_config))

    ctx = click.get_current_context()
    ctx.exit(0)


def _remove_deprecated_keys(
    data: dict,
    deprecated_paths: set[str],
) -> dict:
    """Remove deprecated keys from a deep copy of the data dict.

    Args:
        data: The original dict (e.g. raw parsed TOML).
        deprecated_paths: Set of dotted paths to remove
            (e.g. ``{"coverage.old_field"}``).

    Returns:
        A new dict with deprecated keys removed.  If
        ``deprecated_paths`` is empty, the original dict is
        returned unchanged.
    """
    if not deprecated_paths:
        return data
    result = copy.deepcopy(data)
    for path in deprecated_paths:
        parts = path.split(".")
        current: dict | None = result
        for part in parts[:-1]:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                current = None
                break
        if isinstance(current, dict) and parts[-1] in current:
            del current[parts[-1]]
    return result


def _get_valid_keys_for_section(section: str) -> list[str] | None:
    """Get valid field names for a config section.

    If *section* is a known top-level section (e.g. ``test``),
    returns its valid field names.  If the section itself is
    unknown, returns the valid top-level section names so the user
    can see what sections exist.

    Args:
        section: The top-level section name extracted from a
            Pydantic error ``loc``.

    Returns:
        List of valid field or section names, or ``None`` if no
        suggestion is available.
    """
    section_fields = GdToolsConfig.model_fields
    if section not in section_fields:
        return list(section_fields.keys())
    field_info = section_fields[section]
    nested_model = field_info.annotation
    if nested_model is not None and hasattr(nested_model, "model_fields"):
        return list(nested_model.model_fields.keys())  # type: ignore[arg-type]
    return None


@config.command()
def validate():
    """Validate the configuration file.

    Checks for schema errors (invalid keys, bad values), deprecated
    settings, and path issues.  Schema errors and deprecated settings
    cause a non-zero exit; path warnings are advisory only.
    """
    try:
        project_root = find_project_root()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    config_file = project_root / "gd-tools.toml"

    schema_errors: list[str] = []
    path_warnings: list[str] = []

    # --- No config file: validate defaults ---
    if not config_file.is_file():
        config = GdToolsConfig()
        path_warnings = validate_paths(config, project_root)
        if path_warnings:
            click.echo("Path Warnings:")
            for w in path_warnings:
                click.echo(f"  ! {w}")
        click.echo("No gd-tools.toml found. Using default configuration.")
        click.echo("✓ Configuration is valid (using defaults).")
        ctx = click.get_current_context()
        ctx.exit(0)

    # --- Read raw TOML ---
    try:
        with open(config_file, "rb") as f:
            raw_toml = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        click.echo(f"Schema Error: Invalid TOML syntax: {exc}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)

    # --- Removed GUT runtime (hard error, checked before Pydantic) ---
    test_section = raw_toml.get("test")
    if isinstance(test_section, dict) and test_section.get("runtime") == "gut":
        click.echo(
            'Schema Error: test.runtime = "gut": GUT runtime support was '
            "removed in v0.6.0. The native runtime is the default. Run "
            "`gd-tools migrate` or see docs/gut-migration.md.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)

    # --- Deprecated settings (checked before Pydantic) ---
    deprecated = check_deprecated_settings(raw_toml)
    deprecated_paths = {dep.field_path for dep in deprecated}

    # Remove deprecated keys so they don't trigger extra-forbidden errors
    clean_toml = _remove_deprecated_keys(raw_toml, deprecated_paths)

    # --- Schema validation via Pydantic ---
    config: GdToolsConfig | None = None
    try:
        config = GdToolsConfig(**clean_toml)
    except ValidationError as exc:
        for error in exc.errors():
            loc = ".".join(str(p) for p in error["loc"])
            msg = error["msg"]
            if "Extra inputs are not permitted" in msg:
                parts = loc.split(".")
                section = parts[0] if parts else ""
                valid = _get_valid_keys_for_section(section)
                hint = f" — valid keys: {', '.join(valid)}" if valid else ""
                schema_errors.append(
                    f"Unknown key '{loc}': not a recognized "
                    f"configuration field{hint}"
                )
            else:
                schema_errors.append(f"{loc}: {msg}")

    # --- Path validation (only if schema is valid) ---
    if config is not None:
        path_warnings = validate_paths(config, project_root)

    # --- Print grouped findings ---
    if schema_errors:
        click.echo("Schema Errors:")
        for err in schema_errors:
            click.echo(f"  ✗ {err}")

    if deprecated:
        click.echo("Deprecated Settings:")
        for dep in deprecated:
            click.echo(
                f"  ✗ {dep.field_path}: deprecated since "
                f"v{dep.since_version}"
            )
            if dep.replacement:
                click.echo(f"    Use '{dep.replacement}' instead")
            click.echo(f"    {dep.migration_message}")

    if path_warnings:
        click.echo("Path Warnings:")
        for w in path_warnings:
            click.echo(f"  ! {w}")

    # --- Summary ---
    click.echo(f"Configuration file: {config_file}")
    click.echo("Sections validated: 5 (godot, test, lint, format, coverage)")
    has_errors = bool(schema_errors or deprecated)
    if has_errors or path_warnings:
        click.echo(
            f"Found: {len(schema_errors)} schema error(s), "
            f"{len(deprecated)} deprecated setting(s), "
            f"{len(path_warnings)} path warning(s)"
        )
    if not has_errors:
        click.echo("✓ Configuration is valid.")
        if path_warnings:
            click.echo(f"  ({len(path_warnings)} path warning(s))")

    ctx = click.get_current_context()
    ctx.exit(1 if has_errors else 0)


@config.command(name="schema")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write the schema to this file (parent directories are "
    "created) instead of printing to stdout.",
)
def config_schema(output: Path | None) -> None:
    """Print the JSON Schema for gd-tools.toml.

    Generates the schema from the installed gd-tools version's
    configuration model (JSON Schema draft 2020-12). Point editors
    at the output (or the checked-in ``docs/gd-tools.schema.json``)
    via the ``$schema`` key in ``gd-tools.toml`` or editor-side
    TOML association to get autocomplete and inline validation.
    """
    ctx = click.get_current_context()
    if output is not None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(generate_schema_text(), encoding="utf-8")
        except OSError as e:
            click.echo(f"Error: cannot write schema file: {e}", err=True)
            ctx.exit(2)
        click.echo(f"Schema written to {output}")
    else:
        click.echo(generate_schema_text())
    ctx.exit(0)


@cli.command()
@click.argument(
    "shell",
    type=click.Choice(["bash", "zsh", "fish", "powershell"]),
)
def completion(shell: str) -> None:
    """Generate shell completion scripts for gd-tools.

    Outputs the completion script for the specified shell to stdout.
    Source the script in your shell's configuration file to enable
    tab completion for gd-tools commands and options.

    \b
    Supported shells:
      bash       Generate bash completion script
      zsh        Generate zsh completion script
      fish       Generate fish completion script
      powershell Generate PowerShell completion script

    \b
    Examples:
      eval "$(gd-tools completion bash)"
      gd-tools completion zsh > ~/.zsh/completions/_gd-tools
      gd-tools completion fish > ~/.config/fish/completions/gd-tools.fish
      gd-tools completion powershell | Out-String | Add-Content $PROFILE
    """
    comp_class = get_completion_class(shell)
    if comp_class is None:  # pragma: no cover
        raise click.UsageError(f"Unsupported shell: {shell}")
    prog_name = "gd-tools"
    complete_var = f"_{prog_name.upper().replace('-', '_')}_COMPLETE"
    comp = comp_class(
        cli=cli,
        ctx_args={},
        prog_name=prog_name,
        complete_var=complete_var,
    )
    click.echo(comp.source())
