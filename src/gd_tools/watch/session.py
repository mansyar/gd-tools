"""Interactive watch session: wires the watch loop to the native runtime."""

from __future__ import annotations

import time
from collections.abc import Callable

import click

from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.errors import GdToolsError, TestFailureError
from gd_tools.godot import find_godot
from gd_tools.native_test.command import run_native_test_command
from gd_tools.native_test.discovery import (
    NativeDiscoveryError,
    discover_native_suites,
)
from gd_tools.native_test.protocol import (
    NativeRunResult,
    NativeSuite,
    NativeTestResult,
)
from gd_tools.test_runner import TestResult
from gd_tools.watch.coalescer import DEFAULT_DEBOUNCE_SECONDS
from gd_tools.watch.loop import watch_loop
from gd_tools.watch.observer import WatchdogEventSource
from gd_tools.watch.scope import resolve_watched_files

WATCH_BANNER = "Watching {count} files. Press Ctrl+C to stop."

_STATUS_MAP = {
    "pass": "passed",
    "fail": "failed",
    "skip": "skipped",
}


def _watch_result(result: TestResult | None, status: str) -> NativeRunResult:
    """Map a native command result into the loop's summary result.

    The per-test breakdown is carried over (with statuses translated to
    the native protocol vocabulary) so the watch loop can report how many
    tests each run executed.
    """
    if result is None:
        return NativeRunResult(run_id="watch", status=status)
    tests = [
        NativeTestResult(
            suite=detail.suite,
            name=detail.name,
            status=_STATUS_MAP.get(detail.status, "error"),
            duration_seconds=detail.duration,
            message=detail.message,
        )
        for detail in result.test_details
    ]
    return NativeRunResult(run_id="watch", status=status, tests=tests)


def run_watch_mode(
    config: GdToolsConfig,
    *,
    coverage: bool = False,
    min_percent: int | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    timeout: int | None = 300,
    tags: tuple[str, ...] | None = None,
    test_timeout: float | None = None,
    show_uncovered: bool = False,
    no_cache: bool = False,
    parallel: int | None = None,
    event_source: WatchdogEventSource | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    output: Callable[[str], None] = click.echo,
) -> int:
    """Run the interactive watch session and return the process exit code.

    Validates the environment up front (startup failures propagate as
    ``GdToolsError`` so the CLI exits 2), prints the watching banner, then
    loops: every file save triggers exactly one debounced re-run mapped to
    the affected suite (full suite when nothing maps). Per-run failures are
    reported and do not abort the session; only Ctrl+C ends it.

    Args:
        config: Project configuration.
        coverage: Collect and report coverage on every run.
        min_percent: Optional coverage threshold.
        suite: Optional exact suite filter applied on every run.
        test_name: Optional exact test filter applied on every run.
        junit_xml: Optional JUnit XML output path per run.
        timeout: Godot import and per-suite process timeout in seconds.
        tags: Optional suite tag filters; defaults to configured tags.
        test_timeout: Optional per-test timeout override in seconds.
        show_uncovered: Include uncovered lines in coverage summaries.
        no_cache: Bypass the coverage plan cache.
        parallel: Optional worker count forwarded to every watch re-run.
        event_source: Injectable event source (defaults to watchdog).
        clock: Injectable clock for debounce timing.
        sleep: Injectable sleep used between poll ticks.
        debounce_seconds: Quiet period after the latest change before a
            run becomes due; injectable for tests and fast e2e.
        output: Injectable output sink (defaults to ``click.echo``).

    Returns:
        The process exit code (0 after a clean Ctrl+C shutdown).
    """
    project_root = find_project_root()
    godot_info = find_godot(config.godot)
    if not godot_info.is_valid:
        raise GdToolsError(
            f"Godot {godot_info.version} is not supported; "
            "gd-tools requires Godot 4.5+"
        )

    watched = resolve_watched_files(project_root)
    banner = WATCH_BANNER.format(count=len(watched))
    output(banner)

    selected_tags = list(tags) if tags else list(config.test.tags)
    effective_test_timeout = (
        test_timeout
        if test_timeout is not None
        else config.test.timeout_seconds
    )
    test_dirs = list(config.test.test_dirs)
    retries = config.test.retries

    def discover() -> list[NativeSuite]:
        """Resolve the current suites; transient discovery gaps yield none."""
        try:
            return discover_native_suites(
                project_root,
                test_dirs,
                suite=suite,
                test=test_name,
                tags=selected_tags,
                timeout_seconds=effective_test_timeout,
                retries=retries,
            )
        except NativeDiscoveryError:
            return []

    def runner(suites: list[NativeSuite]) -> NativeRunResult:
        """Execute one run through the existing native command pipeline.

        When the loop narrowed the selection to a single suite (a mapped
        re-run), that suite's name is passed as the exact suite filter so
        only the affected suite executes. Full runs pass every discovered
        suite and therefore no extra filter. The native run's per-test
        breakdown is carried back so the loop can report test counts.
        """
        suite_filter = suites[0].name if len(suites) == 1 else None
        click.clear()
        output(banner)
        try:
            result = run_native_test_command(
                config,
                coverage=coverage,
                min_percent=min_percent,
                suite=suite_filter,
                test_name=test_name,
                junit_xml=junit_xml,
                timeout=timeout,
                tags=selected_tags,
                test_timeout=test_timeout,
                show_uncovered=show_uncovered,
                no_cache=no_cache,
                parallel=parallel,
            )
        except TestFailureError as exc:
            return _watch_result(getattr(exc, "result", None), "failed")
        except GdToolsError as exc:
            output(f"Error: {exc}")
            return NativeRunResult(run_id="watch", status="error")
        return _watch_result(result, "passed")

    return watch_loop(
        project_root,
        discover=discover,
        runner=runner,
        event_source=event_source or WatchdogEventSource(project_root),
        clock=clock,
        sleep=sleep,
        debounce_seconds=debounce_seconds,
        output=output,
    )
