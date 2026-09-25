"""Acceptance E2E coverage for native scene and resource integration.

These tests drive the public ``gd-tools`` CLI on a clean, GUT-free project so
the full user path is verified: ``init`` deploys the managed native runtime,
``test`` runs a scene-driven suite through preflight, and the published
artifacts, JUnit XML, and exit codes stay consistent.
"""

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from textwrap import dedent

import pytest

from conftest import find_godot_binary

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)

skip_if_no_godot = pytest.mark.skipif(
    find_godot_binary() is None,
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)

SUBJECT_SCRIPT = """
extends Node2D

var label := ""

func apply_settings(settings: Resource) -> void:
    label = settings.label
"""

RESOURCE_SCRIPT = """
extends Resource

var label := "acceptance"
"""


def _gd_tools_command() -> list[str]:
    """Use the installed CLI entry point when available."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _run_cli(
    args: list[str], project: Path, godot_bin: str
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "GODOT_BIN": godot_bin,
            "GD_TOOLS_NO_UPDATE_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return subprocess.run(
        [*_gd_tools_command(), *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
    )


def _project_files(
    *, suite_body: str, scene: str = "acceptance"
) -> dict[str, str]:
    """Build a scene-driven suite plus its scenes and named resources."""
    return {
        "scripts/acceptance_subject.gd": dedent(SUBJECT_SCRIPT).strip(),
        "scripts/acceptance_settings.gd": dedent(RESOURCE_SCRIPT).strip(),
        "settings.tres": (
            '[gd_resource type="Resource"'
            ' script_class="AcceptanceSettings"'
            " load_steps=2 format=3]\n\n"
            '[ext_resource type="Script"'
            ' path="res://scripts/acceptance_settings.gd"'
            ' id="1_settings"]\n\n'
            "[resource]\n"
            'script = ExtResource("1_settings")\n'
        ),
        "scenes/acceptance.tscn": (
            "[gd_scene"
            " load_steps=2 format=3]\n\n"
            '[ext_resource type="Script"'
            ' path="res://scripts/acceptance_subject.gd"'
            ' id="1_subject"]\n\n'
            '[node name="Acceptance" type="Node2D"]\n'
            'script = ExtResource("1_subject")\n\n'
            '[node name="Subject" type="Node2D"'
            ' parent="."]\n'
        ),
        "scenes/alt.tscn": (
            "[gd_scene"
            " load_steps=2 format=3]\n\n"
            '[ext_resource type="Script"'
            ' path="res://scripts/acceptance_subject.gd"'
            ' id="1_subject"]\n\n'
            '[node name="Alternate" type="Node2D"]\n'
            'script = ExtResource("1_subject")\n\n'
            '[node name="Alt" type="Node2D" parent="."]\n'
        ),
        f"test/acceptance_{scene}_suite.gd": dedent(suite_body).strip(),
    }


SUITE = """
class_name AcceptanceSuite

extends GdToolsTest

const TAGS := ["acceptance"]

const INTEGRATION := {
    "scene": "res://scenes/acceptance.tscn",
    "resources": {"settings": "res://settings.tres"},
    "tests": {
        "test_alt_scene": {"scene": "res://scenes/alt.tscn"},
        "test_without_scene": {"scene": null},
        "test_missing_node": {"scene": "res://scenes/alt.tscn"},
    },
}

func test_default_scene() -> void:
    var context := get_test_context()
    assert_not_null(context.get_scene_root(), "scene root missing")
    assert_not_null(context.find_node("Subject"), "Subject not found")
    assert_eq(context.get_integration()["scene"], "res://scenes/acceptance.tscn")

func test_named_resource_is_loaded() -> void:
    var context := get_test_context()
    var settings := context.get_resource("settings")
    assert_eq(settings.label, "acceptance")

func test_resources_are_not_assigned_automatically() -> void:
    var subject := get_test_context().find_node("Subject")
    assert_eq(subject.label, "")

func test_alt_scene() -> void:
    var context := get_test_context()
    assert_not_null(context.find_node("Alt"), "Alt not found")
    assert_eq(context.get_integration()["scene"], "res://scenes/alt.tscn")

func test_without_scene() -> void:
    var context := get_test_context()
    assert_null(context.get_scene_root(), "scene should be removed")
    assert_null(context.get_integration()["scene"], "scene should be removed")

func test_missing_node() -> void:
    var context := get_test_context()
    assert_not_null(context.find_node("Ghost"), "MissingNode Ghost")
"""

MISSING_SCENE_SUITE = """
class_name AcceptanceMissingSceneSuite

extends GdToolsTest

const INTEGRATION := {"scene": "res://scenes/absent.tscn"}

func test_scene_is_available() -> void:
    assert_not_null(get_test_context().get_scene_root(), "scene root missing")
"""


def _prepare_project(
    tmp_path: Path, files: dict[str, str], godot_bin: str
) -> Path:
    """Create a clean GUT-free project and deploy the managed runtime."""
    project = tmp_path / "acceptance_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.rmtree(project / "test", ignore_errors=True)
    for relative, content in files.items():
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"{content}\n", encoding="utf-8")

    result = _run_cli(["init", "--non-interactive"], project, godot_bin)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (project / "addons" / "gut").exists()
    return project


def _artifact_index(project: Path) -> dict:
    """Return the published artifact index of the latest run."""
    indexes = sorted(
        (project / ".gd-tools" / "artifacts").glob("*/artifacts.json")
    )
    assert len(indexes) == 1, f"expected one artifact index, got {indexes}"
    return json.loads(indexes[0].read_text(encoding="utf-8"))


def _junit_failures(junit: Path) -> str:
    """Return the concatenated failure text of a JUnit report."""
    root = ET.parse(junit).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    return "\n".join(
        "".join(element.itertext())
        for suite in suites
        for case in suite.iter("testcase")
        for element in list(case)
        if element.tag in {"failure", "error"}
    )


@skip_if_no_godot
def test_native_cli_runs_scene_suite_with_default_and_overridden_metadata(
    tmp_path: Path, godot_bin: str
) -> None:
    """A scene-driven suite honors default and per-test metadata end to end."""
    project = _prepare_project(
        tmp_path, _project_files(suite_body=SUITE), godot_bin
    )

    result = _run_cli(
        ["--quiet", "test", "--suite", "AcceptanceSuite"],
        project,
        godot_bin,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1, output
    assert "MissingNode" in output

    index = _artifact_index(project)
    assert index["status"] == "failed"
    assert index["suites"][0]["suite"] == "AcceptanceSuite"
    assert Path(index["suites"][0]["result"]).is_file()
    assert Path(index["preflight"]["result"]).is_file()

    preflight = json.loads(
        Path(index["preflight"]["result"]).read_text(encoding="utf-8")
    )
    assert preflight["protocol_version"] == 2
    assert preflight["status"] == "ok"
    suite = preflight["suites"][0]
    assert suite["integration"]["mode"] == "headless"
    assert suite["integration"]["scene"] == "res://scenes/acceptance.tscn"
    assert suite["integration"]["resources"] == {
        "settings": "res://settings.tres"
    }
    overrides = {test["name"]: test["integration"] for test in suite["tests"]}
    assert overrides["test_alt_scene"]["scene"] == "res://scenes/alt.tscn"
    assert overrides["test_without_scene"]["scene"] is None
    assert overrides["test_without_scene"]["resources"] == {
        "settings": "res://settings.tres"
    }

    payload = json.loads(
        Path(index["suites"][0]["result"]).read_text(encoding="utf-8")
    )
    statuses = {test["name"]: test["status"] for test in payload["tests"]}
    assert statuses == {
        "test_default_scene": "passed",
        "test_named_resource_is_loaded": "passed",
        "test_resources_are_not_assigned_automatically": "passed",
        "test_alt_scene": "passed",
        "test_without_scene": "passed",
        "test_missing_node": "failed",
    }


@skip_if_no_godot
def test_native_cli_scene_failure_exits_one_with_diagnostics(
    tmp_path: Path, godot_bin: str
) -> None:
    """A structured node-lookup failure exits 1 and reaches JUnit."""
    project = _prepare_project(
        tmp_path, _project_files(suite_body=SUITE), godot_bin
    )

    result = _run_cli(
        [
            "--quiet",
            "test",
            "--suite",
            "AcceptanceSuite",
            "--test",
            "test_missing_node",
            "--junit-xml",
            ".gd-tools/acceptance.xml",
        ],
        project,
        godot_bin,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    failures = _junit_failures(project / ".gd-tools" / "acceptance.xml")
    assert "integration_node" in failures
    assert "MissingNode" in failures
    assert "Ghost" in failures


@skip_if_no_godot
def test_native_cli_missing_scene_declaration_exits_two(
    tmp_path: Path, godot_bin: str
) -> None:
    """An unresolvable scene declaration exits 2 with actionable guidance."""
    files = _project_files(suite_body=SUITE)
    files["test/acceptance_missing_scene_suite.gd"] = dedent(
        MISSING_SCENE_SUITE
    ).strip()
    project = _prepare_project(tmp_path, files, godot_bin)

    result = _run_cli(
        ["--quiet", "test", "--suite", "AcceptanceMissingSceneSuite"],
        project,
        godot_bin,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert "res://scenes/absent.tscn" in output
    assert "res://test/acceptance_missing_scene_suite.gd" in output

    index = _artifact_index(project)
    assert index["status"] == "error"
    assert index["suites"] == []


@skip_if_no_godot
def test_native_cli_tag_selection_skips_unmatched_scene_tests(
    tmp_path: Path, godot_bin: str
) -> None:
    """Tag and test selectors narrow scene tests without leaking siblings."""
    project = _prepare_project(
        tmp_path, _project_files(suite_body=SUITE), godot_bin
    )

    result = _run_cli(
        [
            "--quiet",
            "test",
            "--suite",
            "AcceptanceSuite",
            "--tag",
            "acceptance",
            "--test",
            "test_alt_scene",
        ],
        project,
        godot_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    index = _artifact_index(project)
    payload = json.loads(
        Path(index["suites"][0]["result"]).read_text(encoding="utf-8")
    )
    assert payload["status"] == "passed"
    assert [test["name"] for test in payload["tests"]] == ["test_alt_scene"]
