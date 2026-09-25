"""E2E checks for native Godot integration metadata preflight."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

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
PREFLIGHT_SCRIPT = "res://addons/gd-tools-test/gd_tools_test_preflight.gd"


def _suite_source(
    integration: object | None = None,
    *,
    body: str = "",
) -> str:
    """Create a native suite script with optional integration metadata."""
    lines = ['extends "res://addons/gd-tools-test/gd_tools_test.gd"']
    if integration is not None:
        lines.append(
            "const INTEGRATION := "
            + json.dumps(integration, separators=(",", ":"))
        )
    if body:
        lines.append(body.rstrip())
    lines.extend(
        [
            "func test_pass() -> void:",
            "\tpass",
            "func test_other() -> void:",
            "\tpass",
            "func test_replace_scene() -> void:",
            "\tpass",
            "func test_add_resource() -> void:",
            "\tpass",
            "func test_remove() -> void:",
            "\tpass",
            "func test_unselected() -> void:",
            "\tpass",
        ]
    )
    return "\n".join(lines) + "\n"


def _prepare_project(
    tmp_path: Path,
    godot_bin: str,
    files: dict[str, str],
) -> Path:
    """Create and import an isolated project containing preflight fixtures."""
    project = tmp_path / "native_preflight_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    for relative_path, content in files.items():
        destination = project / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dedent(content).lstrip(), encoding="utf-8")
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    process = subprocess.run(
        [godot_bin, "--headless", "--path", str(project), "--import"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    return project


def _manifest(
    project: Path,
    *,
    suite_path: str = "res://test/integration_suite.gd",
    tests: list[str] | None = None,
    protocol_version: int = 2,
) -> dict:
    """Build a discovery manifest for direct preflight execution."""
    return {
        "protocol_version": protocol_version,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativePreflightSuite",
                "path": suite_path,
                "tags": ["native"],
                "tests": [
                    {"name": name, "timeout_seconds": 5.0}
                    for name in (tests or ["test_pass"])
                ],
            }
        ],
        "coverage": {"enabled": False},
    }


def _run_preflight(
    project: Path,
    godot_bin: str,
    manifest: dict,
    result_path: Path,
):
    """Run the bundled Godot metadata preflight directly."""
    manifest_path = result_path.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"] = str(result_path)
    return subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            PREFLIGHT_SCRIPT,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )


def test_preflight_defaults_without_integration_constant(
    godot_bin,
    tmp_path,
):
    """A legacy native suite receives explicit empty headless metadata."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source()},
    )
    result_path = tmp_path / "preflight-defaults.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 2
    assert payload["status"] == "ok"
    assert payload["error"] is None
    suite = payload["suites"][0]
    assert suite["integration"] == {
        "scene": None,
        "resources": {},
        "mode": "headless",
    }
    assert suite["tests"][0]["integration"] == {
        "scene": None,
        "resources": {},
    }


def test_preflight_merges_integration_field_by_field(godot_bin, tmp_path):
    """Suite defaults and selected-test overrides merge without mutation."""
    integration = {
        "scene": "res://scenes/main.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
        "mode": "windowed",
        "tests": {
            "test_replace_scene": {
                "scene": "res://scenes/alternate.tscn",
            },
            "test_add_resource": {
                "resources": {"extra": "res://resources/extra.tres"},
            },
            "test_remove": {
                "scene": None,
                "resources": {"stats": None},
            },
            "test_unselected": {
                "resources": {"future": "res://resources/extra.tres"},
            },
        },
    }
    files = {
        "test/integration_suite.gd": _suite_source(integration),
        "scenes/main.tscn": (
            '[gd_scene format=3]\n\n[node name="Main" type="Node"]\n'
        ),
        "scenes/alternate.tscn": (
            '[gd_scene format=3]\n\n[node name="Alternate" type="Node"]\n'
        ),
        "resources/config.tres": (
            '[gd_resource type="Resource" format=3]\n\n[resource]\n'
        ),
        "resources/stats.tres": (
            '[gd_resource type="Resource" format=3]\n\n[resource]\n'
        ),
        "resources/extra.tres": (
            '[gd_resource type="Resource" format=3]\n\n[resource]\n'
        ),
    }
    project = _prepare_project(tmp_path, godot_bin, files)
    result_path = tmp_path / "preflight-merge.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(
            project,
            tests=[
                "test_pass",
                "test_replace_scene",
                "test_add_resource",
                "test_remove",
            ],
        ),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    suite = payload["suites"][0]
    assert suite["integration"] == {
        "scene": "res://scenes/main.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
        "mode": "windowed",
    }
    tests = {test["name"]: test["integration"] for test in suite["tests"]}
    assert tests["test_pass"] == {
        "scene": "res://scenes/main.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
    }
    assert tests["test_replace_scene"] == {
        "scene": "res://scenes/alternate.tscn",
        "resources": {
            "config": "res://resources/config.tres",
            "stats": "res://resources/stats.tres",
        },
    }
    assert tests["test_add_resource"]["resources"] == {
        "config": "res://resources/config.tres",
        "stats": "res://resources/stats.tres",
        "extra": "res://resources/extra.tres",
    }
    assert tests["test_remove"] == {
        "scene": None,
        "resources": {"config": "res://resources/config.tres"},
    }
    assert "test_unselected" not in tests


@pytest.mark.parametrize(
    ("integration", "expected_error"),
    [
        ({"unknown": True}, "unknown field 'unknown'"),
        ({"mode": "borderless"}, "headless"),
        ({"scene": "scenes/main.tscn"}, "res://"),
        ({"scene": "res://scenes/missing.tscn"}, "does not exist"),
        ({"resources": []}, "resources must be a dictionary"),
        (
            {"resources": {"bad": "relative.tres"}},
            "res://",
        ),
        ({"tests": {"missing": {}}}, "unknown test 'missing'"),
        (
            {"tests": {"test_pass": {"mode": "windowed"}}},
            "per-test declarations do not support field 'mode'",
        ),
    ],
    ids=[
        "unknown-root-field",
        "invalid-mode",
        "relative-scene",
        "missing-scene",
        "malformed-resources",
        "relative-resource",
        "unknown-test",
        "per-test-mode",
    ],
)
def test_preflight_rejects_malformed_declarations(
    godot_bin,
    tmp_path,
    integration,
    expected_error,
):
    """Malformed metadata produces structured exit-code-2 diagnostics."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(integration)},
    )
    result_path = tmp_path / "preflight-invalid.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 2
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "res://test/integration_suite.gd" in payload["error"]
    assert expected_error in payload["error"]


def test_preflight_rejects_overrides_for_parameterized_tests(
    godot_bin, tmp_path
):
    """A test method with parameters is not a runnable test, so it is unknown.

    Python discovery only selects no-argument ``test_*`` methods, so an
    override targeting a parameterized method must be reported rather than
    silently accepted and then never executed.
    """
    integration = {
        "tests": {
            "test_parameterized": {
                "scene": "res://scenes/main.tscn",
            }
        }
    }
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {
            "test/integration_suite.gd": _suite_source(
                integration,
                body=(
                    "func test_parameterized(value: int = 1) -> void:\n"
                    "\tpass"
                ),
            ),
        },
    )
    result_path = tmp_path / "preflight-parameterized.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert payload["suites"] == []
    assert "unknown test 'test_parameterized'" in payload["error"]


def test_preflight_rejects_protocol_v1(godot_bin, tmp_path):
    """A version-mismatched discovery manifest returns a structured error."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source()},
    )
    result_path = tmp_path / "preflight-protocol.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, protocol_version=1),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert "protocol_version 2" in payload["error"]


def test_preflight_reports_script_load_failure(godot_bin, tmp_path):
    """A missing suite script is an actionable infrastructure error."""
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source()},
    )
    result_path = tmp_path / "preflight-load-failure.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project, suite_path="res://test/missing_suite.gd"),
        result_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert "res://test/missing_suite.gd" in payload["error"]
    assert "load" in payload["error"].lower()


def test_preflight_does_not_instantiate_or_execute_suite(godot_bin, tmp_path):
    """Loading metadata has no suite construction or lifecycle side effects."""
    body = dedent("""
        func _init() -> void:
        \tvar file := FileAccess.open("res://preflight-side-effect.txt", FileAccess.WRITE)
        \tif file != null:
        \t\tfile.store_line("constructed")
        \t\tfile.close()

        func before_all() -> void:
        \tvar file := FileAccess.open("res://preflight-side-effect.txt", FileAccess.WRITE)
        \tif file != null:
        \t\tfile.store_line("before_all")
        \t\tfile.close()
        """).strip()
    project = _prepare_project(
        tmp_path,
        godot_bin,
        {"test/integration_suite.gd": _suite_source(body=body)},
    )
    result_path = tmp_path / "preflight-no-side-effects.json"

    process = _run_preflight(
        project,
        godot_bin,
        _manifest(project),
        result_path,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    assert not (project / "preflight-side-effect.txt").exists()
