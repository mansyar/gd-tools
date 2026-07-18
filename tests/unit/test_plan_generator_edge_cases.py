"""Unit tests for advanced GDScript AST edge cases in the coverage plan generator.

Exercises 8 advanced GDScript 4.5+ syntax patterns against CoverageVisitor:
ternary expressions, lambdas, setter/getter blocks, match bind patterns,
@onready/@export annotations, builtin/static calls, await expressions,
and super() calls.

Audit (Track 38 Phase 1) confirmed only ternary is a genuine gap; the
remaining 7 patterns are already tracked by existing visitor methods.
These tests serve as regression guards for all 8 patterns.
"""

import pytest

from gd_tools.coverage.plan_generator import parse_gdscript

pytestmark = pytest.mark.unit


# --- Ternary (genuine gap — RED until test_expr visitor is added) ---


def test_ternary_produces_both_branch_points():
    """Ternary expression produces ternary_true and ternary_false branch points."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    var x = 10\n"
        "    var r = 42 if x > 5 else 0\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    assert "ternary_true" in branch_types
    assert "ternary_false" in branch_types


# --- Verification tests (audit confirmed already tracked; these guard regressions) ---


def test_lambda_body_statements_tracked():
    """Lambda function body statements are tracked via existing visitor methods."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    var cb = func():\n"
        "        return 42\n"
        "    var result = cb.call()\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    lines = [p.line for p in visitor.points]
    # Lambda body return statement (line 4) must be tracked
    assert 4 in lines
    # Lambda assignment (line 3) and call result (line 5) also tracked
    assert 3 in lines
    assert 5 in lines


def test_setter_getter_bodies_tracked():
    """Setter and getter block bodies are tracked via existing visitor methods."""
    source = (
        "extends Node\n"
        "var health: int = 100:\n"
        "    set(value):\n"
        "        health = value\n"
        "    get:\n"
        "        return health\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    lines = [p.line for p in visitor.points]
    # Setter body (line 4) and getter body (line 6) must be tracked
    assert 4 in lines
    assert 6 in lines


def test_match_bind_pattern_tracked():
    """Match bind pattern (var y:) produces a match_case branch point."""
    source = (
        "extends Node\n"
        "func handle(value):\n"
        "    match value:\n"
        "        var y:\n"
        "            print(y)\n"
        "        _:\n"
        '            print("default")\n'
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    match_branches = [
        p
        for p in visitor.points
        if p.type == "branch" and p.branch_type == "match_case"
    ]
    # At least 2 match cases: var y: (bind) and _ (wildcard)
    assert len(match_branches) >= 2


def test_annotations_produce_no_false_positives():
    """@onready and @export annotations do not produce trackable points."""
    source = (
        "extends Node\n"
        "@onready var node: Node\n"
        "@export var speed: float = 1.0\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    assert len(visitor.points) == 0


def test_builtin_call_tracked():
    """Builtin function calls are tracked via expr_stmt or func_var_assigned."""
    source = "extends Node\n" "func _ready():\n" "    var n = absi(-5)\n"
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    lines = [p.line for p in visitor.points]
    assert 3 in lines


def test_await_expression_tracked():
    """await expressions are tracked via enclosing statement visitor."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    await get_tree().process_frame\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    lines = [p.line for p in visitor.points]
    assert 3 in lines


def test_super_call_tracked():
    """super() calls are tracked via expr_stmt."""
    source = "extends Node\n" "func _ready():\n" "    super._ready()\n"
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    lines = [p.line for p in visitor.points]
    assert 3 in lines
