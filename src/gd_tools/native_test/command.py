"""CLI-facing adapter for the native Godot test runtime."""

from __future__ import annotations

import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from gd_tools import output
from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.coverage import plan_generator, reporter
from gd_tools.coverage.orchestrator import _print_coverage_inline
from gd_tools.errors import (
    ConfigError,
    CoverageThresholdError,
    GdToolsError,
    TestFailureError,
)
from gd_tools.godot import find_godot, run_godot
from gd_tools.native_test.discovery import discover_native_suites
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.protocol import NativeCoverage, NativeRunResult
from gd_tools.test_runner import TestDetail, TestResult, format_test_results


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
        no_cache: Bypass the coverage plan cache.

    Returns:
        The normalized CLI-facing test result.

    Raises:
        GdToolsError: For environment, protocol, process, or runtime errors.
        TestFailureError: When tests fail and ``no_exit_code`` is false.
    """
    project_root = find_project_root()
    godot_info = find_godot(config.godot)
    if not godot_info.is_valid:
        raise GdToolsError(
            f"Godot {godot_info.version} is not supported; "
            "gd-tools requires Godot 4.5+"
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
            "No native GdToolsTest suites were found. Add a suite extending "
            "GdToolsTest or run a legacy project with --runtime gut."
        )

    _import_project(godot_info.path, project_root, timeout)
    coverage_settings, coverage_output_dir = _prepare_coverage(
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
        work_dir=(
            coverage_output_dir / "native" if coverage_output_dir else None
        ),
        process_timeout=float(timeout) if timeout is not None else 300.0,
    )
    _raise_for_native_error(native_result)
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
        if test_failure is not None:
            raise test_failure
        raise

    result = _to_test_result(
        native_result,
        project_root,
        junit_xml,
    )
    format_test_results(result)
    if test_failure is not None:
        raise test_failure
    return result


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
        raise GdToolsError(f"Godot import timed out after {timeout}s") from None


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
    if result.status == "error":
        messages = "; ".join(
            test.message for test in result.tests if test.message
        )
        raise GdToolsError(
            messages
            or "Native test runtime encountered an infrastructure error"
        )


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
    except CoverageThresholdError:
        raise
    _print_coverage_inline(
        report.summary,
        min_percent,
        show_uncovered=show_uncovered,
        file_summaries=report.file_summaries,
        plan=plan,
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
    _write_junit_xml(junit_path, details, duration)
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
    )


def _write_junit_xml(
    path: Path,
    details: list[TestDetail],
    duration: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
