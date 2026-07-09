"""Lint runner module for gd-tools.

Wraps ``gdlint`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes gdlint programmatically, collects issues into structured
dataclasses, and renders results as either a rich terminal table
or JSON.
"""

from dataclasses import dataclass, field


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
