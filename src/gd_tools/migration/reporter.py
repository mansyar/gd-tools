"""Rich rendering of migration reports for the terminal.

Mirrors the coverage terminal reporter: the report is rendered into a
fixed-width force-terminal console and returned as a string, so callers
can print it through the shared console or tests can assert on it.
"""

from __future__ import annotations

import io
from collections.abc import Mapping

from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.text import Text

from gd_tools.migration.gutconfig import (
    GUTCONFIG_OPTIONS,
    ConfigTranslation,
)
from gd_tools.migration.scan import MigrationReport, SuiteReport

_WIDTH = 100

_DOC_POINTER = (
    "See docs/gut-migration.md for the supported subset and migration steps."
)

_OPTIONS_BY_KEY = {option.key: option for option in GUTCONFIG_OPTIONS}


def _plural(count: int, singular: str, plural: str) -> str:
    """Return ``<count> <singular|plural>``."""
    return f"{count} {singular if count == 1 else plural}"


def _render_suite(console: Console, suite: SuiteReport) -> None:
    """Render one suite's migration status."""
    if suite.is_clean:
        console.print(
            Text(
                f"[OK] {suite.path} ({suite.test_count} tests, "
                "no unsupported constructs)",
                style="green",
            )
        )
        return

    console.print(
        Text(f"[FAIL] {suite.path} ({suite.test_count} tests)", style="red")
    )
    console.print("    Unsupported constructs (the bridge cannot run these):")
    for hit in suite.unsupported:
        console.print(f"      line {hit.line}: {hit.name}")
    if suite.aliases:
        console.print("    Bridge-only aliases (works now, rename later):")
        for hit in suite.aliases:
            console.print(f"      line {hit.line}: {hit.name}")
    console.print()


def _render_config(
    console: Console,
    gutconfig_path: str,
    translation: ConfigTranslation,
) -> None:
    """Render the .gutconfig.json classification section."""
    console.print(f".gutconfig.json ({gutconfig_path}):")
    for key, target in translation.mapped:
        option = _OPTIONS_BY_KEY[key]
        console.print(f"  [translate] {key} -> {target} - {option.note}")
    for key in translation.noop:
        console.print(f"  [no-op] {key} (handled automatically)")
    for key in translation.dropped:
        option = _OPTIONS_BY_KEY[key]
        console.print(
            f"  [drop] {key} (no equivalent, file preserved) - {option.note}"
        )
    for key in translation.unknown:
        console.print(f"  [unknown] {key} (not in the migration inventory)")
    console.print()


def render_migration_report(
    report: MigrationReport,
    translation: ConfigTranslation | None = None,
    diffs: Mapping[str, str] | None = None,
) -> str:
    """Render the migration report as an ANSI-colored terminal string.

    Args:
        report: The migration report model produced by the scanner.
        translation: Optional ``.gutconfig.json`` classification; rendered
            when the report records a gutconfig file.
        diffs: Optional ``res://`` path to unified-diff mapping for clean
            suites whose base class can be renamed under ``--apply``.

    Returns:
        The formatted report string with ANSI color codes.
    """
    buf = io.StringIO()
    console = Console(
        file=buf,
        force_terminal=True,
        width=_WIDTH,
        highlighter=NullHighlighter(),
    )

    console.print(Text("Migration Report", style="cyan"))
    console.print()

    if not report.suites:
        console.print("No GUT suites found")
    else:
        for suite in report.suites:
            _render_suite(console, suite)

        dirty_count = sum(1 for suite in report.suites if not suite.is_clean)
        clean_count = len(report.suites) - dirty_count
        console.print(
            f"Summary: "
            f"{_plural(dirty_count, 'suite needs', 'suites need')} migration, "
            f"{_plural(clean_count, 'suite is', 'suites are')} ready"
        )

    clean_paths = {suite.path for suite in report.suites if suite.is_clean}
    proposed = {
        path: diff
        for path, diff in (diffs or {}).items()
        if path in clean_paths and diff
    }
    if proposed:
        console.print()
        console.print(Text("Proposed rewrites (--apply):", style="cyan"))
        for path, diff in proposed.items():
            console.print()
            console.print(diff, markup=False)

    if report.gutconfig_path is not None:
        console.print()
        _render_config(
            console,
            report.gutconfig_path,
            translation or ConfigTranslation(),
        )

    console.print()
    console.print(_DOC_POINTER)
    return buf.getvalue()
