"""E2E full-workflow tests for gd-tools.

Implements TESTING_STRATEGY §6: Full scenario tests that exercise the
entire CLI as a user would.

Tests that require Godot are automatically skipped when the binary is
not on PATH. The ``init`` command itself is covered by integration tests
(``test_init_integration.py``) with mocked network downloads; these E2E
tests use a pre-initialized project (GUT + coverage addon copied from
the spike directory) to exercise the post-init workflow.

All tests are marked ``@pytest.mark.e2e``.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import find_godot_binary
from gd_tools.init import install_coverage_addon

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    find_godot_binary() is None,
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _gd_tools_bin() -> str:
    """Return the path to the gd-tools executable."""
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
    (tmp_path / ".gutconfig.json").write_text(
        json.dumps(
            {
                "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
                "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "gd-tools.toml").write_text("", encoding="utf-8")
    return tmp_path


def _setup_project_with_data(
    tmp_path: Path,
    coverage_fixture: str = "full_coverage.json",
) -> Path:
    """Set up a project with fixture plan + coverage data (no Godot needed)."""
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


def _setup_fresh_project(tmp_path: Path) -> Path:
    """Set up a fresh Godot project without GUT or coverage addons."""
    src = FIXTURES_DIR / "projects" / "sample_project"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
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
# Doctor tests
# ---------------------------------------------------------------------------


@skip_if_no_godot
def test_doctor_on_fresh_project(tmp_path):
    """gd-tools doctor before init → reports missing components."""
    project = _setup_fresh_project(tmp_path)
    result = _run_cli(["doctor"], cwd=project)
    # Exit 1 because GUT and coverage addon are missing
    assert result.returncode == 1
    output = result.stdout.lower() + result.stderr.lower()
    assert "gut" in output or "coverage" in output


@skip_if_no_godot
def test_doctor_after_init(tmp_path):
    """gd-tools doctor after init → all checks pass."""
    project = _setup_project_with_godot(tmp_path)
    result = _run_cli(["doctor"], cwd=project)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Individual command tests
# ---------------------------------------------------------------------------


@skip_if_no_godot
def test_lint_command(tmp_path):
    """gd-tools lint on sample project exits 0."""
    project = _setup_project_with_godot(tmp_path)
    result = _run_cli(["lint", "scripts/"], cwd=project)
    assert result.returncode == 0


@skip_if_no_godot
def test_format_command(tmp_path):
    """gd-tools format --check on sample project exits 0."""
    project = _setup_project_with_godot(tmp_path)
    result = _run_cli(["format", "--check", "scripts/"], cwd=project)
    assert result.returncode == 0


@skip_if_no_godot
def test_test_coverage_command(tmp_path):
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


def test_coverage_show_command(tmp_path):
    """gd-tools coverage show prints a readable summary table."""
    project = _setup_project_with_data(tmp_path)
    result = _run_cli(["coverage", "show"], cwd=project)
    assert result.returncode == 0
    assert "Lines" in result.stdout or "lines" in result.stdout.lower()


def test_coverage_report_command(tmp_path):
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
# Full workflow sequence
# ---------------------------------------------------------------------------


@skip_if_no_godot
@pytest.mark.slow
def test_full_workflow_sequence(tmp_path):
    """Complete user journey: doctor → lint → format → test --coverage → show → report."""
    project = _setup_project_with_godot(tmp_path)

    # 1. Doctor (all checks pass on initialized project)
    result = _run_cli(["doctor"], cwd=project)
    assert result.returncode == 0, f"doctor failed: {result.stderr}"

    # 2. Lint
    result = _run_cli(["lint", "scripts/"], cwd=project)
    assert result.returncode == 0, f"lint failed: {result.stderr}"

    # 3. Format --check
    result = _run_cli(["format", "--check", "scripts/"], cwd=project)
    assert result.returncode == 0, f"format failed: {result.stderr}"

    # 4. Test --coverage
    result = _run_cli(
        ["test", "--coverage", "--suite", "res://test/test_calculator.gd"],
        cwd=project,
    )
    assert result.returncode == 0, f"test --coverage failed: {result.stderr}"
    coverage_dir = project / ".gd-tools" / "coverage"
    assert (coverage_dir / "plan.json").exists()
    assert (coverage_dir / "coverage.json").exists()

    # 5. Coverage show
    result = _run_cli(["coverage", "show"], cwd=project)
    assert result.returncode == 0, f"coverage show failed: {result.stderr}"

    # 6. Coverage report --format lcov
    result = _run_cli(
        ["coverage", "report", "--format", "lcov"],
        cwd=project,
    )
    assert result.returncode == 0, f"coverage report failed: {result.stderr}"
    lcov_path = coverage_dir / "coverage.info"
    assert lcov_path.exists()
