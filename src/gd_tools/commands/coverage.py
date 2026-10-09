"""The ``coverage`` command group (report, merge, show, save-baseline, diff, run)."""

import sys
import webbrowser
from pathlib import Path

import click

from ..config import ConfigError, load_config
from ..coverage.orchestrator import (
    diff_coverage,
    diff_coverage_patch,
    generate_coverage_report,
    merge_coverage_files,
    save_coverage_baseline,
    show_coverage_summary,
)
from ..coverage.playtest import run_playtest_coverage
from ..errors import (
    CoveragePlaytestError,
    CoverageThresholdError,
    GdToolsError,
)


def _is_interactive() -> bool:
    """Return True when stdout is attached to an interactive terminal.

    Returns:
        ``True`` when ``sys.stdout`` reports a TTY.
    """
    return sys.stdout.isatty()


@click.group()
def coverage():
    """Coverage reporting commands."""


_COVERAGE_REPORT_FORMATS = [
    "text",
    "html",
    "lcov",
    "cobertura",
    "json",
    "github-actions",
]


@coverage.command()
@click.option(
    "--report-format",
    type=click.Choice(
        _COVERAGE_REPORT_FORMATS,
        case_sensitive=False,
    ),
    default=None,
    help="Output format for the report (default: the configured "
    "coverage format).",
)
@click.option(
    "--format",
    "format_alias",
    type=click.Choice(
        _COVERAGE_REPORT_FORMATS,
        case_sensitive=False,
    ),
    default=None,
    hidden=True,
    help="Deprecated alias for --report-format.",
)
@click.option(
    "--html-open",
    is_flag=True,
    default=False,
    help="Open the generated HTML report in the default browser "
    "(only with the html format; suppressed when not attached to "
    "a terminal, e.g. in CI).",
)
@click.option("--output-dir", help="Directory to write the report to.")
def report(report_format, format_alias, output_dir, html_open):
    """Generate a coverage report."""
    if report_format is not None and format_alias is not None:
        raise click.UsageError(
            "Cannot use both --report-format and --format. "
            "--format is a deprecated alias; use --report-format."
        )
    format = report_format if report_format is not None else format_alias
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        result = generate_coverage_report(
            config,
            report_format=format,
            output_dir=output_dir,
            annotate_min_percent=(
                config.coverage.min_percent
                if config.coverage.min_percent > 0
                else None
            ),
        )
        effective = format if format is not None else config.coverage.format
        if effective == "github-actions":
            annotations = Path(result.output_path).read_text(encoding="utf-8")
            click.echo(annotations, nl=False)
        click.echo(f"Report written to: {result.output_path}")
        if html_open and effective == "html" and _is_interactive():
            try:
                webbrowser.open(str(result.output_path))
            except (OSError, webbrowser.Error) as e:
                click.echo(f"Warning: could not open browser: {e}", err=True)
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
@click.option(
    "--min-branch",
    type=int,
    help="Minimum branch coverage threshold.",
)
def show(min, min_branch):
    """Show coverage summary."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        show_coverage_summary(
            config, min_percent=min, min_branch_percent=min_branch
        )
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
    help="Baseline file path, or a git ref when --patch is set.",
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
@click.option(
    "--patch",
    is_flag=True,
    default=False,
    help=(
        "Patch-coverage mode: report coverage for only the executable "
        "lines changed relative to the --base git ref (merge-base "
        "contract, same as 'test --changed --base')."
    ),
)
@click.option(
    "--patch-fail-under",
    type=click.FloatRange(0, 100),
    default=None,
    help=(
        "Minimum patch coverage percentage (0-100). Exit 1 below it. "
        "Requires --patch."
    ),
)
@click.option(
    "--patch-annotations",
    type=click.Choice(["true", "false"], case_sensitive=False),
    default=None,
    help=(
        "Emit GitHub Actions annotations for uncovered changed lines. "
        "Defaults to auto-detection via GITHUB_ACTIONS=true. "
        "Requires --patch."
    ),
)
def diff_cmd(
    base,
    show_lines,
    report_format,
    fail_on_regression,
    patch,
    patch_fail_under,
    patch_annotations,
):
    """Compare current coverage against a baseline (--patch: vs a base ref)."""
    if patch_fail_under is not None and not patch:
        click.echo("Error: --patch-fail-under requires --patch.", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)
    if patch_annotations is not None and not patch:
        click.echo("Error: --patch-annotations requires --patch.", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)
    if patch and show_lines:
        click.echo(
            "Error: --show-lines is not compatible with --patch.", err=True
        )
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        if patch:
            diff_coverage_patch(
                config,
                base,
                report_format=report_format.lower(),
                fail_under=patch_fail_under,
                annotations=(
                    patch_annotations.lower() == "true"
                    if patch_annotations is not None
                    else None
                ),
                fail_on_regression=fail_on_regression,
            )
        else:
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
    "--min-branch",
    "min_branch_percent",
    type=int,
    help="Exit 1 when branch coverage falls below this percentage.",
)
@click.option(
    "--report-format",
    type=click.Choice(
        ["text", "html", "lcov", "cobertura", "json", "github-actions"]
    ),
    help="Report format (default: the configured coverage format).",
)
def run(scene, timeout, min_percent, min_branch_percent, report_format):
    """Collect coverage during a manual playtest session."""
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    fmt = report_format if report_format is not None else config.coverage.format
    try:
        result = run_playtest_coverage(
            config,
            scene=scene,
            timeout=timeout,
            min_percent=min_percent,
            min_branch_percent=min_branch_percent,
            report_format=fmt,
        )
        if fmt == "github-actions":
            annotations = Path(result.output_path).read_text(encoding="utf-8")
            click.echo(annotations, nl=False)
        click.echo(f"Report written to: {result.output_path}")
    except CoverageThresholdError as e:
        if fmt == "github-actions" and e.report_result is not None:
            annotations = Path(e.report_result.output_path).read_text(
                encoding="utf-8"
            )
            click.echo(annotations, nl=False)
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
