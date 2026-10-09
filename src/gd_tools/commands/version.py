"""The ``version`` command."""

import json

import click
from rich.console import Console
from rich.table import Table

from ..version import collect_versions


@click.command()
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
