"""CLI entry point for gd-tools."""

import click

from . import __version__


class GdToolsGroup(click.Group):
    """Custom Click group that converts NotImplementedError to exit code 2.

    Stub commands raise ``NotImplementedError`` to indicate they are not
    yet implemented. This class catches that exception and exits with
    code 2 (configuration/usage error), consistent with the gd-tools
    error convention.
    """

    def invoke(self, ctx):
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
@click.argument("path")
@click.option(
    "--report-format",
    help="Output format for the lint report.",
)
def lint(path, report_format):
    """Lint GDScript files."""
    raise NotImplementedError


@cli.command()
@click.argument("path")
@click.option("--check", is_flag=True, help="Check only, don't modify files.")
@click.option("--diff", is_flag=True, help="Show diff of changes.")
def format(path, check, diff):
    """Format GDScript files."""
    raise NotImplementedError


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
