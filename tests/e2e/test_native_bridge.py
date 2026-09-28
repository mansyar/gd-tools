"""E2E tests for the GUT compatibility bridge runner path.

These drive the real Godot binary against the ``gut_bridge_project``
fixture, which contains GUT-style suites (``extends GutTest``).  They
assert the bridge produces the same native result contract: protocol
version 2, native statuses, and matching exit codes -- with no GUT addon
installed (FR-1/FR-7, spec AC-1).
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from conftest import import_godot_project

pytestmark = pytest.mark.e2e

BRIDGE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "gut_bridge_project"
)
BRIDGE_ADDON = (
    Path(__file__).parent.parent.parent
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-test"
)


def _prepare_project(tmp_path: Path, godot_bin: str) -> Path:
    """Copy the bridge fixture project plus the gd-tools-test addon."""
    project = tmp_path / "gut_bridge_project"
    shutil.copytree(BRIDGE_FIXTURE, project)
    shutil.copytree(BRIDGE_ADDON, project / "addons" / "gd-tools-test")
    import_godot_project(godot_bin, project)
    return project


def _suite_entry(name: str, tests: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "path": f"res://test/{name.lower()}.gd",
        "tags": [],
        "integration": {},
        "runtime": "gut",
        "tests": [
            {"name": test_name, "timeout_seconds": 5.0, "retries": 0}
            for test_name in tests
        ],
    }


def _run_bridge_manifest(
    project: Path,
    godot_bin: str,
    suites: list[dict[str, Any]],
    result_path: Path,
) -> tuple[dict[str, Any], subprocess.CompletedProcess[str]]:
    """Write a bridge manifest, invoke the native runner, and read the result."""
    manifest_path = result_path.with_suffix(".manifest.json")
    manifest = {
        "protocol_version": 2,
        "project_root": str(project),
        "runtime": "gut",
        "suites": suites,
        "coverage": {"enabled": False, "plan_path": "", "output_path": ""},
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result_path.unlink(missing_ok=True)
    env = {
        "GD_TOOLS_NATIVE_MANIFEST": str(manifest_path),
        "GD_TOOLS_NATIVE_RESULT": str(result_path),
        "GD_TOOLS_NATIVE_RUN_ID": "bridge-e2e",
    }
    completed = subprocess.run(
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
        timeout=30,
        env=env,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    return result, completed


class TestBridgeResultContract:
    """Bridge suites produce the native result contract."""

    def test_bridge_assertion_signal_async_suites_pass(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        project = _prepare_project(tmp_path, godot_bin)
        result_path = tmp_path / "result.json"
        result, completed = _run_bridge_manifest(
            project,
            godot_bin,
            [
                _suite_entry(
                    "gut_assertion_suite",
                    [
                        "test_value_and_comparison_assertions",
                        "test_container_and_object_assertions",
                        "test_string_assertions",
                        "test_file_assertions",
                    ],
                ),
                _suite_entry(
                    "gut_signal_suite",
                    [
                        "test_signal_emitted_family",
                        "test_signal_not_emitted",
                        "test_connected_assertions",
                    ],
                ),
                _suite_entry(
                    "gut_async_suite",
                    [
                        "test_wait_seconds",
                        "test_frame_waits",
                        "test_wait_for_signal",
                        "test_wait_until",
                        "test_wait_while",
                        "test_yield_aliases",
                    ],
                ),
            ],
            result_path,
        )

        assert result["protocol_version"] == 2
        assert result["status"] == "passed"
        assert completed.returncode == 0
        assert result["tests"], "expected recorded tests"
        assert all(
            test["status"] == "passed" for test in result["tests"]
        ), result["tests"]
        assert completed.stdout is not None

    def test_bridge_lifecycle_hook_order(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        project = _prepare_project(tmp_path, godot_bin)
        result_path = tmp_path / "lifecycle_result.json"
        result, completed = _run_bridge_manifest(
            project,
            godot_bin,
            [
                _suite_entry("gut_lifecycle_suite", ["test_hook_order"]),
            ],
            result_path,
        )

        assert result["status"] == "passed"
        assert completed.returncode == 0
        hook_log = (
            (project / "hook_order.log")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        assert hook_log == [
            "prerun_setup",
            "before_all",
            "before_each",
            "test_hook_order",
            "after_each",
            "after_all",
            "postrun_teardown",
        ]

    def test_bridge_skipping_reports_skipped(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        project = _prepare_project(tmp_path, godot_bin)
        result_path = tmp_path / "skip_result.json"
        result, completed = _run_bridge_manifest(
            project,
            godot_bin,
            [
                _suite_entry(
                    "gut_skip_suite",
                    [
                        "test_explicit_skip",
                        "test_version_skip_lt",
                        "test_version_skip_ne",
                    ],
                ),
            ],
            result_path,
        )

        assert result["status"] == "passed"
        assert completed.returncode == 0
        by_name = {test["name"]: test for test in result["tests"]}
        assert by_name["test_explicit_skip"]["status"] == "skipped"
        assert (
            by_name["test_explicit_skip"]["message"]
            == "not relevant on the bridge"
        )
        assert by_name["test_version_skip_lt"]["status"] == "passed"
        assert by_name["test_version_skip_ne"]["status"] == "passed"

    def test_bridge_broken_suite_records_error(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        """A parse-error bridge suite is a suite error, not a silent green run."""
        project = _prepare_project(tmp_path, godot_bin)
        result_path = tmp_path / "broken_result.json"
        result, completed = _run_bridge_manifest(
            project,
            godot_bin,
            [
                _suite_entry("gut_broken_suite", ["test_never_runs"]),
            ],
            result_path,
        )

        assert result["status"] == "error"
        assert completed.returncode == 2
        assert result["tests"][0]["status"] == "error"
        assert "Unable to load suite" in result["tests"][0]["message"]

    def test_bridge_failure_reports_failed_with_message(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        project = _prepare_project(tmp_path, godot_bin)
        result_path = tmp_path / "failure_result.json"
        result, completed = _run_bridge_manifest(
            project,
            godot_bin,
            [
                _suite_entry("gut_failure_suite", ["test_intentional_failure"]),
            ],
            result_path,
        )

        assert result["status"] == "failed"
        assert completed.returncode == 1
        assert result["tests"][0]["status"] == "failed"
        assert "intentional bridge failure" in result["tests"][0]["message"]
