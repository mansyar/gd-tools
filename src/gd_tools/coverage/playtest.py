"""Playtest coverage orchestrator (Roadmap Track 34).

Launches the Godot game windowed (non-headless) with the coverage
autoload activated in playtest mode, waits for the player to finish,
then collects the coverage data and generates reports through the
existing reporter suite — so ``gd-tools coverage run`` produces the
same report formats as test coverage.
"""

from __future__ import annotations

import re
from pathlib import Path

from gd_tools.config import GdToolsConfig, find_project_root
from gd_tools.coverage import plan_generator, reporter
from gd_tools.coverage.reporter import ReportResult
from gd_tools.errors import CoveragePlaytestError
from gd_tools.godot import find_godot, run_godot

PLAYTEST_ENV = "GD_TOOLS_COVERAGE_PLAYTEST"

PLAN_ENV = "GD_TOOLS_COVERAGE_PLAN"

OUTPUT_ENV = "GD_TOOLS_COVERAGE_OUTPUT"

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
    env = {
        PLAN_ENV: str(output_dir / "plan.json"),
        OUTPUT_ENV: str(coverage_path),
        PLAYTEST_ENV: "1",
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

    run_godot(
        godot_info.path,
        project_root,
        args,
        env=env,
        timeout=timeout,
    )

    effective_format = (
        report_format if report_format is not None else config.coverage.format
    )
    return _collect_and_report(
        project_root, output_dir, coverage_path, effective_format
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
    project_root: Path,
    output_dir: Path,
    coverage_path: Path,
    effective_format: str,
) -> ReportResult:
    """Collect the coverage output and generate the report.

    Args:
        project_root: Root directory of the Godot project.
        output_dir: Coverage output directory (already contains
            ``plan.json``).
        coverage_path: Path the tracker wrote the coverage data to.
        effective_format: Resolved report format (flag > config).

    Returns:
        The generated :class:`ReportResult`.

    Raises:
        CoveragePlaytestError: If no coverage data was produced.
    """
    if not coverage_path.is_file():
        raise CoveragePlaytestError(
            "[Error] Playtest produced no coverage data.\n"
            f"  Cause: The coverage autoload did not write {coverage_path}.\n"
            "  Fix: Ensure the gd-tools coverage addon is installed "
            "(gd-tools init) and the _GDTCoverage autoload is registered."
        )
    plan = plan_generator.read_plan_json(str(output_dir / "plan.json"))
    data = reporter.read_coverage_json(coverage_path)
    return reporter.generate_report(plan, data, output_dir, effective_format)
