"""Unit tests for the playtest coverage orchestrator (Roadmap Track 34).

These tests mock the Godot subprocess boundary (``find_godot`` and
``run_godot``) and the project-root discovery, but exercise the real
plan generator and reporters against a tiny on-disk project.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.coverage.playtest import run_playtest_coverage
from gd_tools.godot import GodotInfo

GODOT_INFO = GodotInfo(path="godot-fake", version="4.7.1", is_valid=True)

PROJECT_GODOT_TEMPLATE = """
config_version=5

[application]

config/name="Playtest Fixture"
run/main_scene="{main_scene}"
"""


def _make_project(tmp_path: Path, main_scene: str | None) -> Path:
    """Create a minimal Godot project with one instrumentable script."""
    project = tmp_path / "proj"
    (project / "scripts").mkdir(parents=True)
    (project / "scripts" / "subject.gd").write_text(
        "extends Node\n\nfunc score() -> int:\n\treturn 1\n",
        encoding="utf-8",
    )
    godot_file = 'config_version=5\n\n[application]\n\nconfig/name="P"\n'
    if main_scene is not None:
        godot_file += f'run/main_scene="{main_scene}"\n'
    (project / "project.godot").write_text(godot_file, encoding="utf-8")
    return project


def _fake_run_godot(captured: dict):
    """Build a run_godot stand-in that records its call and writes data."""

    def _run(binary, project_path, args, env=None, timeout=None):
        captured["binary"] = binary
        captured["project_path"] = project_path
        captured["args"] = args
        captured["env"] = env or {}
        captured["timeout"] = timeout
        plan_path = Path(env["GD_TOOLS_COVERAGE_PLAN"])
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        first = plan["files"][0]
        line_id = first["lines"][0]["id"]
        output_path = Path(env["GD_TOOLS_COVERAGE_OUTPUT"])
        output_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "2026-09-30T00:00:00Z",
                    "files": [
                        {
                            "file_id": first["file_id"],
                            "hits": {str(line_id): 1},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            args=binary, returncode=0, stdout="", stderr=""
        )

    return _run


@pytest.fixture()
def playtest_env(tmp_path, monkeypatch):
    """Patch the subprocess and project-root seams for playtest runs."""
    project = _make_project(tmp_path, main_scene="res://scenes/main.tscn")
    captured: dict = {}
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.find_project_root", lambda: project
    )
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.find_godot", lambda config: GODOT_INFO
    )
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.run_godot", _fake_run_godot(captured)
    )
    return {"project": project, "captured": captured}


def test_playtest_launches_windowed_with_coverage_env(playtest_env):
    config = GdToolsConfig()
    run_playtest_coverage(config)

    captured = playtest_env["captured"]
    args = captured["args"]
    assert "--headless" not in args
    env = captured["env"]
    output_dir = playtest_env["project"] / config.coverage.output_dir
    assert env["GD_TOOLS_COVERAGE_PLAYTEST"] == "1"
    assert Path(env["GD_TOOLS_COVERAGE_PLAN"]) == output_dir / "plan.json"
    assert Path(env["GD_TOOLS_COVERAGE_OUTPUT"]) == output_dir / "coverage.json"
    assert (output_dir / "plan.json").is_file()


def test_playtest_explicit_scene_is_passed_through(playtest_env):
    config = GdToolsConfig()
    run_playtest_coverage(config, scene="res://scenes/level1.tscn")

    args = playtest_env["captured"]["args"]
    assert "res://scenes/level1.tscn" in args


def test_playtest_without_scene_uses_main_scene(playtest_env):
    config = GdToolsConfig()
    run_playtest_coverage(config)

    args = playtest_env["captured"]["args"]
    assert "res://scenes/main.tscn" in args


def test_playtest_waits_for_game_exit_and_reports(playtest_env):
    config = GdToolsConfig()
    result = run_playtest_coverage(config, report_format="text")

    assert result.output_path is not None
    assert result.output_path.is_file()


def test_playtest_passes_timeout_to_godot_process(playtest_env):
    config = GdToolsConfig()
    run_playtest_coverage(config, timeout=30)

    assert playtest_env["captured"]["timeout"] == 30
