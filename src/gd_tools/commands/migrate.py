"""The ``migrate`` command."""

import json
from pathlib import Path

import click

from .. import output
from ..config import ConfigError, find_project_root, load_config
from ..migration.apply import apply_migration, plan_rewrites
from ..migration.gutconfig import translate_gutconfig
from ..migration.reporter import render_migration_report
from ..migration.rewrite import generate_diff
from ..migration.scan import MigrationScanError, build_migration_report
from ..native_test.discovery import discover_native_suites


@click.command()
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
