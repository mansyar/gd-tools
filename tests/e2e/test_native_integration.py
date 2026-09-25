"""E2E contracts for native scene and resource integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from gd_tools.config import GdToolsConfig, GodotConfig, TestConfig
from gd_tools.native_test.command import run_native_test_command
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


def _run_native(
    project: Path,
    godot_bin: str,
    suite_path: Path,
    *,
    retries: int = 0,
    test_timeout: float = 2.0,
):
    """Run discovery, Godot preflight, and the native suite runner."""
    suites = discover_native_suites(
        project,
        [str(suite_path)],
        timeout_seconds=test_timeout,
        retries=retries,
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


def _teardown_files() -> dict[str, str]:
    """Return fixtures that record after_each and scene exit ordering."""
    return {
        "scripts/teardown_subject.gd": """
            extends Node
            class_name TeardownSubject

            func _append_marker(value: String) -> void:
                var file = FileAccess.open("res://teardown.log", FileAccess.READ_WRITE)
                if file == null:
                    file = FileAccess.open("res://teardown.log", FileAccess.WRITE)
                if file == null:
                    return
                file.seek_end()
                file.store_line(value)
                file.close()

            func _exit_tree() -> void:
                _append_marker("exit")
        """,
        "scenes/teardown.tscn": """
            [gd_scene load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/teardown_subject.gd" id="1"]

            [node name="Teardown" type="Node"]
            script = ExtResource("1")
        """,
        "test/teardown_suite.gd": """
            extends GdToolsTest
            class_name TeardownSuite

            const INTEGRATION := {
                "scene": "res://scenes/teardown.tscn",
                "resources": {}
            }

            func _append_marker(value: String) -> void:
                var file = FileAccess.open("res://teardown.log", FileAccess.READ_WRITE)
                if file == null:
                    file = FileAccess.open("res://teardown.log", FileAccess.WRITE)
                if file == null:
                    return
                file.seek_end()
                file.store_line(value)
                file.close()

            func after_each() -> void:
                var context = get_test_context()
                assert_not_null(context)
                assert_not_null(context.get_scene_root())
                _append_marker("after")

            func test_pass() -> void:
                pass

            func test_failure() -> void:
                assert_true(false, "intentional test failure")

            func test_timeout() -> void:
                await get_tree().create_timer(1.0).timeout
        """,
    }


def _retry_files() -> dict[str, str]:
    """Return a suite that requires fresh scene, context, and resource state."""
    return {
        "scripts/retry_subject.gd": """
            extends Node
            class_name RetrySubject
        """,
        "scripts/retry_resource.gd": """
            extends Resource
            class_name RetryResource

            @export var value: int = 0
        """,
        "scenes/retry.tscn": """
            [gd_scene load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/retry_subject.gd" id="1"]

            [node name="Retry" type="Node"]
            script = ExtResource("1")
        """,
        "resources/retry_settings.tres": """
            [gd_resource type="Resource" script_class="RetryResource" load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/retry_resource.gd" id="1"]

            [resource]
            script = ExtResource("1")
            value = 7
        """,
        "test/retry_suite.gd": """
            extends GdToolsTest
            class_name RetrySuite

            const INTEGRATION := {
                "scene": "res://scenes/retry.tscn",
                "resources": {
                    "settings": "res://resources/retry_settings.tres"
                }
            }

            func test_retry() -> void:
                var state = _gd_tools_get_suite_state()
                var attempt := int(state.get("attempt", 0))
                state["attempt"] = attempt + 1
                var context = get_test_context()
                var root = context.get_scene_root()
                var resource = context.get_resource("settings")
                assert_not_null(root)
                assert_not_null(resource)
                if attempt == 0:
                    state["first_root_id"] = root.get_instance_id()
                    state["first_context_id"] = context.get_instance_id()
                    resource.set("value", 99)
                    assert_true(false, "retry once")
                else:
                    assert_true(
                        root.get_instance_id() != int(state["first_root_id"])
                    )
                    assert_true(
                        context.get_instance_id()
                        != int(state["first_context_id"])
                    )
                    assert_eq(resource.get("value"), 7)
        """,
    }


def _cleanup_error_files() -> dict[str, str]:
    """Return a suite whose cleanup assertion must be infrastructure-fatal."""
    return {
        **_teardown_files(),
        "test/teardown_suite.gd": """
            extends GdToolsTest
            class_name CleanupErrorSuite

            const INTEGRATION := {
                "scene": "res://scenes/teardown.tscn",
                "resources": {}
            }

            func after_each() -> void:
                assert_true(false, "cleanup exploded")

            func test_cleanup_error() -> void:
                pass
        """,
    }


def test_native_integration_tears_down_after_each_for_pass_failure_and_timeout(
    tmp_path, godot_bin
):
    """Scenes remain for after_each and exit only after the hook completes."""
    project = _prepare_project(tmp_path, godot_bin, _teardown_files())
    preflight, result = _run_native(
        project,
        godot_bin,
        project / "test" / "teardown_suite.gd",
        test_timeout=0.5,
    )

    assert preflight.status == "ok"
    assert [test.status for test in result.tests] == [
        "passed",
        "failed",
        "timeout",
    ]
    markers = (
        (project / "teardown.log").read_text(encoding="utf-8").splitlines()
    )
    assert markers == ["after", "exit", "after", "exit", "after", "exit"]


def test_native_integration_retry_uses_fresh_attempt_state(tmp_path, godot_bin):
    """A retry receives a new scene/context and an isolated resource value."""
    project = _prepare_project(tmp_path, godot_bin, _retry_files())
    preflight, result = _run_native(
        project,
        godot_bin,
        project / "test" / "retry_suite.gd",
        retries=1,
    )

    assert preflight.status == "ok"
    assert result.status == "passed"
    assert result.tests[0].status == "passed"
    assert result.tests[0].attempts == 2


def test_native_integration_cleanup_failure_is_infrastructure_error(
    tmp_path, godot_bin
):
    """A failure raised by after_each is not reported as an ordinary test failure."""
    project = _prepare_project(tmp_path, godot_bin, _cleanup_error_files())
    preflight, result = _run_native(
        project,
        godot_bin,
        project / "test" / "teardown_suite.gd",
    )

    assert preflight.status == "ok"
    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "cleanup exploded" in result.tests[0].message


def _windowed_files(mode: str, failing: bool) -> dict[str, str]:
    assertion = "assert_true(false, 'windowed failure')" if failing else "pass"
    return {
        "scenes/window.tscn": """
            [gd_scene format=3]

            [node name="Window" type="Node"]
        """,
        "test/windowed_suite.gd": f"""
            extends GdToolsTest
            class_name WindowedSuite

            const INTEGRATION := {{
                "scene": "res://scenes/window.tscn",
                "mode": "{mode}",
                "tests": {{}}
            }}

            func test_windowed() -> void:
                {assertion}
        """,
    }


def _skip_without_display(result):
    if result.tests and result.tests[0].name == "<process>":
        message = result.tests[0].message.lower()
        if any(
            marker in message
            for marker in ("display", "renderer", "x11", "wayland", "window")
        ):
            pytest.skip(
                f"Godot display is unavailable: {result.tests[0].message}"
            )


def test_native_windowed_failure_captures_screenshot_after_each(
    tmp_path, godot_bin
):
    """A failed windowed test records an atomic screenshot artifact."""
    project = _prepare_project(
        tmp_path, godot_bin, _windowed_files("windowed", True)
    )
    preflight, result = _run_native(
        project,
        godot_bin,
        project / "test" / "windowed_suite.gd",
    )
    _skip_without_display(result)

    screenshot = (
        project
        / ".gd-tools"
        / "artifacts"
        / "integration"
        / "native"
        / "suite-0000.failure.png"
    )
    assert preflight.status == "ok"
    assert result.status == "failed"
    assert result.tests[0].status == "failed"
    assert result.tests[0].diagnostics["screenshot"] == str(screenshot)
    assert screenshot.is_file()
    assert screenshot.stat().st_size > 0


def _scene_coverage_files() -> dict[str, str]:
    """Return a scene whose exercised code lives outside the suite script."""
    return {
        "scripts/scene_covered.gd": """
            extends Node
            class_name SceneCovered


            func covered_label() -> String:
                if is_ready():
                    return "ready"
                return "pending"


            func is_ready() -> bool:
                return true


            func uncovered_branch() -> String:
                if false:
                    return "never"
                return "always"
            """,
        "scenes/covered.tscn": """
            [gd_scene load_steps=2 format=3]

            [ext_resource type="Script" path="res://scripts/scene_covered.gd" id="1"]

            [node name="Covered" type="Node"]
            script = ExtResource("1")
            """,
        "test/scene_coverage_suite.gd": """
            extends GdToolsTest
            class_name SceneCoverageSuite

            const INTEGRATION := {"scene": "res://scenes/covered.tscn"}


            func test_scene_code_is_covered() -> void:
                var root := get_test_context().get_scene_root()
                assert_not_null(root, "scene root")
                assert_eq(root.covered_label(), "ready")
            """,
    }


def test_native_coverage_reaches_scripts_driven_by_scenes(
    tmp_path, godot_bin, monkeypatch
):
    """Scene-executed production code contributes to the coverage report."""
    project = _prepare_project(tmp_path, godot_bin, _scene_coverage_files())
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )

    result = run_native_test_command(
        config,
        suite="SceneCoverageSuite",
        coverage=True,
        timeout=30,
    )

    assert result.failed == 0
    assert result.coverage_data_path is not None
    coverage_data = json.loads(
        result.coverage_data_path.read_text(encoding="utf-8")
    )
    plan = json.loads(
        (project / ".gd-tools" / "coverage" / "plan.json").read_text(
            encoding="utf-8"
        )
    )
    path_by_id = {entry["file_id"]: entry["path"] for entry in plan["files"]}
    hits_by_path: dict[str, int] = {}
    for entry in coverage_data["files"]:
        path = path_by_id.get(entry["file_id"])
        assert path is not None, f"unknown file_id {entry['file_id']}"
        hits_by_path[path] = sum(entry["hits"].values())
    assert hits_by_path.get("res://scripts/scene_covered.gd", 0) > 0
    planned = set(path_by_id.values())
    assert "res://scripts/scene_covered.gd" in planned
    assert not any(path.startswith("res://addons/") for path in planned)


def test_native_windowed_pass_and_headless_failure_skip_screenshots(
    tmp_path, godot_bin
):
    """Only failed or timed-out windowed tests create screenshot artifacts."""
    passing_project = _prepare_project(
        tmp_path / "passing", godot_bin, _windowed_files("windowed", False)
    )
    _, passing = _run_native(
        passing_project,
        godot_bin,
        passing_project / "test" / "windowed_suite.gd",
    )
    _skip_without_display(passing)
    assert passing.status == "passed"
    assert not (
        passing_project
        / ".gd-tools"
        / "artifacts"
        / "integration"
        / "native"
        / "suite-0000.failure.png"
    ).exists()

    headless_project = _prepare_project(
        tmp_path / "headless", godot_bin, _windowed_files("headless", True)
    )
    _, headless = _run_native(
        headless_project,
        godot_bin,
        headless_project / "test" / "windowed_suite.gd",
    )
    assert headless.status == "failed"
    assert not (
        headless_project
        / ".gd-tools"
        / "artifacts"
        / "integration"
        / "native"
        / "suite-0000.failure.png"
    ).exists()


def test_native_context_screenshot_write_failure_is_infrastructure(
    tmp_path, godot_bin
):
    """A screenshot write error is surfaced as an infrastructure failure."""
    files = {
        "scenes/window.tscn": """
            [gd_scene format=3]

            [node name="Window" type="Node"]
        """,
        "screenshot-blocker": "not a directory",
        "test/windowed_suite.gd": """
            extends GdToolsTest
            class_name WindowedScreenshotFailureSuite

            const INTEGRATION := {
                "scene": "res://scenes/window.tscn",
                "mode": "windowed"
            }

            func test_invalid_screenshot_path() -> void:
                var result = get_test_context().capture_screenshot(
                    "res://screenshot-blocker/failure.png"
                )
                assert_false(result.get("ok", true))
                assert_true(
                    "screenshot" in result.get("message", "").to_lower(),
                    "screenshot failure should be actionable"
                )
        """,
    }
    project = _prepare_project(tmp_path, godot_bin, files)
    _, result = _run_native(
        project,
        godot_bin,
        project / "test" / "windowed_suite.gd",
    )
    _skip_without_display(result)
    assert result.status == "error"
    engine_result = next(
        test for test in result.tests if test.name == "<engine>"
    )
    assert "Can't save PNG" in "\n".join(
        engine_result.diagnostics.get("engine_errors", [])
    )
