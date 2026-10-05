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
    extra_env: dict[str, str] | None = None,
):
    """Run the native Godot runner with optional event and log artifacts."""
    env = os.environ.copy()
    env.update(extra_env or {})
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
    "test_read_malformed_header_line_reports_clean_error",
    "test_read_missing_header_field_reports_clean_error",
]

ASSERT_METHODS = [
    "test_first_run_writes_and_passes",
    "test_multiple_auto_named_snapshots",
    "test_explicit_snapshot_name",
    "test_mismatch_fails_and_reports_diff",
    "test_io_error_fails_closed",
    "test_snapshot_name_with_separator_fails_cleanly",
    "test_parameterized_case_snapshots",
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


def _with_parameter_cases(manifest: dict) -> dict:
    """Attach preflight-style parameter metadata to the parameterized test."""
    for suite in manifest["suites"]:
        for test in suite["tests"]:
            if test["name"] == "test_parameterized_case_snapshots":
                test["parameters"] = {
                    "names": ["value"],
                    "values": [["alpha"], ["beta"]],
                }
    return manifest


def test_native_snapshot_assert_flow(godot_bin, tmp_path):
    """assert_snapshot writes on first run, matches later, and fails on drift."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = _with_parameter_cases(
        _snapshot_manifest(
            project,
            ASSERT_METHODS,
            suite_name="NativeSnapshotAssertSuite",
            suite_path="res://test/snapshot_assert_suite.gd",
        )
    )

    # Run 1: first-run snapshots are written and the tests still pass.
    first_path = tmp_path / "snapshot-assert-1.json"
    first = _run_native_manifest(project, godot_bin, manifest, first_path)
    assert first.returncode == 0, first.stdout + first.stderr
    first_payload = json.loads(first_path.read_text(encoding="utf-8"))
    for entry in first_payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])

    written = {
        entry["name"]: entry.get("diagnostics", {}).get("snapshots_written", [])
        for entry in first_payload["tests"]
    }
    assert written["test_first_run_writes_and_passes"] == [
        "NativeSnapshotAssertSuite/test_first_run_writes_and_passes/"
        "test_first_run_writes_and_passes_1"
    ]
    snapshot_file = (
        project
        / ".gd-tools"
        / "snapshots"
        / "NativeSnapshotAssertSuite"
        / "test_first_run_writes_and_passes"
        / "test_first_run_writes_and_passes_1.snap"
    )
    assert snapshot_file.exists()
    content = snapshot_file.read_text(encoding="utf-8")
    assert content.startswith("# gd-tools snapshot v1\n")
    assert "\r" not in content

    # Run 2: stored snapshots match, nothing new is written.
    second_path = tmp_path / "snapshot-assert-2.json"
    second = _run_native_manifest(project, godot_bin, manifest, second_path)
    assert second.returncode == 0, second.stdout + second.stderr
    second_payload = json.loads(second_path.read_text(encoding="utf-8"))
    for entry in second_payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])
        assert entry.get("diagnostics", {}).get("snapshots_written", []) == []
    # Every matching comparison is counted for the run summary.
    matched_total = sum(
        int(entry.get("diagnostics", {}).get("snapshots_matched", 0))
        for entry in second_payload["tests"]
    )
    assert matched_total >= 1, second_payload["tests"]

    # Run 3: a tampered stored snapshot fails its owning test.
    snapshot_file.write_text(
        content.replace('{\n  "a": 1\n}', '"tampered"'),
        encoding="utf-8",
        newline="\n",
    )
    third_path = tmp_path / "snapshot-assert-3.json"
    third = _run_native_manifest(project, godot_bin, manifest, third_path)
    assert third.returncode == 1, third.stdout + third.stderr
    third_payload = json.loads(third_path.read_text(encoding="utf-8"))
    entry = next(
        t
        for t in third_payload["tests"]
        if t["name"] == "test_first_run_writes_and_passes"
    )
    assert entry["status"] == "failed", (entry["message"],)
    failures = entry["diagnostics"]["failures"]
    assert len(failures) == 1
    assert failures[0]["assertion"] == "assert_snapshot"
    assert "the rendered output differs" in failures[0]["message"]
    assert "- " in failures[0]["message"]
    assert "+ " in failures[0]["message"]


def test_native_snapshot_parallel_and_selection_compat(godot_bin, tmp_path):
    """Snapshots stay stable across subset runs and concurrent suite runs."""
    project = _prepare_project(tmp_path, godot_bin)
    assert_manifest = _with_parameter_cases(
        _snapshot_manifest(
            project,
            ASSERT_METHODS,
            suite_name="NativeSnapshotAssertSuite",
            suite_path="res://test/snapshot_assert_suite.gd",
        )
    )

    # Prime stored snapshots, then re-run only one selected test.
    primed_path = tmp_path / "snapshot-assert-prime.json"
    primed = _run_native_manifest(
        project, godot_bin, assert_manifest, primed_path
    )
    assert primed.returncode == 0, primed.stdout + primed.stderr
    subset_manifest = _snapshot_manifest(
        project,
        ["test_first_run_writes_and_passes"],
        suite_name="NativeSnapshotAssertSuite",
        suite_path="res://test/snapshot_assert_suite.gd",
    )
    subset_path = tmp_path / "snapshot-assert-subset.json"
    subset = _run_native_manifest(
        project, godot_bin, subset_manifest, subset_path
    )
    assert subset.returncode == 0, subset.stdout + subset.stderr
    subset_payload = json.loads(subset_path.read_text(encoding="utf-8"))
    assert len(subset_payload["tests"]) == 1
    assert subset_payload["tests"][0]["status"] == "passed", (
        subset_payload["tests"][0]["message"],
    )
    assert (
        subset_payload["tests"][0]["diagnostics"].get("snapshots_written", [])
        == []
    )

    # Concurrent suites in one project write disjoint snapshot directories.
    store_manifest = _snapshot_manifest(
        project,
        STORE_METHODS,
        suite_name="NativeSnapshotStoreSuite",
        suite_path="res://test/snapshot_store_suite.gd",
    )
    env = os.environ.copy()
    processes = []
    for label, manifest, result_name in (
        ("assert", assert_manifest, "snapshot-assert-parallel.json"),
        ("store", store_manifest, "snapshot-store-parallel.json"),
    ):
        result_path = tmp_path / result_name
        child_env = env.copy()
        child_env["GD_TOOLS_NATIVE_MANIFEST"] = str(
            result_path.with_suffix(".manifest.json")
        )
        child_env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
        result_path.with_suffix(".manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        processes.append(
            (
                label,
                result_path,
                subprocess.Popen(
                    [
                        godot_bin,
                        "--headless",
                        "--path",
                        str(project),
                        "--script",
                        "res://addons/gd-tools-test/gd_tools_test_runner.gd",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=child_env,
                ),
            )
        )
    for label, result_path, process in processes:
        stdout, stderr = process.communicate(timeout=60)
        assert process.returncode == 0, (label, stdout, stderr)
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        for entry in payload["tests"]:
            assert entry["status"] == "passed", (
                label,
                entry["name"],
                entry["message"],
            )


def test_native_snapshot_update_flag_rewrites_mismatch(godot_bin, tmp_path):
    """--snapshot-update mode rewrites mismatches and reports them as updated."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "snapshot-update.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _snapshot_manifest(
            project,
            ["test_update_mode_rewrites_mismatch"],
            suite_name="NativeSnapshotUpdateSuite",
            suite_path="res://test/snapshot_update_suite.gd",
        ),
        result_path,
        extra_env={"GD_TOOLS_SNAPSHOT_UPDATE": "1"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    entry = payload["tests"][0]
    assert entry["status"] == "passed", (entry["message"],)
    assert entry.get("diagnostics", {}).get("snapshots_updated", []) == [
        "NativeSnapshotUpdateSuite/test_update_mode_rewrites_mismatch/rewritten"
    ]
    snapshot_file = (
        project
        / ".gd-tools"
        / "snapshots"
        / "NativeSnapshotUpdateSuite"
        / "test_update_mode_rewrites_mismatch"
        / "rewritten.snap"
    )
    assert snapshot_file.exists()
    content = snapshot_file.read_text(encoding="utf-8")
    assert '"fresh"' in content
    assert '"stale"' not in content


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
