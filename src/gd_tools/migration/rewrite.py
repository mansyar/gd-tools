"""Conservative GUT suite rewrites and reviewable diffs.

Phase 4 rewrites are deliberately limited to the base-class rename
(``extends GutTest`` -> ``extends GdToolsTest``): everything else the
bridge already runs unchanged. The rewrite never mutates files — callers
get the new source and a unified diff for review, and only the atomic
apply flow (opt-in) writes anything to disk.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

# A real top-level `extends GutTest` declaration. Indented text and
# quoted strings never match; trailing content (comments) is preserved.
_EXTENDS_RE = re.compile(r"(?m)^(extends\s+)GutTest\b(.*)$")


@dataclass(frozen=True)
class RewriteChange:
    """A single rewritten line within a suite."""

    #: 1-based line number of the change.
    line: int
    #: The original line content.
    old: str
    #: The rewritten line content.
    new: str


@dataclass(frozen=True)
class RewriteResult:
    """The outcome of rewriting one suite's source."""

    #: The rewritten source (identical to the input when nothing matched).
    new_source: str
    #: The changes applied, in line order.
    changes: tuple[RewriteChange, ...]

    @property
    def changed_lines(self) -> tuple[int, ...]:
        """1-based numbers of the lines that were rewritten."""
        return tuple(change.line for change in self.changes)


def rewrite_suite(source: str) -> RewriteResult:
    """Rename the GUT base class in a suite's source.

    Args:
        source: The full ``.gd`` file content.

    Returns:
        A :class:`RewriteResult` with the new source and per-line change
        records. Suites that do not declare ``extends GutTest`` are
        returned unchanged with no changes.
    """
    changes: list[RewriteChange] = []
    lines = source.splitlines(keepends=True)
    offset = 0
    for index, line in enumerate(lines):
        match = _EXTENDS_RE.match(line)
        if match is None:
            offset += len(line)
            continue
        rewritten = match.expand(r"\1GdToolsTest\2")
        if line.endswith("\n"):
            rewritten += "\n"
        changes.append(
            RewriteChange(
                line=index + 1,
                old=line.rstrip("\n"),
                new=rewritten.rstrip("\n"),
            )
        )
        lines[index] = rewritten
    return RewriteResult(
        new_source="".join(lines),
        changes=tuple(changes),
    )


def generate_diff(path: str, old_source: str, new_source: str) -> str:
    """Render a unified diff for one suite's rewrite.

    Args:
        path: The ``res://`` path shown in the diff header.
        old_source: The current file content.
        new_source: The proposed rewritten content.

    Returns:
        The unified diff text, or an empty string when the sources are
        identical.
    """
    if old_source == new_source:
        return ""
    diff_lines = difflib.unified_diff(
        old_source.splitlines(keepends=True),
        new_source.splitlines(keepends=True),
        fromfile=path,
        tofile=path,
    )
    return "".join(diff_lines)
