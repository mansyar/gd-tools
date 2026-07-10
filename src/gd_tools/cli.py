"""CLI entry point for gd-tools."""

from typing import Any

import click
from rich.console import Console
from rich.syntax import Syntax

from . import __version__
from .config import load_config
from .errors import ConfigError
from .format_runner import run_format
from .lint_runner import format_lint_json, format_lint_text, run_lint


class GdToolsGroup(click.Group):
    """Custom Click group that converts NotImplementedError to exit code 2.

    Stub commands raise ``NotImplementedError`` to indicate they are not
    yet implemented. This class catches that exception and exits with
    code 2 (configuration/usage error), consistent with the gd-tools
    error convention.
    """

    def invoke(self, ctx) -> Any:
        """Invoke the group, catching NotImplementedError as exit code 2.

        Args:
            ctx: The Click context for this invocation.

        Returns:
            The result of the underlying command invocation.

        Raises:
            SystemExit: With code 2 if a command raises
                NotImplementedError.
        """
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
    raise NotImplementedError


@cli.command()
def doctor():
    """Check the environment for required tools."""
    raise NotImplementedError


@cli.command()
@click.option("--coverage", is_flag=True, help="Generate coverage report.")
@click.option("--min", type=float, help="Minimum coverage threshold.")
@click.option("--suite", help="Specify which test suite to run.")
@click.option("--test", help="Specify which test to run.")
@click.option("--junit-xml", help="Path to write JUnit XML report.")
@click.option(
    "--no-exit-code",
    is_flag=True,
    help="Don't exit with non-zero on test failure.",
)
def test(coverage, min, suite, test, junit_xml, no_exit_code):
    """Run GDScript tests using GUT."""
    raise NotImplementedError


@cli.command()
@click.argument("path", required=False, default=".")
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
def lint(path, report_format, fix):
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

    result = run_lint(config, path, report_format)

    if report_format == "json":
        output = format_lint_json(result)
    else:
        output = format_lint_text(result)

    click.echo(output)

    ctx = click.get_current_context()
    if result.errors:
        ctx.exit(1)
    ctx.exit(0)


@cli.command()
@click.argument("path", required=False, default=".")
@click.option("--check", is_flag=True, help="Check only, don't modify files.")
@click.option("--diff", is_flag=True, help="Show diff of changes.")
def format(path, check, diff):
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

    result = run_format(config, path, check=check, diff=diff)

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
    raise NotImplementedError


@coverage.command()
@click.argument("files", nargs=-1)
@click.option("--output", help="Path for the merged output file.")
def merge(files, output):
    """Merge multiple coverage files."""
    raise NotImplementedError


@coverage.command()
@click.option("--min", type=float, help="Minimum coverage threshold.")
def show(min):
    """Show coverage summary."""
    raise NotImplementedError
