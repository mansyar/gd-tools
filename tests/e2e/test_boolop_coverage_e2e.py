"""Per-arm boolean-operator coverage E2E: short-circuit arms measured
independently.

Exercises the public CLI against a fixture project with ``and``/``or``
subject suites so that the right-operand arm records only when the
operand actually evaluates under GDScript short-circuit semantics, the
``<op>_short`` arm is derived (site minus right), and behavioural
equivalence holds under instrumentation.
"""

import json
import os
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
    # Run the CLI against this checkout's src/ so worktree sessions test
    # their own code instead of a globally installed (editable) copy.
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        os.pathsep.join([repo_src, existing]) if existing else repo_src
    )
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


def _boolop_hits(plan: dict, data: dict) -> dict[tuple, int]:
    """Map (branch_type, line, operand_span, point_id) to hit counts.

    Keyed by span and id rather than branch type alone because chained
    operators emit several same-type points (one per right operand) and
    subject functions contribute same-type points on different lines.
    """
    entry = next(
        f for f in plan["files"] if f["path"].endswith("boolop_subject.gd")
    )
    ids = {
        (
            line["branch_type"],
            line["line"],
            tuple(line["operand_span"]) if line.get("operand_span") else None,
            line["id"],
        ): line["id"]
        for line in entry["lines"]
        if (line.get("branch_type") or "").startswith(("and_", "or_"))
    }
    file_data = next(
        f for f in data["files"] if f["file_id"] == entry["file_id"]
    )
    hits = file_data["hits"]
    return {
        key: int(hits.get(str(point_id), 0)) for key, point_id in ids.items()
    }


def _hits_for(hits: dict, branch_type: str, line: int) -> list[int]:
    """Hit counts for one branch type on one line, ordered by point id."""
    return [
        count
        for key, count in sorted(hits.items(), key=lambda item: item[0][3])
        if key[0] == branch_type and key[1] == line
    ]


def _assert_hits(plan: dict, data: dict) -> dict[tuple, int]:
    """Map (branch_type, line, operand_span, point_id) to hit counts for
    the assert subject."""
    entry = next(
        f for f in plan["files"] if f["path"].endswith("assert_subject.gd")
    )
    ids = {
        (
            line["branch_type"],
            line["line"],
            tuple(line["operand_span"]) if line.get("operand_span") else None,
            line["id"],
        ): line["id"]
        for line in entry["lines"]
        if (line.get("branch_type") or "").startswith("assert_")
    }
    file_data = next(
        f for f in data["files"] if f["file_id"] == entry["file_id"]
    )
    hits = file_data["hits"]
    return {
        key: int(hits.get(str(point_id), 0)) for key, point_id in ids.items()
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
def test_and_right_measured_when_right_evaluates(tmp_path, godot_bin):
    """``and`` with both operands evaluated records site and right only."""
    project, result = _run_coverage_suite(tmp_path, godot_bin, "AndBothSuite")

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _boolop_hits(plan, data)

    assert _hits_for(hits, "and_site", 6) == [1]
    assert _hits_for(hits, "and_right", 6) == [1]
    # The right operand evaluated, so the short-circuit arm never fired.
    assert _hits_for(hits, "and_short", 6) == [0]


@pytest.mark.slow
def test_and_right_not_measured_when_short_circuited(tmp_path, godot_bin):
    """``and`` with a false left operand skips the right operand."""
    project, result = _run_coverage_suite(tmp_path, godot_bin, "AndShortSuite")

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _boolop_hits(plan, data)

    assert _hits_for(hits, "and_site", 6) == [1]
    assert _hits_for(hits, "and_right", 6) == [0]
    assert _hits_for(hits, "and_short", 6) == [1]


@pytest.mark.slow
def test_or_right_measured_when_left_false(tmp_path, godot_bin):
    """``or`` with a false left operand evaluates the right operand."""
    project, result = _run_coverage_suite(tmp_path, godot_bin, "OrRightSuite")

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _boolop_hits(plan, data)

    assert _hits_for(hits, "or_site", 10) == [1]
    assert _hits_for(hits, "or_right", 10) == [1]
    assert _hits_for(hits, "or_short", 10) == [0]


@pytest.mark.slow
def test_or_right_not_measured_when_left_true(tmp_path, godot_bin):
    """``or`` with a true left operand skips the right operand."""
    project, result = _run_coverage_suite(tmp_path, godot_bin, "OrShortSuite")

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _boolop_hits(plan, data)

    assert _hits_for(hits, "or_site", 10) == [1]
    assert _hits_for(hits, "or_right", 10) == [0]
    assert _hits_for(hits, "or_short", 10) == [1]


@pytest.mark.slow
def test_chained_and_arms_measured_independently(tmp_path, godot_bin):
    """Each operator in a chain tracks its own right operand."""
    project, result = _run_coverage_suite(tmp_path, godot_bin, "ChainSuite")

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _boolop_hits(plan, data)

    # ``a and b and c`` with a=true, b=false: the first right operand (b)
    # evaluates, the second (c) never does.
    assert _hits_for(hits, "and_site", 14) == [1]
    assert _hits_for(hits, "and_right", 14) == [1, 0]
    # Short arms derived per operator: b's operator short-circuited on the
    # second operator, so its short arm fired once; b evaluated, so the
    # first operator's short arm never fired.
    assert _hits_for(hits, "and_short", 14) == [0, 1]


@pytest.mark.slow
def test_behavioral_equivalence_under_instrumentation(tmp_path, godot_bin):
    """Wrapping is semantically transparent (FR-3).

    Each right operand evaluates exactly when the original short-circuit
    semantics reach it, and returned values are unchanged.
    """
    _, result = _run_coverage_suite(
        tmp_path, godot_bin, "BoolopBehaviorSuite"
    )

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.slow
def test_assert_true_measured_when_condition_holds(tmp_path, godot_bin):
    """A passing assert records its true arm and never its false arm."""
    project, result = _run_coverage_suite(
        tmp_path, godot_bin, "AssertTrueSuite"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    plan, data = _coverage_artifacts(project)
    hits = _assert_hits(plan, data)

    assert _hits_for(hits, "assert_true", 6) == [1]
    assert _hits_for(hits, "assert_false", 6) == [0]


@pytest.mark.slow
def test_hit_bool_records_exactly_one_arm(tmp_path, godot_bin):
    """One hit_bool call records exactly one arm and passes the value.

    A firing assert halts headless debug runs (the engine never quits),
    so the false arm cannot be observed through a real assert. This test
    drives the collector's own hit_bool entry point through both truth
    values, the same call the assert instrumentation emits.
    """
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )
    # A coverage run installs the addon the probe drives.
    suite_result = _run_cli(
        ["--quiet", "test", "--coverage", "--suite", "AssertTrueSuite"],
        project,
        godot_bin,
    )
    assert suite_result.returncode == 0, (
        suite_result.stdout + suite_result.stderr
    )

    env = os.environ.copy()
    env.update({"GODOT_BIN": godot_bin, "PYTHONIOENCODING": "utf-8"})
    probe = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://collector_probe.gd",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr

    out = json.loads(
        (project / "collector_probe_out.json").read_text(encoding="utf-8")
    )
    file_hits = out["files"][0]["hits"]
    # Two calls, one arm each: the true call hit 10 only, the false call
    # hit 11 only.
    assert file_hits == {"10": 1, "11": 1}
    values = (project / "collector_probe_values.txt").read_text(
        encoding="utf-8"
    )
    assert values.strip() == "activated=true kept=true dropped=false written=true"