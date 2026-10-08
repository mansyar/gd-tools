"""Unit tests for native suite process orchestration."""

import itertools
import json
import os
import signal
import subprocess
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

import pytest

from gd_tools.errors import NativeInterruptError
from gd_tools.native_test import orchestrator as orchestrator_module
from gd_tools.native_test.artifacts import NativeArtifactLayout
from gd_tools.native_test.orchestrator import (
    _kill_process_tree,
    _merge_coverage_shards,
    _raise_interrupt,
    _sigterm_as_interrupt,
    _spawn_process,
    _SuiteOutcome,
    run_native_tests,
)
from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeExecutionMode,
    NativeSuite,
    NativeSuiteIntegration,
    NativeTest,
    RuntimeMode,
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
                "protocol_version": 4,
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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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


def test_bridge_suite_manifest_declares_suite_runtime(tmp_path):
    """Each per-suite manifest carries that suite's own runtime mode."""
    manifests = []

    def fake_run(args, **kwargs):
        manifests.append(
            json.loads(
                Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
            )
        )
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        return CompletedProcess(args, 0, "stdout", "stderr")

    bridge = NativeSuite(
        name="LegacySuite",
        path="res://test/legacy_test.gd",
        runtime=RuntimeMode.GUT,
        tests=[NativeTest(name="test_example")],
    )

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("NativeSuite"), bridge],
            godot_binary="godot",
        )

    assert result.status == "passed"
    assert manifests[0]["runtime"] == "native"
    assert manifests[1]["runtime"] == "gut"


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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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


def test_run_native_tests_publishes_coverage_omissions_in_the_index(tmp_path):
    """Omissions reported by the suites reach the published artifact index (AC 4)."""
    layout = NativeArtifactLayout.create(tmp_path, "run-1")
    warning = (
        "Coverage target omitted: res://scripts/missing_target.gd. "
        "The coverage plan references a file that no longer exists. "
        "Fix: The plan is stale. Re-run with --no-cache to regenerate it."
    )
    omission = {
        "file_id": 1,
        "path": "res://scripts/missing_target.gd",
        "reason": (
            "The coverage plan references a file that no longer exists: "
            "res://scripts/missing_target.gd"
        ),
        "fix": "The plan is stale. Re-run with --no-cache to regenerate it.",
    }

    def fake_run(args, **kwargs):
        _write_result(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"]),
            engine_warnings=[warning],
            run_diagnostics={"coverage_omissions": [omission]},
        )
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("ExampleSuite")],
            godot_binary="godot",
            artifact_layout=layout,
        )

    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert result.engine_warnings == [warning]
    assert result.diagnostics == {"coverage_omissions": [omission]}
    assert index["omitted"] == [omission]


def test_index_omitted_is_union_across_suites(tmp_path):
    """The run index ``omitted`` is the deduplicated union of every suite.

    Each suite process reports its own omissions in its result diagnostics;
    a machine consumer reading the index top-level must see every target
    omitted anywhere in the run, not just one suite's share of them.
    """
    layout = NativeArtifactLayout.create(tmp_path, "run-1")
    shared = {
        "file_id": 1,
        "path": "res://scripts/shared.gd",
        "reason": (
            "Trackers could not be injected, so the script did not reload "
            "(Godot error code 1): res://scripts/shared.gd"
        ),
        "fix": "exclude the file from the plan.",
    }
    first_only = {
        "file_id": 2,
        "path": "res://scripts/only_first.gd",
        "reason": "r1",
        "fix": "f1",
    }
    second_only = {
        "file_id": 3,
        "path": "res://scripts/only_second.gd",
        "reason": "r2",
        "fix": "f2",
    }

    def fake_run(args, **kwargs):
        manifest = json.loads(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
        )
        suite_name = manifest["suites"][0]["name"]
        omissions = [shared]
        omissions.append(
            first_only if suite_name == "FirstSuite" else second_only
        )
        _write_result(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"]),
            run_diagnostics={"coverage_omissions": omissions},
        )
        return CompletedProcess(args, 0, "", "")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            artifact_layout=layout,
        )

    index = json.loads(layout.index_path.read_text(encoding="utf-8"))
    expected = sorted(
        [shared, first_only, second_only], key=lambda omission: omission["path"]
    )
    assert sorted(index["omitted"], key=lambda o: o["path"]) == expected


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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
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

    def fake_run(args, **kwargs):
        raise TimeoutError("process timeout")

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree"),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("TimeoutSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "timed out after 60s" in result.tests[0].message


def test_run_native_tests_records_expired_process_timeout(tmp_path):
    """A real subprocess.TimeoutExpired is an infrastructure result too."""

    def fake_run(args, **kwargs):
        raise TimeoutExpired(
            cmd=["godot"], timeout=5.0, output="partial", stderr="err"
        )

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree"),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("TimeoutSuite")],
            godot_binary="godot",
        )

    assert result.status == "error"
    assert result.tests[0].status == "error"
    assert "timed out after 60s" in result.tests[0].message


# --- parallel suite execution (Phase 2) ---


def _result_for(suite_name: str, status: str = "passed") -> str:
    return json.dumps(
        {
            "protocol_version": 4,
            "run_id": "test-run",
            "status": status,
            "engine_warnings": [],
            "diagnostics": {},
            "tests": [
                {
                    "suite": suite_name,
                    "name": "test_example",
                    "status": status,
                    "duration_seconds": 0.01,
                    "attempts": 1,
                    "message": "",
                    "diagnostics": {},
                }
            ],
        }
    )


def _suite_name_from_env(kwargs) -> str:
    manifest = json.loads(
        Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
    )
    return manifest["suites"][0]["name"]


def test_parallel_runs_suites_concurrently(tmp_path):
    """Two suites with parallel=2 overlap in time (barrier proves it)."""
    barrier = threading.Barrier(2, timeout=5)
    calls = []

    def fake_run(args, **kwargs):
        calls.append(_suite_name_from_env(kwargs))
        barrier.wait()
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(
            _result_for(_suite_name_from_env(kwargs)), encoding="utf-8"
        )
        return CompletedProcess(args, 0, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            parallel=2,
        )

    assert sorted(calls) == ["FirstSuite", "SecondSuite"]
    assert result.status == "passed"
    assert len(result.tests) == 2


def test_parallel_bounded_worker_pool(tmp_path):
    """Three suites with parallel=2: all run, peak concurrency is 2."""
    lock = threading.Lock()
    state = {"inflight": 0, "peak": 0}
    barrier = threading.Barrier(2, timeout=5)
    barrier_arrivals = {"count": 0}

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        with lock:
            state["inflight"] += 1
            state["peak"] = max(state["peak"], state["inflight"])
            use_barrier = barrier_arrivals["count"] < 2
            if use_barrier:
                barrier_arrivals["count"] += 1
        try:
            if use_barrier:
                barrier.wait()
            result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
            result_path.write_text(_result_for(name), encoding="utf-8")
            return CompletedProcess(args, 0, "stdout", "stderr")
        finally:
            with lock:
                state["inflight"] -= 1

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite"), _suite("ThirdSuite")],
            godot_binary="godot",
            parallel=2,
        )

    assert state["peak"] == 2
    assert result.status == "passed"
    assert len(result.tests) == 3


def test_parallel_results_in_discovery_order(tmp_path):
    """Aggregated tests follow discovery order even when completion does not."""
    release_first = threading.Event()

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        if name == "FirstSuite":
            # Complete last: waits until SecondSuite has finished.
            assert release_first.wait(timeout=5)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        if name == "SecondSuite":
            release_first.set()
        return CompletedProcess(args, 0, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [
                _suite("FirstSuite"),
                _suite("SecondSuite"),
                _suite("ThirdSuite"),
            ],
            godot_binary="godot",
            parallel=3,
        )

    assert [test.suite for test in result.tests] == [
        "FirstSuite",
        "SecondSuite",
        "ThirdSuite",
    ]


def test_parallel_failure_does_not_cancel_other_suites(tmp_path):
    """A failing suite does not prevent its peers from completing."""

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        status = "failed" if name == "FirstSuite" else "passed"
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name, status), encoding="utf-8")
        returncode = 1 if status == "failed" else 0
        return CompletedProcess(args, returncode, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            parallel=2,
        )

    assert result.status == "failed"
    assert [(test.suite, test.status) for test in result.tests] == [
        ("FirstSuite", "failed"),
        ("SecondSuite", "passed"),
    ]


def test_parallel_matches_sequential_results(tmp_path):
    """A parallel run aggregates exactly like the sequential run."""

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        return CompletedProcess(args, 0, "stdout", "stderr")

    suites = [_suite("FirstSuite"), _suite("SecondSuite")]
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        sequential = run_native_tests(tmp_path, suites, godot_binary="godot")
        parallel = run_native_tests(
            tmp_path, suites, godot_binary="godot", parallel=2
        )

    assert parallel.status == sequential.status
    assert [
        (test.suite, test.name, test.status) for test in parallel.tests
    ] == [(test.suite, test.name, test.status) for test in sequential.tests]
    assert parallel.stdout == sequential.stdout
    assert parallel.stderr == sequential.stderr


def test_parallel_coverage_matches_sequential_merge(tmp_path):
    """Parallel runs merge coverage into a report identical to sequential."""

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        manifest = json.loads(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_MANIFEST"]).read_text()
        )
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        _write_result(result_path)
        shard_path = Path(manifest["coverage"]["output_path"])
        hits = {"0": 1 if name == "FirstSuite" else 2}
        shard_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "generated_at": "test",
                    "files": [{"file_id": 0, "hits": hits}],
                    "omitted": [{"file_id": 0, "reason": name}],
                }
            ),
            encoding="utf-8",
        )
        return CompletedProcess(args, 0, "", "")

    suites = [_suite("FirstSuite"), _suite("SecondSuite")]
    coverage_kwargs = {
        "coverage": NativeCoverage(
            enabled=True,
            plan_path=tmp_path / "plan.json",
            output_path=tmp_path / "coverage.json",
        )
    }
    (tmp_path / "plan.json").write_text("{}", encoding="utf-8")
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        sequential = run_native_tests(
            tmp_path, suites, godot_binary="godot", **coverage_kwargs
        )
        sequential_report = json.loads(
            sequential.coverage_data_path.read_text(encoding="utf-8")
        )
        parallel = run_native_tests(
            tmp_path,
            suites,
            godot_binary="godot",
            parallel=2,
            **coverage_kwargs,
        )
        parallel_report = json.loads(
            parallel.coverage_data_path.read_text(encoding="utf-8")
        )

    assert parallel_report == sequential_report
    assert parallel_report["files"][0]["hits"] == {"0": 3}
    assert parallel_report["omitted"] == sequential_report["omitted"]
    assert len(parallel_report["omitted"]) == 2


def test_parallel_one_runs_suites_in_discovery_order(tmp_path):
    """parallel=1 behaves like sequential execution, one suite at a time."""
    calls = []

    def fake_run(args, **kwargs):
        calls.append(_suite_name_from_env(kwargs))
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(
            _result_for(_suite_name_from_env(kwargs)), encoding="utf-8"
        )
        return CompletedProcess(args, 0, "stdout", "stderr")

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch(
            "gd_tools.native_test.orchestrator.ThreadPoolExecutor"
        ) as mock_pool,
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            parallel=1,
        )

    assert calls == ["FirstSuite", "SecondSuite"]
    assert result.status == "passed"
    mock_pool.assert_not_called()


def test_parallel_none_never_builds_a_pool(tmp_path):
    """The default (no --parallel) must not touch the pool machinery."""
    with (
        patch(
            "gd_tools.native_test.orchestrator.ThreadPoolExecutor"
        ) as mock_pool,
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(
                lambda args, **kwargs: CompletedProcess(
                    args, 0, "stdout", "stderr"
                )
            ),
        ),
    ):
        run_native_tests(
            tmp_path,
            [_suite("FirstSuite")],
            godot_binary="godot",
        )

    mock_pool.assert_not_called()


def test_parallel_timeout_fails_suite_and_queue_continues(tmp_path):
    """A timed-out suite fails its own slot; remaining suites still run."""
    calls = []

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        calls.append(name)
        if name == "FirstSuite":
            raise TimeoutExpired("godot", 60)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        return CompletedProcess(args, 0, "stdout", "stderr")

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree"),
    ):
        result = run_native_tests(
            tmp_path,
            [
                _suite("FirstSuite"),
                _suite("SecondSuite"),
                _suite("ThirdSuite"),
            ],
            godot_binary="godot",
            process_timeout=60,
            parallel=2,
        )

    assert sorted(calls) == ["FirstSuite", "SecondSuite", "ThirdSuite"]
    timeout_tests = [t for t in result.tests if t.suite == "FirstSuite"]
    assert len(timeout_tests) == 1
    assert timeout_tests[0].status == "error"
    assert "Godot process timed out after 60s" in timeout_tests[0].message
    assert result.status == "error"


def test_parallel_timeouts_are_independent_per_suite(tmp_path):
    """Each timed-out suite reports its own error, not a shared one."""

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        if name in {"FirstSuite", "ThirdSuite"}:
            raise TimeoutExpired("godot", 60)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        return CompletedProcess(args, 0, "stdout", "stderr")

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree"),
    ):
        result = run_native_tests(
            tmp_path,
            [
                _suite("FirstSuite"),
                _suite("SecondSuite"),
                _suite("ThirdSuite"),
            ],
            godot_binary="godot",
            process_timeout=60,
            parallel=2,
        )

    error_suites = [t.suite for t in result.tests if t.status == "error"]
    assert sorted(error_suites) == ["FirstSuite", "ThirdSuite"]
    assert result.status == "error"


def test_parallel_crashed_suite_does_not_block_queue(tmp_path):
    """A crashed suite (no result file) errors its slot; peers complete."""

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        if name == "SecondSuite":
            return CompletedProcess(args, -1073741819, "stdout", "crash")
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        return CompletedProcess(args, 0, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            parallel=2,
        )

    assert result.status == "error"
    assert [(t.suite, t.status) for t in result.tests] == [
        ("FirstSuite", "passed"),
        ("SecondSuite", "error"),
    ]


def test_parallel_junit_xml_preserves_discovery_order(tmp_path):
    """JUnit XML testcases stay in discovery order under parallel runs."""
    from gd_tools.native_test.command import _to_test_result

    release_first = threading.Event()

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        if name == "FirstSuite":
            assert release_first.wait(timeout=5)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        if name == "SecondSuite":
            release_first.set()
        return CompletedProcess(args, 0, "stdout", "stderr")

    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(fake_run),
    ):
        native = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            parallel=2,
        )

    junit_path = tmp_path / "results.xml"
    _to_test_result(native, tmp_path, str(junit_path))

    root = ET.parse(junit_path).getroot()
    classnames = [case.get("classname") for case in root.iter("testcase")]
    assert classnames == ["FirstSuite", "SecondSuite"]


# --- Task 4: interrupt handling (Popen seam, registry, tree kill, abort) ---


class _FakeProcess:
    """Minimal process stand-in for the spawn seam and the registry."""

    def __init__(self, pid):
        self.pid = pid
        self.returncode = None

    def communicate(self, timeout=None):
        return "stdout", "stderr"

    def poll(self):
        return self.returncode


class _FakePopen:
    """Adapts the existing CompletedProcess-style fakes to the Popen seam."""

    _counter = itertools.count(1000)

    def __init__(self, env, runner, args):
        self.pid = next(self._counter)
        self._env = env
        self._runner = runner
        self._args = args
        self.returncode = None
        self._pending_exception = None

    def communicate(self, timeout=None):
        if self._pending_exception is not None:
            # The runner already ran and failed; a reaped re-communicate
            # must not invoke it a second time.
            raise self._pending_exception
        try:
            outcome = self._runner(self._args, env=self._env)
        except Exception as exc:  # noqa: BLE001 - re-raised verbatim below
            self._pending_exception = exc
            raise
        if isinstance(outcome, CompletedProcess):
            self.returncode = outcome.returncode
            return outcome.stdout, outcome.stderr
        raise outcome

    def poll(self):
        return self.returncode


def _spawn_adapter(runner):
    """Wrap a fake_run(args, **kwargs) into the _spawn_process seam."""

    def adapt(command, *, env, registry, abort_event=None):
        process = _FakePopen(env, runner, command)
        registry.add(process)
        if abort_event is not None and abort_event.is_set():
            _kill_process_tree(process.pid)
            registry.remove(process)
        return process

    return adapt


def test_kill_process_tree_windows_uses_taskkill():
    """On Windows the tree kill shells out to taskkill /T /F."""
    with patch("gd_tools.native_test.orchestrator.subprocess.run") as taskkill:
        _kill_process_tree(4242, _platform="win32")

    taskkill.assert_called_once()
    assert taskkill.call_args.args[0] == [
        "taskkill",
        "/T",
        "/F",
        "/PID",
        "4242",
    ]
    assert taskkill.call_args.kwargs.get("check") is False


@pytest.mark.skipif(os.name != "posix", reason="POSIX process groups")
def test_kill_process_tree_posix_kills_process_group(monkeypatch):
    """On POSIX the kill targets the whole process group."""
    calls = []
    monkeypatch.setattr(orchestrator_module.os, "getpgid", lambda pid: 99)
    monkeypatch.setattr(
        orchestrator_module.os,
        "killpg",
        lambda pgid, sig: calls.append((pgid, sig)),
    )
    if not hasattr(orchestrator_module.signal, "SIGKILL"):
        # Some exotic POSIX platforms lack SIGKILL; create it for the test.
        monkeypatch.setattr(
            orchestrator_module.signal, "SIGKILL", 9, raising=False
        )

    _kill_process_tree(4242, _platform="linux")

    assert calls == [(99, signal.SIGKILL)]


@pytest.mark.skipif(os.name != "posix", reason="POSIX process groups")
def test_kill_process_tree_posix_falls_back_to_single_kill(monkeypatch):
    """If the group lookup fails, the direct kill is still attempted."""
    kills = []

    def boom(pid):
        raise ProcessLookupError

    def boom_killpg(pgid, sig):
        raise AssertionError("killpg must not run when the lookup fails")

    monkeypatch.setattr(orchestrator_module.os, "getpgid", boom)
    monkeypatch.setattr(orchestrator_module.os, "killpg", boom_killpg)
    if not hasattr(orchestrator_module.signal, "SIGKILL"):
        # Some exotic POSIX platforms lack SIGKILL; create it for the test.
        monkeypatch.setattr(
            orchestrator_module.signal, "SIGKILL", 9, raising=False
        )
    monkeypatch.setattr(
        orchestrator_module.os,
        "kill",
        lambda pid, sig: kills.append(pid),
    )

    _kill_process_tree(4242, _platform="linux")

    assert kills == [4242]


def test_spawn_process_registers_process_and_uses_popen():
    """_spawn_process creates the Popen with capture kwargs and registers."""
    registry = orchestrator_module._ProcessRegistry()
    with patch(
        "gd_tools.native_test.orchestrator.subprocess.Popen"
    ) as popen_cls:
        popen_cls.return_value = _FakeProcess(11)
        process = _spawn_process(
            ["godot", "--headless"], env={"X": "1"}, registry=registry
        )

    assert process is popen_cls.return_value
    kwargs = popen_cls.call_args.kwargs
    assert kwargs["stdout"] == subprocess.PIPE
    assert kwargs["stderr"] == subprocess.PIPE
    assert kwargs["text"] is True
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["env"] == {"X": "1"}
    if os.name == "posix":
        # Own session so the tree kill can take descendants via killpg.
        assert kwargs["start_new_session"] is True
    assert registry.snapshot() == [process]


def test_run_native_tests_interrupt_kills_processes_and_publishes_incomplete(
    tmp_path,
):
    """A KeyboardInterrupt kills every in-flight tree and marks the run."""
    layout = NativeArtifactLayout.create(tmp_path, "run-int")

    def fake_execute(index, suite, context):
        context.attempted.append(suite.name)
        context.registry.add(_FakeProcess(pid=700 + index))
        if index == 0:
            return _SuiteOutcome(tests=[])
        raise KeyboardInterrupt

    with (
        patch(
            "gd_tools.native_test.orchestrator._execute_suite",
            side_effect=fake_execute,
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree") as kill,
    ):
        with pytest.raises(NativeInterruptError) as excinfo:
            run_native_tests(
                tmp_path,
                [_suite("FirstSuite"), _suite("SecondSuite")],
                godot_binary="godot",
                artifact_layout=layout,
            )

    assert excinfo.value.exit_code == 130
    killed = sorted(call.args[0] for call in kill.call_args_list)
    assert killed == [700, 701]
    payload = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert payload["status"] == "incomplete"
    # Both suites had started execution when the interrupt hit (the second
    # raised mid-flight), so both appear in the incomplete index.
    assert [entry["suite"] for entry in payload["suites"]] == [
        "FirstSuite",
        "SecondSuite",
    ]


def test_run_native_tests_parallel_interrupt_stops_dispatch_and_kills(
    tmp_path,
):
    """A parallel interrupt cancels pending dispatch and kills workers."""
    shutdown_calls = []

    class _FakeFuture:
        def __init__(self, args, raise_interrupt):
            self._args = args
            self._raise_interrupt = raise_interrupt

        def result(self):
            index, _suite_obj, context = self._args
            context.registry.add(_FakeProcess(pid=800 + index))
            if self._raise_interrupt:
                raise KeyboardInterrupt
            return _SuiteOutcome(tests=[])

    class _FakeExecutor:
        def __init__(self, max_workers=None):
            self.max_workers = max_workers

        def submit(self, fn, *args):
            # First suite completes; the second is in flight when the
            # interrupt reaches the dispatch loop.
            index = args[0]
            return _FakeFuture(args, raise_interrupt=index == 1)

        def shutdown(self, wait=False, cancel_futures=False):
            shutdown_calls.append((wait, cancel_futures))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    executor = _FakeExecutor()
    with (
        patch(
            "gd_tools.native_test.orchestrator.ThreadPoolExecutor",
            return_value=executor,
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree") as kill,
    ):
        with pytest.raises(NativeInterruptError) as excinfo:
            run_native_tests(
                tmp_path,
                [_suite("FirstSuite"), _suite("SecondSuite")],
                godot_binary="godot",
                parallel=2,
            )

    assert excinfo.value.exit_code == 130
    assert (False, True) in shutdown_calls
    killed = sorted(call.args[0] for call in kill.call_args_list)
    assert killed == [800, 801]


def test_complete_run_never_publishes_incomplete_status(tmp_path):
    """Regression: a successful parallel run publishes its terminal status."""
    layout = NativeArtifactLayout.create(tmp_path, "run-ok")

    def runner(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        return CompletedProcess(args, 0, "stdout", "stderr")

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(runner),
        ),
        patch("gd_tools.native_test.orchestrator._kill_process_tree"),
    ):
        result = run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            artifact_layout=layout,
            parallel=2,
        )

    assert result.status == "passed"
    payload = json.loads(layout.index_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"


def test_sigterm_handler_raises_keyboard_interrupt():
    """The SIGTERM conversion handler raises KeyboardInterrupt."""
    with pytest.raises(KeyboardInterrupt):
        _raise_interrupt(signal.SIGTERM, None)


def test_sigterm_conversion_installs_and_restores_handler():
    """_sigterm_as_interrupt swaps the handler in and restores it after."""
    previous = signal.getsignal(signal.SIGTERM)
    with _sigterm_as_interrupt():
        assert signal.getsignal(signal.SIGTERM) is _raise_interrupt
    assert signal.getsignal(signal.SIGTERM) is previous


def _env_collecting_runner(envs):
    """Build a fake runner that records the per-suite environment."""

    def runner(args, **kwargs):
        envs.append(kwargs["env"])
        name = _suite_name_from_env(kwargs)
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_RESULT"])
        result_path.write_text(_result_for(name), encoding="utf-8")
        return CompletedProcess(args, 0, "stdout", "stderr")

    return runner


def test_suite_env_carries_suite_name_and_worker_slot(tmp_path):
    """Suite identity and scheduling slot flow to the runner via env."""
    envs = []
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(_env_collecting_runner(envs)),
    ):
        run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
        )

    assert [env["GD_TOOLS_SUITE_NAME"] for env in envs] == [
        "FirstSuite",
        "SecondSuite",
    ]
    assert [env["GD_TOOLS_WORKER_SLOT"] for env in envs] == ["0", "0"]


def test_suite_env_carries_snapshot_update_flag(tmp_path):
    """The snapshot-update flag flows to the runner as a 1-valued env var."""
    envs = []
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(_env_collecting_runner(envs)),
    ):
        run_native_tests(
            tmp_path,
            [_suite("FirstSuite")],
            godot_binary="godot",
            snapshot_update=True,
        )

    assert envs[0]["GD_TOOLS_SNAPSHOT_UPDATE"] == "1"


def test_suite_env_omits_snapshot_update_by_default(tmp_path):
    """Without the flag, no snapshot-update variable reaches the runner."""
    envs = []
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(_env_collecting_runner(envs)),
    ):
        run_native_tests(
            tmp_path,
            [_suite("FirstSuite")],
            godot_binary="godot",
        )

    assert "GD_TOOLS_SNAPSHOT_UPDATE" not in envs[0]


def test_worker_slot_cycles_across_pool(tmp_path):
    """The worker slot is the suite index modulo the worker count.

    Note the slot is a deterministic scheduling hint, not a unique
    in-flight worker identity: with ``parallel=2`` the suites at index 0
    and 2 can run concurrently and both legitimately report slot ``0``.
    """
    envs = []
    with patch(
        "gd_tools.native_test.orchestrator._spawn_process",
        side_effect=_spawn_adapter(_env_collecting_runner(envs)),
    ):
        run_native_tests(
            tmp_path,
            [
                _suite("FirstSuite"),
                _suite("SecondSuite"),
                _suite("ThirdSuite"),
            ],
            godot_binary="godot",
            parallel=2,
        )

    slots = sorted(
        (env["GD_TOOLS_SUITE_NAME"], env["GD_TOOLS_WORKER_SLOT"])
        for env in envs
    )
    assert slots == [
        ("FirstSuite", "0"),
        ("SecondSuite", "1"),
        ("ThirdSuite", "0"),
    ]


def test_parallel_interrupt_with_real_executor_kills_in_flight(tmp_path):
    """A real worker pool: the kill happens before the executor joins.

    Uses the actual ThreadPoolExecutor (not a fake) so the regression in
    which the interrupt handler only ran after ``Executor.__exit__`` had
    already joined every suite is caught: an in-flight suite's registered
    process must be killed while its worker is still blocked inside
    ``communicate``.
    """
    release = threading.Event()
    killed = []

    def fake_run(args, **kwargs):
        name = _suite_name_from_env(kwargs)
        if name == "FirstSuite":
            raise KeyboardInterrupt
        # SecondSuite blocks until its process tree is killed.
        assert release.wait(timeout=10), "suite was never killed"
        return CompletedProcess(args, 0, "stdout", "stderr")

    def fake_kill(pid, **kwargs):
        killed.append(pid)
        release.set()

    with (
        patch(
            "gd_tools.native_test.orchestrator._spawn_process",
            side_effect=_spawn_adapter(fake_run),
        ),
        patch(
            "gd_tools.native_test.orchestrator._kill_process_tree",
            side_effect=fake_kill,
        ),
        pytest.raises(NativeInterruptError) as excinfo,
    ):
        run_native_tests(
            tmp_path,
            [_suite("FirstSuite"), _suite("SecondSuite")],
            godot_binary="godot",
            parallel=2,
        )

    assert excinfo.value.exit_code == 130
    assert killed, "no in-flight process was killed"
