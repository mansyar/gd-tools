"""CLI-facing adapter for the native Godot test runtime."""

from __future__ import annotations

import json
import signal
import subprocess
import threading
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from gd_tools import output
from gd_tools.atomic_io import atomic_write_bytes
from gd_tools.changes import collect_changed_files
from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.coverage import plan_generator, reporter
from gd_tools.coverage.orchestrator import _report_coverage
from gd_tools.errors import (
    ConfigError,
    CoverageThresholdError,
    GdToolsError,
    NativeInterruptError,
    TestFailureError,
)
from gd_tools.godot import GodotInfo, find_godot, run_godot
from gd_tools.native_test.import_cache import (
    check_import_cache,
    compute_import_cache_key,
    store_import_freshness,
)
from gd_tools.native_test.artifacts import (
    ArtifactPublishError,
    NativeArtifactLayout,
    mark_run_started,
    publish_artifact_index,
)
from gd_tools.native_test.discovery import discover_native_suites
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.preflight import NativePreflightError
from gd_tools.native_test.preflight_cache import run_preflight_cached
from gd_tools.native_test.protocol import (
    NativeCoverage,
    NativeManifest,
    NativeRunResult,
    NativeSuite,
    RuntimeMode,
)
from gd_tools.test_runner import TestDetail, TestResult, format_test_results
from gd_tools.watch.mapping import map_changed_file, select_suites_for_changes


def run_native_test_command(
    config: GdToolsConfig,
    coverage: bool = False,
    min_percent: int | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    timeout: int | None = 300,
    tags: list[str] | None = None,
    test_timeout: float | None = None,
    paths: list[str] | None = None,
    show_uncovered: bool = False,
    no_cache: bool = False,
    parallel: int | None = None,
    changed: bool = False,
    base: str | None = None,
) -> TestResult:
    """Run native tests and return the existing CLI-facing result model.

    SIGTERM is converted to ``KeyboardInterrupt`` on platforms that deliver
    it (POSIX; the registration is inert on Windows) so an external kill
    takes the same cleanup path as Ctrl+C, and the previous handler is
    restored when the command returns. See ``_run_native_test_command`` for
    the parameter documentation.
    """
    previous_sigterm = None
    if threading.current_thread() is threading.main_thread():
        previous_sigterm = signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        return _run_native_test_command(
            config,
            coverage=coverage,
            min_percent=min_percent,
            suite=suite,
            test_name=test_name,
            junit_xml=junit_xml,
            no_exit_code=no_exit_code,
            timeout=timeout,
            tags=tags,
            test_timeout=test_timeout,
            paths=paths,
            show_uncovered=show_uncovered,
            no_cache=no_cache,
            parallel=parallel,
            changed=changed,
            base=base,
        )
    finally:
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)


def _raise_interrupt(signum: int, frame: object) -> None:
    """Convert SIGTERM into the interrupt cleanup path."""
    raise KeyboardInterrupt


def _run_native_test_command(
    config: GdToolsConfig,
    coverage: bool = False,
    min_percent: int | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    timeout: int | None = 300,
    tags: list[str] | None = None,
    test_timeout: float | None = None,
    paths: list[str] | None = None,
    show_uncovered: bool = False,
    no_cache: bool = False,
    parallel: int | None = None,
    changed: bool = False,
    base: str | None = None,
) -> TestResult:
    """Run native tests and return the existing CLI-facing result model.

    Args:
        config: Project configuration.
        coverage: Whether to collect and report native coverage.
        min_percent: Optional coverage threshold.
        suite: Optional exact suite filter.
        test_name: Optional exact test filter.
        junit_xml: Optional JUnit XML output path.
        no_exit_code: Return test failures instead of raising them.
        timeout: Godot import and per-suite process timeout in seconds.
        tags: Optional native suite tag filters; defaults to configured tags.
        test_timeout: Optional per-test timeout override in seconds.
        paths: Optional test file or directory selectors.
        show_uncovered: Include uncovered lines in the coverage summary.
        no_cache: Bypass the coverage plan cache and the preflight cache.
        parallel: Optional worker count (1-32) for concurrent suite
            execution; None or 1 runs suites sequentially.
        changed: Only run suites mapped from git-changed files; falls
            back to the full suite when a change maps to no suite.
        base: With ``changed``, diff from ``merge-base(ref, HEAD)`` instead
            of the working tree.

    Returns:
        The normalized CLI-facing test result.

    Raises:
        GdToolsError: For environment, protocol, process, or runtime errors.
        TestFailureError: When tests fail and ``no_exit_code`` is false.
    """
    project_root = find_project_root()

    changed_files: list[Path] = []
    if changed:
        source = "working tree vs HEAD" if base is None else f"base '{base}'"
        changed_files = collect_changed_files(project_root, base)
        if not changed_files:
            output.print_info(
                f"--changed: no changes detected ({source}); " "nothing to run."
            )
            return TestResult(
                total=0,
                passed=0,
                failed=0,
                skipped=0,
                duration=0.0,
                junit_xml_path=project_root / ".gd-tools" / "results.xml",
                coverage_data_path=None,
                artifact_index_path=None,
                stdout="",
                stderr="",
                test_details=[],
            )

    godot_info = find_godot(config.godot)
    if not godot_info.is_valid:
        raise GdToolsError(
            f"Godot {godot_info.version} is not supported; "
            "gd-tools requires Godot 4.5+. Install a supported Godot "
            "or set godot.binary in gd-tools.toml"
        )

    test_dirs = _test_directories(project_root, paths, config)
    selected_tags = (
        list(tags)
        if tags is not None
        else list(getattr(config.test, "tags", []))
    )
    effective_test_timeout = (
        test_timeout
        if test_timeout is not None
        else config.test.timeout_seconds
    )
    suites = discover_native_suites(
        project_root,
        test_dirs,
        suite=suite,
        test=test_name,
        tags=selected_tags,
        timeout_seconds=effective_test_timeout,
        retries=config.test.retries,
    )
    if not suites:
        raise ConfigError(
            "No test suites were found. Add a suite extending GdToolsTest."
        )
    if changed:
        suites = _narrow_changed_suites(
            project_root, suites, changed_files, base
        )

    _ensure_project_imported(
        godot_info, project_root, timeout, no_cache=no_cache
    )
    process_timeout = float(timeout) if timeout is not None else 300.0
    run_id = uuid.uuid4().hex
    artifact_layout = NativeArtifactLayout.create(project_root, run_id)
    try:
        mark_run_started(artifact_layout)
    except OSError as exc:
        raise GdToolsError(
            f"Could not create the native run directory at "
            f"{artifact_layout.run_dir}: {exc}"
        ) from exc
    try:
        preflight_result = run_preflight_cached(
            project_root,
            NativeManifest(
                project_root=project_root,
                runtime=RuntimeMode.NATIVE,
                suites=suites,
            ),
            godot_binary=godot_info.path,
            godot_version=godot_info.version,
            run_dir=artifact_layout.preflight_dir,
            cache_dir=project_root / ".gd-tools" / "native" / "preflight-cache",
            timeout_seconds=process_timeout,
            use_cache=not no_cache,
        )
    except NativePreflightError:
        try:
            publish_artifact_index(
                artifact_layout,
                status="error",
                suite_names=[],
                suite_paths=[],
                preflight_paths=artifact_layout.preflight_paths(),
            )
        except ArtifactPublishError:
            pass
        raise
    except KeyboardInterrupt:
        # An interrupt during preflight leaves no index at all; record the
        # run as incomplete so it is never mistaken for a finished one.
        _report_interrupted_run(artifact_layout)
        raise
    suites = preflight_result.suites
    try:
        coverage_settings, _ = _prepare_coverage(
            config,
            project_root,
            coverage=coverage,
            no_cache=no_cache,
        )
        native_result = run_native_tests(
            project_root,
            suites,
            godot_info.path,
            coverage=coverage_settings,
            work_dir=artifact_layout.native_dir,
            process_timeout=process_timeout,
            parallel=parallel,
            run_id=run_id,
            artifact_layout=artifact_layout,
        )
    except (KeyboardInterrupt, NativeInterruptError):
        # The orchestrator has already published the incomplete index for
        # interrupts during suite execution; report either way so the user
        # always sees where the partial artifacts live. NativeInterruptError
        # (exit 130) carries the run_dir in its message; a bare
        # KeyboardInterrupt from an earlier phase leaves no index at all.
        _report_interrupted_run(artifact_layout)
        raise
    infrastructure_error = native_result.status == "error"
    failed_count = sum(
        test.status in {"failed", "timeout", "error", "crashed"}
        for test in native_result.tests
    )
    test_failure = (
        TestFailureError(f"{failed_count} test(s) failed")
        if failed_count and not no_exit_code
        else None
    )
    try:
        _generate_native_report(
            config,
            project_root,
            native_result,
            coverage=coverage,
            min_percent=min_percent,
            show_uncovered=show_uncovered,
            no_cache=no_cache,
        )
    except CoverageThresholdError:
        if infrastructure_error:
            pass
        elif test_failure is not None:
            raise test_failure
        else:
            raise

    result = _to_test_result(
        native_result,
        project_root,
        junit_xml,
    )
    format_test_results(result)
    if infrastructure_error:
        _raise_for_native_error(native_result)
    if test_failure is not None:
        # Attach the aggregated result so callers (e.g. watch mode) can
        # report the per-test breakdown without re-running anything.
        test_failure.result = result
        raise test_failure
    return result


def _report_interrupted_run(artifact_layout: NativeArtifactLayout) -> None:
    """Report an interrupted run and mark its artifacts incomplete.

    The orchestrator publishes the incomplete index for interrupts that land
    during suite execution. This covers the earlier phases (import, plan
    preparation, preflight) and publishes only when no index exists yet, so
    a richer orchestrator-published index is never overwritten.
    """
    if not artifact_layout.index_path.exists():
        try:
            publish_artifact_index(
                artifact_layout,
                status="incomplete",
                suite_names=[],
                suite_paths=[],
                preflight_paths=artifact_layout.preflight_paths(),
            )
        except (ArtifactPublishError, OSError, ValueError):
            pass
    output.print_error(
        f"Run interrupted: artifacts marked incomplete at "
        f"{artifact_layout.run_dir}"
    )


def _narrow_changed_suites(
    project_root: Path,
    suites: list[NativeSuite],
    changed_files: list[Path],
    base: str | None,
) -> list[NativeSuite]:
    """Narrow discovered suites to those mapped from the changed files.

    Prints the always-on summary line and the per-file mapping detail
    under ``--verbose``. Falls back to the full suite list when any
    changed file maps to no selected suite, with a notice per unmapped
    file (the same contract as watch mode).
    """
    source = "working tree vs HEAD" if base is None else f"base '{base}'"
    # Normalize to project-relative POSIX strings so selection, notices,
    # and verbose detail display identically on every platform.
    changed = [path.as_posix() for path in changed_files]
    selected, unmapped = select_suites_for_changes(
        changed, project_root, suites
    )
    output.print_info(
        f"--changed: {len(selected)} of {len(suites)} suites selected "
        f"({source})"
    )
    for path in sorted(changed):
        mapped = map_changed_file(project_root / path, project_root, suites)
        detail = mapped if mapped is not None else "no mapping"
        output.print_verbose(f"  {path} -> {detail}")
    if unmapped:
        for path in unmapped:
            output.print_info(
                f"No suite mapped for '{path}'; running full suite."
            )
        return list(suites)
    return selected


def _test_directories(
    project_root: Path,
    paths: list[str] | None,
    config: GdToolsConfig,
) -> list[str]:
    if not paths:
        return config.test.test_dirs
    directories: list[str] = []
    for path in paths:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = project_root / candidate
        directories.append(str(candidate))
    return directories


def _import_project(
    godot_binary: str, project_root: Path, timeout: int | None
) -> None:
    try:
        run_godot(
            godot_binary,
            project_root,
            ["--headless", "--import"],
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise GdToolsError(
            f"Godot import timed out after {timeout}s; re-run with a "
            "larger --timeout (a first import may take longer)"
        ) from None


def _ensure_project_imported(
    godot_info: GodotInfo,
    project_root: Path,
    timeout: int | None,
    *,
    no_cache: bool = False,
) -> None:
    """Run the import step unless a fresh import is already recorded.

    A pure optimization: a cache miss, a disabled cache, or any cache
    failure degrades to the unconditional import with unchanged exit
    codes and report output.

    Args:
        godot_info: The resolved Godot binary and version.
        project_root: The Godot project root.
        timeout: Optional import process timeout in seconds.
        no_cache: When True, always import and skip the cache entirely.

    Raises:
        GdToolsError: When the import fails; the cache is never updated.
    """
    cache_dir = project_root / ".gd-tools" / "native" / "import-cache"
    cache_key: str | None = None
    if not no_cache:
        try:
            cache_key = compute_import_cache_key(
                project_root, godot_version=godot_info.version
            )
        except OSError as error:
            output.print_verbose(f"Import cache key failed: {error}")
        else:
            if check_import_cache(cache_dir, cache_key).hit:
                return
    _import_project(godot_info.path, project_root, timeout)
    if cache_key is not None:
        store_import_freshness(cache_dir, cache_key)


def _prepare_coverage(
    config: GdToolsConfig,
    project_root: Path,
    *,
    coverage: bool,
    no_cache: bool,
) -> tuple[NativeCoverage | None, Path | None]:
    if not coverage:
        return None, None
    output_dir = project_root / config.coverage.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    plan, cache_status = plan_generator.generate_plan_cached(
        str(project_root),
        config.coverage.exclude,
        config.coverage.test_dirs,
        cache_path=str(output_dir / "plan.json"),
        use_cache=not no_cache,
    )
    if not cache_status.hit:
        plan_generator.write_plan_json(plan, str(output_dir / "plan.json"))
    output.print_verbose(
        f"Coverage plan cache {'hit' if cache_status.hit else 'miss'}: "
        f"{cache_status.reason}"
    )
    return (
        NativeCoverage(
            enabled=True,
            plan_path=output_dir / "plan.json",
            output_path=output_dir / "coverage.json",
        ),
        output_dir,
    )


def _raise_for_native_error(result: NativeRunResult) -> None:
    if result.status != "error":
        return
    messages = "; ".join(test.message for test in result.tests if test.message)
    detail = (
        messages or "Native test runtime encountered an infrastructure error"
    )
    remedies = [
        test.diagnostics["remedy"]
        for test in result.tests
        if test.diagnostics.get("remedy")
    ]
    if remedies:
        detail = f"{detail} Remedy: {remedies[0]}"
    raise GdToolsError(detail)


def _generate_native_report(
    config: GdToolsConfig,
    project_root: Path,
    result: NativeRunResult,
    *,
    coverage: bool,
    min_percent: int | None,
    show_uncovered: bool,
    no_cache: bool,
) -> None:
    if not coverage or result.coverage_data_path is None:
        return
    output_dir = project_root / config.coverage.output_dir
    plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))
    data = reporter.read_coverage_json(result.coverage_data_path)
    try:
        report = reporter.generate_report(
            plan,
            data,
            output_dir,
            config.coverage.format,
            min_threshold=(
                min_percent / 100 if min_percent is not None else None
            ),
        )
    except CoverageThresholdError as exc:
        # The legacy seam reports the coverage and evaluates the omission gate
        # even when the percentage threshold fails, so `--min` plus omissions
        # exits 2 with the partial block visible instead of a bare threshold
        # error that hides the incompleteness. Mirror that here: the shared
        # _report_coverage raises the gate's exit-2 error in place of the
        # threshold error when omissions exist, and otherwise the threshold
        # error propagates unchanged. The two runtimes cannot disagree about
        # a partial measurement.
        if exc.report_result is not None:
            _report_coverage(
                plan,
                data,
                exc.report_result.summary,
                min_percent,
                show_uncovered=show_uncovered,
                file_summaries=exc.report_result.file_summaries,
            )
        raise
    # The native runtime reaches the same reconciliation, report and gate as
    # the legacy one through the shared _report_coverage, so the two runtimes
    # cannot disagree about a partial measurement.
    _report_coverage(
        plan,
        data,
        report.summary,
        min_percent,
        show_uncovered=show_uncovered,
        file_summaries=report.file_summaries,
    )
    output.print_verbose(f"Coverage report: {report.output_path}")


def _to_test_result(
    native_result: NativeRunResult,
    project_root: Path,
    junit_xml: str | None,
) -> TestResult:
    details: list[TestDetail] = []
    passed = 0
    failed = 0
    skipped = 0
    for test in native_result.tests:
        if test.status == "passed":
            status = "pass"
            passed += 1
        elif test.status in {"skipped", "pending"}:
            status = "skip"
            skipped += 1
        else:
            status = "fail"
            failed += 1
        details.append(
            TestDetail(
                name=test.name,
                suite=test.suite,
                status=status,
                message=test.message,
                duration=test.duration_seconds,
                diagnostics=test.diagnostics,
            )
        )

    if junit_xml:
        junit_path = Path(junit_xml).resolve()
    else:
        junit_path = project_root / ".gd-tools" / "results.xml"
    duration = sum(test.duration_seconds for test in native_result.tests)
    _write_junit_xml(
        junit_path,
        details,
        duration,
        artifact_index_path=native_result.artifact_index_path,
    )
    return TestResult(
        total=len(details),
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration=duration,
        junit_xml_path=junit_path,
        coverage_data_path=native_result.coverage_data_path,
        stdout=native_result.stdout,
        stderr=native_result.stderr,
        test_details=details,
        artifact_index_path=native_result.artifact_index_path,
    )


def _write_junit_xml(
    path: Path,
    details: list[TestDetail],
    duration: float,
    artifact_index_path: Path | None = None,
) -> None:
    root = ET.Element("testsuites")
    suite = ET.SubElement(
        root,
        "testsuite",
        name="gd-tools-native",
        tests=str(len(details)),
        failures=str(sum(detail.status == "fail" for detail in details)),
        skipped=str(sum(detail.status == "skip" for detail in details)),
        time=f"{duration:.6f}",
    )
    if artifact_index_path is not None:
        properties = ET.SubElement(suite, "properties")
        ET.SubElement(
            properties,
            "property",
            name="artifact_index",
            value=str(artifact_index_path),
        )
    for detail in details:
        case = ET.SubElement(
            suite,
            "testcase",
            classname=detail.suite,
            name=detail.name,
            time=f"{detail.duration:.6f}",
        )
        if detail.status == "fail":
            failure = ET.SubElement(
                case,
                "failure",
                message=detail.message or "Test failed",
            )
            failure_text = detail.message
            if detail.diagnostics:
                failure_text += "\nDiagnostics: " + json.dumps(
                    detail.diagnostics,
                    sort_keys=True,
                )
            failure.text = failure_text
        elif detail.status == "skip":
            ET.SubElement(case, "skipped", message=detail.message)
    atomic_write_bytes(
        path, ET.tostring(root, encoding="utf-8", xml_declaration=True)
    )
