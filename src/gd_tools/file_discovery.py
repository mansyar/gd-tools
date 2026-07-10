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

    Recursively walks ``path`` and collects all files with a ``.gd``
    extension (case-insensitive).  Directories whose names appear in
    ``excludes`` are pruned from the walk so their contents are never
    visited.

    Args:
        path: Root directory to search.
        excludes: Directory names to skip.  Defaults to
            :data:`DEFAULT_EXCLUDES` from ``config.py``.

    Returns:
        List of file paths (as strings) to ``.gd`` files.
    """
    if excludes is None:
        excludes = DEFAULT_EXCLUDES

    gd_files: list[str] = []
    for root, dirs, files in os.walk(path):
        # Prune excluded dirs in-place so os.walk doesn't descend into them
        dirs[:] = [d for d in dirs if d not in excludes]
        for file in files:
            if file.lower().endswith(".gd"):
                gd_files.append(os.path.join(root, file))
    return gd_files
