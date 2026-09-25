"""Orchestrate isolated Godot processes for native test suites."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from pydantic import ValidationError

from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeManifest,
    NativeRunResult,
    NativeSuite,
    NativeTestResult,
    RuntimeMode,
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

    Returns:
        Aggregated native result. A process-level failure is represented as
        an error test and does not prevent later suites from running.
    """
    project_root = project_root.resolve()
    output_dir = work_dir or project_root / ".gd-tools" / "native"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    all_tests: list[NativeTestResult] = []
    coverage_shards: list[Path] = []
    coverage_output = _resolve_path(
        project_root,
        coverage.output_path if coverage and coverage.output_path else None,
    )
    has_failure = False
    has_error = False

    for index, suite in enumerate(suites):
        manifest_path = output_dir / f"suite-{index:04d}.manifest.json"
        result_path = output_dir / f"suite-{index:04d}.result.json"
        events_path = output_dir / f"suite-{index:04d}.events.ndjson"
        result_path.unlink(missing_ok=True)
        events_path.unlink(missing_ok=True)

        suite_coverage = coverage or NativeCoverage()
        if coverage and coverage.enabled:
            shard_path = output_dir / f"suite-{index:04d}.coverage.json"
            shard_path.unlink(missing_ok=True)
            coverage_shards.append(shard_path)
            suite_coverage = coverage.model_copy(
                update={"output_path": shard_path}
            )

        manifest = NativeManifest(
            project_root=project_root,
            runtime=RuntimeMode.NATIVE,
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
                "GD_TOOLS_NATIVE_RUN_ID": run_id,
            }
        )
        command = [
            godot_binary,
            "--headless",
            "--path",
            str(project_root),
            "--script",
            runner_script,
        ]

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
        except (subprocess.TimeoutExpired, TimeoutError) as exc:
            has_error = True
            all_tests.append(
                _process_error(
                    suite.name,
                    f"Godot process failed: {exc}",
                )
            )
            continue

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
                    )
                )
                continue
            all_tests.extend(parsed_result.tests)
            if parsed_result.status == "failed":
                has_failure = True
            elif parsed_result.status == "error":
                has_error = True
            continue

        has_error = True
        message_parts = [
            f"Godot process exited with code {completed.returncode}",
            completed.stdout.strip(),
            completed.stderr.strip(),
        ]
        all_tests.append(
            _process_error(
                suite.name,
                "; ".join(part for part in message_parts if part),
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
                )
            )

    if has_error:
        status = "error"
    elif has_failure:
        status = "failed"
    else:
        status = "passed"

    return NativeRunResult(
        run_id=run_id,
        status=status,
        tests=all_tests,
        coverage_data_path=merged_coverage_path,
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
    return _write_json_atomic(
        output_path,
        {
            "version": 1,
            "generated_at": generated_at,
            "files": files,
        },
    )


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


def _process_error(suite_name: str, message: str) -> NativeTestResult:
    return NativeTestResult(
        suite=suite_name,
        name="<process>",
        status="error",
        message=message,
        diagnostics={"kind": "process"},
    )
