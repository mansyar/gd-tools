"""Integration tests for the test runner.

Tests the full flow: run_tests() -> find_godot() -> run_godot() -> GUT ->
parse_junit_xml().  Requires Godot 4.5+ binary in PATH and the GUT addon
in the fixture project (copied from the spike directory at setup time).

All tests are marked ``@pytest.mark.integration`` and are automatically
skipped when the Godot binary is not available on PATH.
"""

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.errors import TestFailureError
from gd_tools.test_runner import run_tests

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    not (os.environ.get("GODOT_BIN") or shutil.which("godot")),
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _setup_project(tmp_path: Path, with_coverage: bool = False) -> Path:
    """Set up a Godot project with GUT in *tmp_path*.

    Copies the fixture project files and the GUT addon (from the spike
    directory) into *tmp_path*.  When *with_coverage* is ``True`` the
    gd-tools-coverage addon is also copied so the pre/post run hook
    scripts exist.
    """
    src = FIXTURES_DIR / "projects" / "sample_project"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    shutil.copytree(
        SPIKE_DIR / "addons" / "gut",
        tmp_path / "addons" / "gut",
        dirs_exist_ok=True,
    )
    if with_coverage:
        shutil.copytree(
            SPIKE_DIR / "addons" / "gd-tools-coverage",
            tmp_path / "addons" / "gd-tools-coverage",
            dirs_exist_ok=True,
        )
    return tmp_path


# ---------------------------------------------------------------------------
# GUT execution + JUnit XML
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_executes_gut_and_produces_junit(tmp_path):
    """run_tests() runs GUT and produces JUnit XML output."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="res://test/test_calculator.gd")

    assert result.total > 0
    assert result.junit_xml_path is not None
    assert Path(result.junit_xml_path).exists()


# ---------------------------------------------------------------------------
# All-passing -> exit 0
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_all_passing_exit_code_0(tmp_path):
    """All-passing tests -> no TestFailureError, TestResult.failed == 0."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="res://test/test_calculator.gd")

    assert result.failed == 0
    assert result.passed > 0


# ---------------------------------------------------------------------------
# Failing test -> exit 1
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_failing_exit_code_1(tmp_path):
    """Failing test -> TestFailureError raised, TestResult.failed > 0."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        with pytest.raises(TestFailureError):
            run_tests(config, suite="res://test/test_failing.gd")


# ---------------------------------------------------------------------------
# --suite filter
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_suite_filter(tmp_path):
    """--suite filter -> only the named suite runs."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="res://test/test_calculator.gd")

    # Only calculator tests ran (4 tests, all pass)
    assert result.failed == 0
    assert result.total == 4


# ---------------------------------------------------------------------------
# --test filter
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_test_name_filter(tmp_path):
    """--test filter -> only matching tests run."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(
            config,
            suite="res://test/test_calculator.gd",
            test_name="test_add",
        )

    assert result.total == 1
    assert result.passed == 1


# ---------------------------------------------------------------------------
# --no-exit-code
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_no_exit_code_true(tmp_path):
    """--no-exit-code -> no exception even with failing tests."""
    project = _setup_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(
            config,
            suite="res://test/test_failing.gd",
            no_exit_code=True,
        )

    assert result.failed > 0


# ---------------------------------------------------------------------------
# --coverage
# ---------------------------------------------------------------------------


@pytest.mark.integration
@skip_if_no_godot
def test_run_tests_coverage_flag(tmp_path):
    """--coverage -> coverage_data_path set, tests still run."""
    project = _setup_project(tmp_path, with_coverage=True)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(
            config,
            coverage=True,
            suite="res://test/test_calculator.gd",
        )

    assert result.coverage_data_path is not None
    assert "coverage" in str(result.coverage_data_path)
    assert result.failed == 0
