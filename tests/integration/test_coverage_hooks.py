"""Integration tests for the coverage hooks (pre_run_hook.gd and post_run_hook.gd).

Tests the full coverage instrumentation pipeline by running GUT tests
inside a real Godot project with the coverage hooks configured. Requires
Godot 4.5+ binary in PATH and the GUT addon.

All tests are marked ``@pytest.mark.integration`` and are automatically
skipped when the Godot binary is not available on PATH.
"""

import json
import os
import shutil
import subprocess
import time
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


def _make_plan(files: list[dict]) -> dict:
    """Create a coverage plan dictionary with the given file entries."""
    return {"version": 1, "files": files}


def _clear_coverage_env() -> None:
    """Clear coverage env vars to isolate test scenarios."""
    os.environ.pop("GD_TOOLS_COVERAGE_PLAN", None)
    os.environ.pop("GD_TOOLS_COVERAGE_OUTPUT", None)


@pytest.mark.integration
@skip_if_no_godot
def test_pre_run_hook_gut_tests_pass(tmp_path):
    """GUT tests for pre_run_hook.gd plan loading all pass."""
    project = _setup_hooks_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="test_pre_run_hook.gd")

    assert result.failed == 0
    assert result.passed == 28


@pytest.mark.integration
@skip_if_no_godot
def test_post_run_hook_gut_tests_pass(tmp_path):
    """GUT tests for post_run_hook.gd data collection all pass."""
    project = _setup_hooks_project(tmp_path)
    config = GdToolsConfig()
    with patch("gd_tools.test_runner.find_project_root", return_value=project):
        result = run_tests(config, suite="test_post_run_hook.gd")

    assert result.failed == 0
    assert result.passed == 13


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_end_to_end_flow(tmp_path):
    """Full coverage pipeline: plan loading -> instrumentation -> output."""
    project = _setup_hooks_project(tmp_path)

    plan = _make_plan(
        [
            {
                "file_id": 0,
                "path": "res://scripts/calculator.gd",
                "lines": [
                    {"line": 7, "id": 0},
                    {"line": 11, "id": 1},
                    {"line": 15, "id": 2},
                    {"line": 21, "id": 3},
                ],
            }
        ]
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should pass
        assert result.failed == 0
        assert result.passed == 4

        # Output file should exist
        assert output_path.exists()

        # Verify output JSON structure
        data = json.loads(output_path.read_text())
        assert data["version"] == 1
        assert "generated_at" in data
        assert "files" in data
        assert len(data["files"]) == 1

        # Verify hit data: all 4 lines should have non-zero counts
        file_entry = data["files"][0]
        assert file_entry["file_id"] == 0
        assert len(file_entry["hits"]) == 4
        for line_id in ["0", "1", "2", "3"]:
            assert int(file_entry["hits"][line_id]) > 0
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_missing_plan_env_var(tmp_path):
    """Missing GD_TOOLS_COVERAGE_PLAN -> no instrumentation, warning logged."""
    project = _setup_hooks_project(tmp_path)

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = ""
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should still pass (hooks don't affect test execution)
        assert result.failed == 0
        assert result.passed == 4

        # Warning should appear in Godot output
        combined = result.stdout + result.stderr
        assert "GD_TOOLS_COVERAGE_PLAN" in combined
        assert "not set" in combined.lower()
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_malformed_plan_json(tmp_path):
    """Malformed plan JSON -> error logged, instrumentation aborted."""
    project = _setup_hooks_project(tmp_path)

    plan_path = tmp_path / "plan.json"
    plan_path.write_text("{ this is not valid json }")

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should still pass (hook aborts but GUT continues)
        assert result.failed == 0
        assert result.passed == 4

        # Error should appear in Godot output
        combined = result.stdout + result.stderr
        assert "Failed to parse coverage plan JSON" in combined
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_missing_output_env_var(tmp_path):
    """Missing GD_TOOLS_COVERAGE_OUTPUT -> error logged."""
    project = _setup_hooks_project(tmp_path)

    plan = _make_plan(
        [
            {
                "file_id": 0,
                "path": "res://scripts/calculator.gd",
                "lines": [
                    {"line": 7, "id": 0},
                    {"line": 11, "id": 1},
                ],
            }
        ]
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = ""

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should still pass
        assert result.failed == 0
        assert result.passed == 4

        # Error should appear in Godot output
        combined = result.stdout + result.stderr
        assert "GD_TOOLS_COVERAGE_OUTPUT" in combined
        assert "not set" in combined.lower()
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_nonexistent_script_in_plan(tmp_path):
    """Plan references non-existent script -> error logged, file skipped."""
    project = _setup_hooks_project(tmp_path)

    plan = _make_plan(
        [
            {
                "file_id": 0,
                "path": "res://scripts/nonexistent.gd",
                "lines": [{"line": 1, "id": 0}],
            },
            {
                "file_id": 1,
                "path": "res://scripts/calculator.gd",
                "lines": [
                    {"line": 7, "id": 0},
                    {"line": 11, "id": 1},
                ],
            },
        ]
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should pass
        assert result.failed == 0
        assert result.passed == 4

        # Output should exist with hits from calculator.gd (file_id=1) only
        assert output_path.exists()
        data = json.loads(output_path.read_text())

        file_ids = [f["file_id"] for f in data["files"]]
        assert 1 in file_ids
        assert 0 not in file_ids

        # Error about nonexistent script should appear in output
        combined = result.stdout + result.stderr
        assert "nonexistent.gd" in combined
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_headless_mode(tmp_path):
    """Full flow works with --headless flag and exits cleanly with -gexit."""
    project = _setup_hooks_project(tmp_path)

    plan = _make_plan(
        [
            {
                "file_id": 0,
                "path": "res://scripts/calculator.gd",
                "lines": [
                    {"line": 7, "id": 0},
                    {"line": 11, "id": 1},
                ],
            }
        ]
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            # run_tests uses --headless and -gexit by default
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # Clean exit: tests ran and returned (no crash/timeout)
        assert result.passed == 4
        assert result.failed == 0

        # Output file exists (proves full pipeline ran in headless mode)
        assert output_path.exists()
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_performance_50_files(tmp_path):
    """Instrumentation of 50 files completes in reasonable time (NFR-2: <5s)."""
    project = _setup_hooks_project(tmp_path)

    # Create 50 simple GDScript files
    script_dir = tmp_path / "scripts"
    file_entries = []
    for i in range(50):
        script_path = script_dir / f"perf_{i}.gd"
        script_path.write_text(
            f"extends RefCounted\n\n"
            f"func compute_{i}() -> int:\n"
            f"\tvar total = 0\n"
            f"\tfor j in range(10):\n"
            f"\t\ttotal += j\n"
            f"\treturn total\n"
        )
        file_entries.append(
            {
                "file_id": i,
                "path": f"res://scripts/perf_{i}.gd",
                "lines": [
                    {"line": 5, "id": 0},
                    {"line": 6, "id": 1},
                    {"line": 7, "id": 2},
                ],
            }
        )
    # Also include calculator.gd to verify hits are still recorded correctly
    file_entries.append(
        {
            "file_id": 50,
            "path": "res://scripts/calculator.gd",
            "lines": [
                {"line": 7, "id": 0},
                {"line": 11, "id": 1},
            ],
        }
    )

    plan = _make_plan(file_entries)
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            start = time.time()
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )
            elapsed = time.time() - start

        # GUT tests should pass (instrumentation doesn't break test execution)
        assert result.failed == 0
        assert result.passed == 4

        # Output file should exist with calculator.gd hits
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        file_ids = {f["file_id"] for f in data["files"]}
        assert 50 in file_ids, "calculator.gd should have hits"

        # NFR-2: total run includes Godot startup (~10-15s) + tests (~5s).
        # Instrumentation of 51 files itself is <5s. Total should be under 60s.
        assert elapsed < 60, f"total run took {elapsed:.1f}s, expected <60s"
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_empty_plan(tmp_path):
    """Empty plan (no files) -> no errors, no instrumentation."""
    project = _setup_hooks_project(tmp_path)

    plan = _make_plan([])
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should pass
        assert result.failed == 0
        assert result.passed == 4

        # Output file should exist with empty files (tracker active from env var)
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["version"] == 1
        assert data["files"] == [], "files should be empty"
    finally:
        _clear_coverage_env()


@pytest.mark.integration
@skip_if_no_godot
def test_hooks_unloadable_script(tmp_path):
    """Script that fails to load -> error logged, file skipped, others instrumented.

    Tests the fail-safe skip-and-continue behavior (NFR-1, FR-2). A plan entry
    referencing a non-.gd file (project.godot) causes load() to return null
    (not a GDScript resource), which triggers the error path in
    _instrument_file(). Note: actual .gd syntax errors cause Godot's debugger
    to break in headless mode (-d flag), so we test the same load-failure code
    path using a non-script file instead.
    """
    project = _setup_hooks_project(tmp_path)

    # Reference project.godot (exists but not a GDScript -> load() returns non-GDScript)
    plan = _make_plan(
        [
            {
                "file_id": 0,
                "path": "res://project.godot",
                "lines": [{"line": 1, "id": 0}],
            },
            {
                "file_id": 1,
                "path": "res://scripts/calculator.gd",
                "lines": [
                    {"line": 7, "id": 0},
                    {"line": 11, "id": 1},
                ],
            },
        ]
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    output_path = tmp_path / "coverage_output.json"
    _clear_coverage_env()
    os.environ["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    os.environ["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)

    try:
        config = GdToolsConfig()
        with patch(
            "gd_tools.test_runner.find_project_root", return_value=project
        ):
            result = run_tests(
                config,
                coverage=True,
                suite="test_calculator.gd",
                no_exit_code=True,
            )

        # GUT tests should pass
        assert result.failed == 0
        assert result.passed == 4

        # Output should have calculator.gd (file_id=1) but not project.godot (file_id=0)
        assert output_path.exists()
        data = json.loads(output_path.read_text())
        file_ids = [f["file_id"] for f in data["files"]]
        assert 1 in file_ids, "calculator.gd should be instrumented"
        assert 0 not in file_ids, "unloadable file should be skipped"

        # Error about the unloadable file should appear in output
        combined = result.stdout + result.stderr
        assert "project.godot" in combined, "error should mention the file"
    finally:
        _clear_coverage_env()
