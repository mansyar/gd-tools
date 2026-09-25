"""E2E checks for the native Godot test runtime."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from gd_tools.config import GdToolsConfig, GodotConfig, TestConfig
from gd_tools.native_test.command import run_native_test_command
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.protocol import NativeSuite, NativeTest

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
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(result_path.with_suffix(".manifest.json"))
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


def test_native_runner_runs_lifecycle_hooks_after_failure(godot_bin, tmp_path):
    """Lifecycle hooks run in order and cleanup follows a failed test."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "lifecycle-manifest.json"
    result_path = tmp_path / "lifecycle-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeLifecycleSuite",
                        "path": "res://test/lifecycle_suite.gd",
                        "tests": [
                            {"name": "test_pass"},
                            {"name": "test_fail"},
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

    assert result.returncode == 1, result.stdout + result.stderr
    events = (
        (project / "lifecycle.log").read_text(encoding="utf-8").splitlines()
    )
    assert events == [
        "before_all",
        "before_each",
        "test_pass",
        "after_each",
        "before_each",
        "test_fail",
        "after_each",
        "after_all",
    ]
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert [test["status"] for test in payload["tests"]] == [
        "passed",
        "failed",
    ]


def test_native_runner_reports_lifecycle_failures_and_preserves_suite_state(
    godot_bin, tmp_path
):
    """Setup/teardown failures and suite state affect the native result."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = {
        "protocol_version": 1,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativeBeforeAllFailureSuite",
                "path": "res://test/review_before_all_suite.gd",
                "tests": [{"name": "test_never_reports_green"}],
            },
            {
                "name": "NativeAfterAllFailureSuite",
                "path": "res://test/review_after_all_suite.gd",
                "tests": [{"name": "test_pass"}],
            },
            {
                "name": "NativeReviewStateSuite",
                "path": "res://test/review_state_suite.gd",
                "tests": [{"name": "test_uses_suite_state"}],
            },
        ],
        "coverage": {"enabled": False},
    }
    result_path = tmp_path / "review-lifecycle-result.json"

    process = _run_native_manifest(project, godot_bin, manifest, result_path)

    assert process.returncode == 1, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    results = {test["suite"]: test for test in payload["tests"]}
    assert results["NativeBeforeAllFailureSuite"]["status"] == "failed"
    assert results["NativeBeforeAllFailureSuite"]["name"] == "before_all"
    assert results["NativeAfterAllFailureSuite"]["status"] == "failed"
    assert results["NativeAfterAllFailureSuite"]["name"] == "after_all"
    assert results["NativeReviewStateSuite"]["status"] == "passed"


def test_native_runner_bounds_lifecycle_timeout_and_runs_cleanup(
    godot_bin, tmp_path
):
    """A hanging setup hook is bounded and cleanup still runs."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = {
        "protocol_version": 1,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativeReviewTimeoutCleanupSuite",
                "path": "res://test/review_timeout_cleanup_suite.gd",
                "tests": [
                    {
                        "name": "test_pass",
                        "timeout_seconds": 0.05,
                    }
                ],
            }
        ],
        "coverage": {"enabled": False},
    }
    result_path = tmp_path / "review-timeout-result.json"
    log_path = tmp_path / "godot-timeout.log"

    process = _run_native_manifest(
        project,
        godot_bin,
        manifest,
        result_path,
        log_path=log_path,
    )

    assert process.returncode == 1, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    test = payload["tests"][0]
    assert test["status"] == "timeout"
    assert test["duration_seconds"] < 0.5
    assert (project / "review-timeout.log").read_text(
        encoding="utf-8"
    ).splitlines() == ["after_each"]


def test_native_runner_captures_engine_errors_and_warnings(
    godot_bin, tmp_path
):
    """Godot engine diagnostics fail the run and appear in native JSON."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = {
        "protocol_version": 1,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativeEngineDiagnosticsSuite",
                "path": "res://test/engine_diagnostics_suite.gd",
                "tests": [{"name": "test_engine_diagnostics"}],
            }
        ],
        "coverage": {"enabled": False},
    }
    result_path = tmp_path / "engine-diagnostics-result.json"
    log_path = tmp_path / "godot-engine.log"

    process = _run_native_manifest(
        project,
        godot_bin,
        manifest,
        result_path,
        log_path=log_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert any("native engine error" in item for item in payload["engine_errors"])
    assert any(
        "native engine warning" in item for item in payload["engine_warnings"]
    )

    """Assertion failures include values, message, and source location."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "assertion-manifest.json"
    result_path = tmp_path / "assertion-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeAssertionSuite",
                        "path": "res://test/assertion_suite.gd",
                        "tests": [{"name": "test_structured_failure"}],
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

    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    failure = payload["tests"][0]["diagnostics"]["failures"][0]
    assert failure["assertion"] == "assert_eq"
    assert failure["actual"] == "1"
    assert failure["expected"] == "2"
    assert failure["message"] == "values differ"
    assert "assertion_suite.gd" in failure["source"]
    assert failure["line"] > 0


def test_native_runner_emits_structured_events(godot_bin, tmp_path):
    """The runner writes parseable NDJSON lifecycle events when requested."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "event-manifest.json"
    result_path = tmp_path / "event-result.json"
    events_path = tmp_path / "events.ndjson"
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
                        "tests": [{"name": "test_pass"}],
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
    env["GD_TOOLS_NATIVE_EVENTS"] = str(events_path)
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
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in events] == [
        "run_started",
        "test_started",
        "test_finished",
        "run_finished",
    ]
    assert events[2]["status"] == "passed"


def test_native_runner_marks_timed_out_tests(godot_bin, tmp_path):
    """A test exceeding its manifest timeout gets a timeout result."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "timeout-manifest.json"
    result_path = tmp_path / "timeout-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeTimeoutSuite",
                        "path": "res://test/timeout_suite.gd",
                        "tests": [
                            {
                                "name": "test_hangs",
                                "timeout_seconds": 0.05,
                            }
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

    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["tests"][0]["status"] == "timeout"
    assert payload["tests"][0]["duration_seconds"] < 1.0


def test_native_runner_retries_failed_test_with_fresh_instance(
    godot_bin, tmp_path
):
    """Retry settings create a fresh attempt and report the attempt count."""
    project = _prepare_project(tmp_path, godot_bin)
    retry_script = project / "test" / "retry_suite.gd"
    retry_script.write_text(
        "extends GdToolsTest\n"
        "static var _attempt_count := 0\n\n\n"
        "func test_retry() -> void:\n"
        "    _attempt_count += 1\n"
        "    if _attempt_count < 2:\n"
        '        assert_true(false, "first attempt fails")\n',
        encoding="utf-8",
    )
    suite = NativeSuite(
        name="NativeRetrySuite",
        path="res://test/retry_suite.gd",
        tests=[NativeTest(name="test_retry", retries=1)],
    )

    result = run_native_tests(
        project,
        [suite],
        godot_bin,
        work_dir=tmp_path / "retry-orchestrated",
    )

    assert result.status == "passed"
    assert len(result.tests) == 1
    assert result.tests[0].status == "passed"
    assert result.tests[0].attempts == 2


def test_native_runner_supports_async_helpers(godot_bin, tmp_path):
    """Native tests can await process, physics, timer, and signal events."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "async-manifest.json"
    result_path = tmp_path / "async-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeAsyncHelpersSuite",
                        "path": "res://test/async_helpers_suite.gd",
                        "tests": [
                            {"name": "test_process_frame"},
                            {"name": "test_physics_frames"},
                            {"name": "test_timer"},
                            {"name": "test_signal"},
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
    assert payload["status"] == "passed"
    assert len(payload["tests"]) == 4
    assert all(test["status"] == "passed" for test in payload["tests"])


def test_native_orchestrator_runs_multiple_real_suites(godot_bin, tmp_path):
    """The Python orchestrator aggregates isolated real Godot processes."""
    project = _prepare_project(tmp_path, godot_bin)
    suites = [
        NativeSuite(
            name="NativeFixtureSuite",
            path="res://test/native_suite.gd",
            tests=[NativeTest(name="test_pass")],
        ),
        NativeSuite(
            name="NativeAsyncHelpersSuite",
            path="res://test/async_helpers_suite.gd",
            tests=[NativeTest(name="test_process_frame")],
        ),
    ]

    result = run_native_tests(
        project,
        suites,
        godot_bin,
        work_dir=tmp_path / "orchestrated",
    )

    assert result.status == "passed"
    assert len(result.tests) == 2
    assert {test.suite for test in result.tests} == {
        "NativeFixtureSuite",
        "NativeAsyncHelpersSuite",
    }
    assert all(test.status == "passed" for test in result.tests)


def test_native_orchestrator_continues_after_process_crash(godot_bin, tmp_path):
    """A crashed suite is recorded without hiding later suite results."""
    project = _prepare_project(tmp_path, godot_bin)
    crash_script = project / "test" / "native_crash_suite.gd"
    crash_script.write_text(
        "extends GdToolsTest\n\n\n"
        "func test_crashes_process() -> void:\n"
        '    OS.crash("intentional native crash")\n',
        encoding="utf-8",
    )
    suites = [
        NativeSuite(
            name="NativeCrashSuite",
            path="res://test/native_crash_suite.gd",
            tests=[NativeTest(name="test_crashes_process")],
        ),
        NativeSuite(
            name="NativeFixtureSuite",
            path="res://test/native_suite.gd",
            tests=[NativeTest(name="test_pass")],
        ),
    ]

    result = run_native_tests(
        project,
        suites,
        godot_bin,
        work_dir=tmp_path / "crash-orchestrated",
    )

    assert result.status == "error"
    assert any(
        test.suite == "NativeCrashSuite" and test.status == "error"
        for test in result.tests
    )
    assert any(
        test.suite == "NativeFixtureSuite" and test.status == "passed"
        for test in result.tests
    )


def test_native_command_runs_real_suite_and_writes_junit(
    godot_bin, tmp_path, monkeypatch
):
    """The native CLI adapter runs a real suite and produces JUnit output."""
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )
    junit_path = tmp_path / "native-results.xml"

    result = run_native_test_command(
        config,
        suite="NativeFixtureSuite",
        junit_xml=str(junit_path),
        timeout=30,
    )

    assert result.total == 2
    assert result.failed == 0
    assert result.junit_xml_path == junit_path
    assert junit_path.is_file()
    assert "test_pass" in junit_path.read_text(encoding="utf-8")


def test_native_command_runs_real_coverage(godot_bin, tmp_path, monkeypatch):
    """The native CLI adapter reuses the existing coverage report pipeline."""
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )

    result = run_native_test_command(
        config,
        suite="NativeCoverageSuite",
        coverage=True,
        timeout=30,
    )

    assert result.failed == 0
    assert result.coverage_data_path is not None
    assert result.coverage_data_path.is_file()
    assert (project / ".gd-tools" / "coverage" / "plan.json").is_file()


def test_native_runner_collects_line_and_branch_coverage(godot_bin, tmp_path):
    """Native coverage records statement and branch hits without GUT."""
    project = _prepare_project(tmp_path, godot_bin)
    plan_path = tmp_path / "native-plan.json"
    coverage_path = tmp_path / "native-coverage.json"
    result_path = tmp_path / "coverage-result.json"
    plan_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_by": "gd-tools-test",
                "files": [
                    {
                        "file_id": 0,
                        "path": "res://scripts/coverage_subject.gd",
                        "source_hash": "sha256:test",
                        "lines": [
                            {
                                "line": 5,
                                "id": 0,
                                "type": "branch",
                                "branch_type": "if_true",
                            },
                            {
                                "line": 6,
                                "id": 1,
                                "type": "statement",
                                "branch_type": None,
                            },
                            {
                                "line": 7,
                                "id": 2,
                                "type": "branch",
                                "branch_type": "if_false",
                            },
                            {
                                "line": 8,
                                "id": 3,
                                "type": "statement",
                                "branch_type": None,
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "coverage-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 1,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeCoverageSuite",
                        "path": "res://test/coverage_suite.gd",
                        "tests": [
                            {"name": "test_statement_and_branch_coverage"}
                        ],
                    }
                ],
                "coverage": {
                    "enabled": True,
                    "plan_path": str(plan_path),
                    "output_path": str(coverage_path),
                },
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
    assert coverage_path.is_file()
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert coverage["version"] == 1
    assert coverage["files"][0]["file_id"] == 0
    hits = coverage["files"][0]["hits"]
    assert hits["0"] > 0
    assert hits["1"] > 0
    assert hits["2"] > 0
    assert hits["3"] > 0
