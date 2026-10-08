"""Lint runner module for gd-tools.

Wraps ``gdlint`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes gdlint programmatically, collects issues into structured
dataclasses, and renders results as either a flat line-based text
format or JSON.
"""

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

import yaml
from rich.console import Console
from rich.text import Text

from gdtoolkit.linter import DEFAULT_CONFIG, lint_code
from lark.exceptions import LarkError

from gd_tools import output
from gd_tools.config import ConfigError, GdToolsConfig, find_project_root
from gd_tools.file_discovery import discover_gd_files
from gd_tools.gh_annotations import (
    escape_gh_message_data,
    escape_gh_property,
)

_GDLINT_RC_NAMES = ("gdlintrc", ".gdlintrc")


def load_gdlint_config(
    config_path: str | None = None,
    project_root: Path | None = None,
) -> MappingProxyType:
    """Load the gdlint config that bare ``gdlint`` would honor.

    Resolution order:

    1. ``config_path`` — an explicit path, loaded directly.
    2. ``project_root`` — when known (a Godot project), the project's
       own ``gdlintrc`` / ``.gdlintrc`` is used; the search does not
       escape the project, so a stray config outside it cannot
       silently govern the project's lint run.
    3. Outside a Godot project, discovery walks up from the current
       working directory — mirroring bare gdlint's own search.
    4. gdtoolkit's ``DEFAULT_CONFIG`` when no file is found.

    Entries absent from the loaded file are filled in from
    ``DEFAULT_CONFIG``, matching gdlint's merge behavior.

    Args:
        config_path: Explicit path to a gdlint config file.
        project_root: Project directory whose gdlintrc governs the
            run, without searching above it.

    Returns:
        An immutable config mapping suitable for
        ``gdtoolkit.linter.lint_code``.
    """
    file_path: Path | None = None
    if config_path is not None:
        file_path = Path(config_path)
    elif project_root is not None:
        for name in _GDLINT_RC_NAMES:
            candidate = project_root / name
            if candidate.is_file():
                file_path = candidate
                break
    else:
        current = Path.cwd().resolve()
        while True:
            for name in _GDLINT_RC_NAMES:
                candidate = current / name
                if candidate.is_file():
                    file_path = candidate
                    break
            if file_path is not None or current == current.parent:
                break
            current = current.parent

    if file_path is None:
        return DEFAULT_CONFIG

    with open(file_path, "r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle.read())
    if not isinstance(loaded, dict):
        loaded = {}
    for key, value in DEFAULT_CONFIG.items():
        if key not in loaded:
            loaded[key] = value
    return MappingProxyType(loaded)


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
    lint_config: Mapping | None = None,
    lint_config_path: str | None = None,
) -> LintResult:
    """Run gdlint on ``paths``, respecting config excludes.

    Discovers ``.gd`` files via :func:`discover_gd_files`, reads each
    file, and invokes ``gdtoolkit.linter.lint_code`` to check for
    issues.  All gdlint problems are treated as errors (gdlint does
    not distinguish severities).

    The gdlint rule config is resolved from ``lint_config_path`` when
    given, else from ``lint_config`` when given, else from the
    project's ``gdlintrc`` (discovered like bare gdlint does), so
    ``disable:`` lists and rule settings behave the same as running
    ``gdlint`` directly.

    Args:
        config: Project configuration with lint excludes.
        paths: Root directories to lint. Defaults to ``["."]``.
        report_format: Output format hint (unused here; formatting
            is handled by :func:`format_lint_text` /
            :func:`format_lint_json`).
        lint_config: Pre-loaded gdlint config mapping for
            ``lint_code``. Takes precedence over discovery but not
            over ``lint_config_path``.
        lint_config_path: Explicit path to a gdlint config file.
            Takes precedence over every other source.

    Returns:
        :class:`LintResult` with file count and issue lists.
    """
    if not paths:
        paths = ["."]

    if lint_config_path is not None:
        lint_config = load_gdlint_config(config_path=lint_config_path)
    elif lint_config is None:
        project_root: Path | None
        try:
            project_root = find_project_root()
        except ConfigError:
            project_root = None
        lint_config = load_gdlint_config(project_root=project_root)

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
            problems = lint_code(code, lint_config)
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


def format_lint_github_actions(result: LintResult) -> str:
    """Format lint results as GitHub Actions workflow log commands.

    Each issue renders as an annotation command per the official
    "Workflow commands for GitHub Actions" spec::

        ::error file=<path>,line=<line>,col=<col>,title=<rule>::<message>

    Errors use ``::error`` and warnings use ``::warning``.  Property
    values (``file``, ``title``) escape ``%``, CR, LF, ``,` and ``:``;
    message data escapes ``%``, CR, LF.  File paths use POSIX
    separators so annotations work across platforms.  Issues are
    sorted by file path, then line, then column.  No issues produce
    an empty string (no annotations, no noise).

    Args:
        result: Lint results to format.

    Returns:
        Workflow log commands, one per line, or an empty string.
    """
    issues = result.errors + result.warnings
    if not issues:
        return ""
    issues.sort(key=lambda i: (i.file, i.line, i.column))
    lines = []
    for issue in issues:
        command = "error" if issue.severity == "error" else "warning"
        path = issue.file.replace("\\", "/")
        lines.append(
            f"::{command} "
            f"file={escape_gh_property(path)},"
            f"line={issue.line},"
            f"col={issue.column},"
            f"title={escape_gh_property(issue.rule)}"
            f"::{escape_gh_message_data(issue.message)}"
        )
    return "\n".join(lines) + "\n"
