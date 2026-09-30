"""Playtest coverage orchestrator (Roadmap Track 34).

Launches the Godot game windowed (non-headless) with the coverage
autoload activated in playtest mode, waits for the player to finish,
then collects the coverage data and generates reports through the
existing reporter suite — so ``gd-tools coverage run`` produces the
same report formats as test coverage.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from gd_tools import output
from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.coverage import plan_generator, reporter
from gd_tools.coverage.orchestrator import (
    _print_coverage_table,
    _print_threshold_footer,
)
from gd_tools.coverage.reporter import ReportResult
from gd_tools.errors import (
    CoveragePlaytestError,
    CoverageThresholdError,
)
from gd_tools.godot import find_godot, run_godot

PLAYTEST_ENV = "GD_TOOLS_COVERAGE_PLAYTEST"

PLAN_ENV = "GD_TOOLS_COVERAGE_PLAN"

OUTPUT_ENV = "GD_TOOLS_COVERAGE_OUTPUT"

INTERVAL_ENV = "GD_TOOLS_COVERAGE_PLAYTEST_INTERVAL"

_MAIN_SCENE_PATTERN = re.compile(r"(?m)^run/main_scene\s*=\s*\"([^\"]+)\"")


def run_playtest_coverage(
    config: GdToolsConfig,
    scene: str | None = None,
    timeout: int | None = None,
    min_percent: int | None = None,
    report_format: str | None = None,
) -> ReportResult:
    """Run a playtest coverage session and generate reports.

    Generates the full-project coverage plan, launches the game
    windowed with playtest coverage activated, waits for the game to
    exit, collects the coverage output, and generates a report.

    Args:
        config: Resolved project configuration.
        scene: Scene to launch as a ``res://`` path. If ``None``, the
            project's main scene from ``project.godot`` is used.
        timeout: Maximum session length in seconds. The game is closed
            automatically when the timeout elapses.
        min_percent: Minimum coverage percentage (0-100). If set and
            session coverage is below this, raises
            :class:`~gd_tools.errors.CoverageThresholdError`.
        report_format: Report format override (e.g., ``"html"``,
            ``"lcov"``, ``"cobertura"``, ``"text"``). If ``None``,
            uses ``config.coverage.format``.

    Returns:
        The :class:`ReportResult` from report generation.

    Raises:
        CoveragePlaytestError: If the project, scene, or launch is
            invalid, or the session ends without coverage data.
        CoverageThresholdError: If ``min_percent`` is set and session
            coverage is below the threshold.
    """
    project_root = find_project_root()
    godot_info = find_godot(config.godot)

    output_dir = project_root / config.coverage.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    plan, cache_status = plan_generator.generate_plan_cached(
        str(project_root),
        config.coverage.exclude,
        config.coverage.test_dirs,
        cache_path=str(output_dir / "plan.json"),
        use_cache=True,
    )
    if not cache_status.hit:
        plan_generator.write_plan_json(plan, str(output_dir / "plan.json"))

    coverage_path = output_dir / "coverage.json"
    # Derive the flush interval from --timeout so at least one periodic
    # snapshot is guaranteed to land before the auto-close kill; the
    # exit flush cannot run when the process is terminated hard.
    interval = min(5.0, timeout / 2) if timeout is not None else 5.0
    env = {
        PLAN_ENV: str(output_dir / "plan.json"),
        OUTPUT_ENV: str(coverage_path),
        PLAYTEST_ENV: "1",
        INTERVAL_ENV: str(interval),
    }

    args: list[str] = []
    if scene is not None:
        args.append(scene)
    else:
        main_scene = _read_main_scene(project_root)
        if main_scene is None:
            raise CoveragePlaytestError(
                "[Error] No scene to playtest.\n"
                "  Cause: No --scene was given and project.godot has no "
                "run/main_scene setting.\n"
                "  Fix: Pass --scene res://path/to/scene.tscn."
            )
        args.append(main_scene)

    try:
        result = run_godot(
            godot_info.path,
            project_root,
            args,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        # --timeout auto-close: subprocess.run hard-killed the game, so
        # only the periodic snapshots are on disk.  That is the expected
        # outcome for a requested timeout, not a crash.
        output.print_warning(
            f"Playtest session reached the {timeout}s timeout; the game "
            "was closed automatically. Reporting the last periodic "
            "snapshot."
        )
        result = None

    effective_format = (
        report_format if report_format is not None else config.coverage.format
    )
    return _collect_and_report(
        output_dir,
        coverage_path,
        effective_format,
        min_percent=min_percent,
        result=result,
    )


def _read_main_scene(project_root: Path) -> str | None:
    """Read the main scene from ``project.godot``.

    Args:
        project_root: Root directory of the Godot project.

    Returns:
        The ``run/main_scene`` value as a ``res://`` path, or ``None``
        when it is not set.
    """
    project_godot = project_root / "project.godot"
    if not project_godot.is_file():
        raise CoveragePlaytestError(
            "[Error] Not a Godot project.\n"
            f"  Cause: No project.godot found at {project_root}.\n"
            "  Fix: Run gd-tools coverage run from inside a Godot project."
        )
    content = project_godot.read_text(encoding="utf-8")
    match = _MAIN_SCENE_PATTERN.search(content)
    if match is None:
        return None
    return match.group(1)


def _collect_and_report(
    output_dir: Path,
    coverage_path: Path,
    effective_format: str,
    *,
    min_percent: int | None,
    result: subprocess.CompletedProcess | None,
) -> ReportResult:
    """Collect the coverage output and generate the report.

    Args:
        output_dir: Coverage output directory (already contains
            ``plan.json``).
        coverage_path: Path the tracker wrote the coverage data to.
        effective_format: Resolved report format (flag > config).
        min_percent: Minimum coverage threshold, or ``None``.
        result: The completed game process, or ``None`` when the
            session ended via the ``--timeout`` auto-close.

    Returns:
        The generated :class:`ReportResult`.

    Raises:
        CoveragePlaytestError: If the game crashed without producing
            data, or no coverage data was produced at all.
        CoverageThresholdError: If session coverage is below
            ``min_percent``.
    """
    if result is not None and result.returncode != 0:
        if not coverage_path.is_file():
            stderr_tail = (result.stderr or "").strip()
            detail = f": {stderr_tail[-300:]}" if stderr_tail else ""
            raise CoveragePlaytestError(
                "[Error] Playtest session failed and produced no coverage "
                "data.\n"
                f"  Cause: The game exited with code {result.returncode}"
                f"{detail}\n"
                "  Fix: Run the game manually to reproduce the crash."
            )
        output.print_warning(
            f"The game exited unexpectedly (exit code {result.returncode}). "
            "Reporting partial data from the last periodic snapshot."
        )

    if not coverage_path.is_file():
        raise CoveragePlaytestError(
            "[Error] Playtest produced no coverage data.\n"
            f"  Cause: The coverage autoload did not write {coverage_path}.\n"
            "  Fix: Ensure the gd-tools coverage addon is installed "
            "(gd-tools init) and the _GDTCoverage autoload is registered."
        )
    plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))
    data = reporter.read_coverage_json(coverage_path)

    summary = reporter.compute_summary(plan, data)
    _print_coverage_table(summary, min_percent)
    _print_threshold_footer(summary, min_percent)

    report = reporter.generate_report(plan, data, output_dir, effective_format)
    if min_percent is not None and summary.line_rate * 100 < min_percent:
        raise CoverageThresholdError(
            f"[Error] Line coverage {summary.line_rate * 100:.1f}% is "
            f"below minimum threshold {min_percent}%\n"
            f"  Cause: Only {summary.covered_lines} of "
            f"{summary.total_lines} lines were executed during the "
            "playtest session.\n"
            f"  Fix: Play more of the game or lower the --min threshold.",
            report_result=report,
        )
    return report
