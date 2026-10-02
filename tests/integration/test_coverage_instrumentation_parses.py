"""Instrumented GDScript must still parse.

The coverage plan generator records a line per trackable point, and
``gd_tools_native_coverage.gd`` inserts a tracker call *before* each of
those lines. If a planned line is not a line where a statement may
begin, the inserted call lands inside open brackets or in a class body
and the instrumented script stops parsing.

An unparseable script fails ``script.reload()`` in
``_instrument_file``, which records the file as an omission. That is the
silent-failure mode this suite exists to prevent: the file simply drops
out of coverage, and ``--min`` then escalates to exit 2.

These tests compile the *instrumented output* against a real Godot
rather than asserting on the plan alone, which cannot detect a bad
insertion point.

Harness notes, learned the hard way:

* The ``GdToolsNativeCoverage`` stub is declared with ``class_name``, not
  as an autoload. Godot rejects a script that both declares a
  ``class_name`` and is registered as an autoload of the same name
  ("Class ... hides an autoload singleton"), and ``--check-only
  --script`` does not initialise autoloads anyway.
* ``--check-only`` resolves ``class_name`` through the global script
  class cache, so ``--import`` must run once per project directory
  before any check.
* A stale ``.godot`` directory makes checks report a false pass. Every
  project here is created fresh per test, and
  :func:`test_harness_detects_a_deliberately_broken_script` asserts the
  harness still flags broken input, so the harness cannot quietly rot
  into always passing.
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
)

PROJECT_FILE = (
    "[application]\n"
    'config/name="instrumentation-parse-check"\n'
    "\n"
    "[rendering]\n"
    'renderer/rendering_method="gl_compatibility"\n'
)

_PARSE_ERROR = re.compile(r"(Parse Error|Compile Error|SCRIPT ERROR)")

#: Cases that previously produced uncompilable instrumented output, plus
#: cases that were already fine and must stay fine.
CASES = {
    # --- previously broken ---
    "ml_stmt": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = (\n\t\t1\n\t\tif a > 0\n\t\telse 2\n\t)\n\tprint(x)\n"
    ),
    "ml_call": (
        "extends Node\n\n\nfunc g(c: int) -> int:\n\treturn c\n\n\n"
        "func f(a: int) -> void:\n"
        "\tg(\n\t\t1 if a > 0\n\t\telse 2\n\t)\n"
    ),
    "const_orphan": (
        "extends Node\n\nconst C = 1 if true else 2\n\n\n"
        "func f() -> void:\n\tprint(C)\n"
    ),
    "const_ml_orphan": (
        "extends Node\n\nconst C = (\n\t1\n\tif true\n\telse 2\n)\n\n\n"
        "func f() -> void:\n\tprint(C)\n"
    ),
    "export_orphan": (
        "extends Node\n\n@export var v: int = 1 if true else 2\n\n\n"
        "func f() -> void:\n\tprint(v)\n"
    ),
    "param_orphan": (
        "extends Node\n\n\nfunc f(a: int, x = 1 if a > 0 else 2) -> void:\n"
        "\tprint(x)\n"
    ),
    # --- already fine; must stay fine ---
    "control_stmt": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = 1 if a > 0 else 2\n\tprint(x)\n"
    ),
    "nested_ternary": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar x = 1 if a > 0 else 2 if a < 0 else 3\n\tprint(x)\n"
    ),
    "lambda_ternary": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tvar c = func(p: int): return 1 if p > 0 else 2\n"
        "\tprint(c.call(1))\n"
    ),
    "ml_if": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tif (\n\t\ta > 0\n\t\tand a < 10\n\t):\n\t\tprint(a)\n"
    ),
    "ternary_in_arr": (
        "extends Node\n\n\nfunc f(a: int) -> void:\n"
        "\tprint([1 if a > 0 else 2, 3])\n"
    ),
    "no_ternary": (
        "extends Node\n\n\nfunc f() -> void:\n\tvar x = 1\n\tprint(x)\n"
    ),
}

#: Deliberately unparseable, used to prove the harness can still fail.
BROKEN_CONTROL = (
    "extends Node\n\n\nfunc f() -> void:\n" "\tvar x = (\n\t\t1\n\tprint(x)\n"
)


def _indent_of(line: str) -> str:
    out = ""
    for ch in line:
        if ch not in (" ", "\t"):
            break
        out += ch
    return out


def _inject(source: str, lines) -> str:
    """Port of ``_inject_trackers`` from the native coverage collector.

    Mirrors the collector's ordering: entries are sorted by line
    descending so that each insertion leaves earlier indices valid.
    """
    src_lines = source.split("\n")
    for entry in sorted(lines, key=lambda e: e.line, reverse=True):
        target = entry.line - 1
        if target < 0 or target >= len(src_lines):
            continue
        if entry.branch_type in ("match_case", "if_false", "elif_true"):
            target += 1
        indent = _indent_of(src_lines[target])
        if not indent:
            indent = _indent_of(src_lines[entry.line - 1])
        src_lines.insert(
            target, f"{indent}GdToolsNativeCoverage.hit(0, {entry.id})"
        )
    return "\n".join(src_lines)


def _run(godot_bin: str, project: Path, *args: str) -> str:
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
    output = _run(
        godot_bin, project, "--check-only", "--script", f"res://{name}"
    )
    is_broken = bool(_PARSE_ERROR.search(output))
    return not is_broken, output


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
    """Each instrumented fixture compiles under a real Godot."""
    project = _build_project(godot_bin, tmp_path, CASES[case], "fixture.gd")

    plan = generate_plan(str(project))
    entry = next(f for f in plan.files if f.path.endswith("fixture.gd"))

    instrumented = _inject(CASES[case], entry.lines)
    (project / "fixture.gd").write_text(instrumented, encoding="utf-8")

    valid, output = _check(godot_bin, project, "fixture.gd")

    assert (
        valid
    ), f"Instrumented '{case}' does not parse:\n{instrumented}\n---\n{output}"
