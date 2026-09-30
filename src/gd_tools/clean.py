"""Core implementation for the ``gd-tools clean`` command.

Removes generated artifacts under ``.gd-tools/`` with a fixed target map
so that only known gd-tools output is ever deleted. With no flags, the
command returns an inventory (sizes and presence) and removes nothing.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

# Statuses for a single target within a CleanResult.
STATUS_REMOVED = "removed"
STATUS_NOTHING = "nothing"
STATUS_WOULD_REMOVE = "would-remove"
STATUS_SUBSUMED = "subsumed"
STATUS_FAILED = "failed"
STATUS_PRESENT = "present"
STATUS_ABSENT = "absent"

# Structural protection: every target is a fixed constant under
# <project_root>/.gd-tools. Nothing outside this tree is ever a target,
# and the project's configuration/addons always survive a clean run.
TARGET_NAMES = ("coverage", "artifacts", "baselines", "cache")


@dataclass(frozen=True)
class TargetResult:
    """Outcome of a clean operation for one named target.

    Attributes:
        name: Target identifier (``coverage``, ``artifacts``,
            ``baselines``, ``cache``).
        path: Absolute path of the target (directory or file).
        status: One of the ``STATUS_*`` constants.
        freed_bytes: Bytes freed (or that *would* be freed on a dry
            run; or the measured size for inventory entries).
        error: Human-readable failure description when
            ``status == STATUS_FAILED``, else ``None``.
    """

    name: str
    path: Path
    status: str
    freed_bytes: int = 0
    error: str | None = None


@dataclass(frozen=True)
class CleanResult:
    """Aggregate outcome of a clean run across all targets."""

    targets: tuple[TargetResult, ...]

    def target(self, name: str) -> TargetResult:
        """Return the result for a named target.

        Args:
            name: Target identifier.

        Returns:
            The :class:`TargetResult` for ``name``.

        Raises:
            KeyError: If ``name`` is not a known target.
        """
        for entry in self.targets:
            if entry.name == name:
                return entry
        raise KeyError(name)

    @property
    def freed_bytes(self) -> int:
        """Total bytes freed (or that would be freed on a dry run)."""
        return sum(entry.freed_bytes for entry in self.targets)

    @property
    def failed(self) -> bool:
        """Whether any target removal failed."""
        return any(entry.status == STATUS_FAILED for entry in self.targets)


def _target_paths(project_root: Path) -> dict[str, Path]:
    """Resolve the fixed target map under ``<project_root>/.gd-tools``.

    Args:
        project_root: The Godot project directory.

    Returns:
        Mapping of target name to absolute path.
    """
    gd = project_root / ".gd-tools"
    return {
        "coverage": gd / "coverage",
        "artifacts": gd / "artifacts",
        "baselines": gd / "coverage" / "baseline.json",
        "cache": gd / "native",
    }


def _measure(path: Path) -> int:
    """Return the total size in bytes of a file or directory.

    Non-existent paths measure as 0. Unreadable entries are skipped.

    Args:
        path: File or directory to measure.

    Returns:
        Total size in bytes.
    """
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                continue
    return total


def _remove_path(path: Path) -> None:
    """Remove a file or a directory tree.

    Args:
        path: Path to remove.

    Raises:
        OSError: If the removal fails.
    """
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _dir_exists(path: Path) -> bool:
    """Whether the target exists (directory or file)."""
    return path.exists()


def run_clean(
    coverage: bool = False,
    artifacts: bool = False,
    baselines: bool = False,
    cache: bool = False,
    all: bool = False,  # noqa: A002 - mirrors the CLI flag name
    dry_run: bool = False,
    project_root: Path | None = None,
) -> CleanResult:
    """Clean generated artifacts, or report an inventory when nothing
    is selected.

    Args:
        coverage: Remove the coverage output directory (including the
            plan cache and ``baseline.json``).
        artifacts: Remove the native test artifacts directory.
        baselines: Remove only ``baseline.json`` from the coverage
            output.
        cache: Remove the native worker scratch directory.
        all: Remove every target directory (subsumes all other flags).
        dry_run: Compute and report what would be removed without
            deleting anything.
        project_root: Godot project directory. Defaults to the current
            working directory.

    Returns:
        A :class:`CleanResult` describing the outcome per target.
    """
    root = project_root if project_root is not None else Path.cwd()
    paths = _target_paths(root)

    if not (coverage or artifacts or baselines or cache or all):
        # Inventory mode: report presence and size, delete nothing.
        entries = tuple(
            TargetResult(
                name=name,
                path=path,
                status=STATUS_PRESENT if _dir_exists(path) else STATUS_ABSENT,
                freed_bytes=_measure(path),
            )
            for name, path in paths.items()
        )
        return CleanResult(targets=entries)

    if all:
        coverage = artifacts = baselines = cache = True

    selected = {
        name
        for name, flag in (
            ("coverage", coverage),
            ("artifacts", artifacts),
            ("baselines", baselines),
            ("cache", cache),
        )
        if flag
    }

    entries: list[TargetResult] = []
    for name, path in paths.items():
        if name not in selected:
            continue
        # Subsumption: --baselines is covered by --coverage, and both
        # explicit flags are covered by --all (which selects all four).
        if name == "baselines" and "coverage" in selected:
            entries.append(
                TargetResult(
                    name=name, path=path, status=STATUS_SUBSUMED, freed_bytes=0
                )
            )
            continue

        size = _measure(path)
        if not _dir_exists(path):
            entries.append(
                TargetResult(
                    name=name, path=path, status=STATUS_NOTHING, freed_bytes=0
                )
            )
            continue

        if dry_run:
            entries.append(
                TargetResult(
                    name=name,
                    path=path,
                    status=STATUS_WOULD_REMOVE,
                    freed_bytes=size,
                )
            )
            continue

        try:
            _remove_path(path)
        except OSError as exc:
            freed = size - _measure(path)
            entries.append(
                TargetResult(
                    name=name,
                    path=path,
                    status=STATUS_FAILED,
                    freed_bytes=freed,
                    error=f"failed to remove {path}: {exc}",
                )
            )
            continue

        entries.append(
            TargetResult(
                name=name, path=path, status=STATUS_REMOVED, freed_bytes=size
            )
        )

    return CleanResult(targets=tuple(entries))
