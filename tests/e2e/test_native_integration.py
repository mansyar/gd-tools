"""E2E contracts for native scene and resource integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from gd_tools.native_test.discovery import discover_native_suites
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.preflight import (
    NativePreflightError,
    run_native_preflight,
)
from gd_tools.native_test.protocol import NativeManifest, RuntimeMode

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


def _prepare_project(
    tmp_path: Path, godot_bin: str, files: dict[str, str]
) -> Path:
    """Copy the fixture, add integration fixtures, and import the project."""
    project = tmp_path / "native_integration_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    for relative_path, content in files.items():
        path = project / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(content), encoding="utf-8")
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    import_result = subprocess.run(
        [godot_bin, "--headless", "--path", str(project), "--import"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert import_result.returncode == 0, (
        import_result.stdout + import_result.stderr
    )
    return project


def _run_native(project: Path, godot_bin: str, suite_path: Path):
    """Run discovery, Godot preflight, and the native suite runner."""
    suites = discover_native_suites(
        project,
        [str(suite_path)],
        timeout_seconds=2.0,
    )
    assert suites
    manifest = NativeManifest(
        project_root=project,
        runtime=RuntimeMode.NATIVE,
        suites=suites,
    )
    artifact_dir = project / ".gd-tools" / "artifacts" / "integration"
    preflight = run_native_preflight(
        project,
        manifest,
        godot_binary=godot_bin,
        run_dir=artifact_dir / "preflight",
        timeout_seconds=30,
    )
    result = run_native_tests(
        project,
        preflight.suites,
        godot_bin,
        work_dir=artifact_dir / "native",
        process_timeout=30,
        run_id="integration",
    )
    return preflight, result


def _integration_files() -> dict[str, str]:
    """Return a scene/resource/suite fixture for the integration contract."""
    return {
        "scripts/integration_subject.gd": """
            extends Node
            class_name IntegrationSubject

            signal pulse

            @export var configured_resource: Resource

            func _ready() -> void:
                pass

            func emit_pulse_after_delay() -> void:
                await get_tree().create_timer(0.05).timeout
                pulse.emit()
        """,
        "scripts/integration_resource.gd": """
            extends Resource
            class_name IntegrationResource

            @export var value: int = 0
        """,
        "scenes/main.tscn": """
            [gd_scene load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/integration_subject.gd" id="1"]

            [node name="Main" type="Node"]
            script = ExtResource("1")

            [node name="Content" type="Node" parent="."]

            [node name="Target" type="Node" parent="Content"]

            [node name="TargetExtra" type="Node" parent="Content"]
        """,
        "scenes/alternate.tscn": """
            [gd_scene load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/integration_subject.gd" id="1"]

            [node name="Alternate" type="Node"]
            script = ExtResource("1")

            [node name="Content" type="Node" parent="."]

            [node name="Target" type="Node" parent="Content"]
        """,
        "resources/settings.tres": """
            [gd_resource type="Resource" script_class="IntegrationResource" load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/integration_resource.gd" id="1"]

            [resource]
            script = ExtResource("1")
            value = 7
        """,
        "resources/extra.tres": """
            [gd_resource type="Resource" script_class="IntegrationResource" load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/integration_resource.gd" id="1"]

            [resource]
            script = ExtResource("1")
            value = 9
        """,
        "test/integration_suite.gd": """
            extends GdToolsTest
            class_name IntegrationSuite

            const INTEGRATION := {
                "scene": "res://scenes/main.tscn",
                "resources": {
                    "settings": "res://resources/settings.tres"
                },
                "tests": {
                    "test_scene_defaults_pass": {},
                    "test_scene_override_pass": {
                        "scene": "res://scenes/alternate.tscn",
                        "resources": {
                            "extra": "res://resources/extra.tres"
                        }
                    },
                    "test_resource_only_pass": {
                        "scene": null
                    },
                    "test_scene_without_resources_pass": {
                        "resources": {
                            "settings": null
                        }
                    },
                    "test_no_auto_assignment_pass": {},
                    "test_missing_lookups": {}
                }
            }

            func before_each() -> void:
                var context = get_test_context()
                assert_not_null(context, "integration context is attached before hooks")
                if context.get_integration().get("scene", null) != null:
                    assert_not_null(context.get_scene_root(), "scene is ready before hooks")

            func after_each() -> void:
                assert_not_null(get_test_context(), "integration context remains through cleanup")

            func test_scene_defaults_pass() -> void:
                var context = get_test_context()
                var root = context.get_scene_root()
                assert_not_null(root)
                assert_eq(root.name, "Main")
                assert_not_null(context.find_node("Content/Target"))
                assert_eq(context.find_nodes("Target*").size(), 2)
                var settings = context.get_resource("settings")
                assert_not_null(settings)
                assert_eq(settings.get("value"), 7)
                assert_null(root.get("configured_resource"))
                root.call("emit_pulse_after_delay")
                assert_true(await context.wait_for_signal(root.pulse, 1.0))

            func test_scene_override_pass() -> void:
                var context = get_test_context()
                var root = context.get_scene_root()
                assert_not_null(root)
                assert_eq(root.name, "Alternate")
                assert_eq(context.get_resource("settings").get("value"), 7)
                assert_eq(context.get_resource("extra").get("value"), 9)

            func test_resource_only_pass() -> void:
                var context = get_test_context()
                assert_null(context.get_scene_root())
                assert_not_null(context.get_resource("settings"))

            func test_scene_without_resources_pass() -> void:
                var context = get_test_context()
                assert_not_null(context.get_scene_root())
                assert_true(context.get_integration().get("resources", {}).is_empty())

            func test_no_auto_assignment_pass() -> void:
                var context = get_test_context()
                var root = context.get_scene_root()
                assert_null(root.get("configured_resource"))
                root.set("configured_resource", context.get_resource("settings"))
                assert_eq(root.get("configured_resource").get("value"), 7)

            func test_missing_lookups() -> void:
                var context = get_test_context()
                assert_null(context.find_node("MissingNode"))
                assert_null(context.get_resource("missing_resource"))
        """,
    }


def test_native_integration_context_supports_scenes_resources_and_diagnostics(
    tmp_path, godot_bin
):
    """The native runner exposes deterministic scene/resource context helpers."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        _integration_files(),
    )
    preflight, result = _run_native(
        project,
        godot_bin,
        project / "test" / "integration_suite.gd",
    )

    assert preflight.status == "ok"
    assert result.status == "failed"
    details = {test.name: test for test in result.tests}
    assert details["test_scene_defaults_pass"].status == "passed"
    assert details["test_scene_override_pass"].status == "passed"
    assert details["test_resource_only_pass"].status == "passed"
    assert details["test_scene_without_resources_pass"].status == "passed"
    assert details["test_no_auto_assignment_pass"].status == "passed"

    missing = details["test_missing_lookups"]
    assert missing.status == "failed"
    diagnostics = json.dumps(missing.diagnostics, sort_keys=True)
    assert "MissingNode" in diagnostics
    assert "missing_resource" in diagnostics

    suite = preflight.suites[0]
    assert suite.integration is not None
    assert suite.integration.scene == "res://scenes/main.tscn"
    assert suite.integration.resources == {
        "settings": "res://resources/settings.tres"
    }
    test_metadata = {test.name: test.integration for test in suite.tests}
    assert test_metadata["test_scene_override_pass"].scene == (
        "res://scenes/alternate.tscn"
    )
    assert test_metadata["test_scene_override_pass"].resources["extra"] == (
        "res://resources/extra.tres"
    )
    assert test_metadata["test_resource_only_pass"].scene is None


def _invalid_integration_files(
    *, scene_path: str | None, resource_path: str | None
) -> dict[str, str]:
    """Build a suite whose declared asset is missing at runtime."""
    resources = {} if resource_path is None else {"missing": resource_path}
    integration = {"scene": scene_path, "resources": resources}
    return {"test/invalid_integration_suite.gd": dedent(f"""
            extends GdToolsTest
            class_name InvalidIntegrationSuite

            const INTEGRATION := {json.dumps(integration)}

            func test_not_run() -> void:
                pass
            """).strip() + "\n"}


def test_native_preflight_rejects_missing_resource(tmp_path, godot_bin):
    """Missing declared resources fail before the suite process starts."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        _invalid_integration_files(
            scene_path=None,
            resource_path="res://resources/missing.tres",
        ),
    )
    with pytest.raises(NativePreflightError, match="missing.tres"):
        _run_native(
            project,
            godot_bin,
            project / "test" / "invalid_integration_suite.gd",
        )


def test_native_runner_reports_runtime_scene_load_failure(tmp_path, godot_bin):
    """A valid non-scene resource fails the runner's scene type check."""
    files = _invalid_integration_files(
        scene_path="res://resources/not_scene.tres",
        resource_path=None,
    )
    files["resources/not_scene.tres"] = dedent("""
        [gd_resource type="Resource" format=3]

        [resource]
        """).lstrip()
    project = _prepare_project(tmp_path, godot_bin, files)
    preflight, result = _run_native(
        project,
        godot_bin,
        project / "test" / "invalid_integration_suite.gd",
    )

    assert preflight.status == "ok"
    assert result.status == "error"
    assert len(result.tests) == 1
    failure = result.tests[0]
    assert failure.name == "test_not_run"
    assert failure.status == "error"
    assert "not_scene.tres" in failure.message
