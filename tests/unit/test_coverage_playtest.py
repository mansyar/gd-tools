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
from gd_tools.errors import GdToolsError
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
        "extends Node\n\n"
        "func score() -> int:\n\treturn 1\n\n"
        "func unused() -> void:\n\treturn\n",
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


# --- Phase 3: result collection & exit semantics ---


def test_playtest_clean_exit_reports_hit_lines(playtest_env):
    config = GdToolsConfig()
    result = run_playtest_coverage(config, report_format="text")

    plan = json.loads(
        (
            playtest_env["project"] / config.coverage.output_dir / "plan.json"
        ).read_text(encoding="utf-8")
    )
    total_lines = sum(len(f["lines"]) for f in plan["files"])
    report = result.output_path.read_text(encoding="utf-8")
    assert "50.0%" in report
    assert str(total_lines) in report


def test_playtest_crash_with_data_warns_and_reports_partial(
    playtest_env, monkeypatch
):
    warnings: list[str] = []
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.output.print_warning",
        lambda message: warnings.append(message),
    )

    def crash_after_snapshot(
        binary, project_path, args, env=None, timeout=None
    ):
        _fake_run_godot({})(binary, project_path, args, env, timeout)
        return subprocess.CompletedProcess(
            args=binary, returncode=1, stdout="", stderr="segfault"
        )

    monkeypatch.setattr(
        "gd_tools.coverage.playtest.run_godot", crash_after_snapshot
    )
    config = GdToolsConfig()
    result = run_playtest_coverage(config, report_format="text")

    assert result.output_path.is_file()
    assert any("partial" in w.lower() for w in warnings)


def test_playtest_timeout_collects_last_snapshot(playtest_env, monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.output.print_warning",
        lambda message: warnings.append(message),
    )

    def snapshot_then_timeout(
        binary, project_path, args, env=None, timeout=None
    ):
        _fake_run_godot({})(binary, project_path, args, env, timeout)
        raise subprocess.TimeoutExpired(cmd=binary, timeout=timeout)

    monkeypatch.setattr(
        "gd_tools.coverage.playtest.run_godot", snapshot_then_timeout
    )
    config = GdToolsConfig()
    result = run_playtest_coverage(config, timeout=30, report_format="text")

    assert result.output_path.is_file()
    assert any("timeout" in w.lower() for w in warnings)


def test_playtest_min_percent_below_threshold_raises_exit_1(playtest_env):
    config = GdToolsConfig()
    with pytest.raises(GdToolsError) as excinfo:
        run_playtest_coverage(config, min_percent=99)
    assert excinfo.value.exit_code == 1


def test_playtest_min_percent_met_does_not_raise(playtest_env):
    config = GdToolsConfig()
    run_playtest_coverage(config, min_percent=50)


def test_playtest_missing_main_scene_and_scene_raises_exit_2(
    tmp_path, monkeypatch
):
    project = _make_project(tmp_path, main_scene=None)
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.find_project_root", lambda: project
    )
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.find_godot", lambda config: GODOT_INFO
    )
    config = GdToolsConfig()

    with pytest.raises(GdToolsError) as excinfo:
        run_playtest_coverage(config)
    assert excinfo.value.exit_code == 2
    assert "--scene" in str(excinfo.value)


def test_playtest_missing_project_raises_exit_2(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.find_project_root", lambda: tmp_path
    )
    monkeypatch.setattr(
        "gd_tools.coverage.playtest.find_godot", lambda config: GODOT_INFO
    )
    config = GdToolsConfig()

    with pytest.raises(GdToolsError) as excinfo:
        run_playtest_coverage(config)
    assert excinfo.value.exit_code == 2
    assert "project.godot" in str(excinfo.value)


def test_playtest_launch_failure_without_data_raises_exit_2(
    playtest_env, monkeypatch
):
    def fail_without_data(binary, project_path, args, env=None, timeout=None):
        return subprocess.CompletedProcess(
            args=binary, returncode=1, stdout="", stderr="boom"
        )

    monkeypatch.setattr(
        "gd_tools.coverage.playtest.run_godot", fail_without_data
    )
    config = GdToolsConfig()

    with pytest.raises(GdToolsError) as excinfo:
        run_playtest_coverage(config)
    assert excinfo.value.exit_code == 2
    assert "boom" in str(excinfo.value)


def test_playtest_clean_exit_without_data_raises_exit_2(
    playtest_env, monkeypatch
):
    def succeed_without_data(
        binary, project_path, args, env=None, timeout=None
    ):
        return subprocess.CompletedProcess(
            args=binary, returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr(
        "gd_tools.coverage.playtest.run_godot", succeed_without_data
    )
    config = GdToolsConfig()

    with pytest.raises(GdToolsError) as excinfo:
        run_playtest_coverage(config)
    assert excinfo.value.exit_code == 2
    assert "no coverage data" in str(excinfo.value).lower()


def test_playtest_supports_lcov_report_format(playtest_env):
    config = GdToolsConfig()
    result = run_playtest_coverage(config, report_format="lcov")

    assert result.output_path.suffix == ".info"


# --- periodic flush interval ---


def test_playtest_sets_flush_interval_from_timeout(playtest_env):
    """The periodic flush interval is derived from --timeout (timeout / 2)."""
    config = GdToolsConfig()
    run_playtest_coverage(config, timeout=8)

    env = playtest_env["captured"]["env"]
    assert env["GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL"] == "4.0"


def test_playtest_uses_default_interval_without_timeout(playtest_env):
    """Without --timeout the default 5s flush interval is used."""
    config = GdToolsConfig()
    run_playtest_coverage(config)

    env = playtest_env["captured"]["env"]
    assert env["GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL"] == "5.0"
