"""Atomic application of migration rewrites and config translation.

The apply flow is two-phase: every suite file is read and rewritten in
memory first, so a read failure aborts before a single file on disk is
touched. Only then are the planned writes executed. The source
``.gutconfig.json`` is never written — translation targets
``gd-tools.toml`` with merge-never-clobber semantics.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from gd_tools.config import load_config, save_config
from gd_tools.migration.rewrite import rewrite_suite
from gd_tools.migration.scan import MigrationReport, MigrationScanError
from gd_tools.migration.translate import build_config_update

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


@dataclass(frozen=True)
class ApplyResult:
    """The outcome of applying a migration."""

    #: ``res://`` paths of suites that were rewritten on disk.
    rewritten: tuple[str, ...]
    #: Whether gd-tools.toml was written.
    config_updated: bool
    #: ``(flag, value)`` pairs the user should pass to ``gd-tools test``.
    cli_flags: tuple[tuple[str, str], ...]
    #: ``(gut_key, gd_tools_target)`` pairs skipped by merge-never-clobber.
    skipped: tuple[tuple[str, str], ...]


def plan_rewrites(
    project_root: Path,
    report: MigrationReport,
) -> dict[str, tuple[Path, str, str]]:
    """Read and rewrite clean suites in memory, without writing.

    Args:
        project_root: Path to the Godot project root.
        report: The migration report produced by the scanner.

    Returns:
        A mapping from ``res://`` suite path to
        ``(file_path, old_source, new_source)`` for every clean suite
        whose base class would be renamed. Suites with unsupported
        constructs are never included (spec FR-3).

    Raises:
        MigrationScanError: If a suite cannot be read.
    """
    root = Path(project_root).resolve()
    plans: dict[str, tuple[Path, str, str]] = {}
    for suite in report.suites:
        if not suite.is_clean:
            # Files with unsupported constructs stay untouched; they
            # are reported with guidance instead (spec FR-3).
            continue
        file_path = root / suite.path.removeprefix("res://")
        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError as error:
            raise MigrationScanError(
                f"Cannot read suite '{suite.path}': {error}"
            ) from error
        result = rewrite_suite(source)
        if result.changes:
            plans[suite.path] = (file_path, source, result.new_source)
    return plans


def apply_migration(
    project_root: Path,
    report: MigrationReport,
    options: Mapping[str, object],
    config_only: bool = False,
) -> ApplyResult:
    """Apply migration rewrites and config translation to a project.

    Args:
        project_root: Path to the Godot project root.
        report: The migration report produced by
            :func:`gd_tools.migration.scan.build_migration_report`.
        options: Parsed ``.gutconfig.json`` content. Ignored when the
            report has no gutconfig path.
        config_only: When ``True``, only the config translation is
            applied and suite files are left untouched.

    Returns:
        An :class:`ApplyResult` describing what changed.

    Raises:
        MigrationScanError: If a suite or ``gd-tools.toml`` cannot be
            read. Raised before any file is written.
    """
    root = Path(project_root).resolve()

    # Phase A — read and rewrite everything in memory.
    plans = {} if config_only else plan_rewrites(root, report)
    rewritten = tuple(plans)

    # Phase B — plan the config translation.
    existing: Mapping[str, object] | None = None
    if report.gutconfig_path is not None:
        config_file = root / "gd-tools.toml"
        if config_file.is_file():
            try:
                with open(config_file, "rb") as handle:
                    existing = tomllib.load(handle)
            except tomllib.TOMLDecodeError as error:
                raise MigrationScanError(
                    f"Invalid TOML in {config_file}: {error}"
                ) from error
        update = build_config_update(options, existing)

    # Phase C — write. Nothing above this point mutated the project.
    for file_path, _old, new_source in plans.values():
        file_path.write_text(new_source, encoding="utf-8")

    config_updated = False
    if report.gutconfig_path is not None and update.test_values:
        config = load_config(root)
        test_section = config.test
        for key, value in update.test_values.items():
            setattr(test_section, key, value)
        save_config(config, root)
        config_updated = True

    return ApplyResult(
        rewritten=rewritten,
        config_updated=config_updated,
        cli_flags=update.cli_flags if report.gutconfig_path is not None else (),
        skipped=update.skipped if report.gutconfig_path is not None else (),
    )
