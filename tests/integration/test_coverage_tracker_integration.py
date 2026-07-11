"""Integration tests for the coverage tracker addon.

Tests the GDScript coverage tracker (_GDTCoverage autoload) by running
GUT tests inside a real Godot project. Requires Godot 4.5+ binary in
PATH and the GUT addon.

All tests are marked ``@pytest.mark.integration`` and are automatically
skipped when the Godot binary is not available on PATH.
"""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.init import install_coverage_addon, register_coverage_autoload
from gd_tools.test_runner import run_tests

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    not (os.environ.get("GODOT_BIN") or shutil.which("godot")),
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _find_godot_binary() -> str:
    """Find the Godot binary path (GODOT_BIN env var or PATH lookup)."""
    return os.environ.get("GODOT_BIN") or shutil.which("godot") or ""


def _import_project(project_path: Path) -> None:
    """Run ``godot --headless --import`` to register GUT class names.

    GUT requires its class_names to be registered before it can run.
    This step must be done once per project before invoking GUT.
    """
    binary = _find_godot_binary()
    subprocess.run(
        [binary, "--headless", "--path", str(project_path), "--import"],
        capture_output=True,
        timeout=60,
    )


def _setup_coverage_project(tmp_path: Path) -> Path:
    """Set up a Godot project with GUT and the coverage tracker addon.

    Copies the fixture project, GUT addon, and the coverage addon from
    the source tree. Registers the _GDTCoverage autoload and copies
    the GUT test script for the coverage tracker.
    """
    src = FIXTURES_DIR / "projects" / "sample_project"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    shutil.copytree(
        SPIKE_DIR / "addons" / "gut",
        tmp_path / "addons" / "gut",
        dirs_exist_ok=True,
    )
    # Deploy coverage addon from source package (real implementation)
    install_coverage_addon(tmp_path)
    # Copy GUT test script into the test directory
    shutil.copy2(
        FIXTURES_DIR / "gdscript" / "test_coverage_tracker.gd",
        tmp_path / "test" / "test_coverage_tracker.gd",
    )
    # Register _GDTCoverage autoload using the production function
    register_coverage_autoload(tmp_path)
    # Import project so GUT class_names are registered
    _import_project(tmp_path)
    return tmp_path


@pytest.mark.integration
@skip_if_no_godot
def test_coverage_tracker_gut_tests_pass(tmp_path):
    """GUT tests for _GDTCoverage tracker all pass."""
    project = _setup_coverage_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="test_coverage_tracker.gd")

    assert result.failed == 0
    assert result.passed == 6
