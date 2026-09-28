"""Map changed project files to the native suites that should re-run."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from gd_tools.native_test.protocol import NativeSuite


def _res_path(relative: Path) -> str:
    """Return Godot's ``res://`` notation for a project-relative path."""
    return f"res://{relative.as_posix()}"


def map_changed_file(
    changed: Path,
    project_root: Path,
    suites: Sequence[NativeSuite],
) -> str | None:
    """Return the ``res://`` path of the suite to re-run for a changed file.

    The mapping uses the project's naming conventions: ``foo.gd`` maps to a
    ``test_foo.gd`` or ``foo_test.gd`` suite, with the ``test_`` prefix taking
    precedence. A sibling in the same directory is preferred; otherwise any
    selected suite with a matching stem is used, which supports the common
    layout where sources live in ``src/`` and suites in ``tests/``. A changed
    file that is itself a selected suite maps to itself.

    Only suites present in ``suites`` — already narrowed by the active
    ``--suite``/``--test``/``--tag`` filters — can be matched, so mapping
    always respects the current selection.

    Args:
        changed: Path of the file that changed on disk.
        project_root: Root of the Godot project containing ``project.godot``.
        suites: Currently selected native suites from discovery.

    Returns:
        The matching suite's ``res://`` path, or ``None`` when no selected
        suite maps to the changed file.
    """
    project_root = project_root.resolve()
    try:
        relative = changed.resolve().relative_to(project_root)
    except ValueError:
        return None

    suite_paths = {suite.path for suite in suites}
    changed_res = _res_path(relative)
    if changed_res in suite_paths:
        return changed_res

    stem = relative.stem
    candidate_stems = (f"test_{stem}", f"{stem}_test")
    for candidate_stem in candidate_stems:
        candidate = _res_path(relative.with_name(f"{candidate_stem}.gd"))
        if candidate in suite_paths:
            return candidate
    for candidate_stem in candidate_stems:
        for suite in suites:
            if Path(suite.path).stem == candidate_stem:
                return suite.path

    return None