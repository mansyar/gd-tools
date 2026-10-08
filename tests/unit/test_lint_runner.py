"""Unit tests for the lint runner module.

Covers data models (LintIssue, LintResult), lint execution
via gdtoolkit, output formatting, and syntax error handling.
"""

import json

import pytest
from rich.console import Console

from gd_tools.config import GdToolsConfig
from gd_tools.lint_runner import (
    LintIssue,
    LintResult,
    format_lint_github_actions,
    format_lint_json,
    format_lint_text,
    load_gdlint_config,
    run_lint,
)
from gdtoolkit.linter import DEFAULT_CONFIG

pytestmark = pytest.mark.unit

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


# --- run_lint core logic ---


def test_run_lint_clean_files(tmp_path):
    """Test run_lint with clean .gd files (no errors, no warnings)."""
    (tmp_path / "clean.gd").write_text("extends Node\n")
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
    assert result.files_checked == 1
    assert result.errors == []
    assert result.warnings == []


def test_run_lint_with_errors(tmp_path):
    """Test run_lint with files that have lint errors."""
    (tmp_path / "bad.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
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
    result = run_lint(config, [str(tmp_path)])
    assert result.warnings == []


def test_run_lint_respects_excludes(tmp_path):
    """Test that run_lint respects config excludes."""
    (tmp_path / "main.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text(
        "extends Node\n\nfunc BadFunctionName():\n    pass\n"
    )
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
    assert result.files_checked == 1
    assert result.errors == []


def test_run_lint_no_gd_files(tmp_path):
    """Test run_lint with no .gd files in the path."""
    (tmp_path / "readme.txt").write_text("hello\n")
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
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
    result = run_lint(config, [str(tmp_path)])
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
    result = run_lint(config, [str(tmp_path)])
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
    result = run_lint(config, [str(tmp_path)])
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
    result = run_lint(config, [str(tmp_path)])
    assert len(result.errors) >= 1
    assert len(result.warnings) == 0


# --- format_lint_text ---


def test_format_lint_text_with_violations(capsys):
    """Test text output with violations in flat file:line:col: format."""
    errors = [
        LintIssue("src/player.gd", 10, 1, "function-name", "Bad name", "error"),
    ]
    warnings = [
        LintIssue("src/enemy.gd", 5, 3, "some-rule", "Warning msg", "warning"),
    ]
    result = LintResult(files_checked=2, errors=errors, warnings=warnings)
    format_lint_text(result)
    captured = capsys.readouterr()
    # Flat line format: file:line:col: rule: message  [SEVERITY]
    assert "src/player.gd:10:1:" in captured.out
    assert "function-name" in captured.out
    assert "Bad name" in captured.out
    assert "[ERROR]" in captured.out
    assert "src/enemy.gd:5:3:" in captured.out
    assert "some-rule" in captured.out
    assert "Warning msg" in captured.out
    assert "[WARN]" in captured.out


def test_format_lint_text_color_coding(capsys, monkeypatch):
    """Test that errors are red and warnings are yellow (ANSI codes present)."""
    monkeypatch.setattr(
        "gd_tools.output.console",
        Console(force_terminal=True),
    )
    errors = [LintIssue("a.gd", 1, 1, "R", "msg", "error")]
    warnings = [LintIssue("b.gd", 2, 1, "R", "msg", "warning")]
    result = LintResult(files_checked=2, errors=errors, warnings=warnings)
    format_lint_text(result)
    captured = capsys.readouterr()
    # ANSI escape codes should be present (colors are applied)
    assert "\x1b[" in captured.out


def test_format_lint_text_summary(capsys, monkeypatch):
    """Test that the summary line is present and colored by severity."""
    errors = [LintIssue("a.gd", 1, 1, "R", "msg", "error")]
    warnings = [LintIssue("b.gd", 2, 1, "R", "msg", "warning")]
    result = LintResult(files_checked=5, errors=errors, warnings=warnings)
    format_lint_text(result)
    captured = capsys.readouterr()
    assert "1 errors" in captured.out
    assert "1 warnings" in captured.out
    assert "5 files checked" in captured.out

    # Force terminal to verify color coding
    monkeypatch.setattr(
        "gd_tools.output.console",
        Console(force_terminal=True),
    )
    # Errors present → red summary
    format_lint_text(result)
    captured = capsys.readouterr()
    summary_line = captured.out.strip().splitlines()[-1]
    assert "\x1b[31" in summary_line  # red summary

    # Warnings only → yellow summary
    result_wo = LintResult(
        files_checked=1,
        errors=[],
        warnings=[LintIssue("b.gd", 2, 1, "R", "msg", "warning")],
    )
    format_lint_text(result_wo)
    captured_wo = capsys.readouterr()
    summary_line_wo = captured_wo.out.strip().splitlines()[-1]
    assert "\x1b[33" in summary_line_wo  # yellow summary


def test_format_lint_text_clean(capsys, monkeypatch):
    """Test clean files output (success message, green-colored)."""
    result = LintResult(files_checked=3, errors=[], warnings=[])
    format_lint_text(result)
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "No lint issues found." in captured.out

    # Force terminal to verify green coloring
    monkeypatch.setattr(
        "gd_tools.output.console",
        Console(force_terminal=True),
    )
    format_lint_text(result)
    captured = capsys.readouterr()
    assert "\x1b[32" in captured.out  # green


def test_format_lint_text_no_files(capsys):
    """Test no .gd files output (informational message)."""
    result = LintResult(files_checked=0, errors=[], warnings=[])
    format_lint_text(result)
    captured = capsys.readouterr()
    assert "No GDScript files found." in captured.out


def test_format_lint_text_long_paths_not_truncated(capsys):
    """Test that long file paths and rule names are not truncated."""
    long_path = (
        "src/very/deeply/nested/module/subsystem/components/"
        "PlayerCharacterController.gd"
    )
    long_rule = "class-name-underscore-prefix-violation-detailed-check"
    errors = [LintIssue(long_path, 10, 1, long_rule, "Some message", "error")]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    format_lint_text(result)
    captured = capsys.readouterr()
    assert long_path in captured.out
    assert long_rule in captured.out
    assert "…" not in captured.out  # No truncation


def test_format_lint_text_prints_directly(capsys):
    """Test that format_lint_text prints to stdout and returns None."""
    result = LintResult(files_checked=1, errors=[], warnings=[])
    ret = format_lint_text(result)
    assert ret is None
    captured = capsys.readouterr()
    assert len(captured.out) > 0


# --- format_lint_json ---


def test_format_lint_json_schema():
    """Test JSON output has files_checked, errors, warnings keys."""
    errors = [LintIssue("a.gd", 10, 1, "rule1", "msg1", "error")]
    warnings = [LintIssue("b.gd", 5, 3, "rule2", "msg2", "warning")]
    result = LintResult(files_checked=2, errors=errors, warnings=warnings)
    data = json.loads(format_lint_json(result))
    assert "files_checked" in data
    assert "errors" in data
    assert "warnings" in data
    assert data["files_checked"] == 2


def test_format_lint_json_issue_fields():
    """Test JSON serialization of LintIssue objects (all fields present)."""
    errors = [
        LintIssue("src/foo.gd", 10, 1, "function-name", "Bad name", "error")
    ]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    data = json.loads(format_lint_json(result))
    issue = data["errors"][0]
    assert issue["file"] == "src/foo.gd"
    assert issue["line"] == 10
    assert issue["column"] == 1
    assert issue["rule"] == "function-name"
    assert issue["message"] == "Bad name"
    assert issue["severity"] == "error"


def test_format_lint_json_no_violations():
    """Test JSON output with no violations (empty arrays, not null)."""
    result = LintResult(files_checked=0, errors=[], warnings=[])
    data = json.loads(format_lint_json(result))
    assert data["errors"] == []
    assert data["warnings"] == []
    assert data["files_checked"] == 0


# --- Multi-path support (FR-4) ---


def test_run_lint_multiple_paths_discovers_all(tmp_path):
    """Test run_lint discovers files across multiple paths."""
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "foo.gd").write_text("extends Node\n")
    (dir_b / "bar.gd").write_text("extends Node\n")

    config = GdToolsConfig()
    result = run_lint(config, [str(dir_a), str(dir_b)])
    assert result.files_checked == 2


def test_run_lint_multiple_paths_deduplicates(tmp_path):
    """Test run_lint deduplicates files discovered via overlapping paths."""
    (tmp_path / "foo.gd").write_text("extends Node\n")
    (tmp_path / "bar.gd").write_text("extends Node\n")

    config = GdToolsConfig()
    # Passing the same root twice should not double-count files
    result = run_lint(config, [str(tmp_path), str(tmp_path)])
    assert result.files_checked == 2


def test_run_lint_default_paths(tmp_path):
    """Test run_lint with None paths defaults to current directory."""
    config = GdToolsConfig()
    result = run_lint(config, None)
    assert isinstance(result, LintResult)


# --- Verbose mode: command display ---


def test_run_lint_verbose_shows_file_being_linted(tmp_path, capsys):
    """In verbose mode, run_lint prints the file being linted."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.VERBOSE)
    (tmp_path / "player.gd").write_text("extends Node\n")
    config = GdToolsConfig()

    run_lint(config, [str(tmp_path)])

    captured = capsys.readouterr()
    assert "player.gd" in captured.out


def test_run_lint_default_mode_no_file_info_shown(tmp_path, capsys):
    """In default mode, run_lint does not print the file being linted."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.DEFAULT)
    (tmp_path / "player.gd").write_text("extends Node\n")
    config = GdToolsConfig()

    run_lint(config, [str(tmp_path)])

    captured = capsys.readouterr()
    assert "Linting:" not in captured.out


# --- Verbose mode: timing display ---


def test_run_lint_verbose_shows_timing(tmp_path, capsys):
    """In verbose mode, run_lint prints elapsed time for the lint scan."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.VERBOSE)
    (tmp_path / "player.gd").write_text("extends Node\n")
    config = GdToolsConfig()

    run_lint(config, [str(tmp_path)])

    captured = capsys.readouterr()
    assert "Elapsed:" in captured.out


def test_run_lint_default_mode_no_timing_shown(tmp_path, capsys):
    """In default mode, run_lint does not print timing information."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.DEFAULT)
    (tmp_path / "player.gd").write_text("extends Node\n")
    config = GdToolsConfig()

    run_lint(config, [str(tmp_path)])

    captured = capsys.readouterr()
    assert "Elapsed:" not in captured.out


# --- Quiet mode: suppress info messages, keep results ---


def test_format_lint_text_no_files_quiet_suppressed(capsys):
    """In quiet mode, 'No GDScript files found.' info message is suppressed."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.QUIET)
    result = LintResult(files_checked=0, errors=[], warnings=[])
    format_lint_text(result)
    captured = capsys.readouterr()
    assert "No GDScript files found." not in captured.out


def test_format_lint_text_violations_render_when_quiet(capsys):
    """In quiet mode, lint violations still render (always shown)."""
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.QUIET)
    errors = [LintIssue("res://foo.gd", 10, 1, "RULE", "Some message", "error")]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    format_lint_text(result)
    captured = capsys.readouterr()
    assert "foo.gd" in captured.out
    assert "Some message" in captured.out


# --- format_lint_github_actions ---


def test_format_lint_github_actions_error_annotation():
    """Test error violations render as ::error workflow log commands."""
    errors = [
        LintIssue("src/foo.gd", 10, 1, "function-name", "Bad name", "error")
    ]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    out = format_lint_github_actions(result)
    assert out == (
        "::error file=src/foo.gd,line=10,col=1,"
        "title=function-name::Bad name\n"
    )


def test_format_lint_github_actions_warning_severity():
    """Test warning violations render as ::warning workflow log commands."""
    warnings = [
        LintIssue("src/foo.gd", 3, 7, "max-line-length", "Too long", "warning")
    ]
    result = LintResult(files_checked=1, errors=[], warnings=warnings)
    out = format_lint_github_actions(result)
    assert out == (
        "::warning file=src/foo.gd,line=3,col=7,"
        "title=max-line-length::Too long\n"
    )


def test_format_lint_github_actions_escapes_message():
    """Test message data escaping: %, CR, LF per the workflow log spec."""
    errors = [
        LintIssue("a.gd", 1, 1, "RULE", "50% done\r\nsecond line", "error")
    ]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    out = format_lint_github_actions(result)
    assert out == (
        "::error file=a.gd,line=1,col=1,title=RULE"
        "::50%25 done%0D%0Asecond line\n"
    )


def test_format_lint_github_actions_escapes_properties():
    """Test property-value escaping: % plus , and : in title and file."""
    errors = [
        LintIssue("src/a,b.gd", 2, 3, "rule, with: colon", "Message", "error")
    ]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    out = format_lint_github_actions(result)
    assert "file=src/a%2Cb.gd" in out
    assert "title=rule%2C with%3A colon" in out


def test_format_lint_github_actions_posix_paths():
    """Test file paths use POSIX separators in annotations."""
    errors = [LintIssue("src\\player.gd", 4, 1, "RULE", "Msg", "error")]
    result = LintResult(files_checked=1, errors=errors, warnings=[])
    out = format_lint_github_actions(result)
    assert "file=src/player.gd" in out
    assert "src\\player.gd" not in out


def test_format_lint_github_actions_sorted():
    """Test annotations are sorted by file, then line, then column."""
    errors = [
        LintIssue("b.gd", 1, 1, "R2", "msg2", "error"),
        LintIssue("a.gd", 5, 1, "R1", "msg1b", "error"),
        LintIssue("a.gd", 2, 1, "R0", "msg1a", "error"),
    ]
    result = LintResult(files_checked=3, errors=errors, warnings=[])
    out = format_lint_github_actions(result)
    lines = out.splitlines()
    assert len(lines) == 3
    assert "file=a.gd,line=2" in lines[0]
    assert "msg1a" in lines[0]
    assert "file=a.gd,line=5" in lines[1]
    assert "file=b.gd,line=1" in lines[2]


def test_format_lint_github_actions_no_issues():
    """Test no issues produces empty output (no annotations, no noise)."""
    result = LintResult(files_checked=3, errors=[], warnings=[])
    assert format_lint_github_actions(result) == ""


# --- gdlintrc config loading (R6) ---


_ORDER_VIOLATION = "extends Node\n\nvar later = 1\nconst EARLIER = 1\n"


def _rules(result):
    return [issue.rule for issue in result.errors]


def test_run_lint_without_gdlintrc_reports_class_definitions_order(tmp_path):
    """Baseline: with no gdlintrc the rule fires (disable is not ambient)."""
    (tmp_path / "order.gd").write_text(_ORDER_VIOLATION)
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
    assert "class-definitions-order" in _rules(result)


def test_run_lint_honors_gdlintrc_disable(tmp_path, monkeypatch):
    """A gdlintrc disable list is honored, matching bare gdlint."""
    (tmp_path / "gdlintrc").write_text(
        "disable:\n  - class-definitions-order\n", encoding="utf-8"
    )
    (tmp_path / "order.gd").write_text(_ORDER_VIOLATION)
    monkeypatch.chdir(tmp_path)
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
    assert "class-definitions-order" not in _rules(result)


def test_run_lint_honors_dot_gdlintrc_disable(tmp_path, monkeypatch):
    """The dotted .gdlintrc variant is discovered like bare gdlint does."""
    (tmp_path / ".gdlintrc").write_text(
        "disable:\n  - class-definitions-order\n", encoding="utf-8"
    )
    (tmp_path / "order.gd").write_text(_ORDER_VIOLATION)
    monkeypatch.chdir(tmp_path)
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)])
    assert "class-definitions-order" not in _rules(result)


def test_run_lint_explicit_lint_config_path(tmp_path):
    """An explicit config path is used regardless of discovery."""
    rc = tmp_path / "custom-lint-config.yaml"
    rc.write_text("disable:\n  - class-definitions-order\n", encoding="utf-8")
    project = tmp_path / "proj"
    project.mkdir()
    (project / "order.gd").write_text(_ORDER_VIOLATION)
    config = GdToolsConfig()
    result = run_lint(config, [str(project)], lint_config_path=str(rc))
    assert "class-definitions-order" not in _rules(result)


def test_run_lint_explicit_lint_config_path_beats_gdlintrc(
    tmp_path, monkeypatch
):
    """The explicit config path wins over a discovered gdlintrc."""
    (tmp_path / "gdlintrc").write_text("disable: []\n", encoding="utf-8")
    rc = tmp_path / "strict.yaml"
    rc.write_text("disable:\n  - class-definitions-order\n", encoding="utf-8")
    (tmp_path / "order.gd").write_text(_ORDER_VIOLATION)
    monkeypatch.chdir(tmp_path)
    config = GdToolsConfig()
    result = run_lint(config, [str(tmp_path)], lint_config_path=str(rc))
    assert "class-definitions-order" not in _rules(result)


def test_load_gdlint_config_defaults_when_absent(tmp_path):
    """A clean project root without a config yields gdtoolkit defaults.

    The search is bounded at the project root, so an ambient gdlintrc
    above it (e.g. a stray file in the temp directory) cannot leak in.
    """
    config = load_gdlint_config(project_root=tmp_path)
    assert dict(config) == dict(DEFAULT_CONFIG)


def test_load_gdlint_config_walks_up_from_cwd(tmp_path, monkeypatch):
    """Outside a Godot project, discovery walks up from the cwd."""
    (tmp_path / "gdlintrc").write_text(
        "disable:\n  - class-definitions-order\n", encoding="utf-8"
    )
    sub = tmp_path / "scripts"
    sub.mkdir()
    monkeypatch.chdir(sub)
    config = load_gdlint_config()
    assert config["disable"] == ["class-definitions-order"]


def test_load_gdlint_config_does_not_escape_project_root(tmp_path):
    """A config outside the project root does not govern the project."""
    (tmp_path / "gdlintrc").write_text(
        "disable:\n  - class-definitions-order\n", encoding="utf-8"
    )
    project = tmp_path / "project"
    project.mkdir()
    config = load_gdlint_config(project_root=project)
    assert dict(config) == dict(DEFAULT_CONFIG)


def test_load_gdlint_config_reads_dotted_variant(tmp_path):
    """Both gdlintrc and .gdlintrc names are accepted."""
    (tmp_path / ".gdlintrc").write_text(
        "disable:\n  - max-line-length\n", encoding="utf-8"
    )
    config = load_gdlint_config(project_root=tmp_path)
    assert config["disable"] == ["max-line-length"]


def test_load_gdlint_config_merges_missing_defaults(tmp_path):
    """Entries absent from the file are filled in from gdtoolkit defaults."""
    (tmp_path / "gdlintrc").write_text(
        "disable:\n  - class-definitions-order\n", encoding="utf-8"
    )
    config = load_gdlint_config(project_root=tmp_path)
    assert config["disable"] == ["class-definitions-order"]
    assert config["max-line-length"] == DEFAULT_CONFIG["max-line-length"]


def test_load_gdlint_config_explicit_path_beats_discovery(tmp_path):
    """An explicit config path is loaded even when a gdlintrc exists."""
    (tmp_path / "gdlintrc").write_text("disable: []\n", encoding="utf-8")
    rc = tmp_path / "strict.yaml"
    rc.write_text("disable:\n  - class-definitions-order\n", encoding="utf-8")
    config = load_gdlint_config(config_path=str(rc), project_root=tmp_path)
    assert config["disable"] == ["class-definitions-order"]
