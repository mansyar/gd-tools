"""Discover and filter native GdToolsTest suites."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from gd_tools.errors import ConfigError
from gd_tools.native_test.protocol import NativeSuite, NativeTest


class NativeDiscoveryError(ConfigError):
    """Raised when native test discovery cannot produce a usable manifest."""


_EXTENDS_RE = re.compile(r"^\s*extends\s+GdToolsTest(?:\s|$)", re.MULTILINE)
_GUT_EXTENDS_RE = re.compile(r"^\s*extends\s+GutTest(?:\s|$)", re.MULTILINE)
_CLASS_NAME_RE = re.compile(
    r"^\s*class_name\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE
)
_TEST_FUNC_RE = re.compile(
    r"^\s*(?:static\s+)?func\s+(test_[A-Za-z0-9_]+)\s*\(\s*\)",
    re.MULTILINE,
)
_TAG_RE = re.compile(r"^\s*const\s+TAGS\b[^=\n]*=\s*\[([^\]]*)\]", re.MULTILINE)
_STRING_RE = re.compile(r"[\"']([^\"']+)[\"']")


def _parse_tags(source: str) -> list[str]:
    """Extract class-level TAGS values from a GDScript source file."""
    match = _TAG_RE.search(source)
    if match is None:
        return []
    return _STRING_RE.findall(match.group(1))


def _class_name(source: str, fallback: str) -> str:
    """Return the declared class name or a filename-derived fallback."""
    match = _CLASS_NAME_RE.search(source)
    return match.group(1) if match else fallback


def _resource_path(path: Path, project_root: Path) -> str:
    """Convert a project-relative path to Godot's ``res://`` notation."""
    return f"res://{path.relative_to(project_root).as_posix()}"


def _iter_test_files(
    project_root: Path, test_dirs: Iterable[str]
) -> list[Path]:
    """Return unique, deterministic GDScript files below test directories."""
    candidates: set[Path] = set()
    for test_dir in test_dirs:
        directory = Path(test_dir)
        if not directory.is_absolute():
            directory = project_root / directory
        if not directory.is_dir():
            continue
        candidates.update(directory.rglob("*.gd"))

    return sorted(candidates, key=lambda path: path.as_posix())


def discover_native_suites(
    project_root: Path,
    test_dirs: Iterable[str],
    *,
    suite: str | None = None,
    test: str | None = None,
    tags: Iterable[str] | None = None,
    timeout_seconds: float = 5.0,
    retries: int = 0,
) -> list[NativeSuite]:
    """Discover native suites and apply path-independent selection filters.

    Args:
        project_root: Root containing ``project.godot``.
        test_dirs: Configured directories to scan for native suites.
        suite: Optional exact suite class-name filter.
        test: Optional exact test-method filter.
        tags: Optional tags; a suite is selected when it has at least one.
        timeout_seconds: Default per-test timeout placed in the manifest.
        retries: Default retry count placed in the manifest.

    Returns:
        Deterministically ordered native suites with selected test methods.

    Raises:
        NativeDiscoveryError: If no native suite exists but GUT suites do.
    """
    project_root = project_root.resolve()
    files = _iter_test_files(project_root, test_dirs)
    requested_tags = set(tags or ())
    native_suites: list[NativeSuite] = []
    found_gut = False

    for path in files:
        source = path.read_text(encoding="utf-8")
        is_native = _EXTENDS_RE.search(source) is not None
        is_gut = _GUT_EXTENDS_RE.search(source) is not None
        found_gut = found_gut or is_gut

        if not is_native:
            continue

        suite_name = _class_name(source, path.stem)
        suite_tags = _parse_tags(source)
        if suite is not None and suite_name != suite:
            continue
        if requested_tags and not requested_tags.intersection(suite_tags):
            continue

        test_names = _TEST_FUNC_RE.findall(source)
        if test is not None:
            test_names = [name for name in test_names if name == test]
        if not test_names:
            continue

        native_suites.append(
            NativeSuite(
                name=suite_name,
                path=_resource_path(path, project_root),
                tags=suite_tags,
                tests=[
                    NativeTest(
                        name=name,
                        timeout_seconds=timeout_seconds,
                        retries=retries,
                    )
                    for name in test_names
                ],
            )
        )

    if not native_suites and found_gut:
        raise NativeDiscoveryError(
            "No native GdToolsTest suites were found, but GUT tests are "
            "present. Run this project with --runtime gut during the migration "
            "period or migrate the suites to GdToolsTest."
        )

    return native_suites
