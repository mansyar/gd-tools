"""Lint runner module for gd-tools.

Wraps ``gdlint`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes gdlint programmatically, collects issues into structured
dataclasses, and renders results as either a rich terminal table
or JSON.
"""

import json
from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table

from gdtoolkit.linter import lint_code
from lark.exceptions import LarkError

from gd_tools.config import GdToolsConfig
from gd_tools.file_discovery import discover_gd_files


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
        try:
            problems = lint_code(code)
        except LarkError as e:
            # Parse/syntax error from Lark — report and continue linting
            errors.append(
                LintIssue(
                    file=file_path,
                    line=getattr(e, "line", 0),
                    column=getattr(e, "column", 0),
                    rule="SYNTAX_ERROR",
                    message=str(e),
                    severity="error",
                )
            )
            continue
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


def format_lint_text(result: LintResult) -> str:
    """Format lint results as a rich terminal table.

    Renders a table with columns File, Line, Column, Rule, Severity,
    and Message.  Error rows are styled red, warning rows yellow.
    A summary line is appended below the table.

    Args:
        result: Lint results to format.

    Returns:
        Formatted string with table and summary, or an informational
        message when there are no files or no issues.
    """
    if result.files_checked == 0:
        return "No GDScript files found."

    if not result.errors and not result.warnings:
        return "[OK] No lint issues found."

    console = Console(force_terminal=True)
    table = Table()
    table.add_column("File")
    table.add_column("Line")
    table.add_column("Column")
    table.add_column("Rule")
    table.add_column("Severity")
    table.add_column("Message")

    for issue in result.errors:
        table.add_row(
            issue.file,
            str(issue.line),
            str(issue.column),
            issue.rule,
            f"[red]{issue.severity}[/red]",
            issue.message,
        )

    for issue in result.warnings:
        table.add_row(
            issue.file,
            str(issue.line),
            str(issue.column),
            issue.rule,
            f"[yellow]{issue.severity}[/yellow]",
            issue.message,
        )

    with console.capture() as capture:
        console.print(table)

    summary = (
        f"{len(result.errors)} errors, "
        f"{len(result.warnings)} warnings, "
        f"{result.files_checked} files checked"
    )

    return capture.get() + "\n" + summary


def format_lint_json(result: LintResult) -> str:
    """Format lint results as a JSON string.

    Serializes the :class:`LintResult` to a JSON object with
    ``files_checked``, ``errors``, and ``warnings`` keys.  Each
    issue is a dict with ``file``, ``line``, ``column``, ``rule``,
    ``message``, and ``severity`` fields.  Empty lists are ``[]``,
    not ``null``.

    Args:
        result: Lint results to format.

    Returns:
        Valid JSON string.
    """
    data = {
        "files_checked": result.files_checked,
        "errors": [
            {
                "file": issue.file,
                "line": issue.line,
                "column": issue.column,
                "rule": issue.rule,
                "message": issue.message,
                "severity": issue.severity,
            }
            for issue in result.errors
        ],
        "warnings": [
            {
                "file": issue.file,
                "line": issue.line,
                "column": issue.column,
                "rule": issue.rule,
                "message": issue.message,
                "severity": issue.severity,
            }
            for issue in result.warnings
        ],
    }
    return json.dumps(data, indent=2)
