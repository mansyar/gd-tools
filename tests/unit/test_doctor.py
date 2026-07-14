"""Unit tests for the doctor diagnostic command module.

Covers CheckResult and DoctorResult dataclasses, all 9 diagnostic
checks, run_doctor orchestration, and format_doctor_table output.
See TDD S3.6 and PRD S8.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from gd_tools.config import GdToolsConfig
from gd_tools.doctor import (
    CheckResult,
    DoctorResult,
    check_godot_binary,
    check_godot_version,
    check_gdtoolkit,
    check_gut_installed,
    check_gut_version,
    check_coverage_addon,
    check_gutconfig,
    check_gd_tools_toml,
    check_autoload,
    run_doctor,
    format_doctor_table,
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


# --- check_gut_version ---


@pytest.mark.unit
@patch("gd_tools.doctor.get_gut_version_for_godot")
@patch("gd_tools.doctor.get_installed_gut_version")
def test_check_gut_version_passes_when_matches(
    mock_get_installed, mock_get_expected
):
    """Test check_gut_version passes when installed matches expected."""
    mock_get_installed.return_value = "9.5.0"
    mock_get_expected.return_value = "9.5.0"
    result = check_gut_version(Path("/fake"), "4.5.0")
    assert result.passed is True
    assert result.name == "GUT Version"
    assert "9.5.0" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.get_gut_version_for_godot")
@patch("gd_tools.doctor.get_installed_gut_version")
def test_check_gut_version_fails_as_warning_when_mismatch(
    mock_get_installed, mock_get_expected
):
    """Test check_gut_version fails as warning when version mismatch."""
    mock_get_installed.return_value = "9.4.0"
    mock_get_expected.return_value = "9.5.0"
    result = check_gut_version(Path("/fake"), "4.5.0")
    assert result.passed is False
    assert "9.4.0" in result.message
    assert "9.5.0" in result.message


@pytest.mark.unit
@patch("gd_tools.doctor.get_gut_version_for_godot")
@patch("gd_tools.doctor.get_installed_gut_version")
def test_check_gut_version_warning_severity(
    mock_get_installed, mock_get_expected
):
    """Test check_gut_version has warning severity on failure."""
    mock_get_installed.return_value = "9.4.0"
    mock_get_expected.return_value = "9.5.0"
    result = check_gut_version(Path("/fake"), "4.5.0")
    assert result.severity == "warning"


@pytest.mark.unit
@patch("gd_tools.doctor.get_gut_version_for_godot")
@patch("gd_tools.doctor.get_installed_gut_version")
def test_check_gut_version_passes_when_version_unknown(
    mock_get_installed, mock_get_expected
):
    """Test check_gut_version passes when installed version is unknown."""
    mock_get_installed.return_value = None
    mock_get_expected.return_value = "9.5.0"
    result = check_gut_version(Path("/fake"), "4.5.0")
    assert result.passed is True


# --- check_coverage_addon ---


@pytest.mark.unit
@patch("gd_tools.doctor.__version__", "0.3.0")
def test_check_coverage_addon_passes_when_all_files_present(tmp_path):
    """Test check_coverage_addon passes when all coverage files exist."""
    cov_dir = tmp_path / "addons" / "gd-tools-coverage"
    cov_dir.mkdir(parents=True)
    for fname in ("coverage.gd", "pre_run_hook.gd", "post_run_hook.gd"):
        (cov_dir / fname).touch()
    (cov_dir / "_version.txt").write_text("0.3.0\n")
    result = check_coverage_addon(tmp_path)
    assert result.passed is True
    assert result.name == "Coverage Addon"
    assert "installed" in result.message.lower()
    assert "0.3.0" in result.message


@pytest.mark.unit
def test_check_coverage_addon_fails_when_files_missing(tmp_path):
    """Test check_coverage_addon fails when some coverage files are missing."""
    cov_dir = tmp_path / "addons" / "gd-tools-coverage"
    cov_dir.mkdir(parents=True)
    (cov_dir / "coverage.gd").touch()
    result = check_coverage_addon(tmp_path)
    assert result.passed is False
    assert result.name == "Coverage Addon"
    assert "pre_run_hook.gd" in result.message
    assert "post_run_hook.gd" in result.message


@pytest.mark.unit
def test_check_coverage_addon_warning_severity(tmp_path):
    """Test check_coverage_addon has warning severity on failure."""
    result = check_coverage_addon(tmp_path)
    assert result.severity == "warning"
    assert "gd-tools init" in result.fix_hint


@pytest.mark.unit
@patch("gd_tools.doctor.__version__", "0.3.0")
def test_check_coverage_addon_warns_when_version_file_missing(tmp_path):
    """Test check_coverage_addon warns when addon files present but version file missing."""
    cov_dir = tmp_path / "addons" / "gd-tools-coverage"
    cov_dir.mkdir(parents=True)
    for fname in ("coverage.gd", "pre_run_hook.gd", "post_run_hook.gd"):
        (cov_dir / fname).touch()
    result = check_coverage_addon(tmp_path)
    assert result.passed is True
    assert result.severity == "warning"
    assert "version file missing" in result.message.lower()
    assert "gd-tools init" in result.fix_hint


@pytest.mark.unit
@patch("gd_tools.doctor.__version__", "0.3.0")
def test_check_coverage_addon_warns_when_stale(tmp_path):
    """Test check_coverage_addon warns with both versions when addon is stale."""
    cov_dir = tmp_path / "addons" / "gd-tools-coverage"
    cov_dir.mkdir(parents=True)
    for fname in ("coverage.gd", "pre_run_hook.gd", "post_run_hook.gd"):
        (cov_dir / fname).touch()
    (cov_dir / "_version.txt").write_text("0.2.0\n")
    result = check_coverage_addon(tmp_path)
    assert result.passed is True
    assert result.severity == "warning"
    assert "0.2.0" in result.message
    assert "0.3.0" in result.message
    assert "gd-tools init" in result.fix_hint


@pytest.mark.unit
@patch("gd_tools.doctor.__version__", "0.3.0")
def test_check_coverage_addon_warns_when_unparseable_version(tmp_path):
    """Test check_coverage_addon warns when addon version is unparseable."""
    cov_dir = tmp_path / "addons" / "gd-tools-coverage"
    cov_dir.mkdir(parents=True)
    for fname in ("coverage.gd", "pre_run_hook.gd", "post_run_hook.gd"):
        (cov_dir / fname).touch()
    (cov_dir / "_version.txt").write_text("not-a-version\n")
    result = check_coverage_addon(tmp_path)
    assert result.passed is True
    assert result.severity == "warning"
    assert "not-a-version" in result.message
    assert "0.3.0" in result.message
    assert "gd-tools init" in result.fix_hint


# --- check_gutconfig ---


@pytest.mark.unit
def test_check_gutconfig_passes_when_valid_with_hooks(tmp_path):
    """Test check_gutconfig passes when .gutconfig.json is valid with hooks."""
    gutconfig = tmp_path / ".gutconfig.json"
    gutconfig.write_text(
        '{"pre_run_script": "res://addons/gd-tools-coverage/'
        'pre_run_hook.gd", '
        '"post_run_script": "res://addons/gd-tools-coverage/'
        'post_run_hook.gd"}'
    )
    result = check_gutconfig(tmp_path)
    assert result.passed is True
    assert result.name == "GUT Config"
    assert "valid" in result.message.lower()


@pytest.mark.unit
def test_check_gutconfig_fails_when_missing(tmp_path):
    """Test check_gutconfig fails when .gutconfig.json does not exist."""
    result = check_gutconfig(tmp_path)
    assert result.passed is False
    assert result.name == "GUT Config"
    assert "not found" in result.message.lower()


@pytest.mark.unit
def test_check_gutconfig_fails_when_invalid_json(tmp_path):
    """Test check_gutconfig fails when .gutconfig.json is invalid JSON."""
    gutconfig = tmp_path / ".gutconfig.json"
    gutconfig.write_text("{invalid json content")
    result = check_gutconfig(tmp_path)
    assert result.passed is False
    assert (
        "invalid" in result.message.lower() or "parse" in result.message.lower()
    )


@pytest.mark.unit
def test_check_gutconfig_fails_when_no_hook_paths(tmp_path):
    """Test check_gutconfig fails when pre/post run script keys are missing."""
    gutconfig = tmp_path / ".gutconfig.json"
    gutconfig.write_text('{"some_other_key": "value"}')
    result = check_gutconfig(tmp_path)
    assert result.passed is False
    assert (
        "pre_run_script" in result.message
        or "post_run_script" in result.message
    )


@pytest.mark.unit
def test_check_gutconfig_warning_severity(tmp_path):
    """Test check_gutconfig has warning severity on failure."""
    result = check_gutconfig(tmp_path)
    assert result.severity == "warning"
    assert "gd-tools init" in result.fix_hint


# --- check_gd_tools_toml ---


@pytest.mark.unit
def test_check_gd_tools_toml_passes_when_valid(tmp_path):
    """Test check_gd_tools_toml passes when gd-tools.toml is valid TOML."""
    toml_file = tmp_path / "gd-tools.toml"
    toml_file.write_text('[godot]\nbinary = "/usr/bin/godot"\n')
    result = check_gd_tools_toml(tmp_path)
    assert result.passed is True
    assert "gd-tools.toml" in result.message


@pytest.mark.unit
def test_check_gd_tools_toml_fails_when_missing(tmp_path):
    """Test check_gd_tools_toml fails when gd-tools.toml does not exist."""
    result = check_gd_tools_toml(tmp_path)
    assert result.passed is False
    assert "not found" in result.message.lower()
    assert "gd-tools init" in result.fix_hint


@pytest.mark.unit
def test_check_gd_tools_toml_fails_when_invalid_toml(tmp_path):
    """Test check_gd_tools_toml fails when gd-tools.toml is invalid TOML."""
    toml_file = tmp_path / "gd-tools.toml"
    toml_file.write_text("this is = = not valid toml [[")
    result = check_gd_tools_toml(tmp_path)
    assert result.passed is False
    assert "invalid" in result.message.lower()


@pytest.mark.unit
def test_check_gd_tools_toml_critical_severity(tmp_path):
    """Test check_gd_tools_toml has critical severity on failure."""
    result = check_gd_tools_toml(tmp_path)
    assert result.severity == "critical"


# --- check_autoload ---


@pytest.mark.unit
def test_check_autoload_passes_when_registered(tmp_path):
    """Test check_autoload passes when _GDTCoverage is in [autoload]."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text(
        "[autoload]\n\n"
        '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"\n'
    )
    result = check_autoload(tmp_path)
    assert result.passed is True
    assert "_GDTCoverage" in result.message


@pytest.mark.unit
def test_check_autoload_fails_when_not_registered(tmp_path):
    """Test check_autoload fails when _GDTCoverage is not in [autoload]."""
    project_godot = tmp_path / "project.godot"
    project_godot.write_text('[autoload]\n\nSomeOther="*res://other.gd"\n')
    result = check_autoload(tmp_path)
    assert result.passed is False
    assert "_GDTCoverage" in result.message
    assert "gd-tools init" in result.fix_hint


@pytest.mark.unit
def test_check_autoload_fails_when_no_project_godot(tmp_path):
    """Test check_autoload fails when project.godot does not exist."""
    result = check_autoload(tmp_path)
    assert result.passed is False
    assert "project.godot" in result.message.lower()


@pytest.mark.unit
def test_check_autoload_critical_severity(tmp_path):
    """Test check_autoload has critical severity on failure."""
    result = check_autoload(tmp_path)
    assert result.severity == "critical"


# --- run_doctor ---


@pytest.fixture
def _mock_doctor_deps():
    """Mock all doctor dependencies for run_doctor tests.

    By default, all checks pass and Godot is found at version 4.6.2.
    Individual tests can override specific mocks via the returned dict.
    """
    with (
        patch("gd_tools.doctor.find_project_root") as mock_root,
        patch("gd_tools.doctor.load_config") as mock_config,
        patch("gd_tools.doctor.find_godot") as mock_godot,
        patch("gd_tools.doctor.check_godot_binary") as mock_bin,
        patch("gd_tools.doctor.check_godot_version") as mock_ver,
        patch("gd_tools.doctor.check_gut_installed") as mock_gut_inst,
        patch("gd_tools.doctor.check_gut_version") as mock_gut_ver,
        patch("gd_tools.doctor.check_coverage_addon") as mock_cov,
        patch("gd_tools.doctor.check_gutconfig") as mock_gutconfig,
        patch("gd_tools.doctor.check_gd_tools_toml") as mock_toml,
        patch("gd_tools.doctor.check_gdtoolkit") as mock_gdtoolkit,
        patch("gd_tools.doctor.check_autoload") as mock_autoload,
    ):
        mock_root.return_value = Path("/fake/project")
        mock_config.return_value = GdToolsConfig()
        mock_godot.return_value = GodotInfo(
            path="/usr/bin/godot", version="4.6.2", is_valid=True
        )

        pass_result = CheckResult(name="test", passed=True, message="OK")
        mock_bin.return_value = pass_result
        mock_ver.return_value = pass_result
        mock_gut_inst.return_value = pass_result
        mock_gut_ver.return_value = pass_result
        mock_cov.return_value = pass_result
        mock_gutconfig.return_value = pass_result
        mock_toml.return_value = pass_result
        mock_gdtoolkit.return_value = pass_result
        mock_autoload.return_value = pass_result

        yield {
            "root": mock_root,
            "config": mock_config,
            "godot": mock_godot,
            "binary": mock_bin,
            "version": mock_ver,
            "gut_inst": mock_gut_inst,
            "gut_ver": mock_gut_ver,
            "cov": mock_cov,
            "gutconfig": mock_gutconfig,
            "toml": mock_toml,
            "gdtoolkit": mock_gdtoolkit,
            "autoload": mock_autoload,
        }


@pytest.mark.unit
def test_run_doctor_returns_doctor_result(_mock_doctor_deps):
    """Test run_doctor returns a DoctorResult instance."""
    result = run_doctor()
    assert isinstance(result, DoctorResult)


@pytest.mark.unit
def test_run_doctor_runs_all_9_checks(_mock_doctor_deps):
    """Test run_doctor runs exactly 9 checks."""
    result = run_doctor()
    assert len(result.checks) == 9


@pytest.mark.unit
def test_run_doctor_all_passed_when_no_failures(_mock_doctor_deps):
    """Test all_passed is True when every check passes."""
    result = run_doctor()
    assert result.all_passed is True
    assert all(c.passed for c in result.checks)


@pytest.mark.unit
def test_run_doctor_all_passed_false_when_any_fails(_mock_doctor_deps):
    """Test all_passed is False when any check fails."""
    _mock_doctor_deps["binary"].return_value = CheckResult(
        name="Godot Binary",
        passed=False,
        message="Not found",
        severity="critical",
    )
    result = run_doctor()
    assert result.all_passed is False
    assert any(not c.passed for c in result.checks)


@pytest.mark.unit
def test_run_doctor_never_raises_on_check_exception(_mock_doctor_deps):
    """Test run_doctor catches exceptions and converts to failed CheckResult."""
    _mock_doctor_deps["binary"].side_effect = RuntimeError("boom")
    result = run_doctor()
    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 9
    failed = [c for c in result.checks if not c.passed]
    assert len(failed) == 1
    assert "boom" in failed[0].message
    assert result.all_passed is False


@pytest.mark.unit
def test_run_doctor_handles_project_root_not_found(_mock_doctor_deps):
    """Test run_doctor falls back to cwd when project root not found."""
    from gd_tools.errors import ConfigError

    _mock_doctor_deps["root"].side_effect = ConfigError("not found")
    result = run_doctor()
    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 9


@pytest.mark.unit
def test_run_doctor_handles_config_load_failure(_mock_doctor_deps):
    """Test run_doctor uses default config when load_config fails."""
    from gd_tools.errors import ConfigError

    _mock_doctor_deps["config"].side_effect = ConfigError("bad config")
    result = run_doctor()
    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 9


@pytest.mark.unit
def test_run_doctor_handles_godot_not_found_for_version(_mock_doctor_deps):
    """Test run_doctor passes 'unknown' version when Godot not found."""
    _mock_doctor_deps["godot"].side_effect = GodotNotFoundError("no godot")
    result = run_doctor()
    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 9


# --- format_doctor_table ---


def _render_table(table):
    """Render a rich Table to string for testing."""
    console = Console(width=120)
    with console.capture() as capture:
        console.print(table)
    return capture.get()


@pytest.mark.unit
def test_format_doctor_table_has_4_columns():
    """Test format_doctor_table creates a table with 4 columns."""
    result = DoctorResult(checks=[], all_passed=True)
    table = format_doctor_table(result)
    assert len(table.columns) == 4


@pytest.mark.unit
def test_format_doctor_table_shows_checkmark_for_pass():
    """Test format_doctor_table shows checkmark for passing checks."""
    result = DoctorResult(
        checks=[
            CheckResult(name="Test Check", passed=True, message="All good"),
        ],
        all_passed=True,
    )
    table = format_doctor_table(result)
    output = _render_table(table)
    assert "\u2713" in output


@pytest.mark.unit
def test_format_doctor_table_shows_x_for_critical_fail():
    """Test format_doctor_table shows X for critical failures."""
    result = DoctorResult(
        checks=[
            CheckResult(
                name="Test Check",
                passed=False,
                message="Failed",
                severity="critical",
            ),
        ],
        all_passed=False,
    )
    table = format_doctor_table(result)
    output = _render_table(table)
    assert "\u2717" in output


@pytest.mark.unit
def test_format_doctor_table_shows_warning_for_warning_fail():
    """Test format_doctor_table shows warning symbol for warning failures."""
    result = DoctorResult(
        checks=[
            CheckResult(
                name="Test Check",
                passed=False,
                message="Warning issue",
                severity="warning",
            ),
        ],
        all_passed=False,
    )
    table = format_doctor_table(result)
    output = _render_table(table)
    assert "\u26a0" in output


@pytest.mark.unit
def test_format_doctor_table_includes_fix_hints():
    """Test format_doctor_table includes fix hints for failures."""
    result = DoctorResult(
        checks=[
            CheckResult(
                name="Test Check",
                passed=False,
                message="Failed",
                fix_hint="Run this command to fix",
                severity="critical",
            ),
        ],
        all_passed=False,
    )
    table = format_doctor_table(result)
    output = _render_table(table)
    assert "Run this command to fix" in output


@pytest.mark.unit
def test_format_doctor_table_shows_summary_line():
    """Test format_doctor_table shows X/9 checks passed summary."""
    checks = [
        CheckResult(name=f"Check {i}", passed=True, message="OK")
        for i in range(9)
    ]
    result = DoctorResult(checks=checks, all_passed=True)
    table = format_doctor_table(result)
    output = _render_table(table)
    assert "9/9" in output
    assert "passed" in output.lower()
