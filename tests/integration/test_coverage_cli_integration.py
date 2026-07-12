"""Integration tests for the coverage CLI orchestrator.

Tests the full coverage flow: run_coverage_test() -> generate plan ->
run tests with GUT hooks -> read coverage data -> generate reports.
Requires Godot 4.5+ binary in PATH and the GUT addon in the fixture
project.

All tests are marked ``@pytest.mark.integration`` and are automatically
skipped when the Godot binary is not available on PATH.
"""

import json
import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.coverage.orchestrator import run_coverage_test
from gd_tools.errors import CoverageThresholdError
from gd_tools.init import install_coverage_addon

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    not (os.environ.get("GODOT_BIN") or shutil.which("godot")),
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _setup_project(tmp_path: Path) -> Path:
    """Set up a Godot project with GUT and coverage addon in *tmp_path*.

    Copies the fixture project files, the GUT addon, and the
    gd-tools-coverage addon (from the spike directory) into *tmp_path*.
    """
    src = FIXTURES_DIR / "projects" / "sample_project"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    shutil.copytree(
        SPIKE_DIR / "addons" / "gut",
        tmp_path / "addons" / "gut",
        dirs_exist_ok=True,
    )
    install_coverage_addon(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# plan.json generation
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_coverage_test_generates_plan_json(tmp_path):
    """run_coverage_test() generates plan.json in .gd-tools/coverage/."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=project,
        ),
        patch(
            "gd_tools.test_runner.find_project_root",
            return_value=project,
        ),
    ):
        run_coverage_test(config, suite="res://test/test_calculator.gd")

    plan_path = project / ".gd-tools" / "coverage" / "plan.json"
    assert plan_path.exists()
    plan_data = json.loads(plan_path.read_text())
    assert plan_data["version"] == 1
    assert len(plan_data["files"]) > 0


# ---------------------------------------------------------------------------
# coverage.json generation
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_coverage_test_generates_coverage_json(tmp_path):
    """run_coverage_test() generates coverage.json in .gd-tools/coverage/."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=project,
        ),
        patch(
            "gd_tools.test_runner.find_project_root",
            return_value=project,
        ),
    ):
        run_coverage_test(config, suite="res://test/test_calculator.gd")

    coverage_path = project / ".gd-tools" / "coverage" / "coverage.json"
    assert coverage_path.exists()
    coverage_data = json.loads(coverage_path.read_text())
    assert coverage_data["version"] == 1
    assert len(coverage_data["files"]) > 0


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_coverage_test_generates_html_report(tmp_path):
    """run_coverage_test() generates HTML report in .gd-tools/coverage/."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=project,
        ),
        patch(
            "gd_tools.test_runner.find_project_root",
            return_value=project,
        ),
    ):
        run_coverage_test(config, suite="res://test/test_calculator.gd")

    coverage_dir = project / ".gd-tools" / "coverage"
    html_files = list(coverage_dir.rglob("*.html"))
    assert len(html_files) > 0


# ---------------------------------------------------------------------------
# JUnit XML generation
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_coverage_test_generates_junit_xml(tmp_path):
    """run_coverage_test() generates JUnit XML alongside coverage."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=project,
        ),
        patch(
            "gd_tools.test_runner.find_project_root",
            return_value=project,
        ),
    ):
        result = run_coverage_test(
            config, suite="res://test/test_calculator.gd"
        )

    assert result.junit_xml_path is not None
    assert Path(result.junit_xml_path).exists()


# ---------------------------------------------------------------------------
# --min threshold enforcement
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_coverage_test_min_threshold_raises(tmp_path):
    """run_coverage_test() with min_percent=100 raises CoverageThresholdError."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=project,
        ),
        patch(
            "gd_tools.test_runner.find_project_root",
            return_value=project,
        ),
    ):
        with pytest.raises(CoverageThresholdError):
            run_coverage_test(
                config,
                suite="res://test/test_calculator.gd",
                min_percent=100,
            )
