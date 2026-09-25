"""E2E checks for the native Godot test runtime."""

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)
NATIVE_ADDON = (
    Path(__file__).parent.parent.parent
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-test"
)


def test_native_fixture_loads_without_gut(godot_bin, tmp_path):
    """A native fixture must load without a GUT installation."""
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    import_result = subprocess.run(
        [godot_bin, "--headless", "--path", str(project), "--import"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert import_result.returncode == 0, (
        import_result.stdout + import_result.stderr
    )

    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://test/load_native_suite.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Parser Error" not in result.stdout + result.stderr
    assert not (project / "addons" / "gut").exists()
