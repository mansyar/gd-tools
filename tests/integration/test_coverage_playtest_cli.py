"""Integration tests for the ``coverage run`` CLI command.

These tests drive the full CLI path -- plan generation, windowed game
launch with the coverage env, data collection and report generation --
against a real Godot binary using a prepared fixture project whose main
scene exercises an instrumented subject.

The windowed launch requires a display server.  CI provides one via
``xvfb-run`` on the ubuntu leg of the integration job (see
``.github/workflows/ci.yml``); the test also skips defensively when no
display is detected on Linux so local headless runs stay clean.
"""

import os
import re
import shutil
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from conftest import import_godot_project

from gd_tools.cli import cli
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

if sys.platform == "linux" and not os.environ.get("DISPLAY"):
    pytest.skip(
        "windowed Godot launch requires a display server on Linux",
        allow_module_level=True,
    )

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

CLEAN_SCENE_SOURCE = (
    "\n".join(
        [
            "extends Node",
            "",
            "",
            "func _ready() -> void:",
            '\tvar Subject: Script = load("res://scripts/playtest_subject.gd")',
            "\tvar subject: Object = Subject.new()",
            "\tsubject.do_work()",
            "\tawait get_tree().create_timer(0.5).timeout",
            "\tget_tree().quit()",
        ]
    )
    + "\n"
)

# Stays alive well past the --timeout so the CLI must close it.
LINGER_SCENE_SOURCE = (
    "\n".join(
        [
            "extends Node",
            "",
            "",
            "func _ready() -> void:",
            '\tvar Subject: Script = load("res://scripts/playtest_subject.gd")',
            "\tvar subject: Object = Subject.new()",
            "\tsubject.do_work()",
            "\tawait get_tree().create_timer(300.0).timeout",
            "\tget_tree().quit()",
        ]
    )
    + "\n"
)

MAIN_SCENE_SOURCE = (
    "\n".join(
        [
            "[gd_scene load_steps=2 format=3]",
            "",
            '[ext_resource type="Script" path="res://scripts/main_scene.gd" id="1"]',
            "",
            '[node name="Main" type="Node"]',
            'script = ExtResource("1")',
        ]
    )
    + "\n"
)


def _prepare_cli_project(tmp_path: Path, godot_bin: str, scene: str) -> Path:
    """Build a fixture project with a main scene that exercises coverage."""
    project = tmp_path / "playtest_cli_project"
    shutil.copytree(AUTOLOAD_FIXTURE, project)
    shutil.copytree(COVERAGE_ADDON, project / "addons" / "gd-tools-coverage")
    (project / "scripts" / "playtest_subject.gd").write_text(
        SUBJECT_SOURCE, encoding="utf-8", newline="\n"
    )
    (project / "scripts" / "main_scene.gd").write_text(
        scene, encoding="utf-8", newline="\n"
    )
    (project / "main.tscn").write_text(
        MAIN_SCENE_SOURCE, encoding="utf-8", newline="\n"
    )
    project_godot = project / "project.godot"
    content = project_godot.read_text(encoding="utf-8")
    content = re.sub(
        r'(config/name="[^"]*")',
        r'\1\nrun/main_scene="res://main.tscn"',
        content,
        count=1,
    )
    project_godot.write_text(content, encoding="utf-8")
    register_coverage_autoload(project)
    import_godot_project(godot_bin, project)
    return project


def _run_cli(project: Path, args: list[str]):
    """Invoke ``coverage run`` from inside the project directory."""
    runner = CliRunner()
    cwd = Path.cwd()
    os.chdir(project)
    try:
        return runner.invoke(cli, ["coverage", "run", *args])
    finally:
        os.chdir(cwd)


def test_coverage_run_reports_after_clean_exit(godot_bin, tmp_path):
    """A scene that quits cleanly produces a report and exits 0."""
    project = _prepare_cli_project(tmp_path, godot_bin, CLEAN_SCENE_SOURCE)
    result = _run_cli(project, ["--report-format", "text"])
    assert result.exit_code == 0, result.output
    assert "Report written to:" in result.output

    coverage_dir = project / ".gd-tools" / "coverage"
    assert (coverage_dir / "plan.json").is_file()
    coverage_json = coverage_dir / "coverage.json"
    assert coverage_json.is_file()
    assert (coverage_dir / "coverage_report.txt").is_file()
    report_text = (coverage_dir / "coverage_report.txt").read_text(
        encoding="utf-8"
    )
    assert "playtest_subject.gd" in report_text


def test_coverage_run_timeout_closes_game_and_reports(godot_bin, tmp_path):
    """--timeout closes a lingering game and reports the last snapshot."""
    project = _prepare_cli_project(tmp_path, godot_bin, LINGER_SCENE_SOURCE)
    result = _run_cli(project, ["--timeout", "15", "--report-format", "text"])
    assert result.exit_code == 0, result.output
    assert "Report written to:" in result.output

    coverage_dir = project / ".gd-tools" / "coverage"
    assert (coverage_dir / "coverage_report.txt").is_file()
