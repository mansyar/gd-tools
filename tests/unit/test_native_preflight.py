"""Unit tests for the native Godot integration-preflight adapter."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeExecutionMode,
    NativeManifest,
    NativePreflightResult,
    NativeSuite,
    NativeSuiteIntegration,
    NativeTest,
    NativeTestIntegration,
    RuntimeMode,
    write_json_atomic,
)
from gd_tools.native_test.preflight import (
    NativePreflightError,
    run_native_preflight,
)

pytestmark = pytest.mark.unit


def _manifest(project_root: Path) -> NativeManifest:
    return NativeManifest(
        project_root=project_root,
        runtime=RuntimeMode.NATIVE,
        suites=[
            NativeSuite(
                name="IntegrationSuite",
                path="res://test/integration_suite.gd",
                integration=NativeSuiteIntegration(
                    scene="res://scenes/main.tscn",
                    resources={"config": "res://resources/config.tres"},
                    mode=NativeExecutionMode.WINDOWED,
                ),
                tests=[
                    NativeTest(
                        name="test_pass",
                        integration=NativeTestIntegration(
                            scene="res://scenes/test.tscn",
                            resources={"stats": "res://resources/stats.tres"},
                        ),
                    )
                ],
            )
        ],
        coverage=NativeCoverage(enabled=False),
    )


def _write_ok_result(manifest_path: Path, result_path: Path) -> None:
    manifest = NativeManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    write_json_atomic(
        result_path,
        NativePreflightResult(status="ok", suites=manifest.suites),
    )


def test_run_native_preflight_writes_one_manifest_and_runs_one_process(
    tmp_path,
):
    """One subprocess receives the manifest and structured result paths."""
    manifest = _manifest(tmp_path)
    run_dir = tmp_path / "artifacts" / "run-1"
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        _write_ok_result(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST"]),
            Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"]),
        )
        return subprocess.CompletedProcess(
            command, 0, "engine stdout", "engine stderr"
        )

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=fake_run,
    ) as run:
        result = run_native_preflight(
            tmp_path,
            manifest,
            godot_binary="godot",
            run_dir=run_dir,
            timeout_seconds=12.5,
        )

    assert result.status == "ok"
    assert result.suites[0].integration is not None
    assert result.suites[0].integration.mode == NativeExecutionMode.WINDOWED
    assert result.suites[0].tests[0].integration is not None
    assert run.call_count == 1
    assert calls[0][0] == [
        "godot",
        "--headless",
        "--path",
        str(tmp_path),
        "--script",
        "res://addons/gd-tools-test/gd_tools_test_preflight.gd",
        "--log-file",
        str(run_dir / "preflight.log"),
    ]
    assert calls[0][1]["capture_output"] is True
    assert calls[0][1]["text"] is True
    assert calls[0][1]["encoding"] == "utf-8"
    assert calls[0][1]["errors"] == "replace"
    assert calls[0][1]["timeout"] == 12.5
    assert calls[0][1]["check"] is False

    manifest_path = run_dir / "preflight.manifest.json"
    result_path = run_dir / "preflight.result.json"
    assert (
        NativeManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
        == manifest
    )
    assert json.loads(result_path.read_text(encoding="utf-8"))["status"] == "ok"


def test_run_native_preflight_isolates_runner_environment(
    tmp_path,
    monkeypatch,
):
    """Preflight paths replace stale runner variables without dropping the OS env."""
    monkeypatch.setenv("GD_TOOLS_EXISTING", "preserved")
    monkeypatch.setenv("GD_TOOLS_NATIVE_MANIFEST", "stale-manifest")
    monkeypatch.setenv("GD_TOOLS_NATIVE_RESULT", "stale-result")
    monkeypatch.setenv("GD_TOOLS_NATIVE_EVENTS", "stale-events")
    monkeypatch.setenv("GD_TOOLS_NATIVE_LOG", "stale-log")
    monkeypatch.setenv("GD_TOOLS_NATIVE_RUN_ID", "stale-run")
    observed_env = {}

    def fake_run(command, **kwargs):
        observed_env.update(kwargs["env"])
        _write_ok_result(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST"]),
            Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"]),
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=fake_run,
    ):
        run_native_preflight(
            tmp_path,
            _manifest(tmp_path),
            godot_binary="godot",
            run_dir=tmp_path / "run",
        )

    assert observed_env["GD_TOOLS_EXISTING"] == "preserved"
    assert observed_env["GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST"].endswith(
        "preflight.manifest.json"
    )
    assert observed_env["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"].endswith(
        "preflight.result.json"
    )
    for name in (
        "GD_TOOLS_NATIVE_MANIFEST",
        "GD_TOOLS_NATIVE_RESULT",
        "GD_TOOLS_NATIVE_EVENTS",
        "GD_TOOLS_NATIVE_LOG",
        "GD_TOOLS_NATIVE_RUN_ID",
    ):
        assert name not in observed_env


def test_run_native_preflight_removes_stale_result_and_reports_missing(
    tmp_path,
):
    """A successful process without fresh structured output is infrastructure failure."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    stale_result = run_dir / "preflight.result.json"
    stale_result.write_text('{"status":"ok"}', encoding="utf-8")

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        return_value=subprocess.CompletedProcess(
            ["godot"],
            0,
            "preflight succeeded",
            "",
        ),
    ):
        with pytest.raises(NativePreflightError) as exc_info:
            run_native_preflight(
                tmp_path,
                _manifest(tmp_path),
                godot_binary="godot",
                run_dir=run_dir,
            )

    assert "did not produce" in str(exc_info.value)
    assert str(stale_result) in str(exc_info.value)
    assert "exit code 0" in str(exc_info.value)
    assert "preflight succeeded" in str(exc_info.value)


def test_run_native_preflight_reports_timeout_with_process_output(tmp_path):
    """Timeout is bounded and retains stdout/stderr only as diagnostics."""
    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["godot"],
            timeout=3.0,
            output="partial stdout",
            stderr="partial stderr",
        ),
    ):
        with pytest.raises(NativePreflightError) as exc_info:
            run_native_preflight(
                tmp_path,
                _manifest(tmp_path),
                godot_binary="godot",
                run_dir=tmp_path / "run",
                timeout_seconds=3.0,
            )

    assert "timed out after 3.0 seconds" in str(exc_info.value)
    assert exc_info.value.stdout == "partial stdout"
    assert exc_info.value.stderr == "partial stderr"


def test_run_native_preflight_rejects_malformed_result_json(tmp_path):
    """Malformed JSON is reported at the result path without stdout parsing."""

    def fake_run(command, **kwargs):
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"])
        result_path.write_text("{not-json", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "looks successful", "")

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=fake_run,
    ):
        with pytest.raises(NativePreflightError) as exc_info:
            run_native_preflight(
                tmp_path,
                _manifest(tmp_path),
                godot_binary="godot",
                run_dir=tmp_path / "run",
            )

    assert "valid JSON" in str(exc_info.value)
    assert "preflight.result.json" in str(exc_info.value)
    assert "looks successful" in str(exc_info.value)


def test_run_native_preflight_rejects_protocol_v1_result(tmp_path):
    """A structured result with an unsupported protocol is an actionable error."""

    def fake_run(command, **kwargs):
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"])
        result_path.write_text(
            json.dumps(
                {
                    "protocol_version": 1,
                    "status": "ok",
                    "suites": [],
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, "", "")

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=fake_run,
    ):
        with pytest.raises(NativePreflightError) as exc_info:
            run_native_preflight(
                tmp_path,
                _manifest(tmp_path),
                godot_binary="godot",
                run_dir=tmp_path / "run",
            )

    assert "protocol_version" in str(exc_info.value)
    assert "preflight.result.json" in str(exc_info.value)


def test_run_native_preflight_raises_structured_status_error(tmp_path):
    """A valid exit-code-2 result becomes the adapter's actionable exception."""

    def fake_run(command, **kwargs):
        result_path = Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"])
        write_json_atomic(
            result_path,
            NativePreflightResult(
                status="error",
                error="INTEGRATION scene must start with 'res://'",
            ),
        )
        return subprocess.CompletedProcess(command, 2, "", "engine warning")

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=fake_run,
    ):
        with pytest.raises(NativePreflightError) as exc_info:
            run_native_preflight(
                tmp_path,
                _manifest(tmp_path),
                godot_binary="godot",
                run_dir=tmp_path / "run",
            )

    assert str(exc_info.value) == ("INTEGRATION scene must start with 'res://'")
    assert exc_info.value.exit_code == 2
    assert exc_info.value.stderr == "engine warning"


def test_run_native_preflight_rejects_status_exit_code_disagreement(tmp_path):
    """Structured status and process exit code must agree."""

    def fake_run(command, **kwargs):
        _write_ok_result(
            Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST"]),
            Path(kwargs["env"]["GD_TOOLS_NATIVE_PREFLIGHT_RESULT"]),
        )
        return subprocess.CompletedProcess(command, 2, "", "")

    with patch(
        "gd_tools.native_test.preflight.subprocess.run",
        side_effect=fake_run,
    ):
        with pytest.raises(NativePreflightError) as exc_info:
            run_native_preflight(
                tmp_path,
                _manifest(tmp_path),
                godot_binary="godot",
                run_dir=tmp_path / "run",
            )

    assert "status 'ok' disagrees with process exit code 2" in str(
        exc_info.value
    )
