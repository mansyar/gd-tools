"""Unit tests for ternary operand span extraction in the plan generator.

Ternary branch points are instrumented by *wrapping* each operand expression
with a value-preserving tracker call, not by inserting a statement before the
anchor line. To do that, the plan must record where each operand sits in the
source: a ``(start_line, start_col, end_line, end_col)`` span with 1-based
lines and columns and an exclusive end.

Covered here (Ternary Branch Separation track):

* every ternary branch point carries its operand's source span (FR-1)
* operand spans come from expression nodes and literal tokens alike (FR-1)
* multi-line ternaries produce spans that cross lines correctly (FR-1)
* a nested ternary's outer false operand spans the whole inner expression (FR-1)
* non-ternary points carry no operand span (FR-1)
* ``PLAN_VERSION`` is bumped 3 -> 4 so stale cached plans regenerate (FR-1)
* spans round-trip through plan JSON (FR-5)
"""

import pytest

from gd_tools.coverage.plan_generator import (
    PLAN_VERSION,
    generate_plan,
    read_plan_json,
    write_plan_json,
)

pytestmark = pytest.mark.unit


# --- Helpers ---


def _ternary_points(tmp_path, source, name="sample.gd"):
    """Write a single GDScript file and return ``[(branch_type, span), ...]``.

    Spans appear in plan order; each entry is the ``operand_span`` of a
    ternary branch point. Assertion helpers key on ``branch_type`` because
    plan order follows the bottom-up visit and is not a contract.
    """
    (tmp_path / name).write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    assert len(plan.files) == 1, "expected exactly one planned file"
    return [
        (p.branch_type, p.operand_span)
        for p in plan.files[0].lines
        if p.branch_type and p.branch_type.startswith("ternary")
    ]


def _by_type(points, branch_type):
    """Return the span recorded for a specific ternary arm."""
    spans = [span for bt, span in points if bt == branch_type]
    assert len(spans) == 1, f"expected exactly one {branch_type} point"
    return spans[0]


# --- FR-1: operand spans on ternary branch points ---


def test_ternary_branch_points_carry_operand_spans(tmp_path):
    """Both arms record the exact source span of their operand."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x = 10 if a > 0 else 20\n"
        "\treturn x\n"
    )
    points = _ternary_points(tmp_path, source)

    assert _by_type(points, "ternary_true") == (4, 10, 4, 12)
    assert _by_type(points, "ternary_false") == (4, 27, 4, 29)


def test_expression_operands_get_span_from_tree(tmp_path):
    """Call operands (Tree nodes) carry their own span, like literal tokens."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar y = foo(1) if a > 0 else 3\n"
        "\treturn y\n"
    )
    points = _ternary_points(tmp_path, source)

    assert _by_type(points, "ternary_true") == (4, 10, 4, 16)
    assert _by_type(points, "ternary_false") == (4, 31, 4, 32)


def test_multiline_ternary_operand_spans_cross_lines(tmp_path):
    """A ternary in multi-line parens records each operand on its own line."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar z = (\n"
        "\t\t100\n"
        "\t\tif a > 0\n"
        "\t\telse 200\n"
        "\t)\n"
        "\tprint(z)\n"
    )
    points = _ternary_points(tmp_path, source)

    # ``100`` sits on line 5, ``200`` on line 7 -- both 1-based, tab = 1 col.
    assert _by_type(points, "ternary_true") == (5, 3, 5, 6)
    assert _by_type(points, "ternary_false") == (7, 8, 7, 11)


def test_nested_ternary_false_operand_span_covers_inner_expression(tmp_path):
    """The outer false operand spans the whole nested ternary expression."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x = 1 if a > 0 else 2 if a < 0 else 3\n"
        "\treturn x\n"
    )
    points = _ternary_points(tmp_path, source)

    assert _by_type(points, "ternary_true") == (4, 10, 4, 11)
    # ``2 if a < 0 else 3`` -- cols 26..42, end-exclusive 43.
    assert _by_type(points, "ternary_false") == (4, 26, 4, 43)


def test_non_ternary_points_have_no_operand_span(tmp_path):
    """Statements and non-ternary branches carry no operand span."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x = 10 if a > 0 else 20\n"
        "\tif x > 0:\n"
        "\t\tprint(x)\n"
        "\treturn x\n"
    )
    (tmp_path / "sample.gd").write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))

    non_ternary = [
        p
        for p in plan.files[0].lines
        if not (p.branch_type or "").startswith("ternary")
    ]
    assert non_ternary, "expected statement and if-branch points to exist"
    assert all(p.operand_span is None for p in non_ternary)


# --- FR-1: plan version bump ---


def test_plan_version_is_7_with_expression_branch_points():
    """PLAN_VERSION bumps past span-less and expression-less plans (3-6)
    so they regenerate."""
    assert PLAN_VERSION == 7


# --- FR-5: JSON round-trip ---


def test_operand_spans_round_trip_through_json(tmp_path):
    """A written plan re-reads with operand spans intact."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x = 10 if a > 0 else 20\n"
        "\treturn x\n"
    )
    (tmp_path / "sample.gd").write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))

    plan_path = tmp_path / "plan.json"
    write_plan_json(plan, str(plan_path))
    reloaded = read_plan_json(str(plan_path))

    original = [
        (p.branch_type, p.operand_span)
        for p in plan.files[0].lines
        if p.branch_type and p.branch_type.startswith("ternary")
    ]
    recovered = [
        (p.branch_type, p.operand_span)
        for p in reloaded.files[0].lines
        if p.branch_type and p.branch_type.startswith("ternary")
    ]
    assert original, "expected ternary points in the plan"
    assert recovered == original
