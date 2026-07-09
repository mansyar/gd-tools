"""Lint runner module for gd-tools.

Wraps ``gdlint`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes gdlint programmatically, collects issues into structured
dataclasses, and renders results as either a rich terminal table
or JSON.
"""

import os
from dataclasses import dataclass, field

from gdtoolkit.linter import lint_code

from gd_tools.config import DEFAULT_EXCLUDES, GdToolsConfig


@dataclass
class LintIssue:
    """A single lint issue found in a GDScript file.

    Attributes:
        file: Path to the file containing the issue.
        line: Line number (1-based) where the issue occurs.
        column: Column number (1-based) where the issue occurs.
        rule: The lint rule name (e.g. ``"function-name"``).
        message: Human-readable description of the issue.
        severity: Either ``"error"`` or ``"warning"``.
    """

    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str


@dataclass
class LintResult:
    """Aggregated lint results for a project.

    Attributes:
        files_checked: Number of ``.gd`` files that were linted.
        errors: List of lint issues with severity ``"error"``.
        warnings: List of lint issues with severity ``"warning"``.
    """

    files_checked: int
    errors: list[LintIssue] = field(default_factory=list)
    warnings: list[LintIssue] = field(default_factory=list)


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


def run_lint(
    config: GdToolsConfig, path: str = ".", report_format: str = "text"
) -> LintResult:
    """Run gdlint on ``path``, respecting config excludes.

    Discovers ``.gd`` files via :func:`discover_gd_files`, reads each
    file, and invokes ``gdtoolkit.linter.lint_code`` to check for
    issues.  All gdlint problems are treated as errors (gdlint does
    not distinguish severities).

    Args:
        config: Project configuration with lint excludes.
        path: Root directory to lint.
        report_format: Output format hint (unused here; formatting
            is handled by :func:`format_lint_text` /
            :func:`format_lint_json`).

    Returns:
        :class:`LintResult` with file count and issue lists.
    """
    excludes = config.lint.exclude
    gd_files = discover_gd_files(path, excludes)

    errors: list[LintIssue] = []
    warnings: list[LintIssue] = []

    for file_path in gd_files:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        problems = lint_code(code)
        for problem in problems:
            errors.append(
                LintIssue(
                    file=file_path,
                    line=problem.line,
                    column=problem.column,
                    rule=problem.name,
                    message=problem.description,
                    severity="error",
                )
            )

    return LintResult(
        files_checked=len(gd_files),
        errors=errors,
        warnings=warnings,
    )
