"""E2E checks for the native Godot test runtime."""

import json
import os
import shutil
import subprocess
from pathlib import Path

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


def _prepare_project(tmp_path: Path, godot_bin: str) -> Path:
    """Copy the clean fixture and import the native addon class cache."""
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
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


def test_native_fixture_loads_without_gut(godot_bin, tmp_path):
    """A native fixture must load without a GUT installation."""
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
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

    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://test/load_native_suite.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Parser Error" not in result.stdout + result.stderr
    assert not (project / "addons" / "gut").exists()


def test_native_runner_executes_manifest(godot_bin, tmp_path):
    """The native runner executes sync/async tests from a manifest."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "manifest.json"
    result_path = tmp_path / "native-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeFixtureSuite",
                        "path": "res://test/native_suite.gd",
                        "tags": ["native"],
                        "tests": [
                            {"name": "test_pass", "timeout_seconds": 5.0},
                            {"name": "test_async", "timeout_seconds": 5.0},
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 1
    assert payload["status"] == "passed"
    assert [test["name"] for test in payload["tests"]] == [
        "test_pass",
        "test_async",
    ]
    assert all(test["status"] == "passed" for test in payload["tests"])
