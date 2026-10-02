"""Unit tests for ternary (test_expr) anchor resolution in the plan generator.

A ternary branch point can only be instrumented when it is recorded at a line
where a statement may begin, because the tracker call is injected *before* the
planned line. Every tracked node except ``test_expr`` begins with a keyword and
is therefore always at a statement boundary. A ternary's first token is an
arbitrary operand, so without anchoring it lands on a continuation line (inside
an open bracket) or on a class-body line, producing GDScript that fails to
parse and causing the file to be dropped from coverage as an omission.

Covered here:

* anchoring to the nearest enclosing tracked statement (FR-1)
* dropping ternaries with no enclosing statement (FR-2)
* resolving true ancestry rather than the next statement visited (FR-3)
* leaving every other node type untouched (FR-4)
* exclusion evaluated against the final, anchored line (FR-5)
"""

import pytest

from gd_tools.coverage.plan_generator import generate_plan

pytestmark = pytest.mark.unit


# --- Helpers ---


def _lines_for(tmp_path, source, name="sample.gd"):
    """Write a single GDScript file and return its planned lines."""
    (tmp_path / name).write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    assert len(plan.files) == 1, "expected exactly one planned file"
    return plan.files[0].lines


def _ternaries(lines):
    """Return ``(id, line)`` for every ternary branch point."""
    return [
        (p.id, p.line)
        for p in lines
        if p.branch_type and p.branch_type.startswith("ternary")
    ]


def _statements(lines):
    return [(p.id, p.line) for p in lines if p.type == "statement"]


# --- FR-1: anchor to the enclosing statement ---


def test_ternary_in_multiline_parens_anchors_to_enclosing_statement(tmp_path):
    """A ternary inside multi-line parens is recorded at the statement line."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tvar x = (\n"
        "\t\t1\n"
        "\t\tif a > 0\n"
        "\t\telse 2\n"
        "\t)\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)

    # Line 4 is ``var x = (`` -- a statement boundary.
    assert _ternaries(lines) == [(0, 4), (1, 4)]


def test_ternary_in_multiline_call_args_anchors_to_call_statement(tmp_path):
    """A ternary inside multi-line call arguments anchors to the call."""
    source = (
        "extends Node\n"
        "\n"
        "func g(c: int) -> int:\n"
        "\treturn c\n"
        "\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tg(\n"
        "\t\t1 if a > 0\n"
        "\t\telse 2\n"
        "\t)\n"
    )
    lines = _lines_for(tmp_path, source)

    # Line 8 is ``g(``.
    assert _ternaries(lines) == [(0, 8), (1, 8)]


def test_ternary_never_recorded_on_a_continuation_line(tmp_path):
    """No ternary point may land on a line that is not a statement boundary."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tvar x = (\n"
        "\t\t1\n"
        "\t\tif a > 0\n"
        "\t\telse 2\n"
        "\t)\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)

    statement_lines = {line for _, line in _statements(lines)}
    for _, line in _ternaries(lines):
        assert line in statement_lines


# --- FR-2: drop ternaries with no enclosing statement ---


def test_ternary_in_const_initializer_is_not_tracked(tmp_path):
    """A class-level const ternary has no statement to anchor to."""
    source = (
        "extends Node\n"
        "\n"
        "const C = 1 if true else 2\n"
        "\n"
        "\n"
        "func f() -> void:\n"
        "\tprint(C)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _ternaries(lines) == []


def test_ternary_in_export_initializer_is_not_tracked(tmp_path):
    """An @export initializer ternary has no statement to anchor to."""
    source = (
        "extends Node\n"
        "\n"
        "@export var v: int = 1 if true else 2\n"
        "\n"
        "\n"
        "func f() -> void:\n"
        "\tprint(v)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _ternaries(lines) == []


def test_ternary_in_default_parameter_is_not_tracked(tmp_path):
    """A default parameter value ternary has no statement to anchor to."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int, x = 1 if a > 0 else 2) -> void:\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _ternaries(lines) == []


def test_ternary_in_multiline_const_is_not_tracked(tmp_path):
    """A multi-line class-level const ternary is dropped, not mis-anchored."""
    source = (
        "extends Node\n"
        "\n"
        "const C = (\n"
        "\t1\n"
        "\tif true\n"
        "\telse 2\n"
        ")\n"
        "\n"
        "\n"
        "func f() -> void:\n"
        "\tprint(C)\n"
    )
    lines = _lines_for(tmp_path, source)
    assert _ternaries(lines) == []


# --- FR-3: resolve true ancestry ---


def test_const_ternary_not_attributed_to_a_later_statement(tmp_path):
    """A const ternary must not be flushed onto the next statement visited.

    Bottom-up traversal visits the const initialiser's subtree before the
    function body that follows it. Buffering the ternary until "the next
    statement" therefore mis-attributes it to ``print(C)``.
    """
    source = (
        "extends Node\n"
        "\n"
        "const C = 1 if true else 2\n"
        "\n"
        "\n"
        "func f() -> void:\n"
        "\tprint(C)\n"
        "\tprint(1)\n"
        "\tprint(2)\n"
    )
    lines = _lines_for(tmp_path, source)

    assert _ternaries(lines) == []
    # Sanity: the three statements are still tracked where they were written.
    assert _statements(lines) == [(0, 7), (1, 8), (2, 9)]


def test_ternary_in_lambda_anchors_to_enclosing_statement_not_outer_call(
    tmp_path,
):
    """A ternary inside a lambda body anchors within that body."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tvar c = func(p: int):\n"
        "\t\treturn 1 if p > 0 else 2\n"
        "\tprint(c.call(1))\n"
    )
    lines = _lines_for(tmp_path, source)

    # Line 5 is the lambda's ``return`` -- the nearest enclosing statement.
    assert _ternaries(lines) == [(0, 5), (1, 5)]


# --- FR-4: existing behaviour preserved ---


def test_single_line_ternary_keeps_statement_line(tmp_path):
    """A ternary already on its statement's line is unaffected."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tvar x = 1 if a > 0 else 2\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)

    assert _statements(lines) == [(2, 4), (3, 5)]
    assert _ternaries(lines) == [(0, 4), (1, 4)]


def test_nested_ternaries_stay_on_statement_line(tmp_path):
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\treturn 1 if a > 0 else 2 if a < 0 else 3\n"
    )
    lines = _lines_for(tmp_path, source)

    # Ids follow bottom-up visit order, so the ternary keeps ids 0/1 and the
    # enclosing statement is id 2. Anchoring changes lines, not visit order.
    assert _statements(lines) == [(2, 4)]
    for _, line in _ternaries(lines):
        assert line == 4


def test_ternary_in_array_literal_stays_on_statement_line(tmp_path):
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tprint([1 if a > 0 else 2, 3])\n"
    )
    lines = _lines_for(tmp_path, source)

    assert _statements(lines) == [(2, 4)]
    assert _ternaries(lines) == [(0, 4), (1, 4)]


def test_multiline_if_condition_is_unaffected(tmp_path):
    """A multi-line if condition was never vulnerable: the branch starts at
    the ``if`` keyword, which is always a statement boundary."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int, b: int) -> bool:\n"
        "\tif (\n"
        "\t\ta > 0\n"
        "\t\tand b > 0\n"
        "\t):\n"
        "\t\treturn true\n"
        "\treturn false\n"
    )
    lines = _lines_for(tmp_path, source)

    assert _ternaries(lines) == []
    if_true = [p for p in lines if p.branch_type == "if_true"]
    assert len(if_true) == 1
    assert if_true[0].line == 4


def test_file_without_ternary_is_unaffected(tmp_path):
    source = "extends Node\n\nfunc f() -> void:\n\tvar x = 1\n\tprint(x)\n"
    lines = _lines_for(tmp_path, source)
    assert _ternaries(lines) == []
    assert _statements(lines) == [(0, 4), (1, 5)]


# --- FR-5: exclusion evaluated against the anchored line ---


def test_no_cover_block_excludes_anchored_ternary_branches(tmp_path):
    """Excluding the statement line excludes the ternary branches anchored to it."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\t# gd-tools: no cover start\n"
        "\tvar x = (\n"
        "\t\t1\n"
        "\t\tif a > 0\n"
        "\t\telse 2\n"
        "\t)\n"
        "\t# gd-tools: no cover end\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)

    assert _ternaries(lines) == []
    # Only the ``print(x)`` statement outside the excluded block survives.
    assert _statements(lines) == [(0, 11)]


def test_no_cover_on_unrelated_line_does_not_drop_ternary(tmp_path):
    """Exclusion is scoped to the annotated lines, not to the whole function."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\t# gd-tools: no cover start\n"
        "\tvar unused = 1\n"
        "\t# gd-tools: no cover end\n"
        "\tvar x = 1 if a > 0 else 2\n"
        "\tprint(x)\n"
    )
    lines = _lines_for(tmp_path, source)

    # ``var x`` is line 7; the excluded block covers only lines 4-6.
    assert _ternaries(lines) == [(0, 7), (1, 7)]


# --- NFR-2: determinism ---


def test_planning_is_deterministic(tmp_path):
    """Repeated planning of the same source yields an identical plan.

    Anchor resolution keys on ``id(tree)``; the map must be built and consumed
    within a single ``visit()`` call so object identity cannot leak out.
    """
    source = (
        "extends Node\n"
        "\n"
        "const C = 1 if true else 2\n"
        "\n"
        "\n"
        "func f(a: int) -> void:\n"
        "\tvar x = (\n"
        "\t\t1\n"
        "\t\tif a > 0\n"
        "\t\telse 2\n"
        "\t)\n"
        "\tprint(x)\n"
    )
    (tmp_path / "sample.gd").write_text(source, encoding="utf-8")

    first = generate_plan(str(tmp_path)).files[0].lines
    second = generate_plan(str(tmp_path)).files[0].lines

    assert first == second


@pytest.mark.parametrize(
    ("name", "source"),
    [
        (
            "multiline_parens",
            "extends Node\n\nfunc f(a: int) -> void:\n\tvar x = (\n"
            "\t\t1\n\t\tif a > 0\n\t\telse 2\n\t)\n\tprint(x)\n",
        ),
        (
            "const_orphan",
            "extends Node\n\nconst C = 1 if true else 2\n\n\n"
            "func f() -> void:\n\tprint(C)\n",
        ),
        (
            "default_param",
            "extends Node\n\nfunc f(a: int, x = 1 if a > 0 else 2) -> void:\n"
            "\tprint(x)\n",
        ),
    ],
)
def test_no_id_collisions_across_ternary_anchor_states(tmp_path, name, source):
    """Ids stay unique per file regardless of whether ternaries are anchored."""
    lines = _lines_for(tmp_path, source, name=f"{name}.gd")
    ids = [p.id for p in lines]
    assert len(ids) == len(set(ids))
