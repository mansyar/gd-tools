"""Unit tests for inference-site annotations and zero-point plan exclusion.

Godot 4.x treats ``INFERENCE_ON_VARIANT`` as an error by default. When the
collector wraps a ternary/boolop operand with a value-preserving tracker call
(the wrapper returns ``Variant``), the whole wrapped expression becomes
statically ``Variant`` — and if that expression initializes a ``var x := …``
statement, the project's own declaration now infers from Variant and the
instrumented script fails to ``reload()``.

Covered here:

* ``:=`` statements whose initializer contains a wrapped operand span are
  recorded in a per-file ``warning_ignores`` field (FR-R2)
* plain initializers, untyped assignments, and excluded statements are not
  annotated (FR-R2)
* annotations round-trip through plan JSON (FR-R2)
* files with zero trackable points are excluded from the plan with a visible
  warning, instead of becoming silent omissions (FR-R1)
* ``PLAN_VERSION`` is bumped 7 -> 8 so stale cached plans regenerate (FR-R1)
"""

import re

import pytest

from gd_tools.coverage.plan_generator import (
    PLAN_VERSION,
    generate_plan,
    read_plan_json,
    write_plan_json,
)

pytestmark = pytest.mark.unit


# --- Helpers ---


def _plan_file(tmp_path, source, name="sample.gd"):
    """Write a single GDScript file and return its :class:`FilePlan`."""
    (tmp_path / name).write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    assert len(plan.files) <= 1, "expected at most one planned file"
    return plan.files[0] if plan.files else None


def _ignore_lines(file_plan):
    """Return the annotated statement lines from a file plan."""
    assert file_plan is not None, "expected the file to be planned"
    return [
        entry["line"]
        for entry in file_plan.warning_ignores
        if entry["warning"] == "inference_on_variant"
    ]


# --- FR-R2: inference-site detection ---


def test_ternary_inferred_declaration_is_annotated(tmp_path):
    """``var x := <ternary>`` records an inference_on_variant annotation."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := 10 if a > 0 else 20\n"
        "\treturn x\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == [4]


def test_boolop_inferred_declaration_is_annotated(tmp_path):
    """``var ok := a and b`` records an inference_on_variant annotation."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool) -> bool:\n"
        "\tvar ok := a and b\n"
        "\treturn ok\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == [4]


def test_multiple_wrapped_spans_yield_one_annotation(tmp_path):
    """Several wrapped operands inside one ``:=`` produce a single entry."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: bool, b: bool, c: bool) -> bool:\n"
        "\tvar ok := (a and b) if c else not a\n"
        "\treturn ok\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == [4]


def test_plain_inferred_declaration_is_not_annotated(tmp_path):
    """An initializer with no wrapped operand needs no annotation."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := a + 1\n"
        "\treturn x\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == []


def test_untyped_assignment_is_not_annotated(tmp_path):
    """Untyped ``var x = <ternary>`` does not trip INFERENCE_ON_VARIANT.

    Verified empirically against Godot 4.7.2 ``--check-only``: the warning
    fires for ``:=`` inference only, so untyped assignments need no
    annotation even though their initializer is wrapped.
    """
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x = 10 if a > 0 else 20\n"
        "\treturn x\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == []


def test_multiline_initializer_annotates_statement_start(tmp_path):
    """The annotation lands on the line where the ``var`` keyword sits."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := (\n"
        "\t\t10 if a > 0 else 20\n"
        "\t)\n"
        "\treturn x\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == [4]


def test_excluded_inferred_declaration_is_not_annotated(tmp_path):
    """An excluded statement is not wrapped, so it needs no annotation."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := 10 if a > 0 else 20  # gd-tools: no cover\n"
        "\treturn x\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == []


def test_distinct_declarations_annotate_their_own_lines(tmp_path):
    """Two ``:=`` statements annotate only the one that wraps an operand."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar plain := a + 1\n"
        "\tvar wrapped := 10 if a > 0 else 20\n"
        "\treturn plain + wrapped\n"
    )
    assert _ignore_lines(_plan_file(tmp_path, source)) == [5]


# --- FR-R2: plan JSON round-trip ---


def test_warning_ignores_round_trip(tmp_path):
    """Annotations survive a write/read cycle through plan JSON."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := 10 if a > 0 else 20\n"
        "\treturn x\n"
    )
    (tmp_path / "sample.gd").write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    plan_path = tmp_path / "plan.json"
    write_plan_json(plan, str(plan_path))
    loaded = read_plan_json(str(plan_path))

    assert loaded.files[0].warning_ignores == [
        {"line": 4, "warning": "inference_on_variant"}
    ]


def test_warning_ignores_key_absent_when_empty(tmp_path):
    """Files without annotations keep the plan JSON shape unchanged."""
    source = (
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := a + 1\n"
        "\treturn x\n"
    )
    (tmp_path / "sample.gd").write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))
    plan_path = tmp_path / "plan.json"
    write_plan_json(plan, str(plan_path))

    import json

    data = json.loads(plan_path.read_text(encoding="utf-8"))
    assert "warning_ignores" not in data["files"][0]


# --- FR-R1: zero-point exclusion ---


def test_zero_point_file_is_excluded(tmp_path):
    """A pure-const data module yields no plan entry at all."""
    source = (
        "class_name TrackWaypoints\n"
        "extends RefCounted\n"
        "\n"
        "const POINTS := [\n"
        "\tVector2(0, 0),\n"
        "\tVector2(1, 1),\n"
        "]\n"
    )
    (tmp_path / "track_waypoints.gd").write_text(source, encoding="utf-8")
    plan = generate_plan(str(tmp_path))

    assert plan.files == [], "zero-point file must not be planned"


def test_zero_point_exclusion_warns(tmp_path, capsys):
    """The skip is announced so users know why the file is not a target."""
    source = (
        "class_name TrackWaypoints\n"
        "extends RefCounted\n"
        "\n"
        "const POINTS := [\n"
        "\tVector2(0, 0),\n"
        "]\n"
    )
    (tmp_path / "track_waypoints.gd").write_text(source, encoding="utf-8")
    generate_plan(str(tmp_path))

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    # Rich soft-wraps under narrow CI consoles: it can split the path
    # mid-word with a newline (stripped below) and it *consumes* the
    # space at a wrap point, so multi-word phrases cannot be matched
    # verbatim. Allow zero-or-more whitespace between words.
    unwrapped = combined.replace("\n", "")
    assert "track_waypoints.gd" in unwrapped
    assert re.search(r"no\s*trackable\s*coverage\s*points", unwrapped)


# --- FR-R1: version bump ---


def test_plan_version_bumped_to_eight():
    """Stale cached plans (version 7) must regenerate, so bump to 8."""
    assert PLAN_VERSION == 8


# --- FR-R1: cache interaction ---


def test_cached_plan_hit_with_zero_point_file(tmp_path):
    """Adding a data-only file must not invalidate a cached plan.

    ``generate_plan_cached`` compares per-file source hashes; a
    zero-point file is absent from the cached plan, so without the
    visitor check in the cache path it would count as "added" and force
    a regeneration on every run.
    """
    from gd_tools.coverage.plan_generator import generate_plan_cached

    (tmp_path / "code.gd").write_text(
        "extends Node\n"
        "\n"
        "func f(a: int) -> int:\n"
        "\tvar x := a + 1\n"
        "\treturn x\n",
        encoding="utf-8",
    )
    cache_path = tmp_path / "plan.json"
    plan, status = generate_plan_cached(
        str(tmp_path), cache_path=str(cache_path)
    )
    assert not status.hit
    write_plan_json(plan, str(cache_path))

    (tmp_path / "data.gd").write_text(
        "class_name TrackWaypoints\n"
        "extends RefCounted\n"
        "\n"
        "const POINTS := [\n"
        "\tVector2(0, 0),\n"
        "]\n",
        encoding="utf-8",
    )
    fresh, cached = generate_plan_cached(
        str(tmp_path), cache_path=str(cache_path)
    )
    assert cached.hit, cached.reason
    assert all(fp.path != "res://data.gd" for fp in fresh.files)
