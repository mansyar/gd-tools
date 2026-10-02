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
    check_editor_plugin,
    check_godot_binary,
    check_godot_version,
    check_gdtoolkit,
    check_native_test_addon,
    check_coverage_addon,
    check_gd_tools_toml,
    check_autoload,
    run_doctor,
    format_doctor_table,
)
from gd_tools.errors import GodotNotFoundError
from gd_tools.godot import GodotInfo
from gd_tools.init import NATIVE_TEST_ADDON_FILES

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


def test_check_native_test_addon_passes_when_files_exist(tmp_path):
    """Doctor detects the bundled native test runtime."""
    addon = tmp_path / "addons" / "gd-tools-test"
    addon.mkdir(parents=True)
    for name in NATIVE_TEST_ADDON_FILES:
        (addon / name).touch()

    result = check_native_test_addon(tmp_path)

    assert result.passed is True
    assert result.name == "Native Test Addon"


@patch("gd_tools.doctor.__version__", "0.3.0")
def test_check_native_test_addon_warns_when_stale(tmp_path):
    """Doctor reports an outdated native runtime without failing the project."""
    addon = tmp_path / "addons" / "gd-tools-test"
    addon.mkdir(parents=True)
    for name in NATIVE_TEST_ADDON_FILES:
        (addon / name).touch()
    (addon / "_version.txt").write_text("0.2.0\n", encoding="utf-8")

    result = check_native_test_addon(tmp_path)

    assert result.passed is True
    assert result.severity == "warning"
    assert "0.2.0" in result.message
    assert "0.3.0" in result.message
    assert "gd-tools init" in result.fix_hint


def test_check_native_test_addon_verifies_mock_module(tmp_path):
    """Doctor treats a missing mock module as a critical runtime gap."""
    addon = tmp_path / "addons" / "gd-tools-test"
    addon.mkdir(parents=True)
    for name in NATIVE_TEST_ADDON_FILES:
        (addon / name).touch()
    (addon / "gd_tools_mock.gd").unlink()

    result = check_native_test_addon(tmp_path)

    assert result.passed is False
    assert result.severity == "critical"
    assert "gd_tools_mock.gd" in result.message


def test_check_native_test_addon_requires_integration_files(tmp_path):
    """Doctor fails when the preflight and context scripts are missing."""
    addon = tmp_path / "addons" / "gd-tools-test"
    addon.mkdir(parents=True)
    for name in ("gd_tools_test.gd", "gd_tools_test_runner.gd"):
        (addon / name).touch()

    result = check_native_test_addon(tmp_path)

    assert result.passed is False
    assert result.severity == "critical"
    assert "gd_tools_test_preflight.gd" in result.message
    assert "gd_tools_test_context.gd" in result.message
    assert "gd-tools init" in result.fix_hint


@patch("gd_tools.doctor.__version__", "0.3.0")
def test_check_native_test_addon_passes_with_full_runtime(tmp_path):
    """Doctor passes when every managed native runtime file is deployed."""
    addon = tmp_path / "addons" / "gd-tools-test"
    addon.mkdir(parents=True)
    for name in NATIVE_TEST_ADDON_FILES:
        (addon / name).touch()
    (addon / "_version.txt").write_text("0.3.0\n", encoding="utf-8")

    result = check_native_test_addon(tmp_path)

    assert result.passed is True
    # The check must have inspected the deployment: it reports the version it
    # read and names no absent or outdated file, so an unconditional pass
    # cannot satisfy this test.
    assert "0.3.0" in result.message
    assert "missing" not in result.message.lower()
    assert "outdated" not in result.message.lower()


def test_check_native_test_addon_rejects_one_missing_runtime_file(tmp_path):
    """A single absent managed file is critical, not a warning."""
    addon = tmp_path / "addons" / "gd-tools-test"
    addon.mkdir(parents=True)
    for name in NATIVE_TEST_ADDON_FILES:
        (addon / name).touch()
    (addon / "gd_tools_test_context.gd").unlink()

    result = check_native_test_addon(tmp_path)

    assert result.passed is False
    assert result.severity == "critical"
    assert "gd_tools_test_context.gd" in result.message


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
        patch("gd_tools.doctor.check_native_test_addon") as mock_native_addon,
        patch("gd_tools.doctor.check_legacy_gut") as mock_legacy_gut,
        patch("gd_tools.doctor.check_coverage_addon") as mock_cov,
        patch("gd_tools.doctor.check_editor_plugin") as mock_editor_addon,
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
        mock_native_addon.return_value = pass_result
        mock_legacy_gut.return_value = pass_result
        mock_cov.return_value = pass_result
        mock_editor_addon.return_value = pass_result
        mock_toml.return_value = pass_result
        mock_gdtoolkit.return_value = pass_result
        mock_autoload.return_value = pass_result

        yield {
            "root": mock_root,
            "config": mock_config,
            "godot": mock_godot,
            "binary": mock_bin,
            "version": mock_ver,
            "native_addon": mock_native_addon,
            "legacy_gut": mock_legacy_gut,
            "cov": mock_cov,
            "editor_addon": mock_editor_addon,
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
def test_run_doctor_includes_legacy_gut_advisory(_mock_doctor_deps):
    """Doctor lists the legacy GUT advisory among its diagnostics."""
    _mock_doctor_deps["legacy_gut"].return_value = CheckResult(
        name="Legacy GUT", passed=True, message="No legacy GUT artifacts"
    )

    result = run_doctor()

    names = [c.name for c in result.checks]
    assert "Legacy GUT" in names
    _mock_doctor_deps["legacy_gut"].assert_called_once_with(
        Path("/fake/project"), GdToolsConfig().test.test_dirs
    )


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


def test_optional_missing_autoload_is_non_blocking(tmp_path):
    """Native mode does not fail doctor for the optional legacy autoload."""
    result = check_autoload(tmp_path, required=False)

    assert result.passed is True
    assert result.severity == "warning"


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


# --- check_editor_plugin ---


@pytest.mark.unit
def test_check_editor_plugin_missing_files(tmp_path: Path):
    """Doctor warns when the editor plugin addon is not deployed."""
    result = check_editor_plugin(tmp_path)

    assert result.name == "Editor Plugin"
    assert result.passed is False
    assert result.severity == "warning"
    assert "missing" in result.message.lower()
    assert "gd-tools init" in result.fix_hint


@pytest.mark.unit
def test_check_editor_plugin_current(tmp_path: Path):
    """Doctor reports the editor plugin as installed when current."""
    from gd_tools import __version__

    addon_dir = tmp_path / "addons" / "gd-tools-editor"
    addon_dir.mkdir(parents=True)
    for name in ("plugin.cfg", "plugin.gd", "dock.gd", "coverage_overlay.gd"):
        (addon_dir / name).write_text("# stub\n", encoding="utf-8")
    (addon_dir / "_version.txt").write_text(
        f"{__version__}\n", encoding="utf-8"
    )

    result = check_editor_plugin(tmp_path)

    assert result.passed is True
    assert "installed" in result.message.lower()


@pytest.mark.unit
def test_check_editor_plugin_stale(tmp_path: Path):
    """Doctor warns when the deployed editor plugin is outdated."""
    addon_dir = tmp_path / "addons" / "gd-tools-editor"
    addon_dir.mkdir(parents=True)
    for name in ("plugin.cfg", "plugin.gd", "dock.gd", "coverage_overlay.gd"):
        (addon_dir / name).write_text("# stub\n", encoding="utf-8")
    (addon_dir / "_version.txt").write_text("0.0.1\n", encoding="utf-8")

    result = check_editor_plugin(tmp_path)

    assert result.passed is True
    assert result.severity == "warning"
    assert "outdated" in result.message.lower()


@pytest.mark.unit
def test_check_editor_plugin_missing_version_file(tmp_path: Path):
    """Doctor warns (non-blocking) when the version file is absent."""
    addon_dir = tmp_path / "addons" / "gd-tools-editor"
    addon_dir.mkdir(parents=True)
    for name in ("plugin.cfg", "plugin.gd", "dock.gd", "coverage_overlay.gd"):
        (addon_dir / name).write_text("# stub\n", encoding="utf-8")

    result = check_editor_plugin(tmp_path)

    assert result.passed is True
    assert result.severity == "warning"
    assert "version file missing" in result.message


@pytest.mark.unit
def test_run_doctor_includes_editor_plugin_check(_mock_doctor_deps):
    """Doctor lists the editor plugin check among its diagnostics."""
    _mock_doctor_deps["editor_addon"].return_value = CheckResult(
        name="Editor Plugin", passed=True, message="OK"
    )

    result = run_doctor()

    names = [c.name for c in result.checks]
    assert "Editor Plugin" in names
    _mock_doctor_deps["editor_addon"].assert_called_once_with(
        Path("/fake/project")
    )
