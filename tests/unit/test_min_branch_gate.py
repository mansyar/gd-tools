"""Per-arm ternary measurement and the ``--min-branch`` gate.

Ternary arms are measured under independent plan-point ids (Ternary Branch
Separation): ``ternary_true`` and ``ternary_false`` must be able to disagree,
and an uncovered arm must be able to fail a branch threshold gate.
"""

import pytest

from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    FilePlan,
    LinePlan,
)
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageThresholdError,
    FileCoverage,
    compute_file_summary,
    compute_summary,
    generate_report,
)

pytestmark = pytest.mark.unit


def _no_branch_plan_and_data():
    """A one-file plan with statements only — zero branch points."""
    plan = CoveragePlan(
        version=4,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://t.gd",
                source_hash="sha256:x",
                lines=[
                    LinePlan(line=4, id=0, type="statement"),
                    LinePlan(line=5, id=1, type="statement"),
                ],
            )
        ],
    )
    data = CoverageData(
        version=1, files=[FileCoverage(file_id=0, hits={"0": 1, "1": 1})]
    )
    return plan, data


def _ternary_plan_and_data(covered_arms: str):
    """A one-file plan with a statement and both ternary arms on line 4."""
    plan = CoveragePlan(
        version=4,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://t.gd",
                source_hash="sha256:x",
                lines=[
                    LinePlan(line=4, id=0, type="statement"),
                    LinePlan(
                        line=4, id=1, type="branch", branch_type="ternary_true"
                    ),
                    LinePlan(
                        line=4, id=2, type="branch", branch_type="ternary_false"
                    ),
                ],
            )
        ],
    )
    hits = {"0": 1}
    if covered_arms in ("true", "both"):
        hits["1"] = 1
    if covered_arms in ("false", "both"):
        hits["2"] = 1
    data = CoverageData(version=1, files=[FileCoverage(file_id=0, hits=hits)])
    return plan, data


def test_ternary_arms_are_measured_independently():
    """One covered arm yields branch_rate 0.5, not 1.0."""
    plan, data = _ternary_plan_and_data("true")

    summary = compute_summary(plan, data)

    assert summary.total_branches == 2
    assert summary.covered_branches == 1
    assert summary.branch_rate == 0.5


def test_uncovered_arm_lists_anchor_line_once():
    """Display stays combined: the anchor line appears once, not per arm."""
    plan, data = _ternary_plan_and_data("true")

    file_summary = compute_file_summary(plan.files[0], data.files[0])

    assert file_summary.uncovered_branches == [4]


def test_min_branch_threshold_fails_on_uncovered_arm(tmp_path):
    """An uncovered ternary arm fails a 100% branch threshold."""
    plan, data = _ternary_plan_and_data("true")

    with pytest.raises(CoverageThresholdError) as exc_info:
        generate_report(
            plan,
            data,
            tmp_path,
            "text",
            min_branch_threshold=1.0,
        )

    assert "branch" in str(exc_info.value).lower()


def test_min_branch_threshold_passes_when_both_arms_covered(tmp_path):
    plan, data = _ternary_plan_and_data("both")

    result = generate_report(
        plan,
        data,
        tmp_path,
        "text",
        min_branch_threshold=1.0,
    )

    assert result.threshold_met is True


def test_min_branch_combines_with_min_line(tmp_path):
    """Both gates must pass; either failing raises."""
    plan, data = _ternary_plan_and_data("true")  # line 100%, branch 50%

    with pytest.raises(CoverageThresholdError):
        generate_report(
            plan,
            data,
            tmp_path,
            "text",
            min_threshold=0.5,
            min_branch_threshold=1.0,
        )

    result = generate_report(
        plan,
        data,
        tmp_path,
        "text",
        min_threshold=0.5,
        min_branch_threshold=0.5,
    )
    assert result.threshold_met is True


def test_no_branch_threshold_keeps_line_only_gate(tmp_path):
    """Without --min-branch the gate behavior is unchanged."""
    plan, data = _ternary_plan_and_data("true")  # branch 50%

    result = generate_report(
        plan,
        data,
        tmp_path,
        "text",
        min_threshold=0.5,
    )

    assert result.threshold_met is True


def test_min_branch_exempt_when_zero_branch_points(tmp_path):
    """A positive --min-branch must not fail a project with no branches."""
    plan, data = _no_branch_plan_and_data()

    result = generate_report(
        plan,
        data,
        tmp_path,
        "text",
        min_branch_threshold=1.0,
    )

    assert result.threshold_met is True
    assert result.summary.total_branches == 0


def test_threshold_footer_notes_zero_branch_exemption(capsys):
    """The footer note explains the exemption instead of a pass/fail line."""
    from gd_tools.coverage.orchestrator import print_threshold_footer

    plan, data = _no_branch_plan_and_data()
    summary = compute_summary(plan, data)

    print_threshold_footer(summary, None, 80)

    out = capsys.readouterr().out
    assert "no branch points" in out.lower()


def test_footer_still_prints_populated_branch_line(capsys):
    """Populated branch projects get the branch-rate footer line."""
    from gd_tools.coverage.orchestrator import print_threshold_footer

    plan, data = _ternary_plan_and_data("true")
    summary = compute_summary(plan, data)

    print_threshold_footer(summary, None, 80)

    out = capsys.readouterr().out
    assert "branch coverage (threshold: 80%)" in out
    assert "no branch points" not in out.lower()
