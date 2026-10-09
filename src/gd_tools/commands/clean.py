"""The ``clean`` command."""

from pathlib import Path

import click

from .. import output
from ..clean import (
    STATUS_ABSENT,
    STATUS_FAILED,
    STATUS_NOTHING,
    STATUS_PRESENT,
    STATUS_REMOVED,
    STATUS_SUBSUMED,
    STATUS_WOULD_REMOVE,
    CleanResult,
    run_clean,
)
from ..config import ConfigError, find_project_root


def _humanize_bytes(num_bytes: int) -> str:
    """Format a byte count for display (e.g., ``150 B``, ``4.2 KB``)."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _clean_target_label(name: str) -> str:
    """Return the user-facing path label for a clean target name."""
    labels = {
        "coverage": ".gd-tools/coverage",
        "artifacts": ".gd-tools/artifacts",
        "baselines": ".gd-tools/coverage/baseline.json",
        "cache": ".gd-tools/native",
        "snapshots": ".gd-tools/snapshots",
    }
    return labels.get(name, name)


def _render_clean(result: CleanResult, inventory: bool, dry_run: bool) -> None:
    """Render the outcome of a clean run.

    Args:
        result: The :class:`CleanResult` returned by ``run_clean``.
        inventory: Whether this was a no-flag inventory run.
        dry_run: Whether deletion was suppressed.
    """
    if inventory:
        output.print_info("gd-tools artifacts inventory (.gd-tools/):")
        for entry in result.targets:
            if entry.status == STATUS_PRESENT:
                click.echo(
                    f"  {_clean_target_label(entry.name)}: "
                    f"{_humanize_bytes(entry.freed_bytes)}"
                )
            elif entry.status == STATUS_ABSENT:
                click.echo(
                    f"  {_clean_target_label(entry.name)}: nothing present"
                )
        output.print_info(
            "Hint: run `gd-tools clean --coverage` (or --artifacts, "
            "--baselines, --cache, --snapshots) to remove a target, or "
            "`gd-tools clean "
            "--all` to remove everything. Nothing was deleted."
        )
        return

    for entry in result.targets:
        label = _clean_target_label(entry.name)
        if entry.status == STATUS_REMOVED:
            output.print_success(
                f"removed {label} ({_humanize_bytes(entry.freed_bytes)} freed)"
            )
        elif entry.status == STATUS_WOULD_REMOVE:
            output.print_info(
                f"would remove {label} ({_humanize_bytes(entry.freed_bytes)})"
            )
        elif entry.status == STATUS_NOTHING:
            output.print_verbose(f"nothing to remove at {label}")
            click.echo(f"  {label}: nothing to remove")
        elif entry.status == STATUS_SUBSUMED:
            output.print_verbose(
                f"{label} covered by a broader target selection"
            )
        elif entry.status == STATUS_FAILED:
            click.echo(f"Error: {entry.error}")

    freed = _humanize_bytes(result.freed_bytes)
    if dry_run:
        output.print_summary(
            "warning", f"dry run: {freed} would be freed (nothing deleted)"
        )
    elif result.failed:
        output.print_summary(
            "fail", f"cleaning failed; {freed} freed before failure"
        )
    elif result.freed_bytes:
        output.print_summary("pass", f"{freed} freed")
    else:
        output.print_summary("pass", "nothing to remove")


@click.command()
@click.option(
    "--coverage",
    is_flag=True,
    help=(
        "Remove the coverage output directory (.gd-tools/coverage, "
        "including the plan cache and baseline.json)."
    ),
)
@click.option(
    "--artifacts",
    is_flag=True,
    help="Remove native test artifacts (.gd-tools/artifacts).",
)
@click.option(
    "--baselines",
    is_flag=True,
    help=(
        "Remove only the saved coverage baseline "
        "(.gd-tools/coverage/baseline.json)."
    ),
)
@click.option(
    "--cache",
    is_flag=True,
    help="Remove the native worker scratch directory (.gd-tools/native).",
)
@click.option(
    "--snapshots",
    is_flag=True,
    help="Remove stored test snapshots (.gd-tools/snapshots).",
)
@click.option(
    "--all",
    "clean_all",
    is_flag=True,
    help="Remove every target directory (overrides individual flags).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Report what would be removed without deleting anything.",
)
def clean(coverage, artifacts, baselines, cache, snapshots, clean_all, dry_run):
    """Remove generated artifacts under .gd-tools (inventory only with no flags)."""
    try:
        project_root = find_project_root()
    except ConfigError:
        project_root = Path.cwd()
    result = run_clean(
        coverage=coverage,
        artifacts=artifacts,
        baselines=baselines,
        cache=cache,
        snapshots=snapshots,
        all=clean_all,
        dry_run=dry_run,
        project_root=project_root,
    )
    inventory = not (coverage or artifacts or baselines or cache or clean_all)
    _render_clean(result, inventory=inventory, dry_run=dry_run)
    ctx = click.get_current_context()
    ctx.exit(2 if result.failed else 0)
