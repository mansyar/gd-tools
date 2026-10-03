"""Per-arm ternary coverage E2E: arms measured and gated independently.

Exercises the public CLI against a fixture project with ternary subject
suites so that ``ternary_true`` and ``ternary_false`` disagree at the
plan/hit level and an uncovered arm can fail ``--min-branch``.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.usefixtures("godot_bin"),
]

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)


def _gd_tools_command() -> list[str]:
    """Use the installed CLI entry point when available."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    return project


def _run_cli(
    args: list[str], project: Path, godot_bin: str
) -> subprocess.CompletedProcess:
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
        timeout=120,
    )


def _coverage_artifacts(project: Path) -> tuple[dict, dict]:
    coverage_dir = project / ".gd-tools" / "coverage"
    plan = json.loads((coverage_dir / "plan.json").read_text(encoding="utf-8"))
    data = json.loads(
        (coverage_dir / "coverage.json").read_text(encoding="utf-8")
    )
    return plan, data


def _ternary_hits(plan: dict, data: dict) -> dict[str, int]:
    """Map ternary branch types to recorded hit counts for the subject."""
    entry = next(
        f for f in plan["files"] if f["path"].endswith("ternary_subject.gd")
    )
    ids = {
        line["branch_type"]: line["id"]
        for line in entry["lines"]
        if (line.get("branch_type") or "").startswith("ternary")
    }
    file_data = next(
        f for f in data["files"] if f["file_id"] == entry["file_id"]
    )
    hits = file_data["hits"]
    return {
        branch_type: int(hits.get(str(point_id), 0))
        for branch_type, point_id in ids.items()
    }


def _run_coverage_suite(
    tmp_path, godot_bin, suite: str, extra: list[str] | None = None
):
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )
    result = _run_cli(
        ["--quiet", "test", "--coverage", "--suite", suite, *(extra or [])],
        project,
        godot_bin,
    )
    return project, result


@pytest.mark.slow
def test_true_arm_only_leaves_false_arm_uncovered(tmp_path, godot_bin):
    """Running only the true arm records ternary_true, not ternary_false."""
    project, result = _run_coverage_suite(
        tmp_path, godot_bin, "TernaryTrueSuite"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _ternary_hits(plan, data)

    assert hits["ternary_true"] > 0
    assert hits["ternary_false"] == 0


@pytest.mark.slow
def test_false_arm_only_leaves_true_arm_uncovered(tmp_path, godot_bin):
    """Running only the false arm records ternary_false, not ternary_true."""
    project, result = _run_coverage_suite(
        tmp_path, godot_bin, "TernaryFalseSuite"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _ternary_hits(plan, data)

    assert hits["ternary_false"] > 0
    assert hits["ternary_true"] == 0


@pytest.mark.slow
def test_both_arms_covered(tmp_path, godot_bin):
    """Running both arms records both plan points."""
    project, result = _run_coverage_suite(
        tmp_path, godot_bin, "TernaryBothSuite"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _ternary_hits(plan, data)

    assert hits["ternary_true"] > 0
    assert hits["ternary_false"] > 0


@pytest.mark.slow
def test_uncovered_arm_fails_min_branch_gate(tmp_path, godot_bin):
    """An uncovered ternary arm fails the ``--min-branch`` gate."""
    _, result = _run_coverage_suite(
        tmp_path, godot_bin, "TernaryTrueSuite", ["--min-branch", "100"]
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert "branch" in (result.stdout + result.stderr).lower()


@pytest.mark.slow
def test_uncovered_arm_display_stays_combined(tmp_path, godot_bin):
    """The human report shows the anchor line once, not once per arm."""
    _, result = _run_coverage_suite(
        tmp_path, godot_bin, "TernaryTrueSuite", ["--show-uncovered"]
    )

    assert result.returncode == 0, result.stdout + result.stderr
    output = result.stdout + result.stderr
    matches = re.findall(r"6 \((ternary_true|ternary_false)\)", output)

    assert len(matches) == 1, output
