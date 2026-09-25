"""Orchestrate isolated Godot processes for native test suites."""

from __future__ import annotations

import os
import subprocess
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
    has_failure = False
    has_error = False

    for index, suite in enumerate(suites):
        manifest_path = output_dir / f"suite-{index:04d}.manifest.json"
        result_path = output_dir / f"suite-{index:04d}.result.json"
        events_path = output_dir / f"suite-{index:04d}.events.ndjson"
        result_path.unlink(missing_ok=True)
        events_path.unlink(missing_ok=True)

        manifest = NativeManifest(
            project_root=project_root,
            runtime=RuntimeMode.NATIVE,
            suites=[suite],
            coverage=coverage or NativeCoverage(),
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
    )


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
