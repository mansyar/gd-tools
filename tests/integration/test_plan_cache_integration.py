"""Integration tests for plan generator caching behavior.

Tests the full CLI flow with plan caching: first run generates plan.json,
second run with no changes uses cached plan (cache hit), modifying a file
triggers regeneration (cache miss), and --no-cache forces regeneration.

Only load_config and external dependencies (Godot test runner, coverage
data reader, report generator) are mocked. The real plan_generator
caching logic, orchestrator flow, and plan.json I/O execute against real
.gd files on disk.
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import GdToolsConfig
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileCoverage,
    ReportResult,
)
from gd_tools.test_runner import TestResult
from gd_tools.verbosity import Verbosity, set_verbosity

pytestmark = pytest.mark.integration

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_verbosity():
    """Reset verbosity to DEFAULT after each test to avoid state leakage."""
    yield
    set_verbosity(Verbosity.DEFAULT)


@pytest.fixture(autouse=True)
def _mock_update_check():
    """Prevent update check network calls in integration tests."""
    with (
        patch("gd_tools.cli.check_for_update", return_value=None),
        patch("gd_tools.cli.check_addon_version", return_value=None),
    ):
        yield


def _setup_project(tmp_path: Path) -> Path:
    """Create a Godot project with .gd files in tmp_path."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    shutil.copy(
        FIXTURES_DIR / "gdscript" / "simple.gd",
        scripts_dir / "simple.gd",
    )
    return tmp_path


@pytest.fixture
def coverage_project(tmp_path, monkeypatch):
    """Set up a project and mock external deps for coverage tests.

    Returns the project root path. The real plan generation, caching,
    and plan.json I/O execute; only Godot/coverage-data/report deps
    are mocked.
    """
    project = _setup_project(tmp_path)
    monkeypatch.chdir(project)
    config = GdToolsConfig()

    mock_test_result = TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.1,
        junit_xml_path=None,
        coverage_data_path=Path("/fake/coverage.json"),
        stdout="",
        stderr="",
    )
    mock_coverage_data = CoverageData(
        version=1,
        generated_at="2025-01-01T00:00:00",
        files=[FileCoverage(file_id=0, hits={"0": 1})],
    )
    mock_report_result = ReportResult(
        output_path=Path("/fake/report.html"),
        format="html",
        summary=CoverageSummary(
            line_rate=1.0,
            branch_rate=1.0,
            covered_lines=1,
            total_lines=1,
            covered_branches=0,
            total_branches=0,
        ),
        file_summaries=[],
        threshold_met=True,
    )

    with (
        patch("gd_tools.cli.load_config", return_value=config),
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=project,
        ),
        patch(
            "gd_tools.coverage.orchestrator.run_tests",
            return_value=mock_test_result,
        ),
        patch(
            "gd_tools.coverage.reporter.read_coverage_json",
            return_value=mock_coverage_data,
        ),
        patch(
            "gd_tools.coverage.reporter.generate_report",
            return_value=mock_report_result,
        ),
    ):
        yield project


# ---------------------------------------------------------------------------
# Cache hit: second run with no changes uses cached plan
# ---------------------------------------------------------------------------


def test_cache_hit_on_second_run(coverage_project):
    """First run generates plan.json; second run with no changes hits cache."""
    runner = CliRunner()

    # First run -- cache miss (no plan.json yet)
    result1 = runner.invoke(cli, ["--verbose", "test", "--coverage"])
    assert result1.exit_code == 0
    assert "cache miss" in result1.output

    plan_path = coverage_project / ".gd-tools" / "coverage" / "plan.json"
    assert plan_path.exists()

    # Second run -- cache hit (no files changed)
    result2 = runner.invoke(cli, ["--verbose", "test", "--coverage"])
    assert result2.exit_code == 0
    assert "cache hit" in result2.output


# ---------------------------------------------------------------------------
# Cache miss: modifying a file triggers regeneration
# ---------------------------------------------------------------------------


def test_cache_miss_on_file_modified(coverage_project):
    """Modifying a file between runs triggers plan regeneration."""
    runner = CliRunner()

    # First run -- cache miss
    result1 = runner.invoke(cli, ["--verbose", "test", "--coverage"])
    assert result1.exit_code == 0
    assert "cache miss" in result1.output

    # Modify a source file
    gd_file = coverage_project / "scripts" / "simple.gd"
    original = gd_file.read_text()
    gd_file.write_text(original + "\n# modified\n")

    # Second run -- cache miss (file modified)
    result2 = runner.invoke(cli, ["--verbose", "test", "--coverage"])
    assert result2.exit_code == 0
    assert "cache miss" in result2.output


# ---------------------------------------------------------------------------
# --no-cache flag forces regeneration
# ---------------------------------------------------------------------------


def test_no_cache_forces_regeneration(coverage_project):
    """--no-cache flag forces plan regeneration even with no changes."""
    runner = CliRunner()

    # First run -- cache miss, plan.json generated
    result1 = runner.invoke(cli, ["--verbose", "test", "--coverage"])
    assert result1.exit_code == 0
    assert "cache miss" in result1.output

    # Second run with --no-cache -- should be cache miss (forced)
    result2 = runner.invoke(
        cli, ["--verbose", "test", "--coverage", "--no-cache"]
    )
    assert result2.exit_code == 0
    assert "cache miss" in result2.output

    # Third run without --no-cache -- should be cache hit (no changes)
    result3 = runner.invoke(cli, ["--verbose", "test", "--coverage"])
    assert result3.exit_code == 0
    assert "cache hit" in result3.output
