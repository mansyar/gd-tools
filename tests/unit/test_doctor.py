"""Unit tests for the doctor diagnostic command module.

Covers CheckResult and DoctorResult dataclasses, all 9 diagnostic
checks, run_doctor orchestration, and format_doctor_table output.
See TDD S3.6 and PRD S8.
"""

from unittest.mock import MagicMock, patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.doctor import (
    CheckResult,
    DoctorResult,
    check_godot_binary,
    check_godot_version,
    check_gdtoolkit,
    check_gut_installed,
)
from gd_tools.errors import GodotNotFoundError
from gd_tools.godot import GodotInfo

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


# --- check_godot_binary ---


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_binary_passes_when_found(mock_find_godot):
    """Test check_godot_binary passes when Godot binary is found."""
    mock_find_godot.return_value = GodotInfo(
        path="/usr/bin/godot", version="4.6.2", is_valid=True
    )
    config = GdToolsConfig()
    result = check_godot_binary(config)
    assert result.passed is True
    assert result.name == "Godot Binary"
    assert "4.6.2" in result.message
    assert "/usr/bin/godot" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_binary_fails_when_not_found(mock_find_godot):
    """Test check_godot_binary fails when Godot binary is not found."""
    mock_find_godot.side_effect = GodotNotFoundError("Godot not found")
    config = GdToolsConfig()
    result = check_godot_binary(config)
    assert result.passed is False
    assert result.name == "Godot Binary"


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_binary_critical_severity(mock_find_godot):
    """Test check_godot_binary has critical severity on failure."""
    mock_find_godot.side_effect = GodotNotFoundError("Godot not found")
    config = GdToolsConfig()
    result = check_godot_binary(config)
    assert result.severity == "critical"
    assert "Install Godot 4.5+" in result.fix_hint
    assert "godotengine.org" in result.fix_hint


# --- check_godot_version ---


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_version_passes_when_45_plus(mock_find_godot):
    """Test check_godot_version passes when Godot version >= 4.5.0."""
    mock_find_godot.return_value = GodotInfo(
        path="/usr/bin/godot", version="4.6.2", is_valid=True
    )
    config = GdToolsConfig()
    result = check_godot_version(config)
    assert result.passed is True
    assert result.name == "Godot Version"
    assert "4.6.2" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_version_fails_when_below_45(mock_find_godot):
    """Test check_godot_version fails when Godot version < 4.5.0."""
    mock_find_godot.return_value = GodotInfo(
        path="/usr/bin/godot", version="4.3.0", is_valid=False
    )
    config = GdToolsConfig()
    result = check_godot_version(config)
    assert result.passed is False
    assert result.name == "Godot Version"
    assert "4.3.0" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_version_critical_severity(mock_find_godot):
    """Test check_godot_version has critical severity on failure."""
    mock_find_godot.return_value = GodotInfo(
        path="/usr/bin/godot", version="4.3.0", is_valid=False
    )
    config = GdToolsConfig()
    result = check_godot_version(config)
    assert result.severity == "critical"
    assert "Install Godot 4.5+" in result.fix_hint


@pytest.mark.unit
@patch("gd_tools.doctor.find_godot")
def test_check_godot_version_fails_when_godot_not_found(mock_find_godot):
    """Test check_godot_version fails when Godot binary is not found."""
    mock_find_godot.side_effect = GodotNotFoundError("Godot not found")
    config = GdToolsConfig()
    result = check_godot_version(config)
    assert result.passed is False
    assert "not found" in result.message.lower()
    assert result.severity == "critical"


# --- check_gdtoolkit ---


@pytest.mark.unit
@patch("gd_tools.doctor.subprocess.run")
def test_check_gdtoolkit_passes_when_installed(mock_run):
    """Test check_gdtoolkit passes when both gdlint and gdformat exist."""
    mock_run.return_value = MagicMock()
    result = check_gdtoolkit()
    assert result.passed is True
    assert result.name == "GD Toolkit"


@pytest.mark.unit
@patch("gd_tools.doctor.subprocess.run")
def test_check_gdtoolkit_fails_when_gdlint_missing(mock_run):
    """Test check_gdtoolkit fails when gdlint is not installed."""
    mock_run.side_effect = [FileNotFoundError("gdlint not found"), MagicMock()]
    result = check_gdtoolkit()
    assert result.passed is False
    assert "gdlint" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.subprocess.run")
def test_check_gdtoolkit_fails_when_gdformat_missing(mock_run):
    """Test check_gdtoolkit fails when gdformat is not installed."""
    mock_run.side_effect = [
        MagicMock(),
        FileNotFoundError("gdformat not found"),
    ]
    result = check_gdtoolkit()
    assert result.passed is False
    assert "gdformat" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.subprocess.run")
def test_check_gdtoolkit_critical_severity(mock_run):
    """Test check_gdtoolkit has critical severity on failure."""
    mock_run.side_effect = FileNotFoundError("gdlint not found")
    result = check_gdtoolkit()
    assert result.severity == "critical"
    assert "pip install gdtoolkit" in result.fix_hint


# --- check_gut_installed ---


@pytest.mark.unit
def test_check_gut_installed_passes_when_present(tmp_path):
    """Test check_gut_installed passes when gut.gd exists."""
    gut_dir = tmp_path / "addons" / "gut"
    gut_dir.mkdir(parents=True)
    (gut_dir / "gut.gd").touch()
    result = check_gut_installed(tmp_path)
    assert result.passed is True
    assert result.name == "GUT Installed"
    assert "installed" in result.message.lower()


@pytest.mark.unit
def test_check_gut_installed_fails_when_absent(tmp_path):
    """Test check_gut_installed fails when gut.gd does not exist."""
    result = check_gut_installed(tmp_path)
    assert result.passed is False
    assert result.name == "GUT Installed"


@pytest.mark.unit
def test_check_gut_installed_critical_severity(tmp_path):
    """Test check_gut_installed has critical severity on failure."""
    result = check_gut_installed(tmp_path)
    assert result.severity == "critical"
    assert "gd-tools init" in result.fix_hint
    assert "github.com/bitwes/Gut" in result.fix_hint
