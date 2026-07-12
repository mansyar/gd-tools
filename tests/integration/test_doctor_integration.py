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
    assert len(result.checks) == 9
    assert not result.all_passed

    check_map = {c.name: c for c in result.checks}

    # Godot checks pass (mocked)
    assert check_map["Godot Binary"].passed
    assert check_map["Godot Version"].passed

    # GUT not installed
    assert not check_map["GUT Installed"].passed
    assert check_map["GUT Installed"].severity == "critical"
    assert "gd-tools init" in check_map["GUT Installed"].fix_hint

    # GUT Version passes (version unknown - cannot verify)
    assert check_map["GUT Version"].passed

    # Coverage addon missing
    assert not check_map["Coverage Addon"].passed
    assert check_map["Coverage Addon"].severity == "warning"

    # .gutconfig.json missing
    assert not check_map["GUT Config"].passed
    assert check_map["GUT Config"].severity == "warning"

    # gd-tools.toml missing
    assert not check_map["gd-tools.toml"].passed
    assert check_map["gd-tools.toml"].severity == "critical"

    # GD Toolkit passes (mocked)
    assert check_map["GD Toolkit"].passed

    # Autoload not registered
    assert not check_map["Autoload"].passed
    assert check_map["Autoload"].severity == "critical"


def test_doctor_after_init(tmp_path, monkeypatch):
    """Doctor after init reports all checks pass.

    Runs ``gd-tools init`` first (with mocked Godot and download),
    then runs ``gd-tools doctor`` and verifies that all checks pass,
    including the _GDTCoverage autoload (registered during init).
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
        run_init(non_interactive=True)

    # Run doctor with Godot and gdtoolkit mocked
    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = run_doctor()

    assert isinstance(result, DoctorResult)
    assert len(result.checks) == 9
    assert result.all_passed  # All checks pass after init

    check_map = {c.name: c for c in result.checks}

    # All checks pass
    assert check_map["Godot Binary"].passed
    assert check_map["Godot Version"].passed
    assert check_map["GUT Installed"].passed
    assert check_map["GUT Version"].passed
    assert check_map["Coverage Addon"].passed
    assert check_map["GUT Config"].passed
    assert check_map["gd-tools.toml"].passed
    assert check_map["GD Toolkit"].passed

    # Autoload passes (registered during init)
    assert check_map["Autoload"].passed
    assert check_map["Autoload"].severity == "critical"
