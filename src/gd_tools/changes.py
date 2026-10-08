"""Git change collection for ``gd-tools test --changed``.

Provides :func:`collect_changed_files`, which resolves the set of changed
files in a project from git in one of two modes:

- **Working tree** (``--changed``): uncommitted changes vs ``HEAD`` via
  ``git status --porcelain``, covering staged, unstaged, untracked,
  deleted, and renamed files.
- **Base ref** (``--changed --base <ref>``): committed changes since the
  merge-base of ``<ref>`` and ``HEAD`` via ``git diff --name-only``.

The same base-ref mode also powers patch coverage via
:func:`collect_changed_lines`, which extracts inclusive added-line
ranges per ``.gd`` file from ``git diff -U0`` output.

Failures are environment/configuration problems (exit code 2): the caller
is not inside a git repository, or the requested base ref does not exist.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from gd_tools.errors import GitChangeError


def collect_changed_files(
    project_root: Path, base: str | None = None
) -> list[Path]:
    """Return the project-relative paths of changed files.

    Args:
        project_root: The Godot project root (also the git working tree).
        base: Optional git ref. When given, the change set is the diff
            from ``merge-base(ref, HEAD)`` (committed changes only).
            When ``None``, the change set is the working tree vs ``HEAD``
            (staged, unstaged, untracked, deleted, and renamed files).

    Returns:
        Changed file paths relative to ``project_root``, in git output
        order. Empty when there are no changes.

    Raises:
        GitChangeError: When the directory is not a git repository or
            ``base`` is not a valid ref.
    """
    if base is None:
        result = _git(["status", "--porcelain"], project_root)
        return _parse_porcelain(result.stdout)
    merge_base = _git(["merge-base", base, "HEAD"], project_root)
    result = _git(
        ["diff", "--name-only", merge_base.stdout.strip(), "HEAD"],
        project_root,
    )
    return _parse_name_only(result.stdout)


def collect_changed_lines(
    project_root: Path, base: str
) -> dict[Path, list[tuple[int, int]]]:
    """Return inclusive added-line ranges per changed ``.gd`` file.

    Diffs from ``merge-base(base, HEAD)`` to ``HEAD`` with
    ``git diff -U0`` and parses the added side of each hunk.

    Deleted files are excluded (their added side is ``/dev/null``),
    and only ``.gd`` files are returned since patch coverage tracks
    GDScript sources.

    Args:
        project_root: The Godot project root (also the git working tree).
        base: Git ref to diff against, via its merge-base with ``HEAD``.

    Returns:
        Mapping of project-relative ``.gd`` paths to sorted, inclusive
        ``(start, end)`` ranges of added lines, in diff order. Files
        whose diff contains no added lines map to an empty list.

    Raises:
        GitChangeError: When the directory is not a git repository or
            ``base`` is not a valid ref.
    """
    merge_base = _git(["merge-base", base, "HEAD"], project_root)
    result = _git(
        ["diff", "-U0", merge_base.stdout.strip(), "HEAD"],
        project_root,
    )
    return _parse_added_line_ranges(result.stdout)


def _git(args: list[str], project_root: Path) -> subprocess.CompletedProcess:
    """Run a git command in ``project_root``.

    Args:
        args: Git arguments (without the ``git`` binary name).
        project_root: Directory to run git in.

    Returns:
        The completed process on success (returncode 0).

    Raises:
        GitChangeError: With an actionable message when git fails.
    """
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise GitChangeError(
            "git not found: --changed requires git on PATH. Install git "
            "or add it to PATH, then retry."
        ) from None
    if result.returncode == 0:
        return result
    if "not a git repository" in (result.stderr or "").lower():
        raise GitChangeError(
            "Not a git repository: --changed requires the project to be "
            "tracked by git."
        )
    if args[0] == "merge-base":
        raise GitChangeError(
            f"Unknown base ref '{args[1]}': --base must name an existing "
            "git ref (branch, tag, or commit)."
        )
    raise GitChangeError(
        f"git {args[0]} failed: {(result.stderr or '').strip()}"
    )


def _parse_porcelain(stdout: str) -> list[Path]:
    """Parse ``git status --porcelain`` output into paths.

    Strips the two-character status prefix and handles rename entries of
    the form ``R  old -> new`` (keeping the new path).
    """
    paths: list[Path] = []
    for line in stdout.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:]
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.append(Path(entry))
    return paths


def _parse_name_only(stdout: str) -> list[Path]:
    """Parse ``git diff --name-only`` output into paths (one per line)."""
    return [Path(line) for line in stdout.splitlines() if line]


_HUNK_HEADER = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _parse_added_line_ranges(
    stdout: str,
) -> dict[Path, list[tuple[int, int]]]:
    """Parse ``git diff -U0`` output into per-file added-line ranges.

    Tracks the current file from ``+++ b/<path>`` headers, skipping
    deleted files (``/dev/null``) and non-``.gd`` paths, then turns
    each ``@@ -a,b +c,d @@`` hunk header into an inclusive
    ``(start, start + count - 1)`` range. Hunks with a zero new-side
    count (pure deletions) contribute no range.
    """
    ranges: dict[Path, list[tuple[int, int]]] = {}
    current: Path | None = None
    for line in stdout.splitlines():
        if line.startswith("diff --git "):
            current = None
            continue
        if line.startswith("+++ "):
            raw = line[4:].split("\t", 1)[0]
            if raw == "/dev/null":
                current = None
                continue
            path = Path(raw[2:] if raw.startswith("b/") else raw)
            if path.suffix == ".gd":
                current = path
                ranges.setdefault(current, [])
            else:
                current = None
            continue
        if current is None:
            continue
        match = _HUNK_HEADER.match(line)
        if match is None:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count > 0:
            ranges[current].append((start, start + count - 1))
    return ranges
