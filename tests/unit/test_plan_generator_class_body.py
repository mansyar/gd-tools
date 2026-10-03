"""Unit tests for class-body statement anchoring in the plan generator.

A statement inside a lambda body records at the lambda's own line. When
that line is a class-member declaration line or a function-signature line,
the collector injects a tracker call where GDScript permits no statement,
the instrumented file fails to parse, and the whole file silently drops
out of coverage. These tests pin the anchoring rules defined in the
instrumentation_hygiene_20261003 spec (FR-1, FR-2, FR-3, FR-6):

- FR-1: no point records on a class-member declaration line or a
  function-signature line.
- FR-2: multi-line lambda body statements keep their own (legal) lines.
- FR-3: illegal points are dropped silently, not mis-anchored.
- FR-6: func-level single-line lambda bodies are unchanged.
"""

import pytest

from gd_tools.coverage.plan_generator import generate_plan

pytestmark = pytest.mark.unit


def _lines_for(tmp_path, source, name="sample.gd"):
    """Write ``source`` into ``tmp_path`` and return its planned points.

    Args:
        tmp_path: Pytest temporary directory to write the fixture into.
        source: GDScript source text.
        name: File name to use inside the temporary directory.

    Returns:
        The ``LinePlan`` list of the single planned file.

    Raises:
        AssertionError: If the plan contains more than one file.
    """
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    assert len(plan.files) == 1
    return plan.files[0].lines


def _statements(lines):
    """Return ``(id, line)`` pairs for statement points.

    Args:
        lines: The ``LinePlan`` list of a planned file.

    Returns:
        List of ``(id, line)`` tuples in plan order.
    """
    return [(p.id, p.line) for p in lines if p.type == "statement"]


CLASS_LAMBDA_CASES = {
    "var_return": (
        "class_name C\n"
        "\n"
        "class Inner:\n"
        "\tvar F = func(): return 2\n"
        "\tfunc m() -> void:\n"
        "\t\tprint(1)\n"
    ),
    "var_print": (
        "class_name C\n"
        "\n"
        "class Inner:\n"
        "\tvar F = func(): print(1)\n"
        "\tfunc m() -> void:\n"
        "\t\tprint(2)\n"
    ),
    "static_var": (
        "class_name C\n"
        "\n"
        "class Inner:\n"
        "\tstatic var S = func(): return 2\n"
        "\tfunc m() -> void:\n"
        "\t\tprint(1)\n"
    ),
    "top_level_var": (
        "class_name C\n"
        "\n"
        "var E = func(): return 2\n"
        "\n"
        "func m() -> void:\n"
        "\tprint(1)\n"
    ),
}


@pytest.mark.parametrize("case", sorted(CLASS_LAMBDA_CASES))
def test_class_level_lambda_body_is_not_tracked(tmp_path, case):
    """FR-1/FR-3: a single-line lambda body in a class member is dropped.

    The body statement records on the declaration line, which is a
    class-body line where no statement may begin. It must be dropped
    rather than mis-anchored; only the method's own statements remain.
    """
    lines = _lines_for(tmp_path, CLASS_LAMBDA_CASES[case])
    assert _statements(lines) == [(0, 6)]


def test_top_level_export_lambda_body_is_not_tracked(tmp_path):
    """FR-1/FR-3: an ``@export`` initializer lambda body is dropped."""
    source = (
        "extends Node\n"
        "\n"
        "@export var E = func(): return 2\n"
        "\n"
        "func m() -> void:\n"
        "\tprint(1)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 6)]


def test_class_level_multiline_lambda_body_stays_tracked(tmp_path):
    """FR-2: a multi-line lambda body records on its own legal line.

    The body statement's line is inside the lambda body, where a
    statement may begin, so it stays tracked.
    """
    source = (
        "class_name C\n"
        "\n"
        "class Inner:\n"
        "\tvar F = func():\n"
        "\t\treturn 2\n"
        "\tfunc m() -> void:\n"
        "\t\tprint(1)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 5), (1, 7)]


def test_func_level_single_line_lambda_is_unchanged(tmp_path):
    """FR-6: a func-level single-line lambda body still records.

    The declaration line sits inside a function body, where injecting
    before it is legal, so both the ``var`` statement and the lambda
    body statement keep recording on it.
    """
    source = (
        "extends Node\n"
        "\n"
        "func m() -> void:\n"
        "\tvar f = func(): return 2\n"
        "\tf.call()\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 4), (1, 4), (2, 5)]


def test_default_parameter_lambda_body_is_not_tracked(tmp_path):
    """FR-1/FR-3: a lambda in a default parameter is dropped.

    The body statement records on the ``func`` signature line, which is
    never a legal insertion point.
    """
    source = (
        "extends Node\n"
        "\n"
        "func f(x = func(): return 2) -> void:\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 4)]


def test_plain_class_initializer_records_no_statement(tmp_path):
    """A plain class-level initializer never records a statement point.

    Guards the existing behaviour that makes only lambda body
    statements leak onto class-body lines.
    """
    source = (
        "class_name C\n"
        "\n"
        "class Inner:\n"
        "\tvar n = 1\n"
        "\tfunc m() -> void:\n"
        "\t\tprint(n)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 6)]


def test_method_statements_are_unaffected(tmp_path):
    """FR-6: statements inside regular methods are untouched."""
    source = (
        "extends Node\n"
        "\n"
        "func m() -> void:\n"
        "\tvar a = 1\n"
        "\tprint(a)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 4), (1, 5)]


# --- Bracket-continuation lines (review finding: High) ---


CONTINUATION_CASES = {
    "inline_dict": (
        "extends Node\n"
        "\n"
        "var handlers = {\n"
        '\t"k": func(): print(1),\n'
        "}\n"
        "\n"
        "func m() -> void:\n"
        "\tprint(handlers)\n"
    ),
    "paren_lambda": (
        "extends Node\n"
        "\n"
        "var f = (\n"
        "\tfunc(): print(1)\n"
        ")\n"
        "\n"
        "func m() -> void:\n"
        "\tprint(f)\n"
    ),
    "func_ml_expr": (
        "extends Node\n"
        "\n"
        "func m() -> void:\n"
        "\tvar F = foo(\n"
        "\t\tfunc(): print(1)\n"
        "\t)\n"
        "\tprint(F)\n"
    ),
    "backslash": (
        "extends Node\n"
        "\n"
        "func m() -> void:\n"
        "\tvar x = 1 + \\\n"
        "\t\tfunc(): print(1)\n"
        "\tprint(x)\n"
    ),
    "block_in_dict": (
        "extends Node\n"
        "\n"
        "var h = {\n"
        '\t"k": func():\n'
        "\t\tprint(1),\n"
        "}\n"
        "\n"
        "func m() -> void:\n"
        "\tprint(h)\n"
    ),
    "nested_lambda_inline": (
        "extends Node\n"
        "\n"
        'var h = {"k": func(): print(func(): return 1)}\n'
        "\n"
        "func m() -> void:\n"
        "\tprint(h)\n"
    ),
}

CONTINUATION_EXPECTED = {
    "inline_dict": [(0, 8)],
    "paren_lambda": [(0, 8)],
    "func_ml_expr": [(0, 4), (1, 7)],
    "backslash": [(0, 4), (1, 6)],
    "block_in_dict": [(0, 9)],
    "nested_lambda_inline": [(0, 6)],
}


@pytest.mark.parametrize("case", sorted(CONTINUATION_CASES))
def test_statement_on_a_bracket_continuation_line_is_dropped(tmp_path, case):
    """A point on a line inside an open bracket must not be recorded.

    The lambda body statement squashes onto a continuation line of a
    multi-line initializer expression. Injecting a tracker before such a
    line places a statement inside the open bracket, the instrumented
    file fails to parse, and the file silently drops out of coverage.
    The point must be dropped instead; only statements on legal lines
    remain.
    """
    lines = _lines_for(tmp_path, CONTINUATION_CASES[case])
    assert _statements(lines) == CONTINUATION_EXPECTED[case]


def test_onready_lambda_body_is_dropped(tmp_path):
    """An ``@onready`` initializer lambda body is dropped like ``@export``.

    Annotations do not change the AST node name, so the declaration line
    rule must cover ``@onready`` the same way.
    """
    source = (
        "class_name C\n"
        "\n"
        "class Inner:\n"
        "\t@onready var F = func(): return 2\n"
        "\tfunc m() -> void:\n"
        "\t\tprint(1)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 6)]


def test_multiline_signature_lambda_body_is_not_tracked(tmp_path):
    """A lambda body inside a wrapped signature span is dropped.

    The signature-span rule must hold across the whole ``func_header``
    span, not only on single-line signatures where the span is
    degenerate.
    """
    source = (
        "extends Node\n"
        "\n"
        "func f(\n"
        "\tx = func():\n"
        "\t\tprint(9),\n"
        ") -> void:\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _statements(lines) == [(0, 7)]
