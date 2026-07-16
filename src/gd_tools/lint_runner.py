"""Lint runner module for gd-tools.

Wraps ``gdlint`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes gdlint programmatically, collects issues into structured
dataclasses, and renders results as either a flat line-based text
format or JSON.
"""

import json
import time
from dataclasses import dataclass, field

from rich.console import Console
from rich.text import Text

from gdtoolkit.linter import lint_code
from lark.exceptions import LarkError

from gd_tools import output
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
    config: GdToolsConfig,
    paths: list[str] | None = None,
    report_format: str = "text",
) -> LintResult:
    """Run gdlint on ``paths``, respecting config excludes.

    Discovers ``.gd`` files via :func:`discover_gd_files`, reads each
    file, and invokes ``gdtoolkit.linter.lint_code`` to check for
    issues.  All gdlint problems are treated as errors (gdlint does
    not distinguish severities).

    Args:
        config: Project configuration with lint excludes.
        paths: Root directories to lint. Defaults to ``["."]``.
        report_format: Output format hint (unused here; formatting
            is handled by :func:`format_lint_text` /
            :func:`format_lint_json`).

    Returns:
        :class:`LintResult` with file count and issue lists.
    """
    if not paths:
        paths = ["."]

    excludes = config.lint.exclude
    gd_files: list[str] = []
    for p in paths:
        gd_files.extend(discover_gd_files(p, excludes))
    gd_files = list(dict.fromkeys(gd_files))

    errors: list[LintIssue] = []
    warnings: list[LintIssue] = []
    files_skipped = 0

    console = Console()

    start_time = time.perf_counter()
    for file_path in gd_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except (OSError, UnicodeDecodeError) as e:
            console.print(
                f"[yellow]Warning: Skipping {file_path}: {e}[/yellow]"
            )
            files_skipped += 1
            continue
        output.print_verbose(f"Linting: {file_path}")
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

    elapsed = time.perf_counter() - start_time
    output.print_verbose(f"Elapsed: {elapsed:.2f}s")

    return LintResult(
        files_checked=len(gd_files) - files_skipped,
        errors=errors,
        warnings=warnings,
    )


def format_lint_text(result: LintResult) -> None:
    """Format and print lint results as flat line-based text.

    Each issue is rendered as ``file:line:col: rule: message  [SEVERITY]``,
    matching the convention used by ESLint, ruff, flake8, and other
    linters.  Issues are sorted by file path, then line, then column.
    Error severity tags are styled red, warning tags yellow.  The
    summary line is rendered via the shared :func:`print_summary`
    helper (red for errors, yellow for warnings only).  The clean
    state uses :func:`print_success` (green ``[OK]`` marker).

    Output is printed directly to the shared console — this function
    does not return a string.

    Args:
        result: Lint results to format and print.
    """
    if result.files_checked == 0:
        output.print_info("No GDScript files found.")
        return

    if not result.errors and not result.warnings:
        output.print_success("No lint issues found.")
        return

    all_issues = result.errors + result.warnings
    all_issues.sort(key=lambda i: (i.file, i.line, i.column))

    for issue in all_issues:
        if issue.severity == "error":
            color = "red"
            severity_tag = "ERROR"
        else:
            color = "yellow"
            severity_tag = "WARN"
        output.console.print(
            Text.assemble(
                f"{issue.file}:{issue.line}:{issue.column}: "
                f"{issue.rule}: {issue.message}  ",
                (f"[{severity_tag}]", color),
            )
        )

    output.console.print()  # blank line before summary

    counts = f"{len(result.errors)} errors, {len(result.warnings)} warnings"
    if result.errors:
        status = "fail"
    else:
        status = "warning"
    output.print_summary(status, counts, result.files_checked)


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
