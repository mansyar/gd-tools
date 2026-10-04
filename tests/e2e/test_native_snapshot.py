"""E2E checks for the native snapshot-testing subsystem.

Mirrors the harness helpers from ``test_native_runtime.py`` (the repo
convention keeps each e2e module self-contained) and drives the
snapshot-related fixture suites through the native Godot runner.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import import_godot_project

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)
NATIVE_ADDON = (
    Path(__file__).parent.parent.parent
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-test"
)


def _prepare_project(tmp_path: Path, godot_bin: str) -> Path:
    """Copy the clean fixture and import the native addon class cache."""
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    import_godot_project(godot_bin, project)
    return project


def _run_native_manifest(
    project: Path,
    godot_bin: str,
    manifest: dict,
    result_path: Path,
    *,
    events_path: Path | None = None,
    log_path: Path | None = None,
):
    """Run the native Godot runner with optional event and log artifacts."""
    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(
        result_path.with_suffix(".manifest.json")
    )
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    if events_path is not None:
        env["GD_TOOLS_NATIVE_EVENTS"] = str(events_path)
    if log_path is not None:
        env["GD_TOOLS_NATIVE_LOG"] = str(log_path)
    result_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    command = [
        godot_bin,
        "--headless",
        "--path",
        str(project),
        "--script",
        "res://addons/gd-tools-test/gd_tools_test_runner.gd",
    ]
    if log_path is not None:
        command.extend(["--log-file", str(log_path)])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )


def _snapshot_manifest(
    project: Path,
    names: list[str],
    suite_name: str = "NativeSnapshotSerializerSuite",
    suite_path: str = "res://test/snapshot_serializer_suite.gd",
) -> dict:
    """Build a native manifest over a snapshot fixture suite."""
    return {
        "protocol_version": 3,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": suite_name,
                "path": suite_path,
                "tests": [{"name": name} for name in names],
            }
        ],
        "coverage": {"enabled": False},
    }


SERIALIZER_PASSING_METHODS = [
    "test_renders_primitives",
    "test_renders_arrays_multiline",
    "test_renders_empty_containers_compact",
    "test_sorts_dictionary_keys",
    "test_renders_nested_containers_indented",
    "test_render_is_deterministic_across_calls",
]

OBJECT_NODE_METHODS = [
    "test_renders_script_object_properties",
    "test_renders_object_without_script",
    "test_renders_node_tree_structure",
    "test_renders_node_without_script",
]

CYCLE_METHODS = [
    "test_renders_self_referencing_dictionary_as_ref",
    "test_renders_self_referencing_array_as_ref",
    "test_renders_object_cycle_as_ref",
    "test_cyclic_render_is_deterministic",
]

STORE_METHODS = [
    "test_write_creates_versioned_snapshot_file",
    "test_read_round_trips_stored_value",
    "test_read_missing_snapshot_reports_not_found",
    "test_read_malformed_snapshot_reports_error",
]


def _single_failure(payload: dict, name: str) -> dict:
    """Return the one failure recorded for a test entry."""
    for entry in payload["tests"]:
        if entry["name"] == name:
            failures = entry.get("failures", [])
            assert len(failures) == 1, (name, failures)
            return failures[0]
    pytest.fail(f"test {name} missing from results: {payload}")


def test_native_snapshot_serializer_renders_values(godot_bin, tmp_path):
    """The serializer renders primitives, arrays, and dicts canonically."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "snapshot-serializer.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _snapshot_manifest(project, SERIALIZER_PASSING_METHODS),
        result_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(SERIALIZER_PASSING_METHODS)
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def test_native_snapshot_serializer_renders_objects_and_nodes(
    godot_bin, tmp_path
):
    """Tier 2/3: script objects dump declared properties; nodes dump trees."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "snapshot-objects.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _snapshot_manifest(project, OBJECT_NODE_METHODS),
        result_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def test_native_snapshot_serializer_renders_cycles_as_refs(godot_bin, tmp_path):
    """Self-referencing containers and object cycles render as <ref>."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "snapshot-cycles.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _snapshot_manifest(project, CYCLE_METHODS),
        result_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def test_native_snapshot_store_round_trip(godot_bin, tmp_path):
    """The snapshot store writes versioned files and reads them back."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "snapshot-store.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _snapshot_manifest(
            project,
            STORE_METHODS,
            suite_name="NativeSnapshotStoreSuite",
            suite_path="res://test/snapshot_store_suite.gd",
        ),
        result_path,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])
