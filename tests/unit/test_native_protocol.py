"""Unit tests for the native test protocol models."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from gd_tools.native_test.protocol import (
    NATIVE_PROTOCOL_VERSION,
    NativeCoverage,
    NativeExecutionMode,
    NativeManifest,
    NativePreflightResult,
    NativeRunResult,
    NativeSuite,
    NativeSuiteIntegration,
    NativeTest,
    NativeTestIntegration,
    NativeTestResult,
    RuntimeMode,
    write_json_atomic,
)

pytestmark = pytest.mark.unit


def _manifest(**overrides) -> NativeManifest:
    """Build a valid native manifest for tests."""
    values = {
        "project_root": Path("project"),
        "runtime": RuntimeMode.NATIVE,
        "suites": [
            NativeSuite(
                name="ExampleSuite",
                path="res://test/example_test.gd",
                tags=["smoke"],
                integration=NativeSuiteIntegration(
                    scene="res://tests/fixtures/player.tscn",
                    resources={"stats": "res://tests/fixtures/stats.tres"},
                    mode=NativeExecutionMode.WINDOWED,
                ),
                tests=[
                    NativeTest(
                        name="test_example",
                        tags=["fast"],
                        timeout_seconds=1.5,
                        integration=NativeTestIntegration(
                            scene="res://tests/fixtures/player_damaged.tscn",
                            resources={
                                "stats": "res://tests/fixtures/damaged_stats.tres"
                            },
                        ),
                    )
                ],
            )
        ],
        "coverage": NativeCoverage(
            enabled=True,
            plan_path=Path("coverage/plan.json"),
            output_path=Path("coverage/results.json"),
        ),
    }
    values.update(overrides)
    return NativeManifest(**values)


def test_manifest_defaults_to_current_protocol_version():
    """The manifest exposes the current protocol version."""
    assert _manifest().protocol_version == NATIVE_PROTOCOL_VERSION


def test_manifest_serializes_suite_test_and_coverage_metadata(tmp_path):
    """A manifest round-trips its complete native execution contract."""
    manifest = _manifest()

    path = write_json_atomic(tmp_path / "manifest.json", manifest)
    loaded = NativeManifest.model_validate(json.loads(path.read_text()))

    assert loaded.protocol_version == 2
    assert loaded.project_root == Path("project")
    assert loaded.runtime is RuntimeMode.NATIVE
    assert loaded.suites[0].name == "ExampleSuite"
    assert loaded.suites[0].integration is not None
    assert (
        loaded.suites[0].integration.scene == "res://tests/fixtures/player.tscn"
    )
    assert loaded.suites[0].integration.mode is NativeExecutionMode.WINDOWED
    assert loaded.suites[0].integration.resources == {
        "stats": "res://tests/fixtures/stats.tres"
    }
    assert loaded.suites[0].tests[0].name == "test_example"
    assert loaded.suites[0].tests[0].tags == ["fast"]
    assert loaded.suites[0].tests[0].timeout_seconds == 1.5
    assert loaded.suites[0].tests[0].integration is not None
    assert (
        loaded.suites[0].tests[0].integration.scene
        == "res://tests/fixtures/player_damaged.tscn"
    )
    assert loaded.suites[0].tests[0].integration.resources == {
        "stats": "res://tests/fixtures/damaged_stats.tres"
    }
    assert loaded.coverage.enabled is True
    assert loaded.coverage.plan_path == Path("coverage/plan.json")


def test_manifest_rejects_unsupported_protocol_version():
    """A future/invalid protocol version is rejected explicitly."""
    with pytest.raises(ValidationError):
        NativeManifest(
            protocol_version=NATIVE_PROTOCOL_VERSION + 1,
            project_root=Path("project"),
            runtime=RuntimeMode.NATIVE,
            suites=[],
        )


def test_manifest_rejects_non_positive_timeout():
    """Test timeout values must be positive."""
    with pytest.raises(ValidationError):
        NativeTest(name="test_example", timeout_seconds=0)


def test_manifest_rejects_unknown_runtime():
    """Only the explicitly supported runtime names are accepted."""
    with pytest.raises(ValidationError):
        NativeManifest(
            project_root=Path("project"),
            runtime="pytest",
            suites=[],
        )


def test_run_result_serializes_test_status_and_attempts(tmp_path):
    """Native results retain status, timing, and retry metadata."""
    result = NativeRunResult(
        run_id="run-123",
        status="failed",
        tests=[
            NativeTestResult(
                suite="ExampleSuite",
                name="test_example",
                status="failed",
                duration_seconds=0.25,
                attempts=2,
                message="Expected 2, got 3",
            )
        ],
    )

    path = write_json_atomic(tmp_path / "result.json", result)
    loaded = NativeRunResult.model_validate(json.loads(path.read_text()))

    assert loaded.protocol_version == NATIVE_PROTOCOL_VERSION
    assert loaded.run_id == "run-123"
    assert loaded.status == "failed"
    assert loaded.tests[0].status == "failed"
    assert loaded.tests[0].attempts == 2
    assert loaded.tests[0].message == "Expected 2, got 3"


def test_run_result_serializes_engine_diagnostics_and_timestamps(tmp_path):
    """Native results retain engine diagnostics and lifecycle timestamps."""
    result = NativeRunResult(
        run_id="run-diagnostics",
        status="error",
        started_at="2026-09-25T07:00:00",
        finished_at="2026-09-25T07:00:01",
        engine_errors=["native engine error"],
        engine_warnings=["native engine warning"],
    )

    path = write_json_atomic(tmp_path / "diagnostics.json", result)
    loaded = NativeRunResult.model_validate(json.loads(path.read_text()))

    assert loaded.started_at == "2026-09-25T07:00:00"
    assert loaded.finished_at == "2026-09-25T07:00:01"
    assert loaded.engine_errors == ["native engine error"]
    assert loaded.engine_warnings == ["native engine warning"]


def test_write_json_atomic_replaces_existing_file(tmp_path):
    """Atomic serialization replaces a previous result without extra files."""
    path = tmp_path / "result.json"
    path.write_text('{"old": true}', encoding="utf-8")

    write_json_atomic(path, _manifest())

    assert json.loads(path.read_text())["project_root"] == "project"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["result.json"]


def test_protocol_v2_is_current():
    """Python and Godot share the intentionally incremented protocol version."""
    assert NATIVE_PROTOCOL_VERSION == 2


def test_integration_defaults_to_headless_without_assets():
    """A suite without declarations remains an ordinary headless suite."""
    integration = NativeSuiteIntegration()

    assert integration.scene is None
    assert integration.resources == {}
    assert integration.mode is NativeExecutionMode.HEADLESS


@pytest.mark.parametrize(
    ("model", "metadata"),
    [
        (NativeSuiteIntegration, {"mode": "offscreen"}),
        (NativeSuiteIntegration, {"unexpected": True}),
        (NativeSuiteIntegration, {"resources": []}),
        (NativeSuiteIntegration, {"scene": 42}),
        (NativeTestIntegration, {"mode": "headless"}),
        (NativeTestIntegration, {"unexpected": True}),
        (NativeTestIntegration, {"resources": []}),
        (NativeTestIntegration, {"scene": 42}),
    ],
)
def test_integration_metadata_rejects_invalid_schema(model, metadata):
    """Unknown, malformed, and per-test mode metadata are rejected."""
    with pytest.raises(ValidationError):
        model(**metadata)


@pytest.mark.parametrize(
    "model", [NativeSuiteIntegration, NativeTestIntegration]
)
def test_integration_metadata_requires_res_scene_paths(model):
    """Primary scenes must use a non-empty res:// path."""
    with pytest.raises(ValidationError):
        model(scene="tests/fixtures/player.tscn")


@pytest.mark.parametrize(
    "model", [NativeSuiteIntegration, NativeTestIntegration]
)
def test_integration_metadata_requires_res_resource_paths(model):
    """Named resources must use non-empty res:// paths."""
    with pytest.raises(ValidationError):
        model(resources={"stats": "tests/fixtures/stats.tres"})


@pytest.mark.parametrize(
    "model", [NativeSuiteIntegration, NativeTestIntegration]
)
@pytest.mark.parametrize(
    "path", ["res://", "res://../outside.tscn", "res://a/../.."]
)
def test_integration_metadata_rejects_traversing_paths(model, path):
    """A res:// prefix alone is not enough; the whole path must be project-local."""
    with pytest.raises(ValidationError):
        if model is NativeSuiteIntegration:
            model(scene=path)
        else:
            model(resources={"stats": path})


def test_manifest_rejects_protocol_v1():
    """Protocol-v1 manifests are rejected after the v2 migration."""
    with pytest.raises(ValidationError):
        NativeManifest(
            protocol_version=1,
            project_root=Path("project"),
            runtime=RuntimeMode.NATIVE,
        )


def test_run_result_rejects_protocol_v1():
    """Protocol-v1 run results are rejected after the v2 migration."""
    with pytest.raises(ValidationError):
        NativeRunResult(
            protocol_version=1,
            run_id="run-v1",
            status="passed",
        )


def test_preflight_result_rejects_protocol_v1():
    """Protocol-v1 preflight results are rejected after the v2 migration."""
    with pytest.raises(ValidationError):
        NativePreflightResult(protocol_version=1, status="ok")


def test_preflight_result_round_trips_integration_metadata(tmp_path):
    """Preflight output atomically preserves effective suite/test metadata."""
    result = NativePreflightResult(
        status="ok",
        suites=[_manifest().suites[0]],
    )

    path = write_json_atomic(tmp_path / "preflight.json", result)
    loaded = NativePreflightResult.model_validate(json.loads(path.read_text()))

    assert loaded.protocol_version == 2
    assert loaded.status == "ok"
    assert loaded.error is None
    assert loaded.suites[0].integration is not None
    assert loaded.suites[0].integration.mode is NativeExecutionMode.WINDOWED
    assert loaded.suites[0].tests[0].integration is not None
    assert loaded.suites[0].tests[0].integration.resources == {
        "stats": "res://tests/fixtures/damaged_stats.tres"
    }
    assert sorted(item.name for item in tmp_path.iterdir()) == [
        "preflight.json"
    ]


@pytest.mark.parametrize(
    ("status", "error"),
    [
        ("ok", "unexpected error"),
        ("error", None),
        ("error", ""),
    ],
)
def test_preflight_result_requires_status_error_consistency(status, error):
    """Preflight status and error text must describe the same outcome."""
    with pytest.raises(ValidationError):
        NativePreflightResult(status=status, error=error)


def test_preflight_result_rejects_unknown_status():
    """Only successful and failed preflight states are accepted."""
    with pytest.raises(ValidationError):
        NativePreflightResult(status="partial")
