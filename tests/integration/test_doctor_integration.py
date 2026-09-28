"""Integration tests for the doctor command.

Tests the full doctor flow end-to-end with only external dependencies
mocked (Godot binary detection, gdtoolkit subprocess calls, network
downloads for init). All file I/O, config parsing, and check logic
run against real files in tmp_path.
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gd_tools.doctor import DoctorResult, run_doctor
from gd_tools.godot import GodotInfo
from gd_tools.init import run_init

pytestmark = pytest.mark.integration


def _create_fake_gut_zip(version: str = "9.5.0") -> bytes:
    """Create a fake GUT archive zip in memory.

    The zip mirrors the real GUT GitHub archive structure:
    Gut-<version>/addons/gut/gut.gd and plugin.cfg
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            f"Gut-{version}/addons/gut/gut.gd",
            "extends Node\n",
        )
        zf.writestr(
            f"Gut-{version}/addons/gut/plugin.cfg",
            f'[plugin]\nname="Gut"\nversion="{version}"\n',
        )
    return buf.getvalue()


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal Godot project in tmp_path."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    return tmp_path


def test_doctor_on_fresh_project(tmp_path, monkeypatch):
    """Doctor on a project before init reports missing components.

    Only Godot and gdtoolkit are mocked (external tools). All
    file-based checks run against the real (empty) project.
    """
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    with (
        patch(
            "gd_tools.doctor.find_godot",
            return_value=GodotInfo(
                path="/fake/godot", version="4.6.2", is_valid=True
            ),
        ),
        patch("subprocess.run"),
    ):
        result = run_doctor()

    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 11
    assert not result.all_passed

    check_map = {c.name: c for c in result.checks}

    # Godot checks pass (mocked)
    assert check_map["Godot Binary"].passed
    assert check_map["Godot Version"].passed

    # Native addon is required in the default runtime.
    assert not check_map["Native Test Addon"].passed
    assert check_map["Native Test Addon"].severity == "critical"

    # GUT is never required; the bridge provides GutTest natively.
    assert check_map["GUT Installed"].passed
    assert check_map["GUT Installed"].severity == "critical"
    assert "compatibility bridge" in check_map["GUT Installed"].message.lower()

    # GUT Version passes (informational; not used by any runtime)
    assert check_map["GUT Version"].passed

    # GUT Suites reports no bridge-eligible suites on a fresh project.
    assert check_map["GUT Suites"].passed

    # Coverage addon missing
    assert not check_map["Coverage Addon"].passed
    assert check_map["Coverage Addon"].severity == "warning"

    # .gutconfig.json is optional in the native runtime.
    assert check_map["GUT Config"].passed
    assert check_map["GUT Config"].severity == "critical"

    # gd-tools.toml missing
    assert not check_map["gd-tools.toml"].passed
    assert check_map["gd-tools.toml"].severity == "critical"

    # GD Toolkit passes (mocked)
    assert check_map["GD Toolkit"].passed

    # The legacy coverage autoload is optional in the native runtime.
    assert check_map["Autoload"].passed
    assert check_map["Autoload"].severity == "critical"


def test_doctor_after_init(tmp_path, monkeypatch):
    """Doctor after ``init --with-gut`` flags the bridge conflict.

    The GUT addon installed by ``--with-gut`` provides ``class_name
    GutTest``, which conflicts with the compatibility bridge's own
    ``GutTest`` base class. Doctor therefore warns about the addon
    instead of celebrating its presence; every other check passes.
    """
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    fake_zip = _create_fake_gut_zip()
    mock_response = Mock()
    mock_response.content = fake_zip
    mock_response.raise_for_status = Mock()

    godot_info = GodotInfo(path="/fake/godot", version="4.5.1", is_valid=True)

    # Run init with mocked Godot and download
    with (
        patch("gd_tools.init.find_godot", return_value=godot_info),
        patch("gd_tools.init.requests.get", return_value=mock_response),
    ):
        run_init(non_interactive=True, with_gut=True)

    # Run doctor with Godot and gdtoolkit mocked
    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = run_doctor()

    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 11
    # The GUT addon installed by --with-gut conflicts with the bridge.
    assert not result.all_passed

    check_map = {c.name: c for c in result.checks}

    # All non-GUT checks pass
    assert check_map["Godot Binary"].passed
    assert check_map["Godot Version"].passed
    assert check_map["Coverage Addon"].passed
    assert check_map["GUT Config"].passed
    assert check_map["gd-tools.toml"].passed
    assert check_map["GD Toolkit"].passed

    # GUT Installed warns about the bridge conflict.
    assert not check_map["GUT Installed"].passed
    assert check_map["GUT Installed"].severity == "warning"
    assert "compatibility bridge" in check_map["GUT Installed"].message.lower()
    assert "docs/gut-migration.md" in check_map["GUT Installed"].fix_hint

    # GUT Version is informational only.
    assert check_map["GUT Version"].passed

    # GUT Suites: init --with-gut installs no suites, so nothing to report.
    assert check_map["GUT Suites"].passed

    # Autoload passes (registered during init)
    assert check_map["Autoload"].passed
    assert check_map["Autoload"].severity == "critical"


def test_doctor_after_native_init_does_not_require_gut(tmp_path, monkeypatch):
    """Native init produces a healthy project without legacy GUT files."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    godot_info = GodotInfo(path="/fake/godot", version="4.5.1", is_valid=True)

    with patch("gd_tools.init.find_godot", return_value=godot_info):
        run_init(non_interactive=True)

    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = run_doctor()

    assert result.all_passed
    assert not (tmp_path / "addons" / "gut").exists()
    assert not (tmp_path / ".gutconfig.json").exists()
    check_map = {check.name: check for check in result.checks}
    assert check_map["Native Test Addon"].passed
    assert check_map["GUT Installed"].passed
    assert check_map["GUT Config"].passed
    assert check_map["Autoload"].passed
