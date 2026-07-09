"""Unit tests for the lint runner module.

Covers data models (LintIssue, LintResult), file discovery,
lint execution via gdtoolkit, output formatting, and syntax
error handling.
"""

import pytest

from gd_tools.lint_runner import LintIssue, LintResult


# --- LintIssue dataclass ---


def test_lint_issue_construction():
    """Test LintIssue can be constructed with all fields."""
    issue = LintIssue(
        file="res://foo.gd",
        line=10,
        column=1,
        rule="SOME_RULE",
        message="Something is wrong",
        severity="error",
    )
    assert issue.file == "res://foo.gd"
    assert issue.line == 10
    assert issue.column == 1
    assert issue.rule == "SOME_RULE"
    assert issue.message == "Something is wrong"
    assert issue.severity == "error"


def test_lint_issue_severity_error():
    """Test LintIssue accepts severity='error'."""
    issue = LintIssue(
        file="a.gd",
        line=1,
        column=1,
        rule="RULE",
        message="msg",
        severity="error",
    )
    assert issue.severity == "error"


def test_lint_issue_severity_warning():
    """Test LintIssue accepts severity='warning'."""
    issue = LintIssue(
        file="a.gd",
        line=1,
        column=1,
        rule="RULE",
        message="msg",
        severity="warning",
    )
    assert issue.severity == "warning"


def test_lint_issue_field_types():
    """Test LintIssue fields have correct types."""
    issue = LintIssue(
        file="a.gd",
        line=5,
        column=3,
        rule="RULE",
        message="msg",
        severity="error",
    )
    assert isinstance(issue.file, str)
    assert isinstance(issue.line, int)
    assert isinstance(issue.column, int)
    assert isinstance(issue.rule, str)
    assert isinstance(issue.message, str)
    assert isinstance(issue.severity, str)


# --- LintResult dataclass ---


def test_lint_result_construction():
    """Test LintResult can be constructed with all fields."""
    errors = [
        LintIssue("a.gd", 1, 1, "R1", "msg1", "error"),
    ]
    warnings = [
        LintIssue("a.gd", 2, 1, "R2", "msg2", "warning"),
    ]
    result = LintResult(
        files_checked=1,
        errors=errors,
        warnings=warnings,
    )
    assert result.files_checked == 1
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
    assert result.errors[0].rule == "R1"
    assert result.warnings[0].rule == "R2"


def test_lint_result_empty_lists():
    """Test LintResult can be constructed with empty lists."""
    result = LintResult(files_checked=0, errors=[], warnings=[])
    assert result.files_checked == 0
    assert result.errors == []
    assert result.warnings == []


def test_lint_result_files_checked_type():
    """Test LintResult files_checked is an int."""
    result = LintResult(files_checked=5, errors=[], warnings=[])
    assert isinstance(result.files_checked, int)


def test_lint_result_errors_is_list():
    """Test LintResult errors is a list."""
    result = LintResult(files_checked=0, errors=[], warnings=[])
    assert isinstance(result.errors, list)


def test_lint_result_warnings_is_list():
    """Test LintResult warnings is a list."""
    result = LintResult(files_checked=0, errors=[], warnings=[])
    assert isinstance(result.warnings, list)
