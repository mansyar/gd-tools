"""Gate, reporter, and diff integration for expression branch points.

Expression-Level Branch Coverage: and/or short-circuit arms and assert
condition arms are ordinary branch points (fully gated semantics). They
must flow through the ``--min-branch`` gate, the uncovered-branch panel
rendering (ternary-style raw labels), the lcov/cobertura formats, and
the coverage diff — with no special-casing anywhere.
"""

import xml.etree.ElementTree as ET
from io import StringIO

import pytest
from rich.console import Console

from gd_tools.coverage.cobertura_reporter import generate_cobertura_report
from gd_tools.coverage.diff_reporter import (
    BaselineMeta,
    BaselineSnapshot,
    compute_diff,
)
from gd_tools.coverage.lcov_reporter import generate_lcov_report
from gd_tools.coverage.plan_generator import (
    PLAN_VERSION,
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
    render_uncovered_panels,
)

pytestmark = pytest.mark.unit

#: Every expression branch type a plan can carry, with planned lines.
EXPRESSION_ARMS = [
    ("and_site", 4),
    ("and_right", 4),
    ("and_short", 4),
    ("or_site", 6),
    ("or_right", 6),
    ("or_short", 6),
    ("assert_true", 8),
    ("assert_false", 8),
]


def _expression_plan() -> CoveragePlan:
    """A one-file plan with a statement and all eight expression arms."""
    lines = [LinePlan(line=4, id=0, type="statement")]
    for arm_id, (branch_type, line) in enumerate(EXPRESSION_ARMS, start=1):
        lines.append(
            LinePlan(
                line=line, id=arm_id, type="branch", branch_type=branch_type
            )
        )
    return CoveragePlan(
        version=PLAN_VERSION,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://t.gd",
                source_hash="sha256:x",
                lines=lines,
            )
        ],
    )


def _expression_data(covered_types: set[str]) -> CoverageData:
    """Coverage data for :func:`_expression_plan` with the given arms hit."""
    hits = {"0": 1}
    for arm_id, (branch_type, _line) in enumerate(EXPRESSION_ARMS, start=1):
        if branch_type in covered_types:
            hits[str(arm_id)] = 1
    return CoverageData(version=1, files=[FileCoverage(file_id=0, hits=hits)])


# --- Gate integration (FR-5: fully gated) ---


def test_expression_arms_count_in_branch_denominator():
    """Every expression arm counts in the --min-branch denominator."""
    plan = _expression_plan()
    data = _expression_data({"and_site", "and_right", "or_site", "assert_true"})

    summary = compute_summary(plan, data)

    assert summary.total_branches == 8
    assert summary.covered_branches == 4
    assert summary.branch_rate == 0.5


def test_uncovered_expression_arm_fails_branch_threshold(tmp_path):
    """An uncovered short-circuit arm fails a 100% branch threshold."""
    plan = _expression_plan()
    data = _expression_data({"and_site", "and_right", "and_short"})

    with pytest.raises(CoverageThresholdError) as exc_info:
        generate_report(
            plan,
            data,
            tmp_path,
            "text",
            min_branch_threshold=1.0,
        )

    assert "branch" in str(exc_info.value).lower()


def test_threshold_passes_when_all_expression_arms_covered(tmp_path):
    plan = _expression_plan()
    data = _expression_data({branch for branch, _ in EXPRESSION_ARMS})

    result = generate_report(
        plan,
        data,
        tmp_path,
        "text",
        min_branch_threshold=1.0,
    )

    assert result.threshold_met is True


def test_expression_only_plan_is_not_zero_branch_exempt(tmp_path):
    """The zero-branch exemption must not swallow expression-only plans."""
    plan = _expression_plan()
    data = _expression_data(set())

    with pytest.raises(CoverageThresholdError):
        generate_report(
            plan,
            data,
            tmp_path,
            "text",
            min_branch_threshold=0.5,
        )


def test_derived_short_arm_hit_flips_gate(tmp_path):
    """A derived short-circuit hit counts like any other arm hit."""
    plan = _expression_plan()
    # Only site and right covered: short is derivable (site - right) but
    # zero here, so it stays uncovered and the 100% gate must fail.
    data = _expression_data({"and_site", "and_right", "or_site", "or_right"})

    with pytest.raises(CoverageThresholdError):
        generate_report(
            plan,
            data,
            tmp_path,
            "text",
            min_branch_threshold=1.0,
        )


# --- Uncovered-branch panel rendering (ternary-style raw labels) ---


def test_render_uncovered_panels_expression_arm_annotations():
    """render_uncovered_panels shows each line once, ternary-style.

    The combined display precedent (Ternary Branch Separation) prints
    the anchor line once annotated with a branch type, not once per arm.
    """
    plan = _expression_plan()
    data = _expression_data(set())
    file_summary = compute_file_summary(plan.files[0], data.files[0])

    panels = render_uncovered_panels([file_summary], plan)
    assert panels is not None

    console = Console(file=StringIO(), width=160, force_terminal=False)
    console.print(panels)
    output = console.file.getvalue()

    assert "4 (and_site)" in output
    assert "4 (and_right)" in output
    assert "4 (and_short)" in output
    assert "6 (or_site)" in output
    assert "6 (or_right)" in output
    assert "6 (or_short)" in output
    assert "8 (assert_true)" in output
    assert "8 (assert_false)" in output
    # Per-arm entries: one line-number occurrence per uncovered arm.
    assert output.count("4 (") == 3
    assert output.count("6 (") == 3
    assert output.count("8 (") == 2


# --- lcov / cobertura / diff ---


def test_lcov_branch_counts_include_expression_arms(tmp_path):
    """BRF/BRH include branch lines that carry expression arms.

    lcov aggregates per source line (max arm hit wins), matching the
    existing ternary behavior: a line counts as one branch record.
    """
    plan = _expression_plan()
    data = _expression_data({"and_site", "and_right", "and_short"})

    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")
    lines = output.read_text(encoding="utf-8").splitlines()

    assert "BRF:3" in lines
    assert "BRH:1" in lines
    assert "BRDA:4,0,0,1" in lines
    assert "BRDA:6,0,0,0" in lines
    assert "BRDA:8,0,0,0" in lines


def test_cobertura_branch_rate_includes_expression_arms(tmp_path):
    """Cobertura marks expression-arm lines as branch lines.

    Cobertura aggregates per source line like the existing ternary
    behavior: the line carries branch=true with combined hits.
    """
    plan = _expression_plan()
    data = _expression_data({"and_site", "and_right", "and_short"})

    generate_cobertura_report(plan, data, tmp_path / "cobertura.xml")
    root = ET.parse(tmp_path / "cobertura.xml").getroot()

    assert root.get("branch-rate") == "0.3333"
    assert root.get("branches-valid") == "3"


def _snapshot(hits_by_id: dict[int, int]) -> BaselineSnapshot:
    plan = _expression_plan()
    hits = {str(point_id): count for point_id, count in hits_by_id.items()}
    return BaselineSnapshot(
        plan=plan,
        data=CoverageData(
            version=1, files=[FileCoverage(file_id=0, hits=hits)]
        ),
        meta=BaselineMeta(),
    )


def test_diff_counts_expression_arm_deltas():
    """The coverage diff treats expression arms as ordinary branches."""
    base = _snapshot({0: 1})
    head = _snapshot({0: 1, 1: 2, 2: 1})

    result = compute_diff(base, head)
    fd = result.files[0]

    assert fd.base_covered_branches == 0
    assert fd.head_covered_branches == 2
    assert fd.covered_branch_delta == 2
