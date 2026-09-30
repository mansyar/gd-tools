"""Integration tests for the coverage tracker's playtest mode.

These tests drive the real Godot binary against a prepared fixture
project: the ``gd-tools-coverage`` addon is installed as an autoload and
a driver script executes an instrumented subject before quitting.  The
tests assert the tracker's playtest behavior (periodic + exit flush)
entirely from the outside, through the coverage output JSON file.

The GUT-era GDScript suites under ``tests/fixtures/gdscript/`` have no
live driver anymore (their e2e runners were removed with the legacy GUT
runtime), so Python-driven Godot runs are the live way to exercise addon
behavior -- mirroring ``tests/e2e/test_native_runtime.py``.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import import_godot_project

from gd_tools.init import register_coverage_autoload

pytestmark = pytest.mark.integration

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
AUTOLOAD_FIXTURE = FIXTURES_DIR / "autoload_coverage"
COVERAGE_ADDON = (
    Path(__file__).parents[2]
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-coverage"
)

# The subject under instrumentation. Line numbers are load-bearing: the
# plan below tracks exactly lines 5 (statement), 6 (if_true branch), and
# 7 (statement) of this source.
SUBJECT_SOURCE = (
    "\n".join(
        [
            "extends RefCounted",
            "",
            "",
            "func do_work() -> int:",
            "\tvar value: int = 1",
            "\tif value > 0:",
            "\t\tvalue = value + 1",
            "\treturn value",
        ]
    )
    + "\n"
)

# SceneTree driver: executes the subject, then exercises one playtest
# flush path depending on GD_TOOLS_PLAYTEST_DRIVER_MODE and reports via
# stdout markers that the coverage output existed at that moment.
DRIVER_SOURCE = (
    "\n".join(
        [
            "extends SceneTree",
            "",
            "",
            "func _init() -> void:",
            '\tcall_deferred("_run")',
            "",
            "",
            "func _run() -> void:",
            "\tawait process_frame",
            '\tvar Subject: Script = load("res://scripts/playtest_subject.gd")',
            "\tvar subject: Object = Subject.new()",
            "\tsubject.do_work()",
            '\tvar tracker: Node = root.get_node("_GDTCoverage")',
            '\tvar mode: String = OS.get_environment("GD_TOOLS_PLAYTEST_DRIVER_MODE")',
            '\tvar output: String = OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")',
            '\tif mode == "notify_exit":',
            "\t\ttracker.notification(Node.NOTIFICATION_WM_CLOSE_REQUEST)",
            "\t\tif FileAccess.file_exists(output):",
            '\t\t\tprint("EXIT_FLUSH_OK")',
            '\telif mode == "notify_exit_no_output":',
            "\t\ttracker.notification(Node.NOTIFICATION_WM_CLOSE_REQUEST)",
            '\telif mode == "wait_periodic":',
            "\t\tawait create_timer(1.0).timeout",
            "\t\tif FileAccess.file_exists(output):",
            '\t\t\tprint("PERIODIC_FLUSH_OK")',
            "\tquit()",
        ]
    )
    + "\n"
)


def _playtest_plan() -> dict:
    """Return a minimal coverage plan tracking the playtest subject."""
    return {
        "version": 2,
        "generated_by": "playtest-integration-test",
        "files": [
            {
                "file_id": 0,
                "path": "res://scripts/playtest_subject.gd",
                "source_hash": "sha256:test",
                "lines": [
                    {
                        "line": 5,
                        "id": 0,
                        "type": "statement",
                        "branch_type": None,
                    },
                    {
                        "line": 6,
                        "id": 1,
                        "type": "branch",
                        "branch_type": "if_true",
                    },
                    {
                        "line": 7,
                        "id": 2,
                        "type": "statement",
                        "branch_type": None,
                    },
                ],
            }
        ],
    }


def _prepare_playtest_project(tmp_path: Path, godot_bin: str) -> Path:
    """Copy the fixture project, install the coverage addon and autoload."""
    project = tmp_path / "playtest_project"
    shutil.copytree(AUTOLOAD_FIXTURE, project)
    shutil.copytree(COVERAGE_ADDON, project / "addons" / "gd-tools-coverage")
    (project / "scripts" / "playtest_subject.gd").write_text(
        SUBJECT_SOURCE, encoding="utf-8", newline="\n"
    )
    (project / "playtest_driver.gd").write_text(
        DRIVER_SOURCE, encoding="utf-8", newline="\n"
    )
    register_coverage_autoload(project)
    import_godot_project(godot_bin, project)
    return project


def _run_playtest(
    tmp_path: Path,
    project: Path,
    godot_bin: str,
    plan: dict,
    extra_env: dict[str, str],
    driver_mode: str | None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run the playtest driver with the given env and return (result, output)."""
    plan_path = tmp_path / "playtest-plan.json"
    output_path = tmp_path / "playtest-coverage.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    env = os.environ.copy()
    env["GD_TOOLS_COVERAGE_PLAN"] = str(plan_path)
    env["GD_TOOLS_COVERAGE_OUTPUT"] = str(output_path)
    if driver_mode is not None:
        env["GD_TOOLS_PLAYTEST_DRIVER_MODE"] = driver_mode
    env.update(extra_env)

    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://playtest_driver.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=60,
        cwd=str(project),
    )
    return result, output_path


def test_playtest_exit_flush_writes_coverage_on_close(godot_bin, tmp_path):
    """Playtest mode finalizes and writes coverage data on window close."""
    project = _prepare_playtest_project(tmp_path, godot_bin)
    result, output_path = _run_playtest(
        tmp_path,
        project,
        godot_bin,
        _playtest_plan(),
        {"GD_TOOLS_COVERAGE_PLAYTEST": "1"},
        driver_mode="notify_exit",
    )
    assert result.returncode == 0, result.stderr
    assert "EXIT_FLUSH_OK" in result.stdout

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert len(data["files"]) == 1
    hits = data["files"][0]["hits"]
    assert hits["0"] == 1  # statement
    assert hits["1"] == 1  # if_true branch
    assert hits["2"] == 1  # statement


def test_playtest_periodic_flush_writes_before_exit(godot_bin, tmp_path):
    """Periodic flush writes the output file while the game is still running."""
    project = _prepare_playtest_project(tmp_path, godot_bin)
    result, output_path = _run_playtest(
        tmp_path,
        project,
        godot_bin,
        _playtest_plan(),
        {
            "GD_TOOLS_COVERAGE_PLAYTEST": "1",
            "GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL": "0.25",
        },
        driver_mode="wait_periodic",
    )
    assert result.returncode == 0, result.stderr
    assert "PERIODIC_FLUSH_OK" in result.stdout

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["files"][0]["hits"]


def test_playtest_without_output_env_exits_cleanly(godot_bin, tmp_path):
    """Playtest mode with no output path warns once, not again at exit."""
    project = _prepare_playtest_project(tmp_path, godot_bin)
    result, output_path = _run_playtest(
        tmp_path,
        project,
        godot_bin,
        _playtest_plan(),
        {
            "GD_TOOLS_COVERAGE_PLAYTEST": "1",
            "GD_TOOLS_COVERAGE_OUTPUT": "",
        },
        driver_mode="notify_exit_no_output",
    )
    assert result.returncode == 0, result.stderr
    assert "Cannot write coverage output" not in result.stderr
    assert "SCRIPT ERROR" not in result.stderr
    assert not output_path.exists()


def test_playtest_inactive_without_env(godot_bin, tmp_path):
    """Without the playtest env var the tracker must not write anything."""
    project = _prepare_playtest_project(tmp_path, godot_bin)
    result, output_path = _run_playtest(
        tmp_path,
        project,
        godot_bin,
        _playtest_plan(),
        {},
        driver_mode=None,
    )
    assert result.returncode == 0, result.stderr
    assert not output_path.exists()
