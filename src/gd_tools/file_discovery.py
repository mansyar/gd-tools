"""Shared file discovery module for gd-tools.

Discovers ``.gd`` files under a given path, applying exclude
patterns from the configuration. Used by both the lint runner
and the format runner.
"""

import os

from gd_tools.config import DEFAULT_EXCLUDES


def discover_gd_files(
    path: str, excludes: list[str] | None = None
) -> list[str]:
    """Discover ``.gd`` files in ``path``, skipping excluded directories.

    Exclude entries are interpreted with hybrid matching:

    - **Bare names** (no path separator, e.g. ``addons``, ``.godot``)
      match any directory *basename* at any depth (backward compatible
      with :data:`DEFAULT_EXCLUDES`).
    - **Path prefixes** (containing ``/`` or ``\\``, e.g.
      ``scripts/autoload``) match as a path prefix relative to the
      search root — any file whose relative path starts with the
      prefix is excluded.

    Args:
        path: Root directory to search.
        excludes: Exclude entries (bare names or path prefixes).
            Defaults to :data:`DEFAULT_EXCLUDES` from ``config.py``.

    Returns:
        List of file paths (as strings) to ``.gd`` files.
    """
    if excludes is None:
        excludes = DEFAULT_EXCLUDES

    bare_excludes: set[str] = set()
    path_excludes: list[str] = []
    for entry in excludes:
        if "/" in entry or "\\" in entry:
            # Normalize separators to the OS-native form
            path_excludes.append(
                entry.replace("\\", os.sep).replace("/", os.sep)
            )
        else:
            bare_excludes.add(entry)

    gd_files: list[str] = []
    for root, dirs, files in os.walk(path):
        # Prune basename-excluded dirs in-place so os.walk doesn't descend
        dirs[:] = [d for d in dirs if d not in bare_excludes]
        for file in files:
            if file.lower().endswith(".gd"):
                file_path = os.path.join(root, file)
                if path_excludes:
                    rel_path = os.path.relpath(file_path, path)
                    normalized = rel_path.replace("\\", os.sep).replace(
                        "/", os.sep
                    )
                    if any(
                        normalized == prefix
                        or normalized.startswith(prefix + os.sep)
                        for prefix in path_excludes
                    ):
                        continue
                gd_files.append(file_path)
    return gd_files
