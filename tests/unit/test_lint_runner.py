"""Unit tests for the lint runner module.

Covers data models (LintIssue, LintResult), file discovery,
lint execution via gdtoolkit, output formatting, and syntax
error handling.
"""

from pathlib import Path

from gd_tools.config import GdToolsConfig
from gd_tools.lint_runner import (
    LintIssue,
    LintResult,
    discover_gd_files,
    format_lint_text,
    run_lint,
)

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


# --- File discovery ---


def test_discover_gd_files_recursive(tmp_path):
    """Test that .gd files are collected from nested directories."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "enemy.gd").write_text("extends Node\n")
    (tmp_path / "subdir" / "nested").mkdir()
    (tmp_path / "subdir" / "nested" / "boss.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=[])
    assert len(result) == 3
    files = [Path(f).name for f in result]
    assert "player.gd" in files
    assert "enemy.gd" in files
    assert "boss.gd" in files


def test_discover_gd_files_case_insensitive(tmp_path):
    """Test that .GD and .Gd extensions are also collected."""
    (tmp_path / "lower.gd").write_text("extends Node\n")
    (tmp_path / "upper.GD").write_text("extends Node\n")
    (tmp_path / "mixed.Gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=[])
    assert len(result) == 3
    files = [Path(f).name for f in result]
    assert "lower.gd" in files
    assert "upper.GD" in files
    assert "mixed.Gd" in files


def test_discover_gd_files_excludes(tmp_path):
    """Test that excluded directories are skipped by name."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text("extends Node\n")
    (tmp_path / ".godot").mkdir()
    (tmp_path / ".godot" / "imported.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=["addons", ".godot"])
    assert len(result) == 1
    assert Path(result[0]).name == "player.gd"


def test_discover_gd_files_excludes_nested(tmp_path):
    """Test that excluded directories are skipped at any nesting level."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.gd").write_text("extends Node\n")
    (tmp_path / "src" / "addons").mkdir()
    (tmp_path / "src" / "addons" / "plugin.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=["addons"])
    assert len(result) == 1
    assert Path(result[0]).name == "main.gd"


def test_discover_gd_files_no_files(tmp_path):
    """Test that a directory with no .gd files returns an empty list."""
    (tmp_path / "readme.txt").write_text("hello\n")
    (tmp_path / "config.json").write_text("{}\n")

    result = discover_gd_files(str(tmp_path), excludes=[])
    assert result == []


def test_discover_gd_files_default_excludes(tmp_path):
    """Test that DEFAULT_EXCLUDES are used when excludes is None."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text("extends Node\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hook.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path))
    assert len(result) == 1
    assert Path(result[0]).name == "player.gd"


# --- run_lint core logic ---


def test_run_lint_clean_files(tmp_path):
    """Test run_lint with clean .gd files (no errors, no warnings)."""
    (tmp_path / "clean.gd").write_text("extends Node\n")
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 1
    assert result.errors == []
    assert result.warnings == []


def test_run_lint_with_errors(tmp_path):
    """Test run_lint with files that have lint errors."""
    (tmp_path / "bad.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 1
    assert len(result.errors) >= 1
    issue = result.errors[0]
    assert issue.rule == "function-name"
    assert issue.severity == "error"
    assert issue.line == 3
    assert issue.column == 6
    assert "BadFunctionName" in issue.message


def test_run_lint_warnings_empty(tmp_path):
    """Test that warnings list is empty (gdlint does not produce warnings)."""
    (tmp_path / "bad.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.warnings == []


def test_run_lint_respects_excludes(tmp_path):
    """Test that run_lint respects config excludes."""
    (tmp_path / "main.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 1
    assert result.errors == []


def test_run_lint_no_gd_files(tmp_path):
    """Test run_lint with no .gd files in the path."""
    (tmp_path / "readme.txt").write_text("hello\n")
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 0
    assert result.errors == []
    assert result.warnings == []


def test_run_lint_multiple_files(tmp_path):
    """Test run_lint with multiple files, some clean and some with errors."""
    (tmp_path / "clean.gd").write_text("extends Node\n")
    (tmp_path / "bad.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 2
    assert len(result.errors) >= 1
    # All errors should be from the bad file
    for issue in result.errors:
        assert "bad.gd" in issue.file


# --- Syntax error handling ---


def test_run_lint_syntax_error(tmp_path):
    """Test that a syntax error is reported as rule=SYNTAX_ERROR, severity=error."""
    (tmp_path / "broken.gd").write_text("extends Node\n\nfunc ():\n    pass\n")
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 1
    assert len(result.errors) == 1
    issue = result.errors[0]
    assert issue.rule == "SYNTAX_ERROR"
    assert issue.severity == "error"
    assert issue.line == 3
    assert issue.column == 6
    assert "broken.gd" in issue.file


def test_run_lint_syntax_error_continues(tmp_path):
    """Test that a syntax error does not crash — other files are still linted."""
    (tmp_path / "broken.gd").write_text("extends Node\n\nfunc ():\n    pass\n")
    (tmp_path / "bad.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    (tmp_path / "clean.gd").write_text("extends Node\n")
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert result.files_checked == 3
    # Should have the syntax error plus the function-name error
    assert len(result.errors) >= 2
    rules = [issue.rule for issue in result.errors]
    assert "SYNTAX_ERROR" in rules
    assert "function-name" in rules


def test_run_lint_syntax_error_counts_as_error(tmp_path):
    """Test that syntax errors are in the errors list (would cause exit code 1)."""
    (tmp_path / "broken.gd").write_text("extends Node\n\nfunc ():\n    pass\n")
    config = GdToolsConfig()
    result = run_lint(config, str(tmp_path))
    assert len(result.errors) >= 1
    assert len(result.warnings) == 0


# --- format_lint_text ---


def test_format_lint_text_with_violations():
    """Test text output with violations contains table columns and values."""
    errors = [
        LintIssue("src/player.gd", 10, 1, "function-name", "Bad name", "error"),
    ]
    warnings = [
        LintIssue("src/enemy.gd", 5, 3, "some-rule", "Warning msg", "warning"),
    ]
    result = LintResult(files_checked=2, errors=errors, warnings=warnings)
    output = format_lint_text(result)
    assert "File" in output
    assert "Line" in output
    assert "Column" in output
    assert "Rule" in output
    assert "Severity" in output
    assert "Message" in output
    assert "src/player.gd" in output
    assert "10" in output
    assert "function-name" in output
    assert "Bad name" in output
    assert "src/enemy.gd" in output
    assert "some-rule" in output
    assert "Warning msg" in output


def test_format_lint_text_color_coding():
    """Test that errors are red and warnings are yellow (ANSI codes present)."""
    errors = [LintIssue("a.gd", 1, 1, "R", "msg", "error")]
    warnings = [LintIssue("b.gd", 2, 1, "R", "msg", "warning")]
    result = LintResult(files_checked=2, errors=errors, warnings=warnings)
    output = format_lint_text(result)
    # ANSI escape codes should be present (colors are applied)
    assert "\x1b[" in output


def test_format_lint_text_summary():
    """Test that the summary line is present."""
    errors = [LintIssue("a.gd", 1, 1, "R", "msg", "error")]
    warnings = [LintIssue("b.gd", 2, 1, "R", "msg", "warning")]
    result = LintResult(files_checked=5, errors=errors, warnings=warnings)
    output = format_lint_text(result)
    assert "1 errors" in output
    assert "1 warnings" in output
    assert "5 files checked" in output


def test_format_lint_text_clean():
    """Test clean files output (success message)."""
    result = LintResult(files_checked=3, errors=[], warnings=[])
    output = format_lint_text(result)
    assert "[OK] No lint issues found." in output


def test_format_lint_text_no_files():
    """Test no .gd files output (informational message)."""
    result = LintResult(files_checked=0, errors=[], warnings=[])
    output = format_lint_text(result)
    assert "No GDScript files found." in output
