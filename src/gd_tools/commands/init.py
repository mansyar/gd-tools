"""The ``init`` command."""

import click

from ..errors import GdToolsError
from ..init import run_init


@click.command()
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
