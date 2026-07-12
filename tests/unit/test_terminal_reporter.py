"""Tests for the terminal reporter."""

from pathlib import Path

from gd_tools.coverage.plan_generator import read_plan_json
from gd_tools.coverage.reporter import read_coverage_json
from gd_tools.coverage.terminal_reporter import generate_terminal_report

import pytest

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PLAN_FIXTURE = _FIXTURES_DIR / "coverage_plans" / "test_plan.json"
_FULL_COV = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
_PARTIAL_COV = _FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
_ZERO_COV = _FIXTURES_DIR / "coverage_data" / "zero_coverage.json"


def test_terminal_report_returns_string():
    """generate_terminal_report returns a non-empty string."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_terminal_report(plan, data)
    assert isinstance(result, str)
    assert len(result) > 0


def test_terminal_report_contains_table_columns():
    """Output contains all required column headers."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_terminal_report(plan, data)
    assert "File" in result
    assert "Lines Found" in result
    assert "Lines Hit" in result
    assert "Line %" in result
    assert "Branches Found" in result
    assert "Branches Hit" in result
    assert "Branch %" in result


def test_terminal_report_contains_overall_summary():
    """Output contains overall summary at the bottom."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_terminal_report(plan, data)
    # Full coverage = 100.0% line rate, 100.0% branch rate
    assert "100.0%" in result


def test_terminal_report_includes_zero_coverage_files():
    """Zero-coverage files appear in the table with 0% metrics."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    result = generate_terminal_report(plan, data)
    assert "res://player.gd" in result
    assert "res://enemy.gd" in result
    assert "0.0%" in result


def test_terminal_report_includes_all_files():
    """Output includes all files from the plan."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_terminal_report(plan, data)
    assert "res://player.gd" in result
    assert "res://enemy.gd" in result


def test_terminal_report_color_coding_green():
    """Green color markers present for >=80% coverage (full coverage)."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_terminal_report(plan, data)
    # ANSI green: \x1b[32m
    assert "\x1b[32m" in result


def test_terminal_report_color_coding_yellow():
    """Yellow color markers present for 50-79% coverage (partial)."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    result = generate_terminal_report(plan, data)
    # ANSI yellow: \x1b[33m
    # File 0 line rate = 60% (yellow), file 1 line rate = 66.7% (yellow)
    assert "\x1b[33m" in result


def test_terminal_report_color_coding_red():
    """Red color markers present for <50% coverage (zero coverage)."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    result = generate_terminal_report(plan, data)
    # ANSI red: \x1b[31m
    assert "\x1b[31m" in result
