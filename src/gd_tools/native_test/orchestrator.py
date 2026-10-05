"""Orchestrate isolated Godot processes for native test suites."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gd_tools.errors import NativeInterruptError
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


class _ProcessRegistry:
    """Thread-safe registry of the Godot processes spawned for a run.

    Workers register their process before waiting on it and unregister once
    it has been reaped, so the abort path can find and kill every process
    still in flight when the run is interrupted.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._processes: set[subprocess.Popen[Any]] = set()

    def add(self, process: Any) -> None:
        with self._lock:
            self._processes.add(process)

    def remove(self, process: Any) -> None:
        with self._lock:
            self._processes.discard(process)

    def snapshot(self) -> list[Any]:
        with self._lock:
            return list(self._processes)


def _raise_interrupt(signum: int, frame: Any) -> None:
    """Convert a SIGTERM delivery into a KeyboardInterrupt."""
    raise KeyboardInterrupt


@contextlib.contextmanager
def _sigterm_as_interrupt() -> Iterator[None]:
    """Treat SIGTERM like Ctrl+C for the duration of the context.

    Only installed on the main thread (signal handlers must be), and only
    when the platform defines SIGTERM. The previous handler is restored on
    exit so the CLI never leaks its handler into callers.
    """
    if threading.current_thread() is not threading.main_thread() or not hasattr(
        signal, "SIGTERM"
    ):
        yield
        return
    previous = signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _ignore_sigterm() -> None:
    """Stop converting further SIGTERMs while the abort path runs.

    A second SIGTERM during process-tree kills or artifact publishing must
    not abort the abort; the previous handler is restored by the enclosing
    ``_sigterm_as_interrupt`` context.
    """
    if threading.current_thread() is not threading.main_thread() or not hasattr(
        signal, "SIGTERM"
    ):
        return
    with contextlib.suppress(OSError, ValueError):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)


def _kill_process_tree(pid: int, *, _platform: str | None = None) -> None:
    """Kill a process and all of its descendants, best effort.

    Godot spawns child processes (e.g. for import steps), so killing only
    the direct child would leak orphans. Windows uses ``taskkill /T /F``;
    POSIX kills the whole process group (suites are started in their own
    session via ``start_new_session``).
    """
    platform_name = _platform if _platform is not None else sys.platform
    if platform_name.startswith("win"):
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except OSError:
        with contextlib.suppress(OSError):
            os.kill(pid, signal.SIGKILL)


def _spawn_process(
    command: list[str],
    *,
    env: dict[str, str],
    registry: _ProcessRegistry,
    abort_event: threading.Event | None = None,
) -> subprocess.Popen[str]:
    """Start one Godot suite process and register it for abort handling.

    If the run was interrupted between the process being spawned and being
    registered, the process is killed here so it cannot escape the abort
    snapshot.
    """
    kwargs: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
        "env": env,
    }
    if os.name == "posix":
        # Own session/process group so the tree kill can take descendants.
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    registry.add(process)
    if abort_event is not None and abort_event.is_set():
        # The abort snapshot was taken before this spawn registered; kill
        # the latecomer here so no tree outlives the interrupted run.
        _kill_process_tree(process.pid)
        with contextlib.suppress(Exception):
            process.communicate()
        registry.remove(process)
    return process


@dataclass
class _SuiteContext:
    """Constants shared by every per-suite worker invocation."""

    project_root: Path
    godot_binary: str
    runner_script: str
    process_timeout: float
    run_id: str
    output_dir: Path
    artifact_layout: NativeArtifactLayout | None
    coverage: NativeCoverage | None
    parallel: int = 1
    snapshot_update: bool = False
    registry: _ProcessRegistry = field(default_factory=_ProcessRegistry)
    # Suites whose execution has started, in start order. The incomplete
    # index published on interrupt lists only these, so suites that never
    # began are not advertised as partially run.
    attempted: list[str] = field(default_factory=list)
    abort_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class _SuiteOutcome:
    """Everything one suite execution contributes to the aggregate."""

    tests: list[NativeTestResult]
    stdout: str = ""
    stderr: str = ""
    has_failure: bool = False
    has_error: bool = False
    suite_paths: dict[str, Any] | None = None
    coverage_shard: Path | None = None
    engine_warnings: list[str] = field(default_factory=list)
    coverage_omissions: list[dict[str, Any]] = field(default_factory=list)


def _interrupt_message(context: _SuiteContext) -> str:
    """User-facing message for an interrupted run."""
    if context.artifact_layout is not None:
        return (
            "Test run interrupted. In-flight Godot processes were killed "
            "and the run was marked incomplete under "
            f"{context.artifact_layout.run_dir}."
        )
    return "Test run interrupted. In-flight Godot processes were killed."


def _abort_run(context: _SuiteContext) -> None:
    """Kill every in-flight suite process and mark the run incomplete.

    Only suites whose execution actually started are listed; the index is a
    record of what happened, not of what was planned. Suite paths are
    published without any realized artifacts (nothing was verified as
    written at abort time), keeping ``suite_names`` and ``suite_paths``
    aligned.
    """
    # Tell spawns racing this snapshot to clean up after themselves.
    context.abort_event.set()
    for process in context.registry.snapshot():
        if process.poll() is None:
            _kill_process_tree(process.pid)
            context.registry.remove(process)
    if context.artifact_layout is None:
        return
    try:
        publish_artifact_index(
            context.artifact_layout,
            status="incomplete",
            suite_names=list(context.attempted),
            suite_paths=[{} for _ in context.attempted],
            preflight_paths=context.artifact_layout.preflight_paths(),
        )
    except ArtifactPublishError:
        # The interrupt must surface even if the index cannot be written;
        # the run marker still lets retention identify the directory.
        pass


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
    parallel: int | None = None,
    snapshot_update: bool = False,
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
        parallel: Optional worker count for concurrent suite execution.
            ``None`` or a value below 2 runs suites sequentially. Results are
            always aggregated in discovery order regardless of completion
            order.
        snapshot_update: When True, the runner rewrites mismatched and
            malformed snapshots instead of failing their tests.

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

    context = _SuiteContext(
        project_root=project_root,
        godot_binary=godot_binary,
        runner_script=runner_script,
        process_timeout=process_timeout,
        run_id=run_id,
        output_dir=output_dir,
        artifact_layout=artifact_layout,
        coverage=coverage,
        parallel=parallel if parallel and parallel > 1 else 1,
        snapshot_update=snapshot_update,
    )
    work_items = list(enumerate(suites))
    with _sigterm_as_interrupt():
        if parallel is not None and parallel > 1:
            with ThreadPoolExecutor(max_workers=parallel) as executor:
                futures = [
                    executor.submit(_execute_suite, index, suite, context)
                    for index, suite in work_items
                ]
                try:
                    outcomes = [future.result() for future in futures]
                except KeyboardInterrupt:
                    # Handle the interrupt INSIDE the with-block:
                    # __exit__ calls shutdown(wait=True), which would
                    # otherwise join every still-running suite before
                    # the kill path runs. Killing first makes that
                    # join return almost immediately.
                    _ignore_sigterm()
                    executor.shutdown(wait=False, cancel_futures=True)
                    _abort_run(context)
                    raise NativeInterruptError(
                        _interrupt_message(context)
                    ) from None
        else:
            try:
                outcomes = [
                    _execute_suite(index, suite, context)
                    for index, suite in work_items
                ]
            except KeyboardInterrupt:
                _ignore_sigterm()
                _abort_run(context)
                raise NativeInterruptError(
                    _interrupt_message(context)
                ) from None

    all_tests: list[NativeTestResult] = []
    coverage_shards: list[Path] = []
    has_failure = False
    has_error = False
    process_stdout: list[str] = []
    process_stderr: list[str] = []
    suite_artifact_paths: list[dict[str, Any]] = []
    engine_warnings: list[str] = []
    coverage_omissions: list[dict[str, Any]] = []
    for outcome in outcomes:
        all_tests.extend(outcome.tests)
        if outcome.stdout:
            process_stdout.append(outcome.stdout)
        if outcome.stderr:
            process_stderr.append(outcome.stderr)
        if outcome.has_failure:
            has_failure = True
        if outcome.has_error:
            has_error = True
        if outcome.suite_paths is not None:
            suite_artifact_paths.append(outcome.suite_paths)
        if outcome.coverage_shard is not None:
            coverage_shards.append(outcome.coverage_shard)
        # R5: omissions and warnings ride the existing channels. Every
        # suite instruments the whole plan, so the same omission arrives
        # from each shard; dedupe to keep the aggregate honest.
        for warning in outcome.engine_warnings:
            if warning not in engine_warnings:
                engine_warnings.append(warning)
        for omission in outcome.coverage_omissions:
            if omission not in coverage_omissions:
                coverage_omissions.append(omission)

    coverage_output = _resolve_path(
        project_root,
        coverage.output_path if coverage and coverage.output_path else None,
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


def _execute_suite(
    index: int,
    suite: NativeSuite,
    context: _SuiteContext,
) -> _SuiteOutcome:
    """Run one suite in an isolated Godot process and collect its outcome.

    Side effects are confined to this suite's own artifact paths, so the
    function is safe to run concurrently for distinct suites.
    """
    context.attempted.append(suite.name)
    artifact_layout = context.artifact_layout
    if artifact_layout is not None:
        suite_paths = artifact_layout.suite_paths(index)
        manifest_path = suite_paths["manifest"]
        result_path = suite_paths["result"]
        events_path = suite_paths["events"]
        log_path = suite_paths["log"]
        screenshot_path = suite_paths["screenshot_base"]
    else:
        manifest_path = context.output_dir / f"suite-{index:04d}.manifest.json"
        result_path = context.output_dir / f"suite-{index:04d}.result.json"
        events_path = context.output_dir / f"suite-{index:04d}.events.ndjson"
        log_path = context.output_dir / f"suite-{index:04d}.log"
        screenshot_path = context.output_dir / f"suite-{index:04d}"
    result_path.unlink(missing_ok=True)
    events_path.unlink(missing_ok=True)
    log_path.unlink(missing_ok=True)

    suite_coverage = context.coverage or NativeCoverage()
    coverage_shard: Path | None = None
    if context.coverage and context.coverage.enabled:
        shard_path = (
            suite_paths["coverage"]
            if artifact_layout is not None
            else context.output_dir / f"suite-{index:04d}.coverage.json"
        )
        shard_path.unlink(missing_ok=True)
        coverage_shard = shard_path
        suite_coverage = context.coverage.model_copy(
            update={"output_path": shard_path}
        )

    manifest = NativeManifest(
        project_root=context.project_root,
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
            "GD_TOOLS_NATIVE_RUN_ID": context.run_id,
            "GD_TOOLS_SUITE_NAME": suite.name,
            "GD_TOOLS_WORKER_SLOT": str(index % context.parallel),
        }
    )
    if context.snapshot_update:
        env["GD_TOOLS_SNAPSHOT_UPDATE"] = "1"
    command = [context.godot_binary]
    if (
        suite.integration is None
        or suite.integration.mode == NativeExecutionMode.HEADLESS
    ):
        command.append("--headless")
    command.extend(
        [
            "--path",
            str(context.project_root),
            "--script",
            context.runner_script,
            "--log-file",
            str(log_path),
        ]
    )

    process = _spawn_process(
        command,
        env=env,
        registry=context.registry,
        abort_event=context.abort_event,
    )
    try:
        stdout, stderr = process.communicate(timeout=context.process_timeout)
    except (subprocess.TimeoutExpired, TimeoutError):
        _kill_process_tree(process.pid)
        with contextlib.suppress(Exception):
            # Re-call communicate() after the kill so the direct child is
            # reaped and its pipes are closed (subprocess.run did this
            # implicitly; communicate(timeout=...) does not).
            process.communicate()
        context.registry.remove(process)
        return _SuiteOutcome(
            tests=[
                _process_error(
                    suite.name,
                    f"Godot process timed out after "
                    f"{context.process_timeout:g}s "
                    f"running suite {suite.name!r}",
                    diagnostics={
                        "kind": "process",
                        "expected": (
                            f"completion within {context.process_timeout:g}s"
                        ),
                        "found": "timeout",
                        "remedy": (
                            "increase the timeout (--timeout or "
                            "[test].timeout_seconds) and re-run"
                        ),
                    },
                )
            ],
            has_error=True,
            suite_paths=suite_paths if artifact_layout is not None else None,
            coverage_shard=coverage_shard,
        )
    context.registry.remove(process)
    returncode = process.returncode

    outcome = _SuiteOutcome(
        tests=[],
        stdout=stdout,
        stderr=stderr,
        suite_paths=suite_paths if artifact_layout is not None else None,
        coverage_shard=coverage_shard,
    )
    parsed_result = _read_native_result(result_path)
    if parsed_result is not None:
        expected_returncode = {
            "passed": 0,
            "failed": 1,
            "error": 2,
            "cancelled": 1,
        }[parsed_result.status]
        if returncode != expected_returncode:
            outcome.has_error = True
            outcome.tests.append(
                _process_error(
                    suite.name,
                    "Native result status "
                    f"{parsed_result.status} disagrees with process exit "
                    f"code {returncode}",
                    diagnostics={
                        "kind": "protocol",
                        "expected": (
                            f"exit code {expected_returncode} for status "
                            f"'{parsed_result.status}'"
                        ),
                        "found": f"exit code {returncode}",
                        "remedy": (
                            "re-run the suite directly to reproduce; "
                            "report this if it persists"
                        ),
                    },
                )
            )
            return outcome
        parsed_result = parsed_result.model_copy(
            update={
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        outcome.tests.extend(parsed_result.tests)
        outcome.engine_warnings = list(parsed_result.engine_warnings)
        outcome.coverage_omissions = list(
            parsed_result.diagnostics.get("coverage_omissions", [])
        )
        if artifact_layout is not None:
            suite_paths["screenshots"] = [
                Path(test.diagnostics["screenshot"])
                for test in parsed_result.tests
                if test.diagnostics.get("screenshot")
            ]
        if parsed_result.status == "failed":
            outcome.has_failure = True
        elif parsed_result.status == "error":
            outcome.has_error = True
        return outcome

    outcome.has_error = True
    if result_path.is_file():
        # The runner wrote something it cannot be parsed as a protocol v3
        # result: a protocol mismatch rather than an engine crash.
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
        f"Godot process exited with code {returncode} ({found})",
        stdout.strip(),
        stderr.strip(),
    ]
    outcome.tests.append(
        _process_error(
            suite.name,
            "; ".join(part for part in message_parts if part),
            diagnostics={
                "kind": kind,
                "expected": "a parseable protocol v3 result.json",
                "found": found,
                "remedy": remedy,
            },
        )
    )
    return outcome


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
