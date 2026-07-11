"""Integration tests for the coverage hooks (pre_run_hook.gd and post_run_hook.gd).

Tests the full coverage instrumentation pipeline by running GUT tests
inside a real Godot project with the coverage hooks configured. Requires
Godot 4.5+ binary in PATH and the GUT addon.

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
    """Run ``godot --headless --import`` to register GUT class names."""
    binary = _find_godot_binary()
    subprocess.run(
        [binary, "--headless", "--path", str(project_path), "--import"],
        capture_output=True,
        timeout=60,
    )


def _setup_hooks_project(tmp_path: Path) -> Path:
    """Set up a Godot project with GUT, coverage addon, and hooks configured.

    Copies the fixture project, GUT addon, and deploys the coverage addon
    (including pre_run_hook.gd and post_run_hook.gd). Registers the
    _GDTCoverage autoload and copies GUT test scripts.
    """
    src = FIXTURES_DIR / "projects" / "sample_project"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    shutil.copytree(
        SPIKE_DIR / "addons" / "gut",
        tmp_path / "addons" / "gut",
        dirs_exist_ok=True,
    )
    install_coverage_addon(tmp_path)
    register_coverage_autoload(tmp_path)
    # Copy GUT test scripts for hooks
    for test_script in ["test_pre_run_hook.gd", "test_post_run_hook.gd"]:
        fixture = FIXTURES_DIR / "gdscript" / test_script
        if fixture.exists():
            shutil.copy2(fixture, tmp_path / "test" / test_script)
    _import_project(tmp_path)
    return tmp_path


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_end_to_end_flow(tmp_path):
    """Full coverage pipeline: plan loading -> instrumentation -> output."""
    # Phase 5: Set env vars, create plan JSON, run Godot, verify output.
    pass


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_missing_plan_env_var(tmp_path):
    """Missing GD_TOOLS_COVERAGE_PLAN -> no instrumentation, warning logged."""
    # Phase 5: Run without env var, verify no coverage output.
    pass


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_malformed_plan_json(tmp_path):
    """Malformed plan JSON -> error logged, instrumentation aborted."""
    # Phase 5: Write bad JSON to env var path, verify error in output.
    pass


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_missing_output_env_var(tmp_path):
    """Missing GD_TOOLS_COVERAGE_OUTPUT -> error logged."""
    # Phase 5: Set plan env var but not output, verify error.
    pass


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_headless_mode(tmp_path):
    """Full flow works with --headless flag and exits cleanly."""
    # Phase 5: Run with headless flag, verify clean exit.
    pass
