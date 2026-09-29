"""E2E tests for the GUT compatibility bridge runner path.

These drive the real Godot binary against the ``gut_bridge_project``
fixture, which contains GUT-style suites (``extends GutTest``).  They
assert the bridge produces the same native result contract: protocol
version 2, native statuses, and matching exit codes -- with no GUT addon
installed (FR-1/FR-7, spec AC-1).
"""

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
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


def _run_cli(
    args: list[str], project: Path, godot_bin: str
) -> subprocess.CompletedProcess:
    """Run the gd-tools CLI from inside the project directory."""
    env = os.environ.copy()
    env.update(
        {
            "GODOT_BIN": godot_bin,
            "GD_TOOLS_NO_UPDATE_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "gd_tools", *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
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
        (project / "test" / "gut_broken_suite.gd").write_text(
            "extends GutTest\n"
            "class_name BridgeBrokenSuite\n\n"
            "func test_never_runs() -> void:\n"
            "\tassert_eq(1, 2\n",
            encoding="utf-8",
        )
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

    def test_bridge_cli_broken_suite_fails_at_preflight(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        """The CLI preflight rejects an unloadable suite before running (FR-3)."""
        project = _prepare_project(tmp_path, godot_bin)
        (project / "test" / "gut_broken_suite.gd").write_text(
            "extends GutTest\n"
            "class_name BridgeBrokenSuite\n\n"
            "func test_never_runs() -> void:\n"
            "\tassert_eq(1, 2\n",
            encoding="utf-8",
        )

        result = _run_cli(["test"], project, godot_bin)

        assert result.returncode == 2
        combined = result.stdout + result.stderr
        assert "Unable to load suite script" in combined
        assert "gut_broken_suite.gd" in combined

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

    def test_bridge_parameterized_suites_expand_into_cases(
        self, tmp_path: Path, godot_bin: str
    ) -> None:
        """Bridge parameterization follows the native result contract.

        ``test_ranked[2-user]`` and ``test_item[beta]`` fail by design.
        """
        project = _prepare_project(tmp_path, godot_bin)
        result_path = tmp_path / "parameterize_result.json"
        suite = _suite_entry(
            "gut_parameterize_suite",
            ["test_ranked", "test_plain", "test_item"],
        )
        suite["tests"][0]["parameters"] = {
            "names": ["value", "label"],
            "values": [[1, "admin"], [2, "user"]],
        }
        suite["tests"][2]["parameters"] = {
            "names": ["value"],
            "values": [["alpha"], ["beta"]],
        }

        result, completed = _run_bridge_manifest(
            project, godot_bin, [suite], result_path
        )

        statuses = {test["name"]: test["status"] for test in result["tests"]}
        assert statuses == {
            "test_ranked[1-admin]": "passed",
            "test_ranked[2-user]": "failed",
            "test_plain": "passed",
            "test_item[alpha]": "passed",
            "test_item[beta]": "failed",
        }
        assert result["status"] == "failed"
        assert completed.returncode == 1
        assert all(test["attempts"] == 1 for test in result["tests"])


def test_bridge_cli_parameterized_suite_runs_end_to_end(tmp_path, godot_bin):
    """A bridge suite using parameterize runs through the full CLI pipeline.

    The bridge scan must accept parameterization, preflight must resolve the
    declaration, and the runner must expand cases with native naming.
    ``test_ranked[2-user]`` and ``test_item[beta]`` fail by design, so the
    run exits 1.
    """
    project = _prepare_project(tmp_path, godot_bin)

    result = _run_cli(
        [
            "test",
            "--suite",
            "BridgeParameterizeSuite",
            "--junit-xml",
            "bridge-parameterize.xml",
        ],
        project,
        godot_bin,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "unsupported" not in (result.stdout + result.stderr).lower()
    root = ET.parse(project / "bridge-parameterize.xml").getroot()
    outcomes = {
        testcase.attrib["name"]: testcase.find("failure") is not None
        for testcase in root.iter("testcase")
    }
    assert outcomes == {
        "test_ranked[1-admin]": False,
        "test_ranked[2-user]": True,
        "test_plain": False,
        "test_item[alpha]": False,
        "test_item[beta]": True,
    }


@pytest.mark.e2e_smoke
def test_bridge_cli_mixed_run_uses_native_contract(tmp_path, godot_bin):
    """A mixed GdToolsTest+GutTest project runs in one CLI invocation (AC-2).

    The bridge fixture intentionally ships a failing suite, so the run exits
    1; the assertions here target routing and result visibility, not the
    aggregate exit code.
    """
    project = _prepare_project(tmp_path, godot_bin)
    (project / "test" / "native_mixed_suite.gd").write_text(
        "extends GdToolsTest\n"
        "class_name NativeMixedSuite\n\n"
        "func test_native_side() -> void:\n"
        "\tassert_eq(2 + 2, 4)\n",
        encoding="utf-8",
    )

    result = _run_cli(
        ["test", "--junit-xml", "mixed-junit.xml"], project, godot_bin
    )

    assert result.returncode == 1, result.stdout + result.stderr
    root = ET.parse(project / "mixed-junit.xml").getroot()
    suite_names = {
        testcase.attrib.get("classname", "")
        for testcase in root.iter("testcase")
    }
    assert "NativeMixedSuite" in suite_names
    assert "BridgeAssertionSuite" in suite_names
    failures = {
        testcase.attrib["name"]
        for testcase in root.iter("testcase")
        if testcase.find("failure") is not None
    }
    assert failures == {
        "test_intentional_failure",
        # The parameterize fixture ships two by-design failures.
        "test_ranked[2-user]",
        "test_item[beta]",
    }


def test_bridge_cli_run_with_coverage_produces_plan_schema_v1(
    tmp_path, godot_bin
):
    """`gd-tools test --coverage` reports bridge suites like native ones (AC-5)."""
    project = _prepare_project(tmp_path, godot_bin)

    result = _run_cli(["test", "--coverage"], project, godot_bin)

    assert result.returncode == 1, result.stdout + result.stderr
    coverage_dir = project / ".gd-tools" / "coverage"
    plan = json.loads((coverage_dir / "plan.json").read_text(encoding="utf-8"))
    assert plan["version"] == 1
    planned_paths = [entry["path"] for entry in plan["files"]]
    assert "res://scripts/bridge_subject.gd" in planned_paths

    data = json.loads(
        (coverage_dir / "coverage.json").read_text(encoding="utf-8")
    )
    measured = {entry["file_id"]: entry for entry in data["files"]}
    subject_ids = [
        entry["file_id"]
        for entry in plan["files"]
        if entry["path"] == "res://scripts/bridge_subject.gd"
    ]
    assert subject_ids, "the bridge subject must be planned"
    assert subject_ids[0] in measured
    assert sum(measured[subject_ids[0]]["hits"].values()) > 0


def test_bridge_mocking_suites_run_through_bridge(tmp_path, godot_bin):
    """Bridge suites may use double()/stub()/assert_called* (FR-5).

    The bridge shim inherits the native mocking API from ``GdToolsTest``, so
    a GutTest suite runs mocking constructs with identical semantics.
    """
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "mocking_result.json"
    result, completed = _run_bridge_manifest(
        project,
        godot_bin,
        [
            _suite_entry(
                "gut_mocking_suite",
                [
                    "test_bridge_double_and_stub_work",
                    "test_bridge_partial_double_runs_real",
                    "test_bridge_call_assertions_work",
                ],
            ),
        ],
        result_path,
    )

    assert result["status"] == "passed"
    assert completed.returncode == 0
    assert len(result["tests"]) == 3
    for entry in result["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def test_bridge_cli_allows_mocking_constructs(tmp_path, godot_bin):
    """The CLI preflight scan no longer rejects mocking constructs."""
    project = _prepare_project(tmp_path, godot_bin)

    result = _run_cli(
        ["--quiet", "test", "--suite", "BridgeMockingSuite"], project, godot_bin
    )

    assert result.returncode == 0, result.stdout + result.stderr
