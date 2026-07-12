"""End-to-end tests for the coverage CLI commands.

Tests the full CLI flow via subprocess: ``gd-tools test --coverage``,
``gd-tools coverage report/merge/show``.  Tests that require Godot
are automatically skipped when the binary is not on PATH.

All tests are marked ``@pytest.mark.e2e``.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gd_tools.init import install_coverage_addon

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    not (os.environ.get("GODOT_BIN") or shutil.which("godot")),
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _gd_tools_bin() -> str:
    """Return the path to the gd-tools executable."""
    # Prefer the venv's gd-tools over a system-installed one.
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        path = bin_dir / name
        if path.exists():
            return str(path)
    found = shutil.which("gd-tools")
    if found:
        return found
    return str(bin_dir / "gd-tools")


def _setup_project_with_godot(tmp_path: Path) -> Path:
    """Set up a Godot project with GUT + coverage addon for E2E tests."""
    src = FIXTURES_DIR / "projects" / "sample_project"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    shutil.copytree(
        SPIKE_DIR / "addons" / "gut",
        tmp_path / "addons" / "gut",
        dirs_exist_ok=True,
    )
    install_coverage_addon(tmp_path)
    return tmp_path


def _setup_project_with_data(
    tmp_path: Path,
    coverage_fixture: str = "full_coverage.json",
) -> Path:
    """Set up a project with fixture plan + coverage data (no Godot needed).

    Creates a minimal ``project.godot`` and copies fixture coverage
    data into ``.gd-tools/coverage/`` so that ``coverage report/show``
    commands can operate without running tests.
    """
    (tmp_path / "project.godot").write_text(
        '[application]\nname="Test"\n', encoding="utf-8"
    )
    coverage_dir = tmp_path / ".gd-tools" / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        FIXTURES_DIR / "coverage_plans" / "test_plan.json",
        coverage_dir / "plan.json",
    )
    shutil.copy(
        FIXTURES_DIR / "coverage_data" / coverage_fixture,
        coverage_dir / "coverage.json",
    )
    return tmp_path


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run gd-tools CLI with *args* in *cwd*."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [_gd_tools_bin(), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )


# ---------------------------------------------------------------------------
# gd-tools test --coverage (requires Godot)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_if_no_godot
def test_e2e_test_coverage_full_flow(tmp_path):
    """gd-tools test --coverage runs tests and generates coverage artifacts."""
    project = _setup_project_with_godot(tmp_path)
    result = _run_cli(
        ["test", "--coverage", "--suite", "res://test/test_calculator.gd"],
        cwd=project,
    )
    assert result.returncode == 0
    coverage_dir = project / ".gd-tools" / "coverage"
    assert (coverage_dir / "plan.json").exists()
    assert (coverage_dir / "coverage.json").exists()


@pytest.mark.e2e
@skip_if_no_godot
def test_e2e_test_coverage_min_threshold_exit_1(tmp_path):
    """gd-tools test --coverage --min 100 exits 1 when below 100%."""
    project = _setup_project_with_godot(tmp_path)
    result = _run_cli(
        [
            "test",
            "--coverage",
            "--min",
            "100",
            "--suite",
            "res://test/test_calculator.gd",
        ],
        cwd=project,
    )
    assert result.returncode == 1


# ---------------------------------------------------------------------------
# gd-tools coverage report (no Godot needed)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_e2e_coverage_report_generates_html(tmp_path):
    """gd-tools coverage report generates HTML report from existing data."""
    project = _setup_project_with_data(tmp_path)
    result = _run_cli(["coverage", "report"], cwd=project)
    assert result.returncode == 0
    assert "Report written to:" in result.stdout
    coverage_dir = project / ".gd-tools" / "coverage"
    html_files = list(coverage_dir.rglob("*.html"))
    assert len(html_files) > 0


@pytest.mark.e2e
def test_e2e_coverage_report_lcov_format(tmp_path):
    """gd-tools coverage report --format lcov generates LCOV file."""
    project = _setup_project_with_data(tmp_path)
    result = _run_cli(
        ["coverage", "report", "--format", "lcov"],
        cwd=project,
    )
    assert result.returncode == 0
    lcov_path = project / ".gd-tools" / "coverage" / "coverage.info"
    assert lcov_path.exists()


# ---------------------------------------------------------------------------
# gd-tools coverage merge (no Godot needed)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_e2e_coverage_merge_combines_files(tmp_path):
    """gd-tools coverage merge combines two coverage JSON files."""
    (tmp_path / "project.godot").write_text(
        '[application]\nname="Test"\n', encoding="utf-8"
    )
    file1 = FIXTURES_DIR / "coverage_data" / "full_coverage.json"
    file2 = FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
    output = tmp_path / "merged.json"
    result = _run_cli(
        ["coverage", "merge", str(file1), str(file2), "--output", str(output)],
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert output.exists()
    merged = json.loads(output.read_text())
    assert merged["version"] == 1
    assert len(merged["files"]) == 2
    # full (2) + partial (0) = 2 for file_id=0, line_id=1
    assert merged["files"][0]["hits"]["1"] == 2


# ---------------------------------------------------------------------------
# gd-tools coverage show (no Godot needed)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_e2e_coverage_show_prints_summary(tmp_path):
    """gd-tools coverage show prints a readable summary table."""
    project = _setup_project_with_data(tmp_path)
    result = _run_cli(["coverage", "show"], cwd=project)
    assert result.returncode == 0
    assert "Lines" in result.stdout or "lines" in result.stdout.lower()


@pytest.mark.e2e
def test_e2e_coverage_show_threshold_exit_1(tmp_path):
    """gd-tools coverage show --min 100 exits 1 with partial coverage."""
    project = _setup_project_with_data(
        tmp_path, coverage_fixture="partial_coverage.json"
    )
    result = _run_cli(
        ["coverage", "show", "--min", "100"],
        cwd=project,
    )
    assert result.returncode == 1
