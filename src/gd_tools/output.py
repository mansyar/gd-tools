"""Shared output module for consistent terminal rendering.

Provides rendering helpers used by all commands for a unified visual
language: success/error/warning/info markers, summary footers, and
table rendering via a shared Console instance.

Color semantics (per product-guidelines.md §2.1):
    Green  = pass / covered / success
    Red    = fail / uncovered / error
    Yellow = warning / partial coverage
    Cyan   = info / headers
    Dim    = secondary info, file paths

Markers (per product-guidelines.md §7, ASCII-only):
    [OK]   — success
    [FAIL] — failure
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .verbosity import Verbosity, get_verbosity

# Shared Console instance — auto-detects terminal capabilities
# (no ANSI codes when stdout is piped).
console = Console()


def print_success(message: str) -> None:
    """Render a success message with [OK] marker in green.

    Args:
        message: The success message to display.
    """
    console.print(Text.assemble(("[OK] ", "green"), (message, "green")))


def print_error(message: str) -> None:
    """Render an error message with [FAIL] marker in red.

    Args:
        message: The error message to display.
    """
    console.print(Text.assemble(("[FAIL] ", "red"), (message, "red")))


def print_warning(message: str) -> None:
    """Render a warning message in yellow.

    Suppressed when verbosity is QUIET.

    Args:
        message: The warning message to display.
    """
    if get_verbosity() == Verbosity.QUIET:
        return
    console.print(Text(message, style="yellow"))


def print_info(message: str) -> None:
    """Render an informational message in cyan.

    Suppressed when verbosity is QUIET.

    Args:
        message: The informational message to display.
    """
    if get_verbosity() == Verbosity.QUIET:
        return
    console.print(Text(message, style="cyan"))


def print_verbose(message: str) -> None:
    """Render a verbose-only message in dim style.

    Only renders when verbosity is VERBOSE; suppressed in DEFAULT and
    QUIET modes.

    Args:
        message: The verbose message to display.
    """
    if get_verbosity() != Verbosity.VERBOSE:
        return
    console.print(Text(message, style="dim"))


def print_summary(
    status: str,
    counts: str,
    files_checked: int = 0,
    extra_info: str | None = None,
) -> None:
    """Render a standardized summary footer line with color coding.

    The summary is composed of the ``counts`` string, optionally
    followed by ``"{files_checked} files checked"`` when
    ``files_checked`` is non-zero, and optionally ``extra_info``.
    Color is determined by ``status``: green for pass, red for
    fail, yellow for warning.

    Args:
        status: Summary status — ``"pass"``, ``"fail"``, or
            ``"warning"``.
        counts: Pre-formatted count string (e.g.,
            ``"3 errors, 2 warnings"``).
        files_checked: Number of files checked. When zero, the
            ``"files checked"`` suffix is omitted.
        extra_info: Optional additional info appended to the
            summary.
    """
    parts: list[str] = [counts]
    if files_checked:
        parts.append(f"{files_checked} files checked")
    if extra_info:
        parts.append(extra_info)
    text = ", ".join(parts)

    color_map = {"pass": "green", "fail": "red", "warning": "yellow"}
    color = color_map.get(status, "white")
    console.print(Text(text, style=color))


def print_table(table: Table) -> None:
    """Render a Rich Table via the shared console.

    Args:
        table: The :class:`rich.table.Table` to render.
    """
    console.print(table)
