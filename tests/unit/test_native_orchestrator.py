"""Unit tests for native suite process orchestration."""

import json
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

import pytest

from gd_tools.native_test.artifacts import NativeArtifactLayout
from gd_tools.native_test.orchestrator import (
    _merge_coverage_shards,
    run_native_tests,
)
from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeExecutionMode,
    NativeSuite,
    NativeSuiteIntegration,
    NativeTest,
)

pytestmark = pytest.mark.unit


def _suite(name: str) -> NativeSuite:
    return NativeSuite(
        name=name,
        path=f"res://test/{name.lower()}_test.gd",
        tests=[NativeTest(name="test_example")],
    )


def _write_result(
    result_path: Path,
    status: str = "passed",
    diagnostics: dict | None = None,
    engine_warnings: list[str] | None = None,
    run_diagnostics: dict | None = None,
) -> None:
    result_path.write_text(
        json.dumps(
            {
                "protocol_version": 2,
                "run_id": "test-run",
                "status": status,
                "engine_warnings": engine_warnings or [],
                "diagnostics": run_diagnostics or {},
                "tests": [
                    {
                        "suite": "ExampleSuite",
                        "name": "test_example",
                        "status": status,
                        "duration_seconds": 0.01,
                        "attempts": 1,
                        "message": "",
                        "diagnostics": diagnostics or {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_run_native_tests_uses_one_process_per_suite(tmp_path):
    """Each suite gets its own manifest and Godot process."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        manifest = json.loads(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
        )
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        assert len(manifest["suites"]) == 1
        return CompletedProcess(args, 0, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
        )

    assert len(calls) == 2
    assert result.status == "passed"
    assert len(result.tests) == 2
    assert all("--headless" in call[0] for call in calls)


def test_run_result_aggregates_engine_warnings_and_coverage_omissions(tmp_path):
    """R5: omissions ride the existing channels into the aggregated result.

    Every suite process instruments the whole plan, so the same omission is
    reported by each shard; the aggregate must carry it once, not per suite.
    """
    omission = {
        "file_id": 1,
        "path": "res://scripts/missing_target.gd",
        "reason": (
            "The coverage plan references a file that no longer exists: "
            "res://scripts/missing_target.gd"
        ),
        "fix": "The plan is stale. Re-run with --no-cache to regenerate it.",
    }
    warning = "Skipped uninstrumentable coverage target: missing_target.gd"

    def fake_run(args, **kwargs):
        _write_result(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"]),
            engine_warnings=[warning],
            run_diagnostics={"coverage_omissions": [omission]},
        )
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
        )

    assert result.engine_warnings == [warning]
    assert result.diagnostics == {"coverage_omissions": [omission]}


def test_merge_coverage_shards_unions_omitted_targets(tmp_path):
    """Shard merging keeps the collector-reported omission reasons.

    Every shard instruments the same plan, so the same omission appears in
    each; the merged coverage data must carry it once, with the reason intact.
    """
    omission = {
        "file_id": 1,
        "path": "res://scripts/missing_target.gd",
        "reason": "stale plan",
        "fix": "re-run with --no-cache",
    }
    shard1 = tmp_path / "suite-0000.coverage.json"
    shard1.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-01-01T00:00:00Z",
                "files": [{"file_id": 0, "hits": {"0": 1}}],
                "omitted": [omission],
            }
        ),
        encoding="utf-8",
    )
    shard2 = tmp_path / "suite-0001.coverage.json"
    shard2.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-01-01T00:00:01Z",
                "files": [],
                "omitted": [omission],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "merged.coverage.json"

    assert _merge_coverage_shards([shard1, shard2], output)

    merged = json.loads(output.read_text(encoding="utf-8"))
    assert merged["omitted"] == [omission]
    assert merged["files"] == [{"file_id": 0, "hits": {"0": 1}}]


def test_run_native_tests_publishes_run_index_and_prunes_old_runs(tmp_path):
    """A completed run records suite paths before retaining the latest run."""
    old_run = tmp_path / ".gd-tools" / "artifacts" / "old-run"
    old_run.mkdir(parents=True)
    (old_run / "artifacts.json").write_text("old", encoding="utf-8")
    layout = NativeArtifactLayout.create(tmp_path, "run-1")

    def fake_run(args, **kwargs):
        _write_result(Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"]))
        assert kwargs["env"]["GD_TOOLS_NATIVE_SCREENSHOT"] == str(
            layout.suite_paths(0)["screenshot_base"]
        )
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("ExampleSuite")],
            godot_binary="godot",
            artifact_layout=layout,
        )

    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert result.status == "passed"
    assert result.artifact_index_path == layout.index_path
    assert index["run_id"] == "run-1"
    assert index["suites"][0]["suite"] == "ExampleSuite"
    assert index["suites"][0]["result"] == str(layout.suite_paths(0)["result"])
    assert "screenshot" not in index["suites"][0]
    assert not old_run.exists()


def test_run_native_tests_passes_screenshot_base_and_indexes_captures(
    tmp_path,
):
    """The runner gets a per-suite screenshot base, and captures are indexed."""
    layout = NativeArtifactLayout.create(tmp_path, "run-1")
    captured = layout.native_dir / "suite-0000.test_example.failure.png"

    def fake_run(args, **kwargs):
        assert kwargs["env"]["GD_TOOLS_NATIVE_SCREENSHOT"] == str(
            layout.suite_paths(0)["screenshot_base"]
        )
        captured.parent.mkdir(parents=True, exist_ok=True)
        captured.write_bytes(b"png")
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path, diagnostics={"screenshot": str(captured)})
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("ExampleSuite")],
            godot_binary="godot",
            artifact_layout=layout,
        )

    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert result.status == "passed"
    assert index["suites"][0]["screenshots"] == [str(captured)]


def test_run_native_tests_republishes_index_when_retention_fails(tmp_path):
    """A prune failure must not leave a passing index beside an error exit."""
    layout = NativeArtifactLayout.create(tmp_path, "run-1")

    def fake_run(args, **kwargs):
        _write_result(Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"]))
        return CompletedProcess(args, 0, "", "")

    with (
        patch(
            "gd_tools.native_test.orchestrator.subprocess.run",
            side_effect=fake_run,
        ),
        patch(
            "gd_tools.native_test.artifacts._prune_old_runs",
            side_effect=OSError("cannot remove old run"),
        ),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("ExampleSuite")],
            godot_binary="godot",
            artifact_layout=layout,
        )

    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert result.status == "error"
    assert index["status"] == "error"
    assert "prune" in result.tests[-1].message.lower()


def test_run_native_tests_omits_headless_for_windowed_suite(tmp_path):
    """A windowed suite uses the same runner without the headless flag."""
    suite = _suite("WindowedSuite").model_copy(
        update={
            "integration": NativeSuiteIntegration(
                mode=NativeExecutionMode.WINDOWED
            )
        }
    )

    def fake_run(args, **kwargs):
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ) as run:
        result = run_native_tests(
            tmp_path,
            [suite],
            godot_binary="godot",
        )

    command = run.call_args.args[0]
    assert "--headless" not in command
    assert result.status == "passed"


def test_run_native_tests_continues_after_process_failure(tmp_path):
    """A suite process failure is recorded and later suites still run."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            return CompletedProcess(args, 2, "startup failed", "missing runner")

        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("BrokenSuite"), _suite("WorkingSuite")],
            godot_binary="godot",
        )

    assert len(calls) == 2
    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert result.tests[1].status == "passed"
    assert "startup failed" in result.tests[0].message


def test_run_native_tests_rejects_inconsistent_process_result(tmp_path):
    """A nonzero process code cannot be masked by a passing result file."""

    def fake_run(args, **kwargs):
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 1, "test failed", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("InconsistentSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "process exit code 1" in result.tests[0].message


def test_run_native_tests_merges_coverage_shards(tmp_path):
    """Per-suite coverage files are merged into the final configured path."""
    final_coverage = tmp_path / "coverage.json"
    plan_path = tmp_path / "plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        manifest = json.loads(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
        )
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        shard_path = Path(manifest["coverage"]["output_path"])
        assert shard_path != final_coverage
        hit_count = len(calls)
        shard_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "test",
                    "files": [{"file_id": 0, "hits": {"0": hit_count}}],
                }
            ),
            encoding="utf-8",
        )
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=fake_run,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            coverage=NativeCoverage(
                enabled=True,
                plan_path=plan_path,
                output_path=final_coverage,
            ),
        )

    merged = json.loads(final_coverage.read_text(encoding="utf-8"))
    assert merged["files"][0]["hits"]["0"] == 3
    assert result.coverage_data_path == final_coverage


def test_run_native_tests_records_subprocess_timeout(tmp_path):
    """A subprocess timeout becomes an infrastructure result."""
    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=TimeoutError("process timeout"),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("TimeoutSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "process timeout" in result.tests[0].message


def test_run_native_tests_records_expired_process_timeout(tmp_path):
    """A real subprocess.TimeoutExpired is an infrastructure result too."""
    with patch(
        "gd_tools.native_test.orchestrator.subprocess.run",
        side_effect=TimeoutExpired(
            cmd=["godot"], timeout=5.0, output="partial", stderr="err"
        ),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("TimeoutSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "Godot process failed" in result.tests[0].message
