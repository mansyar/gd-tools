"""Compile every instrumented fixture against a real Godot.

The unit tests for the plan generator assert *which line* a point is
recorded on. They cannot assert that the GDScript which results from
injecting a tracker before each recorded line actually compiles, because
nothing in a plan is aware of GDScript's grammar. This module closes
that gap: each fixture is planned, instrumented with a port of the
collector's insertion logic, and handed to a real Godot.

The suite covers two generations of the same defect: ternary branch
points recorded on continuation lines (anchored since PLAN_VERSION 3)
and statement points squashed onto class-member declaration or signature
lines by an inline lambda body (dropped since PLAN_VERSION 4).

Two harness constraints were learned the hard way and are load-bearing:

* ``GdToolsNativeCoverage`` must be declared with ``class_name``, not as an
  autoload. Godot rejects a script that both declares a ``class_name`` and is
  registered as an autoload of the same name (``Class ... hides an autoload
  singleton``), and ``--check-only --script`` does not initialise autoloads.
* ``--import`` must run once per project before any check, or the global
  script class cache is empty and every fixture fails with ``Identifier not
  found``. A stale ``.godot`` directory silently reports broken fixtures as
  valid, which is what the canary below exists to catch.

The port in :func:`_inject` is guarded by
:func:`test_injection_port_tracks_the_collector`, so it cannot silently
diverge from the real collector.
"""

import re
import subprocess
from pathlib import Path

import pytest

from gd_tools.coverage.plan_generator import generate_plan

pytestmark = pytest.mark.integration

STUB = (
    "extends RefCounted\n"
    "class_name GdToolsNativeCoverage\n"
    "\n"
    "\n"
    "static func hit(_file_id: int, _point_id: int) -> void:\n"
    "\tpass\n"
    "\n"
    "\n"
    "static func hit_ret(\n"
    "\t\t_file_id: int, _point_id: int, value: Variant\n"
    ") -> Variant:\n"
    "\treturn value\n"
)

PROJECT_FILE = (
    "[application]\n"
    'config/name="instrumentation-parse-check"\n'
    "\n"
    "[rendering]\n"
    'renderer/rendering_method="gl_compatibility"\n'
)

_PARSE_ERROR = re.compile(r"(Parse Error|Compile Error|SCRIPT ERROR)")

#: Branch types whose tracker is injected *after* the recorded line, into the
#: branch body, because the recorded line is a keyword or case label rather
#: than the body itself. Mirrors the collector; guarded against drift by
#: :func:`test_injection_port_tracks_the_collector`.
_AFTER_LINE_BRANCH_TYPES = frozenset({"match_case", "if_false", "elif_true"})

_COLLECTOR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-test"
    / "gd_tools_native_coverage.gd"
)

#: ``name: (source, expected ternary lines, expected statement lines)``.
#: The expected lines are asserted because "it compiles" is satisfied by a
#: plan recording zero points -- which is exactly how ternaries in
#: control-flow headers were once dropped in silence. The third element
#: (``None`` when uninteresting) pins the *statement* lines the same way for
#: class-body cases, where the defect was a statement recorded on a
#: class-member declaration line.
CASES = {
    # --- previously produced uncompilable output ---
    "ml_stmt": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = (\n\t\t1\n\t\tif a > 0\n\t\telse 2\n\t)\n\tprint(x)\n",
        [5, 5],
        None,
    ),
    "ml_call": (
        "extends Node\n\n\nfunc g(c: int) -> int:\n\treturn c\n\n\n"
        "func f(a: int) -> void:\n"
        "\tg(\n\t\t1 if a > 0\n\t\telse 2\n\t)\n",
        [9, 9],
        None,
    ),
    "const_orphan": (
        "extends Node\n\nconst C = 1 if true else 2\n\n\n"
        "func f() -> void:\n\tprint(C)\n",
        [],
        None,
    ),
    "const_ml_orphan": (
        "extends Node\n\nconst C = (\n\t1\n\tif true\n\telse 2\n)\n\n\n"
        "func f() -> void:\n\tprint(C)\n",
        [],
        None,
    ),
    "export_orphan": (
        "extends Node\n\n@export var v: int = 1 if true else 2\n\n\n"
        "func f() -> void:\n\tprint(v)\n",
        [],
        None,
    ),
    # Await inside a ternary operand: the operand span covers the await
    # expression, so wrapping produces ``hit_ret(id, await f())``. Verifies the
    # instrumented form still compiles (semantics: the wrapper is synchronous
    # and returns its argument, so await resolution order is unchanged).
    "ternary_await": (
        "extends Node\n\n\nfunc f(cond: bool) -> int:\n"
        "\tvar value = await truthy() if cond else 0\n\treturn value\n\n\n"
        "func truthy() -> int:\n\treturn 1\n",
        [5, 5],
        [5, 6, 10],
    ),
    # Evidence for the @export open question: a hand-instrumented @export
    # initializer (tracker call in the ternary operand) still compiles, so
    # excluding @export ternaries is a conservative choice, not a hard
    # technical blocker. They stay untracked (no anchor), like const and
    # default-parameter ternaries. The trailing function keeps the file a
    # plan target now that zero-point files are excluded from plans.
    "ternary_export_wrapped": (
        "extends Node\n\n@export var enabled := true\n\n\n"
        "@export var size: int = GdToolsNativeCoverage.hit_ret(0, 5, 2) "
        "if enabled else 4\n\n\n"
        "func f() -> void:\n\tprint(enabled)\n",
        [],
        [10],
    ),
    # A `:=` initializer holding a wrapped operand infers from Variant
    # (INFERENCE_ON_VARIANT is error-by-default in Godot 4.x), so the
    # annotation must ride the same line or the instrumented file cannot
    # reload at all.
    "inferred_wrapped": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x := 10 if a > 0 else 20\n\tprint(x)\n",
        [5, 5],
        [5, 6],
    ),
    "param_orphan": (
        "extends Node\n\n\nfunc f(a: int, x = 1 if a > 0 else 2) -> void:\n"
        "\tprint(x)\n",
        [],
        None,
    ),
    # --- header ternaries, dropped until the anchor set was widened ---
    "if_header": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tif (1 if a > 0 else 2) > 0:\n\t\tprint(a)\n",
        [5, 5],
        None,
    ),
    "if_header_ml": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tif (\n\t\t1 if a > 0 else 2\n\t) > 0:\n\t\tprint(a)\n",
        [5, 5],
        None,
    ),
    "for_header": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tfor i in range(1 if a > 0 else 2):\n\t\tprint(i)\n",
        [5, 5],
        None,
    ),
    "for_header_ml": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tfor i in range(\n\t\t1 if a > 0 else 2\n\t):\n\t\tprint(i)\n",
        [5, 5],
        None,
    ),
    "while_header": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\twhile (a if a > 0 else 0) > 1:\n\t\tprint(a)\n",
        [5, 5],
        None,
    ),
    "match_header": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tmatch (1 if a > 0 else 2):\n\t\t1:\n\t\t\tprint(a)\n",
        [5, 5],
        None,
    ),
    # --- already fine; must stay fine ---
    "control_stmt": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = 1 if a > 0 else 2\n\tprint(x)\n",
        [5, 5],
        None,
    ),
    "nested_ternary": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = 1 if a > 0 else 2 if a < 0 else 3\n\tprint(x)\n",
        [5, 5],
        None,
    ),
    "lambda_ternary": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar c = func(p: int): return 1 if p > 0 else 2\n"
        "\tprint(c.call(1))\n",
        [5, 5],
        None,
    ),
    "ml_if": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tif (\n\t\ta > 0\n\t\tand a < 10\n\t):\n\t\tprint(a)\n",
        [],
        None,
    ),
    "ternary_in_arr": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tprint([1 if a > 0 else 2, 3])\n",
        [5, 5],
        None,
    ),
    "no_ternary": (
        "extends Node\n\n\nfunc f() -> void:\n\tvar x = 1\n\tprint(x)\n",
        [],
        None,
    ),
    # --- class-body statements, dropped since PLAN_VERSION 4 --- (plus @onready annotations)
    "class_lambda_var": (
        "extends Node\n\n\n"
        "class Inner:\n"
        "\tvar F = func(): return 2\n"
        "\tfunc m() -> void:\n"
        '\t\tprint("m")\n',
        [],
        [7],
    ),
    "class_lambda_print": (
        "extends Node\n\n\n"
        "class Inner:\n"
        "\tvar F = func(): print(1)\n"
        "\tfunc m() -> void:\n"
        '\t\tprint("m")\n',
        [],
        [7],
    ),
    "class_static_lambda": (
        "extends Node\n\n\n"
        "class Inner:\n"
        "\tstatic var S = func(): return 2\n"
        "\tfunc m() -> void:\n"
        '\t\tprint("m")\n',
        [],
        [7],
    ),
    "class_export_lambda": (
        "extends Node\n\n\n"
        "class Inner:\n"
        "\t@export var E = func(): return 2\n"
        "\tfunc m() -> void:\n"
        '\t\tprint("m")\n',
        [],
        [7],
    ),
    "class_lambda_multiline": (
        "extends Node\n\n\n"
        "class Inner:\n"
        "\tvar F = func():\n"
        "\t\treturn 2\n"
        "\tfunc m() -> void:\n"
        '\t\tprint("m")\n',
        [],
        [6, 8],
    ),
    "func_lambda": (
        "extends Node\n\n\n"
        "func f() -> void:\n"
        "\tvar c = func(): return 2\n"
        "\tprint(c.call())\n",
        [],
        [5, 5, 6],
    ),
    "signature_lambda": (
        "extends Node\n\n\n"
        "func f(a: int, x = func(): return 2) -> void:\n"
        "\tprint(a)\n",
        [],
        [5],
    ),
    "top_lambda_var": (
        "extends Node\n\n"
        "var F = func(): return 2\n\n\n"
        "func f() -> void:\n"
        "\tprint(F.call())\n",
        [],
        [7],
    ),
    # --- bracket-continuation statements, dropped since PLAN_VERSION 5 ---
    "cont_inline_dict": (
        'extends Node\n\nvar handlers = {\n\t"k": func(): print(1),\n}\n\n'
        "func m() -> void:\n\tprint(handlers)\n",
        [],
        [8],
    ),
    "cont_paren_lambda": (
        "extends Node\n\nvar f = (\n\tfunc(): print(1)\n)\n\n"
        "func m() -> void:\n\tprint(f)\n",
        [],
        [8],
    ),
    "cont_func_ml_expr": (
        "extends Node\n\nfunc m() -> void:\n"
        "\tvar F = [1].map(\n\t\tfunc(): return 2\n\t)\n\tprint(F)\n",
        [],
        [4, 7],
    ),
    "cont_backslash": (
        "extends Node\n\nfunc m() -> void:\n"
        "\tvar x = [1].map( \\\n\t\tfunc(): return 2\n\t)\n\tprint(x)\n",
        [],
        [4, 7],
    ),
    "cont_block_in_dict": (
        'extends Node\n\nvar h = {\n\t"k": func():\n\t\tprint(1),\n}\n\n'
        "func m() -> void:\n\tprint(h)\n",
        [],
        [9],
    ),
    "cont_block_lambda_kept": (
        "extends Node\n\nvar F = func():\n\treturn 2\n\n"
        "func m() -> void:\n\tprint(F)\n",
        [],
        [4, 7],
    ),
    "class_onready_lambda": (
        "extends Node\n\n\n"
        "class Inner extends Node:\n"
        "\t@onready var F = func(): return 2\n"
        "\tfunc m() -> void:\n"
        '\t\tprint("m")\n',
        [],
        [7],
    ),
}

#: Deliberately unparseable, used to prove the harness can still fail.
BROKEN_CONTROL = (
    "extends Node\n\n\nfunc f() -> void:\n" "\tvar x = (\n\t\t1\n\tprint(x)\n"
)


def _indent_of(line: str) -> str:
    """Return the leading whitespace of ``line``."""
    out = ""
    for ch in line:
        if ch not in (" ", "\t"):
            break
        out += ch
    return out


def _inject(source: str, lines, warning_ignores=()) -> str:
    """Port of ``_inject_trackers`` from the native coverage collector.

    Mirrors the collector's ordering: operand wrapping first, then
    same-line ``@warning_ignore`` prefixes (annotations never shift line
    counts), then entries sorted by line descending so that each insertion
    leaves earlier indices valid. Ternary arms are instrumented by
    wrapping their operand text with ``hit_ret`` instead of inserting a
    line-based ``hit()`` on the shared anchor line.
    """
    wrapped = _wrap_operands(source, lines)
    src_lines = wrapped.split("\n")
    for annotation in warning_ignores:
        target = annotation["line"] - 1
        if 0 <= target < len(src_lines) and annotation.get("warning"):
            indent = _indent_of(src_lines[target])
            src_lines[target] = (
                f'{indent}@warning_ignore("{annotation["warning"]}") '
                f"{src_lines[target][len(indent):]}"
            )
    for entry in sorted(lines, key=lambda e: e.line, reverse=True):
        if getattr(entry, "operand_span", None) is not None:
            continue
        target = entry.line - 1
        if target < 0 or target >= len(src_lines):
            continue
        if entry.branch_type in _AFTER_LINE_BRANCH_TYPES:
            target += 1
        indent = _indent_of(src_lines[target])
        if not indent:
            indent = _indent_of(src_lines[entry.line - 1])
        src_lines.insert(
            target, f"{indent}GdToolsNativeCoverage.hit(0, {entry.id})"
        )
    return "\n".join(src_lines)


def _offset_of(source: str, line: int, col: int) -> int:
    """Absolute character offset of a 1-based line/column position, or -1."""
    src_lines = source.split("\n")
    if line < 1 or line > len(src_lines) or col < 1:
        return -1
    offset = sum(len(src_lines[i]) + 1 for i in range(line - 1))
    target = offset + (col - 1)
    return target if target <= len(source) else -1


def _wrap_operands(source: str, lines) -> str:
    """Port of the collector's ternary operand wrapping.

    Replaces each operand span with a ``hit_ret`` wrapper. Wrappers never
    add or remove newline characters, so line numbers stay valid for the
    line-based insertion that follows.
    """
    spans = []
    for entry in lines:
        span = getattr(entry, "operand_span", None)
        if span is None:
            continue
        start = _offset_of(source, span[0], span[1])
        end = _offset_of(source, span[2], span[3])
        if start < 0 or end < 0 or start >= end or end > len(source):
            continue
        spans.append({"start": start, "end": end, "id": entry.id})
    if not spans:
        return source
    spans.sort(key=lambda s: (s["start"], -s["end"]))
    return _wrap_spans(source, spans, 0, 0, len(source))


def _wrap_spans(
    source: str, spans, index: int, start_from: int, to: int
) -> str:
    """Emit source[start_from:to] with spans[index..] wrapped in place."""
    result = ""
    cursor = start_from
    i = index
    while i < len(spans):
        span = spans[i]
        start, end = span["start"], span["end"]
        if start >= to or end > to:
            break
        if start < cursor:
            i += 1
            continue
        children = []
        j = i + 1
        while j < len(spans) and spans[j]["end"] <= end:
            children.append(spans[j])
            j += 1
        result += source[cursor:start]
        operand = _wrap_spans(source, children, 0, start, end)
        result += f"GdToolsNativeCoverage.hit_ret(0, {span['id']}, {operand})"
        cursor = end
        i = j
    return result + source[cursor:to]


def _run(godot_bin: str, project: Path, *args: str) -> str:
    """Invoke Godot and return its combined output."""
    result = subprocess.run(
        [godot_bin, "--headless", "--path", str(project), *args],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return result.stdout + result.stderr


def _build_project(godot_bin: str, root: Path, source: str, name: str) -> Path:
    """Create a fresh project holding ``source``, then import it.

    ``--import`` must run after every ``.gd`` file exists so the global
    script class cache is populated before any ``--check-only``.
    """
    project = root
    project.mkdir(parents=True, exist_ok=True)
    (project / "project.godot").write_text(PROJECT_FILE, encoding="utf-8")
    (project / "gdtools_stub.gd").write_text(STUB, encoding="utf-8")
    (project / name).write_text(source, encoding="utf-8")
    _run(godot_bin, project, "--import")
    return project


def _check(godot_bin: str, project: Path, name: str) -> tuple[bool, str]:
    """Return whether ``name`` parses, plus the raw Godot output."""
    output = _run(
        godot_bin, project, "--check-only", "--script", f"res://{name}"
    )
    is_broken = bool(_PARSE_ERROR.search(output))
    return not is_broken, output


def test_injection_port_tracks_the_collector():
    """The port must keep matching the collector it reimplements.

    If the collector's insertion rules change and this port does not, the
    suite keeps passing while no longer testing the real thing -- the exact
    failure mode its own canary exists to prevent.
    """
    source = _COLLECTOR.read_text(encoding="utf-8")

    shift_list = re.search(r"branch_type in \[(.*?)\]", source, re.DOTALL)
    assert shift_list, (
        "Collector no longer has a `branch_type in [...]` shift list; "
        "_inject must be updated to match."
    )
    collector_types = set(re.findall(r'"([a-z_]+)"', shift_list.group(1)))
    assert collector_types == set(_AFTER_LINE_BRANCH_TYPES), (
        "Collector's after-the-line branch types changed. "
        f"Collector: {sorted(collector_types)}; "
        f"port: {sorted(_AFTER_LINE_BRANCH_TYPES)}."
    )

    descending_sort = re.search(
        r'sort_custom\(func\(a, b\):\s*return\s+int\(a\["line"\]\)\s*>\s*'
        r'int\(b\["line"\]\)\)',
        source,
    )
    assert descending_sort, (
        "Collector no longer sorts insertions by line descending; "
        "_inject's ordering assumption is now wrong."
    )

    hit_ret = re.search(r"static func hit_ret\(", source)
    assert hit_ret, (
        "Collector no longer defines hit_ret; _inject's ternary operand "
        "wrapping has no runtime counterpart to record the hit."
    )

    operand_wrap = re.search(r"operand_span", source)
    assert operand_wrap, (
        "Collector no longer consults operand_span; ternary arms would be "
        "instrumented by line insertion again, which fires both arms in "
        "lockstep and cannot ever report an uncovered arm."
    )

    warning_annotation = re.search(r"@warning_ignore\(", source)
    assert warning_annotation, (
        "Collector no longer injects @warning_ignore for plan "
        "warning_ignores entries; wrapped operands inside inferred `:=` "
        "declarations would fail to reload (INFERENCE_ON_VARIANT is "
        "error-by-default) and the file would vanish from coverage."
    )


SIMPLE_TERNARY = (
    "extends Node\n\n\nfunc f(a: int) -> void:\n"
    "\tvar x = 10 if a > 0 else 20\n\tprint(x)\n"
)


def _plan_lines(tmp_path, source):
    """Generate the plan entries for a single-file project."""
    project = tmp_path
    (project / "fixture.gd").write_text(source, encoding="utf-8")
    plan = generate_plan(str(project))
    entry = next(f for f in plan.files if f.path.endswith("fixture.gd"))
    return entry.lines


def _ternary_ids(lines):
    return [
        p.id
        for p in lines
        if p.branch_type and p.branch_type.startswith("ternary")
    ]


def test_ternary_arms_are_wrapped_not_line_inserted(tmp_path):
    """Each ternary arm becomes a hit_ret wrapper around its operand text."""
    lines = _plan_lines(tmp_path, SIMPLE_TERNARY)
    true_id, false_id = _ternary_ids(lines)

    out = _inject(SIMPLE_TERNARY, lines)

    assert f"GdToolsNativeCoverage.hit_ret(0, {true_id}, 10)" in out, out
    assert f"GdToolsNativeCoverage.hit_ret(0, {false_id}, 20)" in out, out
    # The lockstep bug: dual hit() insertion on the shared anchor line.
    assert f"GdToolsNativeCoverage.hit(0, {true_id})" not in out
    assert f"GdToolsNativeCoverage.hit(0, {false_id})" not in out
    # Line insertion for other points must not disturb the wrapped line.
    assert "\tvar x = " in out


def test_multiline_operand_wrapper_preserves_line_count(tmp_path):
    """A wrapper never adds or removes newline characters."""
    source = (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = (\n\t\tfoo(\n\t\t\t1,\n\t\t\t2\n\t\t)\n"
        "\t\tif a > 0\n\t\telse 3\n\t)\n\tprint(x)\n"
    )
    lines = _plan_lines(tmp_path, source)

    # Wrapping alone must not change the line count.
    wrapped = _wrap_operands(source, lines)
    assert wrapped.count("\n") == source.count("\n"), wrapped

    out = _inject(source, lines)
    true_id, false_id = _ternary_ids(lines)
    true_arm = f"GdToolsNativeCoverage.hit_ret(0, {true_id}, foo(\n\t\t\t1,\n\t\t\t2\n\t\t))"
    assert true_arm in out, out
    assert f"GdToolsNativeCoverage.hit_ret(0, {false_id}, 3)" in out, out


def test_nested_ternary_outer_arms_wrap_inner_text_verbatim(tmp_path):
    """Nested ternaries track the outer arms; inner text passes through."""
    source = (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = 1 if a > 0 else 2 if a < 0 else 3\n"
    )
    lines = _plan_lines(tmp_path, source)
    true_id, false_id = _ternary_ids(lines)
    assert len(_ternary_ids(lines)) == 2

    out = _inject(source, lines)

    expected = (
        "\tvar x = "
        f"GdToolsNativeCoverage.hit_ret(0, {true_id}, 1) if a > 0 else "
        f"GdToolsNativeCoverage.hit_ret(0, {false_id}, 2 if a < 0 else 3)"
    )
    assert expected in out, out


def test_non_ternary_points_still_inject_line_trackers(tmp_path):
    """Statement and if-branch instrumentation is unchanged."""
    source = (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = 1\n\tif a > 0:\n\t\tprint(x)\n"
    )
    lines = _plan_lines(tmp_path, source)
    stmt_ids = [p.id for p in lines if p.type == "statement"]

    out = _inject(source, lines)

    for pid in stmt_ids:
        assert f"GdToolsNativeCoverage.hit(0, {pid})" in out, out


def test_ternary_entry_without_span_falls_back_to_line_tracker(tmp_path):
    """A ternary point missing its span (stale/hand-built plan) still
    instruments by line insertion rather than being dropped silently."""
    from gd_tools.coverage.plan_generator import LinePlan

    lines = [
        LinePlan(line=5, id=99, type="branch", branch_type="ternary_true"),
    ]

    out = _inject(SIMPLE_TERNARY, lines)

    assert "GdToolsNativeCoverage.hit(0, 99)" in out, out


def test_harness_detects_a_deliberately_broken_script(tmp_path, godot_bin):
    """The harness must flag broken input, or every other test is vacuous.

    A stale ``.godot`` cache or a missing stub once made broken scripts
    report as valid. This canary pins that failure mode shut.
    """
    project = _build_project(godot_bin, tmp_path, BROKEN_CONTROL, "control.gd")

    valid, output = _check(godot_bin, project, "control.gd")

    assert not valid, (
        "Harness reported a deliberately broken script as valid, so every "
        f"other assertion here is unreliable. Output:\n{output}"
    )


@pytest.mark.parametrize("case", sorted(CASES))
def test_instrumented_source_parses(case, tmp_path, godot_bin):
    """Each instrumented fixture compiles and records the expected points."""
    source, expected_ternaries, expected_statements = CASES[case]
    project = _build_project(godot_bin, tmp_path, source, "fixture.gd")

    plan = generate_plan(str(project))
    entry = next(f for f in plan.files if f.path.endswith("fixture.gd"))

    planned = [
        p.line
        for p in entry.lines
        if p.branch_type and p.branch_type.startswith("ternary")
    ]
    assert planned == expected_ternaries, (
        f"Case '{case}' recorded ternary lines {planned}, expected "
        f"{expected_ternaries}. A plan recording zero points compiles "
        f"trivially, so this is asserted separately from the parse."
    )

    if expected_statements is not None:
        stmt_lines = sorted(
            p.line for p in entry.lines if p.type == "statement"
        )
        assert stmt_lines == expected_statements, (
            f"Case '{case}' recorded statement lines {stmt_lines}, expected "
            f"{expected_statements}. A point on a class-body or signature "
            f"line makes the instrumented file unparseable."
        )

    instrumented = _inject(source, entry.lines, entry.warning_ignores)
    for annotation in entry.warning_ignores:
        assert f'@warning_ignore("{annotation["warning"]}")' in instrumented, (
            f"Case '{case}' lost its {annotation['warning']} annotation; "
            "the instrumented source would fail to reload with "
            f"INFERENCE_ON_VARIANT.\n{instrumented}"
        )
    (project / "fixture.gd").write_text(instrumented, encoding="utf-8")

    valid, output = _check(godot_bin, project, "fixture.gd")

    assert (
        valid
    ), f"Instrumented '{case}' does not parse:\n{instrumented}\n---\n{output}"
