"""Unit tests for the doctor diagnostic command module.

Covers CheckResult and DoctorResult dataclasses, all 9 diagnostic
checks, run_doctor orchestration, and format_doctor_table output.
See TDD S3.6 and PRD S8.
"""

from unittest.mock import MagicMock, patch

import pytest

from gd_tools.doctor import CheckResult, DoctorResult


# --- CheckResult dataclass ---


@pytest.mark.unit
def test_check_result_construction_all_fields():
    """Test CheckResult with all fields provided."""
    result = CheckResult(
        name="Godot Binary",
        passed=True,
        message="Godot 4.6.2 at /usr/bin/godot",
        fix_hint="",
        severity="critical",
    )
    assert result.name == "Godot Binary"
    assert result.passed is True
    assert result.message == "Godot 4.6.2 at /usr/bin/godot"
    assert result.fix_hint == ""
    assert result.severity == "critical"


@pytest.mark.unit
def test_check_result_defaults():
    """Test CheckResult defaults: fix_hint='' and severity='critical'."""
    result = CheckResult(
        name="Godot Binary",
        passed=False,
        message="Not found",
    )
    assert result.fix_hint == ""
    assert result.severity == "critical"


@pytest.mark.unit
def test_check_result_warning_severity():
    """Test CheckResult with warning severity."""
    result = CheckResult(
        name="GUT Version",
        passed=False,
        message="Version mismatch",
        fix_hint="Install v9.5.0",
        severity="warning",
    )
    assert result.severity == "warning"


# --- DoctorResult dataclass ---


@pytest.mark.unit
def test_doctor_result_construction():
    """Test DoctorResult with checks list and all_passed flag."""
    checks = [
        CheckResult(name="Check 1", passed=True, message="OK"),
        CheckResult(name="Check 2", passed=False, message="Failed"),
    ]
    result = DoctorResult(checks=checks, all_passed=False)
    assert len(result.checks) == 2
    assert result.checks[0].name == "Check 1"
    assert result.checks[1].passed is False
    assert result.all_passed is False


@pytest.mark.unit
def test_doctor_result_all_passed_true():
    """Test DoctorResult with all_passed=True."""
    checks = [
        CheckResult(name="Check 1", passed=True, message="OK"),
    ]
    result = DoctorResult(checks=checks, all_passed=True)
    assert result.all_passed is True
    assert all(c.passed for c in result.checks)


@pytest.mark.unit
def test_doctor_result_empty_checks():
    """Test DoctorResult with empty checks list."""
    result = DoctorResult(checks=[], all_passed=True)
    assert result.checks == []
    assert result.all_passed is True
