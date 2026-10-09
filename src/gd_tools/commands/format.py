"""The ``format`` command."""

import click
from rich.syntax import Syntax

from .. import output
from ..config import ConfigError, load_config
from ..format_runner import run_format


@click.command()
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
