"""The ``lint`` command."""

import click

from ..config import ConfigError, load_config
from ..lint_runner import (
    format_lint_github_actions,
    format_lint_json,
    format_lint_text,
    run_lint,
)


@click.command()
@click.argument("paths", nargs=-1)
@click.option(
    "--report-format",
    type=click.Choice(["text", "json", "github-actions"]),
    default="text",
    help="Output format for the lint report.",
)
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to fix lint issues (no-op for gdlint).",
)
@click.option(
    "--lint-config",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help=(
        "Path to a gdlint config file (gdlintrc). Defaults to the "
        "project's gdlintrc discovered like bare gdlint does."
    ),
)
def lint(paths, report_format, fix, lint_config):
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

    result = run_lint(
        config, list(paths), report_format, lint_config_path=lint_config
    )

    if report_format == "json":
        click.echo(format_lint_json(result))
    elif report_format == "github-actions":
        click.echo(format_lint_github_actions(result), nl=False)
    else:
        format_lint_text(result)

    ctx = click.get_current_context()
    if result.errors:
        ctx.exit(1)
    ctx.exit(0)
