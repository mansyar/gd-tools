"""Orchestrate isolated Godot processes for native test suites."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gd_tools.native_test.artifacts import (
    ArtifactPublishError,
    NativeArtifactLayout,
    publish_artifact_index,
)
from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeExecutionMode,
    NativeManifest,
    NativeRunResult,
    NativeSuite,
    NativeTestResult,
    write_json_atomic,
)

DEFAULT_RUNNER_SCRIPT = "res://addons/gd-tools-test/gd_tools_test_runner.gd"


def run_native_tests(
    project_root: Path,
    suites: list[NativeSuite],
    godot_binary: str,
    *,
    coverage: NativeCoverage | None = None,
    runner_script: str = DEFAULT_RUNNER_SCRIPT,
    process_timeout: float = 60.0,
    work_dir: Path | None = None,
    run_id: str | None = None,
    artifact_layout: NativeArtifactLayout | None = None,
) -> NativeRunResult:
    """Run each native suite in an isolated Godot process.

    Args:
        project_root: Godot project root.
        suites: Suites to execute.
        godot_binary: Godot executable path.
        coverage: Optional native coverage settings.
        runner_script: Godot resource path for the native runner.
        process_timeout: Maximum seconds allowed for each Godot process.
        work_dir: Directory for per-suite manifests and results. Defaults to
            ``<project_root>/.gd-tools/native``.
        run_id: Optional identifier shared with the integration preflight.
        artifact_layout: Optional run-scoped layout for publishing an artifact
            index and retaining only the latest run.

    Returns:
        Aggregated native result. A process-level failure is represented as
        an error test and does not prevent later suites from running.
    """
    project_root = project_root.resolve()
    if artifact_layout is not None:
        if run_id is not None and run_id != artifact_layout.run_id:
            raise ValueError("run_id does not match artifact layout")
        run_id = artifact_layout.run_id
        output_dir = artifact_layout.native_dir
    else:
        run_id = run_id or uuid.uuid4().hex
        output_dir = work_dir or project_root / ".gd-tools" / "native"
    output_dir.mkdir(parents=True, exist_ok=True)
    all_tests: list[NativeTestResult] = []
    coverage_shards: list[Path] = []
    coverage_output = _resolve_path(
        project_root,
        coverage.output_path if coverage and coverage.output_path else None,
    )
    has_failure = False
    has_error = False
    process_stdout: list[str] = []
    process_stderr: list[str] = []
    suite_artifact_paths: list[dict[str, Any]] = []
    engine_warnings: list[str] = []
    coverage_omissions: list[dict[str, Any]] = []

    for index, suite in enumerate(suites):
        if artifact_layout is not None:
            suite_paths = artifact_layout.suite_paths(index)
            manifest_path = suite_paths["manifest"]
            result_path = suite_paths["result"]
            events_path = suite_paths["events"]
            log_path = suite_paths["log"]
            screenshot_path = suite_paths["screenshot_base"]
            suite_artifact_paths.append(suite_paths)
        else:
            manifest_path = output_dir / f"suite-{index:04d}.manifest.json"
            result_path = output_dir / f"suite-{index:04d}.result.json"
            events_path = output_dir / f"suite-{index:04d}.events.ndjson"
            log_path = output_dir / f"suite-{index:04d}.log"
            screenshot_path = output_dir / f"suite-{index:04d}"
        result_path.unlink(missing_ok=True)
        events_path.unlink(missing_ok=True)
        log_path.unlink(missing_ok=True)

        suite_coverage = coverage or NativeCoverage()
        if coverage and coverage.enabled:
            shard_path = (
                suite_paths["coverage"]
                if artifact_layout is not None
                else output_dir / f"suite-{index:04d}.coverage.json"
            )
            shard_path.unlink(missing_ok=True)
            coverage_shards.append(shard_path)
            suite_coverage = coverage.model_copy(
                update={"output_path": shard_path}
            )

        manifest = NativeManifest(
            project_root=project_root,
            runtime=suite.runtime,
            suites=[suite],
            coverage=suite_coverage,
        )
        write_json_atomic(manifest_path, manifest)
        env = os.environ.copy()
        env.update(
            {
                "GD_TOOLS_NATIVE_MANIFEST": str(manifest_path),
                "GD_TOOLS_NATIVE_RESULT": str(result_path),
                "GD_TOOLS_NATIVE_EVENTS": str(events_path),
                "GD_TOOLS_NATIVE_LOG": str(log_path),
                "GD_TOOLS_NATIVE_SCREENSHOT": str(screenshot_path),
                "GD_TOOLS_NATIVE_RUN_ID": run_id,
            }
        )
        command = [godot_binary]
        if (
            suite.integration is None
            or suite.integration.mode == NativeExecutionMode.HEADLESS
        ):
            command.append("--headless")
        command.extend(
            [
                "--path",
                str(project_root),
                "--script",
                runner_script,
                "--log-file",
                str(log_path),
            ]
        )

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=process_timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, TimeoutError):
            has_error = True
            all_tests.append(
                _process_error(
                    suite.name,
                    f"Godot process timed out after {process_timeout:g}s "
                    f"running suite {suite.name!r}",
                    diagnostics={
                        "kind": "process",
                        "expected": f"completion within {process_timeout:g}s",
                        "found": "timeout",
                        "remedy": (
                            "increase the timeout (--timeout or "
                            "[test].timeout_seconds) and re-run"
                        ),
                    },
                )
            )
            continue
        except KeyboardInterrupt:
            # subprocess.run kills the in-flight Godot child when the
            # interrupt arrives (its Popen context manager kills on any
            # exception), and this loop stops spawning further suites once
            # the interrupt propagates. Record the run as incomplete so an
            # interrupted run is never mistaken for a passing one, then let
            # the interrupt keep propagating to the CLI.
            _publish_incomplete_index(
                artifact_layout,
                [attempted.name for attempted in suites[: index + 1]],
                suite_artifact_paths,
            )
            raise

        if completed.stdout:
            process_stdout.append(completed.stdout)
        if completed.stderr:
            process_stderr.append(completed.stderr)
        parsed_result = _read_native_result(result_path)
        if parsed_result is not None:
            expected_returncode = {
                "passed": 0,
                "failed": 1,
                "error": 2,
                "cancelled": 1,
            }[parsed_result.status]
            if completed.returncode != expected_returncode:
                has_error = True
                all_tests.append(
                    _process_error(
                        suite.name,
                        "Native result status "
                        f"{parsed_result.status} disagrees with process exit "
                        f"code {completed.returncode}",
                        diagnostics={
                            "kind": "protocol",
                            "expected": (
                                f"exit code {expected_returncode} for status "
                                f"'{parsed_result.status}'"
                            ),
                            "found": f"exit code {completed.returncode}",
                            "remedy": (
                                "re-run the suite directly to reproduce; "
                                "report this if it persists"
                            ),
                        },
                    )
                )
                continue
            parsed_result = parsed_result.model_copy(
                update={
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            )
            all_tests.extend(parsed_result.tests)
            # R5: omissions and warnings ride the existing channels. Every
            # suite instruments the whole plan, so the same omission arrives
            # from each shard; dedupe to keep the aggregate honest.
            for warning in parsed_result.engine_warnings:
                if warning not in engine_warnings:
                    engine_warnings.append(warning)
            for omission in parsed_result.diagnostics.get(
                "coverage_omissions", []
            ):
                if omission not in coverage_omissions:
                    coverage_omissions.append(omission)
            if artifact_layout is not None:
                suite_artifact_paths[-1]["screenshots"] = [
                    Path(test.diagnostics["screenshot"])
                    for test in parsed_result.tests
                    if test.diagnostics.get("screenshot")
                ]
            if parsed_result.status == "failed":
                has_failure = True
            elif parsed_result.status == "error":
                has_error = True
            continue

        has_error = True
        if result_path.is_file():
            # The runner wrote something it cannot be parsed as a protocol
            # v2 result: a protocol mismatch rather than an engine crash.
            kind = "protocol"
            remedy = (
                "the runner wrote an unreadable result.json; verify the "
                "gd-tools addon version matches the CLI protocol and re-run"
            )
            found = "unparseable result.json"
        else:
            kind = "engine"
            remedy = (
                f"inspect the engine log under {log_path.parent} and "
                "re-run the suite directly"
            )
            found = "no result.json"
        message_parts = [
            f"Godot process exited with code {completed.returncode} "
            f"({found})",
            completed.stdout.strip(),
            completed.stderr.strip(),
        ]
        all_tests.append(
            _process_error(
                suite.name,
                "; ".join(part for part in message_parts if part),
                diagnostics={
                    "kind": kind,
                    "expected": "a parseable protocol v2 result.json",
                    "found": found,
                    "remedy": remedy,
                },
            )
        )

    merged_coverage_path: Path | None = None
    if coverage and coverage.enabled:
        merged_coverage_path = coverage_output
        if not _merge_coverage_shards(coverage_shards, merged_coverage_path):
            has_error = True
            all_tests.append(
                _process_error(
                    "<coverage>",
                    "Unable to merge native coverage shards",
                    diagnostics={
                        "kind": "coverage",
                        "expected": "valid protocol v1 coverage shards",
                        "found": "missing or invalid shard",
                        "remedy": (
                            "re-run with --coverage and --no-cache, or "
                            "run without --coverage"
                        ),
                    },
                )
            )

    if has_error:
        status = "error"
    elif has_failure:
        status = "failed"
    else:
        status = "passed"

    artifact_index_path: Path | None = None
    if artifact_layout is not None:
        try:
            artifact_index_path = publish_artifact_index(
                artifact_layout,
                status=status,
                suite_names=[suite.name for suite in suites],
                suite_paths=suite_artifact_paths,
                preflight_paths=artifact_layout.preflight_paths(),
                omitted=coverage_omissions or None,
            )
        except ArtifactPublishError as exc:
            has_error = True
            all_tests.append(_process_error("<artifacts>", str(exc)))
            # Retention runs after the index is written, so a retention-only
            # failure leaves an index that disagrees with the reported status.
            # Republish so the recorded status always matches the exit code.
            try:
                artifact_index_path = publish_artifact_index(
                    artifact_layout,
                    status="error",
                    suite_names=[suite.name for suite in suites],
                    suite_paths=suite_artifact_paths,
                    preflight_paths=artifact_layout.preflight_paths(),
                    omitted=coverage_omissions or None,
                )
            except ArtifactPublishError:
                pass
            status = "error"

    return NativeRunResult(
        run_id=run_id,
        status=status,
        tests=all_tests,
        coverage_data_path=merged_coverage_path,
        artifact_index_path=artifact_index_path,
        engine_warnings=engine_warnings,
        diagnostics=(
            {"coverage_omissions": coverage_omissions}
            if coverage_omissions
            else {}
        ),
        stdout="\n".join(process_stdout),
        stderr="\n".join(process_stderr),
    )


def _resolve_path(project_root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else project_root / path


def _merge_coverage_shards(
    shard_paths: list[Path], output_path: Path | None
) -> bool:
    if output_path is None or not shard_paths:
        return False

    merged: dict[int, dict[int, int]] = {}
    generated_at = ""
    omitted: list[dict[str, Any]] = []
    for shard_path in shard_paths:
        if not shard_path.is_file():
            continue
        try:
            data = json.loads(shard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(data, dict) or data.get("version") != 1:
            return False
        generated_at = str(data.get("generated_at", generated_at))
        # R5: carry the collector-reported omissions into the merged data so
        # the terminal report keeps the real reasons instead of generic
        # fallbacks. Every shard instruments the same plan, so dedupe.
        for omission in data.get("omitted", []):
            if isinstance(omission, dict) and omission not in omitted:
                omitted.append(omission)
        for file_data in data.get("files", []):
            file_id = int(file_data.get("file_id", -1))
            if file_id < 0:
                return False
            file_hits = merged.setdefault(file_id, {})
            for line_id, count in file_data.get("hits", {}).items():
                file_hits[int(line_id)] = file_hits.get(int(line_id), 0) + int(
                    count
                )

    files = [
        {
            "file_id": file_id,
            "hits": {str(line_id): count for line_id, count in hits.items()},
        }
        for file_id, hits in sorted(merged.items())
    ]
    payload: dict[str, Any] = {
        "version": 1,
        "generated_at": generated_at,
        "files": files,
    }
    if omitted:
        payload["omitted"] = omitted
    return _write_json_atomic(output_path, payload)


def _write_json_atomic(path: Path, data: dict) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        return True
    except (OSError, TypeError, ValueError):
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        return False


def _read_native_result(path: Path) -> NativeRunResult | None:
    if not path.is_file():
        return None
    try:
        return NativeRunResult.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValidationError, ValueError):
        return None


def _publish_incomplete_index(
    artifact_layout: NativeArtifactLayout | None,
    attempted_suites: list[str],
    suite_artifact_paths: list[dict[str, Any]],
) -> None:
    """Publish an artifact index recording an interrupted run.

    Best-effort: a publish failure must not mask the interrupt, so the
    exception is swallowed and the interrupt keeps propagating either way.
    """
    if artifact_layout is None:
        return
    try:
        publish_artifact_index(
            artifact_layout,
            status="incomplete",
            suite_names=attempted_suites,
            suite_paths=suite_artifact_paths,
            preflight_paths=artifact_layout.preflight_paths(),
        )
    except (ArtifactPublishError, ValueError, OSError):
        pass


def _process_error(
    suite_name: str,
    message: str,
    diagnostics: dict[str, Any] | None = None,
) -> NativeTestResult:
    return NativeTestResult(
        suite=suite_name,
        name="<process>",
        status="error",
        message=message,
        diagnostics=diagnostics or {"kind": "process"},
    )
