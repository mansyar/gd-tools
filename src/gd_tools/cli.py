"""CLI entry point for gd-tools."""

import copy
import json
import sys
from pathlib import Path
from typing import Any

import click
from pydantic import ValidationError
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from . import __version__
from .config import (
    check_deprecated_settings,
    find_project_root,
    format_config_json,
    format_config_table,
    format_config_toml,
    load_config,
    validate_paths,
    GdToolsConfig,
)
from .coverage.orchestrator import (
    generate_coverage_report,
    merge_coverage_files,
    run_coverage_test,
    show_coverage_summary,
)
from .doctor import format_doctor_table, run_doctor
from .errors import (
    ConfigError,
    CoverageThresholdError,
    GdToolsError,
    TestFailureError,
)
from .format_runner import run_format
from .init import run_init
from .lint_runner import format_lint_json, format_lint_text, run_lint
from .test_runner import run_tests
from .update_check import check_for_update
from .addon_check import check_addon_version
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

        Args:
            ctx: The Click context for this invocation.

        Returns:
            The result of the underlying command invocation.

        Raises:
            SystemExit: With code 2 if a command raises
                NotImplementedError.
        """
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
def cli():
    """gd-tools: A modern development workflow CLI for GDScript."""


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


@cli.command()
@click.argument("paths", nargs=-1)
@click.option("--coverage", is_flag=True, help="Generate coverage report.")
@click.option("--min", type=int, help="Minimum coverage threshold.")
@click.option("--suite", help="Specify which test suite to run.")
@click.option("--test", help="Specify which test to run.")
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
def test(paths, coverage, min, suite, test, junit_xml, no_exit_code, timeout):
    """Run GDScript tests using GUT."""
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

    try:
        if coverage:
            run_coverage_test(
                config,
                suite=suite,
                test_name=test,
                junit_xml=junit_xml,
                no_exit_code=no_exit_code,
                min_percent=min,
                timeout=timeout,
                paths=list(paths) if paths else None,
            )
        else:
            run_tests(
                config,
                coverage=coverage,
                min_percent=min,
                suite=suite,
                test_name=test,
                junit_xml=junit_xml,
                no_exit_code=no_exit_code,
                timeout=timeout,
                paths=list(paths) if paths else None,
            )
    except TestFailureError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)

    ctx = click.get_current_context()
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
        click.echo("No .gd files found.")
        ctx.exit(0)

    if check:
        if result.files_needing_format > 0:
            for file_path in result.files_needing_format_paths:
                click.echo(f"  {file_path}")
            click.echo(
                f"\n{result.files_needing_format} file(s) need "
                f"formatting (out of {result.files_checked} checked)."
            )
            ctx.exit(1)
        else:
            click.echo(f"All {result.files_checked} file(s) are formatted.")
            ctx.exit(0)
    elif diff:
        console = Console()
        for diff_str in result.diffs:
            syntax = Syntax(diff_str, "diff", theme="ansi_dark")
            console.print(syntax)
        ctx.exit(0)
    else:
        if result.files_formatted > 0:
            click.echo(
                f"Formatted {result.files_formatted} of "
                f"{result.files_checked} file(s)."
            )
        else:
            click.echo(f"All {result.files_checked} file(s) already formatted.")
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
