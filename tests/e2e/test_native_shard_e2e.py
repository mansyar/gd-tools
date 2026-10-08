"""End-to-end tests for ``--shard k/N`` composed with ``--parallel``/coverage.

These exercise the full CLI pipeline against a real Godot project:
changed-filtering (none here) -> shard selection -> parallelism within the
shard, plus per-shard coverage artifacts (spec FR2.4, FR2.7, FR2.9, NFR2).
"""

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)

SUITE_COUNT = 6


def _gd_tools_command() -> list[str]:
    """Use the installed CLI entry point when available."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _run_cli(
    args: list[str], project: Path, godot_bin: str
) -> subprocess.CompletedProcess:
    """Run the CLI in the project directory with the given Godot binary."""
    import os

    env = os.environ.copy()
    env.update(
        {
            "GODOT_BIN": godot_bin,
            "GD_TOOLS_NO_UPDATE_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return subprocess.run(
        [*_gd_tools_command(), *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
    )


def _suite_files() -> dict[str, str]:
    """Return ``SUITE_COUNT`` trivially passing suites with stable names."""
    files: dict[str, str] = {}
    for i in range(1, SUITE_COUNT + 1):
        files[f"test/shard_suite_{i:02d}.gd"] = (
            f"extends GdToolsTest\nclass_name ShardSuite{i:02d}\n\n\n"
            "func test_ok() -> void:\n"
            '\tassert_true(true, "always passes")\n'
        )
    return files


def _prepare_project(tmp_path: Path, godot_bin: str) -> Path:
    """Create a clean project with six passing suites and deploy the addon."""
    project = tmp_path / "shard_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.rmtree(project / "test", ignore_errors=True)
    for relative, content in _suite_files().items():
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    # The fixture's subject scripts are only ever loaded by the fixture's own
    # suites (removed above); excluding them keeps coverage instrumentation
    # complete for this minimal project.
    config = project / "gd-tools.toml"
    config.write_text(
        "[coverage]\n"
        'output_dir = ".gd-tools/coverage"\n'
        "exclude = [\n"
        '    "scripts",\n'
        '    "addons",\n'
        '    ".godot",\n'
        '    ".gd-tools",\n'
        '    ".git",\n'
        "]\n",
        encoding="utf-8",
    )

    result = _run_cli(["init", "--non-interactive"], project, godot_bin)
    assert result.returncode == 0, result.stdout + result.stderr
    return project


def _junit_suite_names(junit_path: Path) -> set[str]:
    """Return the distinct suite names recorded in a JUnit XML file."""
    root = ET.parse(junit_path).getroot()
    return {
        case.attrib["classname"]
        for case in root.iter("testcase")
        if case.attrib.get("classname")
    }


def test_shard_one_of_two_with_parallel_runs_only_shard_suites(
    tmp_path, godot_bin
):
    """``--shard 1/2 --parallel 2`` runs the shard's suites in parallel."""
    project = _prepare_project(tmp_path, godot_bin)

    result = _run_cli(
        ["test", "--shard", "1/2", "--parallel", "2", "--junit-xml", "s1.xml"],
        project,
        godot_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Running shard 1/2 (3 of 6 suites)" in result.stdout
    names = _junit_suite_names(project / "s1.xml")
    assert names == {"ShardSuite01", "ShardSuite03", "ShardSuite05"}


def test_shard_selection_is_deterministic_across_runs(tmp_path, godot_bin):
    """Two runs of the same shard select the same suites (FR2.3)."""
    project = _prepare_project(tmp_path, godot_bin)

    first = _run_cli(
        ["test", "--shard", "1/2", "--junit-xml", "run_a.xml"],
        project,
        godot_bin,
    )
    second = _run_cli(
        ["test", "--shard", "1/2", "--junit-xml", "run_b.xml"],
        project,
        godot_bin,
    )

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert _junit_suite_names(project / "run_a.xml") == _junit_suite_names(
        project / "run_b.xml"
    )


def test_shard_with_coverage_writes_per_shard_artifacts(tmp_path, godot_bin):
    """Sharded coverage runs keep one full plan and write shard coverage.

    The coverage plan is built pre-shard (NFR2): both shards see the same
    plan, and each shard writes its own per-run coverage data (FR2.9).
    """
    project = _prepare_project(tmp_path, godot_bin)
    coverage_dir = project / ".gd-tools" / "coverage"

    first = _run_cli(
        ["test", "--shard", "1/2", "--coverage", "--junit-xml", "c1.xml"],
        project,
        godot_bin,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    assert "Running shard 1/2 (3 of 6 suites)" in first.stdout
    plan_after_first = (coverage_dir / "plan.json").read_text(encoding="utf-8")
    assert _junit_suite_names(project / "c1.xml") == {
        "ShardSuite01",
        "ShardSuite03",
        "ShardSuite05",
    }

    second = _run_cli(
        ["test", "--shard", "2/2", "--coverage", "--junit-xml", "c2.xml"],
        project,
        godot_bin,
    )
    assert second.returncode == 0, second.stdout + second.stderr
    assert "Running shard 2/2 (3 of 6 suites)" in second.stdout
    assert _junit_suite_names(project / "c2.xml") == {
        "ShardSuite02",
        "ShardSuite04",
        "ShardSuite06",
    }

    # Identical plan regardless of shard: the plan cache is shard-agnostic.
    assert (coverage_dir / "plan.json").read_text(encoding="utf-8") == (
        plan_after_first
    )
    plan = json.loads(plan_after_first)
    assert [entry["path"] for entry in plan["files"]] == [
        "res://collector_probe.gd"
    ]
    assert (coverage_dir / "coverage.json").is_file()
