"""CLI entry point for gd-tools."""

import sys
from pathlib import Path
from typing import Any

import click
from click.shell_completion import (
    BashComplete,
    add_completion_class,
)

from . import __version__
from .addon_check import check_addon_version
from .commands.clean import clean
from .commands.completion import create_completion_command
from .commands.config import config
from .commands.coverage import coverage
from .commands.doctor import doctor
from .commands.format import format
from .commands.init import init
from .commands.install_hooks import install_hooks
from .commands.lint import lint
from .commands.migrate import migrate
from .commands.test import test
from .commands.version import version
from .config import set_explicit_project_root
from .update_check import check_for_update
from .verbosity import Verbosity, set_verbosity


def _configure_windows_utf8() -> None:
    """Reconfigure stdout/stderr to UTF-8 on Windows.

    Windows defaults to the system codepage (e.g. cp1252) for console
    output, which cannot encode Unicode characters used by Rich (✓, ✗,
    ⚠). This reconfigures the standard streams to UTF-8, matching the
    effect of setting PYTHONUTF8=1.
    """
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


_configure_windows_utf8()


_SOURCE_POWERSHELL = """Register-ArgumentCompleter -Native -CommandName %(prog_name)s -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $words = $commandAst.CommandElements | ForEach-Object { $_.ToString() }
    $env:COMP_WORDS = $words -join ' '
    $commandElements = $commandAst.CommandElements
    $env:COMP_CWORD = $commandElements.Count
    for ($i = 0; $i -lt $commandElements.Count; $i++) {
        if ($cursorPosition -le $commandElements[$i].Extent.StartOffset) {
            $env:COMP_CWORD = $i
            break
        }
    }

    $env:%(complete_var)s = "powershell_complete"
    %(prog_name)s | ForEach-Object {
        $values = $_.Split(",")
        if ($values[0] -eq "dir") {
            [System.Management.Automation.CompletionResult]::new($values[1], $values[1], "ParameterValue", $values[1])
        } elseif ($values[0] -eq "file") {
            [System.Management.Automation.CompletionResult]::new($values[1], $values[1], "ParameterValue", $values[1])
        } else {
            $help = if ($values[2] -eq "_") { "" } else { $values[2] }
            [System.Management.Automation.CompletionResult]::new($values[1], $values[1], "ParameterValue", $help)
        }
    }

    $env:COMP_WORDS = $null
    $env:COMP_CWORD = 0
    $env:%(complete_var)s = $null
}
"""


class PowerShellComplete(BashComplete):
    """Shell completion for PowerShell.

    Click 8.2.x does not include a PowerShell completion class.
    This subclass reuses BashComplete's completion args and
    format_completion, providing a PowerShell-compatible source
    template using Register-ArgumentCompleter.
    """

    name = "powershell"
    source_template = _SOURCE_POWERSHELL


add_completion_class(PowerShellComplete)


class GdToolsGroup(click.Group):
    """Custom Click group that converts NotImplementedError to exit code 2.

    Stub commands raise ``NotImplementedError`` to indicate they are not
    yet implemented. This class catches that exception and exits with
    code 2 (configuration/usage error), consistent with the gd-tools
    error convention.
    """

    def invoke(self, ctx) -> Any:
        """Invoke the group, catching NotImplementedError as exit code 2.

        Performs an update check before dispatching to the subcommand.
        If a newer version is available, a notification is printed to
        stderr. The check fails silently and never blocks execution.

        In quiet mode (``--quiet``/``-q``), both the update check and
        the addon version check are skipped entirely.

        Args:
            ctx: The Click context for this invocation.

        Returns:
            The result of the underlying command invocation.

        Raises:
            SystemExit: With code 2 if a command raises
                NotImplementedError.
        """
        # Use raw ctx.params here — set_verbosity() runs inside the group
        # callback (invoked by super().invoke below), so get_verbosity()
        # is not yet set at this point.
        quiet = ctx.params.get("quiet", False)
        if not quiet:
            latest = check_for_update()
            if latest is not None:
                click.echo(
                    f"A new version of gd-tools is available: {latest} "
                    f"(you have {__version__}).\n"
                    f"Run `pip install --upgrade gd-tools-cli` to update.",
                    err=True,
                )
            check_addon_version()
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
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show verbose output including underlying commands and timing.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Suppress non-essential output (update checks, progress info).",
)
@click.option(
    "--project",
    "-p",
    "project_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to the Godot project root. Defaults to discovery from "
    "the current working directory.",
)
def cli(verbose: bool, quiet: bool, project_path: Path | None):
    """gd-tools: A modern development workflow CLI for GDScript."""
    set_explicit_project_root(project_path)
    if verbose and quiet:
        click.echo(
            "Error: --verbose and --quiet are mutually exclusive.", err=True
        )
        ctx = click.get_current_context()
        ctx.exit(2)
    if verbose:
        set_verbosity(Verbosity.VERBOSE)
    elif quiet:
        set_verbosity(Verbosity.QUIET)
    else:
        set_verbosity(Verbosity.DEFAULT)


# Register the extracted commands, preserving the original help order:
# init, doctor, version, clean, install-hooks, test, migrate, lint,
# format, coverage, config, completion.
cli.add_command(init)
cli.add_command(doctor)
cli.add_command(version)
cli.add_command(clean)
cli.add_command(install_hooks)


cli.add_command(test)
cli.add_command(migrate)
cli.add_command(lint)
cli.add_command(format)
cli.add_command(coverage)
cli.add_command(config)
cli.add_command(create_completion_command(cli))
