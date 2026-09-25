"""Python adapter for the native Godot integration-preflight process."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from pydantic import ValidationError

from gd_tools.errors import GdToolsError

from .protocol import (
    NativeManifest,
    NativePreflightResult,
    write_json_atomic,
)

PREFLIGHT_SCRIPT = "res://addons/gd-tools-test/gd_tools_test_preflight.gd"
_RUNNER_ENVIRONMENT_KEYS = (
    "GD_TOOLS_NATIVE_MANIFEST",
    "GD_TOOLS_NATIVE_RESULT",
    "GD_TOOLS_NATIVE_EVENTS",
    "GD_TOOLS_NATIVE_LOG",
    "GD_TOOLS_NATIVE_RUN_ID",
)


class NativePreflightError(GdToolsError):
    """Infrastructure or declaration failure from native integration preflight."""

    def __init__(
        self,
        message: str,
        *,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """Initialize an exit-code-2 preflight error with process diagnostics."""
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


def run_native_preflight(
    project_root: Path,
    manifest: NativeManifest,
    *,
    godot_binary: str,
    run_dir: Path,
    timeout_seconds: float = 30.0,
) -> NativePreflightResult:
    """Run one structured Godot preflight and return its enriched manifest.

    The caller must import the project before invoking this boundary. Human
    process output is retained only as exception diagnostics; the result file is
    the sole source of truth for preflight status.

    Args:
        project_root: Imported Godot project root.
        manifest: Protocol-v2 discovery manifest to resolve.
        godot_binary: Resolved Godot executable.
        run_dir: Directory receiving manifest, result, and engine log files.
        timeout_seconds: Maximum duration for the preflight process.

    Returns:
        The validated protocol-v2 preflight result.

    Raises:
        NativePreflightError: If the process times out or returns an invalid,
            missing, or unsuccessful structured result.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")

    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / "preflight.manifest.json"
    result_path = run_dir / "preflight.result.json"
    log_path = run_dir / "preflight.log"
    write_json_atomic(manifest_path, manifest)
    result_path.unlink(missing_ok=True)
    log_path.unlink(missing_ok=True)

    env = os.environ.copy()
    for key in _RUNNER_ENVIRONMENT_KEYS:
        env.pop(key, None)
    env.update(
        {
            "GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST": str(manifest_path),
            "GD_TOOLS_NATIVE_PREFLIGHT_RESULT": str(result_path),
        }
    )
    command = [
        godot_binary,
        "--headless",
        "--path",
        str(project_root),
        "--script",
        PREFLIGHT_SCRIPT,
        "--log-file",
        str(log_path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout_seconds,
            check=False,
        )
    except (subprocess.TimeoutExpired, TimeoutError) as exc:
        raise NativePreflightError(
            "Godot integration preflight timed out after "
            f"{timeout_seconds} seconds",
            stdout=_process_text(getattr(exc, "stdout", None)),
            stderr=_process_text(getattr(exc, "stderr", None)),
        ) from exc

    result = _read_preflight_result(
        result_path,
        process_exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    expected_exit_code = 0 if result.status == "ok" else 2
    if completed.returncode != expected_exit_code:
        raise NativePreflightError(
            f"Native integration preflight status '{result.status}' disagrees "
            f"with process exit code {completed.returncode}",
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    if result.status == "error":
        raise NativePreflightError(
            result.error
            or "Godot integration preflight reported an unknown error",
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    return result


def _read_preflight_result(
    result_path: Path,
    *,
    process_exit_code: int,
    stdout: str,
    stderr: str,
) -> NativePreflightResult:
    if not result_path.is_file():
        message = (
            "Godot integration preflight did not produce a structured result at "
            f"'{result_path}' (process exit code {process_exit_code})"
        )
        message = _append_process_output(message, stdout, stderr)
        raise NativePreflightError(message, stdout=stdout, stderr=stderr)

    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        message = (
            "Godot integration preflight did not write valid JSON at "
            f"'{result_path}': {exc}"
        )
        message = _append_process_output(message, stdout, stderr)
        raise NativePreflightError(
            message, stdout=stdout, stderr=stderr
        ) from exc

    try:
        return NativePreflightResult.model_validate(payload)
    except ValidationError as exc:
        message = (
            "Godot integration preflight result at "
            f"'{result_path}' is invalid for native protocol 2: {exc}"
        )
        message = _append_process_output(message, stdout, stderr)
        raise NativePreflightError(
            message, stdout=stdout, stderr=stderr
        ) from exc


def _bounded_output(text: str | None, limit: int = 5_000) -> str:
    """Return process output bounded so one noisy run cannot flood a report.

    Args:
        text: Captured process output, which may be absent.
        limit: Maximum characters retained from the end of the output.

    Returns:
        The tail of the output, marked when characters were dropped.
    """
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return f"[truncated {len(text) - limit} characters]\n{text[-limit:]}"


def _append_process_output(message: str, stdout: str, stderr: str) -> str:
    """Append bounded process output to an error message.

    Args:
        message: Actionable error prefix.
        stdout: Captured standard output.
        stderr: Captured standard error.

    Returns:
        The message with any bounded process output appended.
    """
    if stdout.strip():
        message = f"{message}; stdout: {_bounded_output(stdout.strip())}"
    if stderr.strip():
        message = f"{message}; stderr: {_bounded_output(stderr.strip())}"
    return message


def _process_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
