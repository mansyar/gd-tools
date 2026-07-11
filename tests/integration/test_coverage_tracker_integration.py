"""Integration tests for the coverage tracker addon.

Tests the GDScript coverage tracker (_GDTCoverage autoload) by running
GUT tests inside a real Godot project. Requires Godot 4.5+ binary in
PATH and the GUT addon.

All tests are marked ``@pytest.mark.integration`` and are automatically
skipped when the Godot binary is not available on PATH.
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.init import install_coverage_addon
from gd_tools.test_runner import run_tests

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    shutil.which("godot") is None,
    reason="Godot binary not found in PATH",
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
    # Register _GDTCoverage autoload in project.godot
    project_godot = tmp_path / "project.godot"
    content = project_godot.read_text()
    if "[autoload]" not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += (
            "\n[autoload]\n\n"
            '_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"\n'
        )
        project_godot.write_text(content)
    return tmp_path


@pytest.mark.integration
@skip_if_no_godot
def test_coverage_tracker_gut_tests_pass(tmp_path):
    """GUT tests for _GDTCoverage tracker all pass."""
    project = _setup_coverage_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="res://test/test_coverage_tracker.gd")

    assert result.failed == 0
    assert result.passed == 6
