"""Unit tests for match statement coverage end-to-end.

Tests that the plan generator correctly identifies match_case branches
and the reporter correctly marks them as covered when hits are recorded.
This test does not require Godot — it exercises the Python-side pipeline
only (plan generation -> hit simulation -> coverage reporting).
"""

import pytest

from gd_tools.coverage.plan_generator import generate_plan
from gd_tools.coverage.reporter import FileCoverage, compute_file_summary

pytestmark = pytest.mark.unit

_MATCH_SOURCE = (
    "extends Node\n"
    "func handle_state(state: int) -> void:\n"
    "\tmatch state:\n"
    "\t\t0:\n"
    '\t\t\tprint("idle")\n'
    "\t\t1:\n"
    '\t\t\tprint("running")\n'
    "\t\t2:\n"
    '\t\t\tprint("paused")\n'
    "\t\t_:\n"
    '\t\t\tprint("unknown")\n'
)


def test_match_coverage_all_branches_hit(tmp_path):
    """All match_case branches are reported as covered when all are hit."""
    (tmp_path / "match_test.gd").write_text(_MATCH_SOURCE, encoding="utf-8")

    plan = generate_plan(str(tmp_path))
    assert len(plan.files) == 1
    file_plan = plan.files[0]

    match_branches = [
        lp for lp in file_plan.lines if lp.branch_type == "match_case"
    ]
    assert (
        len(match_branches) == 4
    ), "should have 4 match_case branches (0, 1, 2, _)"

    # Simulate hits for all match_case branches
    hits = {str(lp.id): 1 for lp in match_branches}
    file_coverage = FileCoverage(file_id=file_plan.file_id, hits=hits)

    summary = compute_file_summary(file_plan, file_coverage)
    assert summary.total_branches == 4, "should have 4 total branches"
    assert (
        summary.covered_branches == 4
    ), "all 4 match_case branches should be covered"


def test_match_coverage_partial_branches_hit(tmp_path):
    """Only hit match_case branches are reported as covered."""
    (tmp_path / "match_test.gd").write_text(_MATCH_SOURCE, encoding="utf-8")

    plan = generate_plan(str(tmp_path))
    file_plan = plan.files[0]

    match_branches = [
        lp for lp in file_plan.lines if lp.branch_type == "match_case"
    ]
    assert len(match_branches) == 4

    # Hit only the first 2 match_case branches
    hits = {str(match_branches[0].id): 1, str(match_branches[1].id): 1}
    file_coverage = FileCoverage(file_id=file_plan.file_id, hits=hits)

    summary = compute_file_summary(file_plan, file_coverage)
    assert summary.total_branches == 4, "should have 4 total branches"
    assert (
        summary.covered_branches == 2
    ), "only 2 match_case branches should be covered"
    assert summary.branch_rate == 0.5, "branch rate should be 50%"
