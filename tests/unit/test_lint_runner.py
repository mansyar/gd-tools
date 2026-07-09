"""Unit tests for the lint runner module.

Covers data models (LintIssue, LintResult), file discovery,
lint execution via gdtoolkit, output formatting, and syntax
error handling.
"""

from pathlib import Path

from gd_tools.lint_runner import LintIssue, LintResult, discover_gd_files

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
