"""Unit tests for boolean-operator and assert branch points in the plan
generator.

``and``/``or`` short-circuit and ``assert`` conditions are instrumented by
*wrapping* operand expressions with value-preserving tracker calls, exactly
like ternary arms. Each boolean operator node contributes:

* one ``<op>_site`` branch point whose span covers the whole operator
  expression (the site counter used to derive the short-circuit arm),
* one ``<op>_right`` branch point per right operand (operands sit at even
  child indices >= 2 in gdtoolkit's flat chains), and
* one ``<op>_short`` branch point with no span -- its hit count is derived
  by the collector as ``site - right``, so it must never be line-injected.

Each ``assert`` call contributes ``assert_true`` and ``assert_false`` points
sharing the condition's source span.

Covered here (Expression-Level Branch Coverage track):

* simple ``and``/``or`` conditions produce site/right/short points (FR-1)
* chained operators are measured per operator (FR-1)
* precedence mixes ``and``/``or`` with nested nodes (FR-1)
* parenthesized and multi-line expressions produce correct spans (FR-1)
* boolops in statements (assignment, while) are tracked (FR-1)
* class-level boolops without an anchor are not tracked (FR-1)
* ``assert`` calls produce assert_true/assert_false with the condition span
  (FR-1); the message argument is excluded
* plain conditions produce no expression points (FR-1)
"""

import pytest

from gd_tools.coverage.plan_generator import (
    PLAN_VERSION,
    CoveragePlan,
    generate_plan,
    generate_plan_cached,
    write_plan_json,
)

pytestmark = pytest.mark.unit


# --- Helpers ---


def _expr_points(tmp_path, source, name="sample.gd"):
    """Write a single GDScript file and return expression branch points.

    Returns ``[(branch_type, line, span), ...]`` for every point whose
    ``branch_type`` belongs to the expression families (``and_*``, ``or_*``,
    ``assert_*``). Assertion helpers key on ``branch_type`` because plan
    order follows the bottom-up visit and is not a contract.
    """
    (tmp_path / name).write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    assert len(plan.files) == 1, "expected exactly one planned file"
    prefixes = ("and_", "or_", "assert_")
    return [
        (p.branch_type, p.line, p.operand_span)
        for p in plan.files[0].lines
        if p.branch_type and p.branch_type.startswith(prefixes)
    ]


def _by_type(points, branch_type):
    """Return the ``(line, span)`` recorded for a specific expression point."""
    entries = [(line, span) for bt, line, span in points if bt == branch_type]
    assert len(entries) == 1, f"expected exactly one {branch_type} point"
    return entries[0]


def _count(points, branch_type):
    """Return how many points carry a branch type."""
    return len([1 for bt, _line, _span in points if bt == branch_type])


# --- FR-1: boolean-operator branch points ---


def test_simple_and_condition_produces_site_right_short(tmp_path):
    """``if a and b:`` yields one site, one right operand, one short arm."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\tif a and b:\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    # ``a and b`` starts at col 5; ``b`` sits at col 11; end-exclusive.
    assert _by_type(points, "and_site") == (4, (4, 5, 4, 12))
    assert _by_type(points, "and_right") == (4, (4, 11, 4, 12))
    short_line, short_span = _by_type(points, "and_short")
    assert short_span is None, "the derived short arm carries no span"
    assert short_line == 4


def test_simple_or_condition_produces_site_right_short(tmp_path):
    """``if a or b:`` yields the or_ family with the same shape."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\tif a or b:\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    # ``a or b`` starts at col 5; ``b`` sits at col 10; end-exclusive.
    assert _by_type(points, "or_site") == (4, (4, 5, 4, 11))
    assert _by_type(points, "or_right") == (4, (4, 10, 4, 11))
    assert _count(points, "or_short") == 1


def test_chained_and_is_measured_per_operator(tmp_path):
    """``a and b and c`` is one flat node: one site, two rights, two shorts."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool, c: bool) -> void:\n"
        "\tif a and b and c:\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    assert _count(points, "and_site") == 1
    assert _count(points, "and_right") == 2
    assert _count(points, "and_short") == 2
    assert _by_type(points, "and_site") == (4, (4, 5, 4, 18))
    # Right operands ``b`` (col 11) and ``c`` (col 17).
    right_spans = sorted(
        span for bt, _line, span in points if bt == "and_right"
    )
    assert right_spans == [(4, 11, 4, 12), (4, 17, 4, 18)]


def test_precedence_mix_produces_nested_operator_points(tmp_path):
    """``a or b and c`` tracks both the or node and the inner and node."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool, c: bool) -> void:\n"
        "\tif a or b and c:\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    # Outer or node: right operand is the whole ``b and c`` expression.
    assert _by_type(points, "or_site") == (4, (4, 5, 4, 17))
    assert _by_type(points, "or_right") == (4, (4, 10, 4, 17))
    # Inner and node spans ``b and c``; its right operand is ``c``.
    assert _by_type(points, "and_site") == (4, (4, 10, 4, 17))
    assert _by_type(points, "and_right") == (4, (4, 16, 4, 17))
    assert _count(points, "or_short") == 1
    assert _count(points, "and_short") == 1


def test_parenthesized_boolop_is_tracked(tmp_path):
    """``a and (b or c)`` tracks the and node and the parenthesized or."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool, c: bool) -> void:\n"
        "\tif a and (b or c):\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    assert _count(points, "and_site") == 1
    assert _count(points, "or_site") == 1
    # The and node's right operand spans the parenthesized ``b or c``.
    and_right_line, and_right_span = _by_type(points, "and_right")
    assert and_right_span[0] == 4
    assert and_right_span[1] == 11


def test_multiline_boolop_spans_cross_lines(tmp_path):
    """A boolop inside multi-line parens records spans across lines."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\tvar y = (\n"
        "\t\ta\n"
        "\t\tand b\n"
        "\t)\n"
        "\tprint(y)\n"
    )
    points = _expr_points(tmp_path, source)

    # The span crosses lines, but the recorded line stays on the anchor
    # statement (line 4), matching the ternary precedent.
    assert _by_type(points, "and_site") == (4, (5, 3, 6, 8))
    assert _by_type(points, "and_right") == (4, (6, 7, 6, 8))
    # The recorded line is the anchor statement's line, not a continuation.
    short_line, short_span = _by_type(points, "and_short")
    assert short_line == 4
    assert short_span is None


def test_boolop_in_assignment_is_tracked(tmp_path):
    """A boolop on the right side of an assignment is tracked."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\tvar x = a and b\n"
        "\treturn x\n"
    )
    points = _expr_points(tmp_path, source)

    # ``a and b`` starts at col 10 on line 4.
    assert _by_type(points, "and_site") == (4, (4, 10, 4, 17))
    assert _by_type(points, "and_right") == (4, (4, 16, 4, 17))


def test_boolop_in_while_condition_is_tracked(tmp_path):
    """A while condition's boolop is tracked like an if condition's."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\twhile a and b:\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    assert _by_type(points, "and_site") == (4, (4, 8, 4, 15))
    assert _count(points, "and_right") == 1


def test_class_level_boolop_is_not_tracked(tmp_path):
    """A boolop in a class-level initializer has no anchor and is dropped."""
    source = (
        "extends Node\n"
        "\n"
        "var flag: bool = true and false\n"
        "\n"
        "func f() -> void:\n"
        "\tprint(flag)\n"
    )
    points = _expr_points(tmp_path, source)

    assert points == [], "class-level boolops must not be tracked"


def test_plain_condition_produces_no_expression_points(tmp_path):
    """Conditions without and/or/assert produce no expression points."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool) -> void:\n"
        "\tif a:\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    assert points == []


# --- FR-1: assert branch points ---


def test_assert_produces_true_and_false_arms(tmp_path):
    """``assert(cond)`` yields assert_true/assert_false on the condition."""
    source = "extends Node\n" "\n" "func f(a: bool) -> void:\n" "\tassert(a)\n"
    points = _expr_points(tmp_path, source)

    # ``a`` sits at col 9 on line 4 (tab + ``assert(``).
    assert _by_type(points, "assert_true") == (4, (4, 9, 4, 10))
    assert _by_type(points, "assert_false") == (4, (4, 9, 4, 10))


def test_assert_with_message_excludes_message_from_span(tmp_path):
    """The condition span ends before the message argument."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool) -> void:\n"
        '\tassert(a, "must hold")\n'
    )
    points = _expr_points(tmp_path, source)

    assert _by_type(points, "assert_true") == (4, (4, 9, 4, 10))
    assert _by_type(points, "assert_false") == (4, (4, 9, 4, 10))


def test_assert_condition_expression_carries_full_span(tmp_path):
    """A non-literal assert condition spans the whole expression."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\tassert(a and b)\n"
    )
    points = _expr_points(tmp_path, source)

    # The assert condition is the whole ``a and b`` expression (cols 9-16).
    assert _by_type(points, "assert_true") == (4, (4, 9, 4, 16))
    assert _by_type(points, "assert_false") == (4, (4, 9, 4, 16))
    # The nested and node inside the assert condition is tracked too.
    assert _count(points, "and_site") == 1


# --- Exclusion interaction (FR-4) ---


def test_no_cover_annotation_suppresses_boolop_points(tmp_path):
    """A line-level no-cover annotation suppresses the line's boolop arms."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> void:\n"
        "\tif a and b:  # gd-tools: no cover\n"
        "\t\tprint(1)\n"
    )
    points = _expr_points(tmp_path, source)

    assert points == [], "excluded boolop lines must emit no expression points"


def test_no_cover_annotation_suppresses_assert_points(tmp_path):
    """A line-level no-cover annotation suppresses the line's assert arms."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool) -> void:\n"
        "\tassert(a)  # gd-tools: no cover\n"
    )
    points = _expr_points(tmp_path, source)

    assert points == [], "excluded assert lines must emit no expression points"


# --- Cache invalidation (FR-2) ---


def test_generate_plan_cached_miss_stale_plan_version(tmp_path):
    """A cached plan from a previous PLAN_VERSION is regenerated."""
    cache_path = tmp_path / "plan.json"
    (tmp_path / "player.gd").write_text(
        "extends Node\nfunc _ready():\n\tpass\n", encoding="utf-8"
    )
    stale = CoveragePlan(
        version=PLAN_VERSION - 1, generated_by="gd-tools", files=[]
    )
    write_plan_json(stale, str(cache_path))

    plan, status = generate_plan_cached(
        str(tmp_path), cache_path=str(cache_path)
    )

    assert status.hit is False, "stale plan version must force regeneration"
    assert plan.version == PLAN_VERSION
