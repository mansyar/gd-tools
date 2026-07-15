"""Unit tests for the shared output module.

Tests the rendering helpers (print_success, print_error, print_warning,
print_info, print_summary, print_table) and the shared Console instance
for consistent terminal detection behavior.
"""

import pytest
from rich.console import Console
from rich.table import Table

from gd_tools.output import (
    console,
    print_error,
    print_info,
    print_success,
    print_summary,
    print_table,
    print_warning,
)

pytestmark = pytest.mark.unit


# --- print_success ---


def test_print_success_contains_ok_marker(capsys):
    """print_success() renders [OK] marker and the message."""
    print_success("All good")
    captured = capsys.readouterr()
    assert "[OK]" in captured.out
    assert "All good" in captured.out


def test_print_success_green_color(capsys, monkeypatch):
    """print_success() renders in green (ANSI codes present when forced)."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_success("All good")
    captured = capsys.readouterr()
    assert "\x1b[32" in captured.out  # green


# --- print_error ---


def test_print_error_contains_fail_marker(capsys):
    """print_error() renders [FAIL] marker and the message."""
    print_error("Something broke")
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.out
    assert "Something broke" in captured.out


def test_print_error_red_color(capsys, monkeypatch):
    """print_error() renders in red (ANSI codes present when forced)."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_error("Something broke")
    captured = capsys.readouterr()
    assert "\x1b[31" in captured.out  # red


# --- print_warning ---


def test_print_warning_contains_message(capsys):
    """print_warning() renders the message."""
    print_warning("Heads up")
    captured = capsys.readouterr()
    assert "Heads up" in captured.out


def test_print_warning_yellow_color(capsys, monkeypatch):
    """print_warning() renders in yellow (ANSI codes present when forced)."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_warning("Heads up")
    captured = capsys.readouterr()
    assert "\x1b[33" in captured.out  # yellow


# --- print_info ---


def test_print_info_contains_message(capsys):
    """print_info() renders the message."""
    print_info("FYI")
    captured = capsys.readouterr()
    assert "FYI" in captured.out


def test_print_info_cyan_color(capsys, monkeypatch):
    """print_info() renders in cyan (ANSI codes present when forced)."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_info("FYI")
    captured = capsys.readouterr()
    assert "\x1b[36" in captured.out  # cyan


# --- print_summary ---


def test_print_summary_contains_counts(capsys):
    """print_summary() renders the counts string and files_checked."""
    print_summary("fail", "3 errors, 2 warnings", 5)
    captured = capsys.readouterr()
    assert "3 errors, 2 warnings" in captured.out
    assert "5 files checked" in captured.out


def test_print_summary_pass_green(capsys, monkeypatch):
    """print_summary() with status='pass' renders in green."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_summary("pass", "5 passed", 5)
    captured = capsys.readouterr()
    assert "\x1b[32" in captured.out  # green


def test_print_summary_fail_red(capsys, monkeypatch):
    """print_summary() with status='fail' renders in red."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_summary("fail", "3 errors", 5)
    captured = capsys.readouterr()
    assert "\x1b[31" in captured.out  # red


def test_print_summary_warning_yellow(capsys, monkeypatch):
    """print_summary() with status='warning' renders in yellow."""
    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    print_summary("warning", "2 warnings", 3)
    captured = capsys.readouterr()
    assert "\x1b[33" in captured.out  # yellow


def test_print_summary_extra_info(capsys):
    """print_summary() includes extra_info when provided."""
    print_summary("pass", "5 passed", 5, extra_info="duration: 1.2s")
    captured = capsys.readouterr()
    assert "duration: 1.2s" in captured.out


def test_print_summary_no_files_checked_omitted(capsys):
    """print_summary() omits 'files checked' when files_checked is 0."""
    print_summary("pass", "All done", 0)
    captured = capsys.readouterr()
    assert "All done" in captured.out
    assert "files checked" not in captured.out


# --- print_table ---


def test_print_table_renders_table(capsys):
    """print_table() renders a Rich Table via the shared console."""
    table = Table(title="Test Table")
    table.add_column("Name")
    table.add_row("Alice")
    print_table(table)
    captured = capsys.readouterr()
    assert "Alice" in captured.out
    assert "Name" in captured.out


# --- Shared Console instance ---


def test_console_is_rich_console():
    """The shared console instance is a rich.console.Console."""
    assert isinstance(console, Console)


def test_console_no_ansi_when_piped(capsys):
    """The shared console does not emit ANSI codes when stdout is piped."""
    print_info("test message")
    captured = capsys.readouterr()
    assert "\x1b[" not in captured.out  # no ANSI escape codes
