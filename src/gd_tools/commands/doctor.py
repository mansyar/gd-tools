"""The ``doctor`` command."""

import click
from rich.console import Console

from .. import output
from ..doctor import format_doctor_table, run_doctor
from ..verbosity import Verbosity, get_verbosity


@click.command()
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
