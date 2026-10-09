"""The ``install-hooks`` command."""

import sys
from pathlib import Path

import click

from .. import output
from ..config import ConfigError, find_project_root
from ..errors import GdToolsError
from ..pre_commit import (
    STATUS_ADDED,
    STATUS_NOTHING_TO_DO,
    InstallResult,
    install_hooks as run_install_hooks,
)

_HOOK_NAMES = ("format", "lint", "test")


def _stdin_is_tty() -> bool:
    """Return True when stdin is an interactive terminal."""
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _render_install_hooks(result: InstallResult) -> None:
    """Render the install-hooks result via the shared output helpers.

    Args:
        result: The :class:`~gd_tools.pre_commit.InstallResult` to render.
    """
    if result.status == STATUS_NOTHING_TO_DO:
        output.print_warning("No hooks selected; nothing to install.")
        return
    for hook in result.hooks:
        if hook.status == STATUS_ADDED:
            output.print_success(f"Added {hook.id} ({hook.name}).")
        else:
            output.print_info(f"Updated {hook.id} ({hook.name}).")
    if result.deselected_present:
        names = ", ".join(result.deselected_present)
        output.print_warning(
            f"Present but not selected: {names} (left in "
            ".pre-commit-config.yaml; remove manually if unwanted)."
        )
    output.print_success(f"Wrote {result.hooks_file.name}")
    output.print_success(f"Merged {result.config_file.name}")


@click.command("install-hooks")
@click.option(
    "--all",
    "install_all",
    is_flag=True,
    help="Enable every hook (format, lint, and test).",
)
@click.option(
    "--hooks",
    default=None,
    is_flag=False,
    flag_value="",
    metavar="HOOKS",
    help="Comma-separated hook selection, e.g. --hooks format,lint. "
    "An empty selection does nothing (exit 1).",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Never prompt; install the default pair (format and lint) "
    "unless overridden with --all or --hooks.",
)
def install_hooks(install_all, hooks, non_interactive):
    """Install pre-commit hooks for gd-tools in the current project.

    Generates .pre-commit-hooks.yaml and merges gd-tools hook entries
    into .pre-commit-config.yaml. Existing hooks and foreign entries
    are preserved; re-runs update gd-tools entries in place.
    """
    if install_all:
        selection: tuple[str, ...] = _HOOK_NAMES
    elif hooks is not None:
        names = tuple(
            dict.fromkeys(h.strip() for h in hooks.split(",") if h.strip())
        )
        for name in names:
            if name not in _HOOK_NAMES:
                raise click.BadParameter(
                    f"unknown hook {name!r}; choose from "
                    f"{', '.join(_HOOK_NAMES)}."
                )
        selection = names
    elif non_interactive or not _stdin_is_tty():
        selection = ("format", "lint")
    else:
        defaults = (True, True, False)
        selection = tuple(
            name
            for name, default in zip(_HOOK_NAMES, defaults)
            if click.confirm(f"Install the {name} hook?", default=default)
        )
    try:
        project_root = find_project_root()
    except ConfigError:
        project_root = Path.cwd()
    try:
        result = run_install_hooks(
            selection=selection, project_root=project_root
        )
    except GdToolsError as e:
        output.print_error(str(e))
        ctx = click.get_current_context()
        ctx.exit(e.exit_code)
    _render_install_hooks(result)
    ctx = click.get_current_context()
    ctx.exit(0 if result.status != STATUS_NOTHING_TO_DO else 1)
