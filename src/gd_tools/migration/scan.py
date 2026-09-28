"""Static analysis of GUT suites for migration reporting.

The scanner reuses the bridge preflight's unsupported-construct detection so
the migration report and the preflight gate always agree on what the bridge
supports. Bridge-only alias calls (constructs that run unchanged through the
native base class) are reported separately as rename candidates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gd_tools.errors import GdToolsError
from gd_tools.native_test.bridge_scan import find_unsupported_constructs
from gd_tools.native_test.protocol import NativeSuite, RuntimeMode

GUTCONFIG_PATH = "res://.gutconfig.json"

# Bridge-only aliases: constructs the native base class already provides, so
# they run unchanged, but whose GUT-style spellings are worth renaming during
# a migration for consistency with the native API.
_ALIAS_CALL_RE = re.compile(r"(?<![\w.])(assert_in|pending_test)\s*\(")


class MigrationScanError(GdToolsError):
    """A suite listed for migration could not be read on disk."""


@dataclass(frozen=True)
class ConstructHit:
    """One construct call site found in a suite source."""

    name: str
    line: int


@dataclass(frozen=True)
class SuiteFindings:
    """Scan result for a single suite source, ordered by line."""

    unsupported: tuple[ConstructHit, ...] = ()
    aliases: tuple[ConstructHit, ...] = ()


@dataclass(frozen=True)
class SuiteReport:
    """Migration status of one bridge suite."""

    path: str
    test_count: int
    unsupported: tuple[ConstructHit, ...] = ()
    aliases: tuple[ConstructHit, ...] = ()

    @property
    def is_clean(self) -> bool:
        """Whether the suite uses only constructs the bridge supports."""
        return not self.unsupported


@dataclass(frozen=True)
class MigrationReport:
    """Full migration status of a project's test suites."""

    suites: tuple[SuiteReport, ...] = ()
    gutconfig_path: str | None = None


def scan_source(source: str) -> SuiteFindings:
    """Return unsupported-construct and alias call sites in suite source.

    Args:
        source: GDScript source of a bridge suite.

    Returns:
        Every unsupported construct call site and every bridge-only alias
        call site, each ordered by source line.
    """
    unsupported = tuple(
        ConstructHit(name=name, line=line)
        for name, line in find_unsupported_constructs(source)
    )
    aliases = tuple(
        ConstructHit(
            name=match.group(1), line=source.count("\n", 0, match.start()) + 1
        )
        for match in _ALIAS_CALL_RE.finditer(source)
    )
    return SuiteFindings(unsupported=unsupported, aliases=aliases)


def build_migration_report(
    project_root: Path, suites: list[NativeSuite]
) -> MigrationReport:
    """Scan bridge suites and assemble the migration report model.

    Args:
        project_root: Godot project root used to resolve ``res://`` paths.
        suites: Suites discovered the same way ``gd-tools test`` discovers
            them; only ``RuntimeMode.GUT`` suites are scanned.

    Returns:
        A report with one entry per bridge suite and the location of a
        ``.gutconfig.json`` when one exists at the project root.

    Raises:
        MigrationScanError: If a bridge suite cannot be read from disk.
    """
    project_root = project_root.resolve()
    suite_reports: list[SuiteReport] = []
    for suite in suites:
        if suite.runtime is not RuntimeMode.GUT:
            continue
        source_path = project_root / suite.path.removeprefix("res://")
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError as error:
            raise MigrationScanError(
                f"Cannot read suite '{suite.path}': {error}"
            ) from error
        findings = scan_source(source)
        suite_reports.append(
            SuiteReport(
                path=suite.path,
                test_count=len(suite.tests),
                unsupported=findings.unsupported,
                aliases=findings.aliases,
            )
        )
    gutconfig = project_root / ".gutconfig.json"
    gutconfig_path = GUTCONFIG_PATH if gutconfig.is_file() else None
    return MigrationReport(
        suites=tuple(suite_reports), gutconfig_path=gutconfig_path
    )
