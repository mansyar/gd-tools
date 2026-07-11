"""Unit tests for the coverage plan generator module.

Covers data structures (CoveragePlan, FilePlan, LinePlan),
JSON serialization/deserialization, AST parsing, statement
classification, branch classification, and plan generation.
"""

import json
from pathlib import Path

import pytest

from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    FilePlan,
    LinePlan,
    generate_plan,
    parse_gdscript,
    read_plan_json,
    write_plan_json,
)

# --- Data structures ---


def test_line_plan_construction_defaults():
    """LinePlan with only required fields defaults branch_type to None."""
    lp = LinePlan(line=5, id=0, type="statement")
    assert lp.line == 5
    assert lp.id == 0
    assert lp.type == "statement"
    assert lp.branch_type is None


def test_line_plan_construction_with_branch_type():
    """LinePlan accepts an optional branch_type string."""
    lp = LinePlan(line=10, id=2, type="branch", branch_type="if_true")
    assert lp.branch_type == "if_true"


def test_file_plan_construction_defaults():
    """FilePlan with only required fields defaults lines to empty list."""
    fp = FilePlan(file_id=0, path="res://player.gd", source_hash="sha256:abc")
    assert fp.file_id == 0
    assert fp.path == "res://player.gd"
    assert fp.source_hash == "sha256:abc"
    assert fp.lines == []


def test_file_plan_construction_with_lines():
    """FilePlan accepts a list of LinePlan objects."""
    lp1 = LinePlan(line=1, id=0, type="statement")
    lp2 = LinePlan(line=5, id=1, type="branch", branch_type="if_true")
    fp = FilePlan(
        file_id=1,
        path="res://enemy.gd",
        source_hash="sha256:def",
        lines=[lp1, lp2],
    )
    assert len(fp.lines) == 2
    assert fp.lines[0].line == 1
    assert fp.lines[1].branch_type == "if_true"


def test_coverage_plan_construction_defaults():
    """CoveragePlan with only required fields defaults files to empty list."""
    cp = CoveragePlan(version=1, generated_by="gd-tools")
    assert cp.version == 1
    assert cp.generated_by == "gd-tools"
    assert cp.files == []


def test_coverage_plan_construction_with_files():
    """CoveragePlan accepts a list of FilePlan objects."""
    fp = FilePlan(file_id=0, path="res://a.gd", source_hash="sha256:x")
    cp = CoveragePlan(version=1, generated_by="gd-tools", files=[fp])
    assert len(cp.files) == 1
    assert cp.files[0].path == "res://a.gd"


def test_line_plan_type_field_values():
    """LinePlan type field accepts 'statement' and 'branch'."""
    lp_stmt = LinePlan(line=1, id=0, type="statement")
    lp_branch = LinePlan(line=2, id=1, type="branch", branch_type="loop_body")
    assert lp_stmt.type == "statement"
    assert lp_branch.type == "branch"


# --- write_plan_json ---


def test_write_plan_json_valid_structure(tmp_path):
    """write_plan_json produces a JSON file with version, generated_by, files."""
    lp = LinePlan(line=3, id=0, type="statement")
    fp = FilePlan(
        file_id=0,
        path="res://player.gd",
        source_hash="sha256:abc123",
        lines=[lp],
    )
    cp = CoveragePlan(version=1, generated_by="gd-tools", files=[fp])

    output = tmp_path / "plan.json"
    write_plan_json(cp, str(output))

    data = json.loads(output.read_text())
    assert data["version"] == 1
    assert data["generated_by"] == "gd-tools"
    assert len(data["files"]) == 1
    assert data["files"][0]["file_id"] == 0
    assert data["files"][0]["path"] == "res://player.gd"
    assert data["files"][0]["source_hash"] == "sha256:abc123"
    assert len(data["files"][0]["lines"]) == 1
    assert data["files"][0]["lines"][0]["line"] == 3
    assert data["files"][0]["lines"][0]["id"] == 0
    assert data["files"][0]["lines"][0]["type"] == "statement"
    assert data["files"][0]["lines"][0]["branch_type"] is None


def test_write_plan_json_empty_plan(tmp_path):
    """write_plan_json with no files produces valid JSON with empty files array."""
    cp = CoveragePlan(version=1, generated_by="gd-tools")
    output = tmp_path / "empty_plan.json"
    write_plan_json(cp, str(output))

    data = json.loads(output.read_text())
    assert data["version"] == 1
    assert data["generated_by"] == "gd-tools"
    assert data["files"] == []


# --- read_plan_json ---


def test_read_plan_json_valid(tmp_path):
    """read_plan_json deserializes a valid JSON file into CoveragePlan."""
    json_data = {
        "version": 1,
        "generated_by": "gd-tools",
        "files": [
            {
                "file_id": 0,
                "path": "res://player.gd",
                "source_hash": "sha256:abc",
                "lines": [
                    {
                        "line": 1,
                        "id": 0,
                        "type": "statement",
                        "branch_type": None,
                    },
                ],
            },
        ],
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))

    cp = read_plan_json(str(plan_file))
    assert cp.version == 1
    assert cp.generated_by == "gd-tools"
    assert len(cp.files) == 1
    assert cp.files[0].file_id == 0
    assert cp.files[0].lines[0].line == 1
    assert cp.files[0].lines[0].branch_type is None


def test_read_plan_json_missing_file(tmp_path):
    """read_plan_json raises CoveragePlanError for missing file."""
    from gd_tools.errors import CoveragePlanError

    with pytest.raises(CoveragePlanError):
        read_plan_json(str(tmp_path / "nonexistent.json"))


def test_read_plan_json_invalid_json(tmp_path):
    """read_plan_json raises CoveragePlanError for malformed JSON."""
    from gd_tools.errors import CoveragePlanError

    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json")
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(bad_file))


def test_read_plan_json_wrong_version(tmp_path):
    """read_plan_json raises CoveragePlanError for wrong schema version."""
    from gd_tools.errors import CoveragePlanError

    json_data = {"version": 99, "generated_by": "gd-tools", "files": []}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


def test_read_plan_json_missing_required_field(tmp_path):
    """read_plan_json raises CoveragePlanError when required fields are missing."""
    from gd_tools.errors import CoveragePlanError

    json_data = {"version": 1, "files": []}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


def test_read_plan_json_round_trip(tmp_path):
    """Round-trip: write then read produces an equal CoveragePlan."""
    lp1 = LinePlan(line=1, id=0, type="statement")
    lp2 = LinePlan(line=5, id=1, type="branch", branch_type="if_true")
    fp = FilePlan(
        file_id=0,
        path="res://player.gd",
        source_hash="sha256:abc",
        lines=[lp1, lp2],
    )
    original = CoveragePlan(version=1, generated_by="gd-tools", files=[fp])

    plan_file = tmp_path / "round_trip.json"
    write_plan_json(original, str(plan_file))
    loaded = read_plan_json(str(plan_file))

    assert loaded.version == original.version
    assert loaded.generated_by == original.generated_by
    assert len(loaded.files) == len(original.files)
    assert loaded.files[0].file_id == original.files[0].file_id
    assert loaded.files[0].path == original.files[0].path
    assert loaded.files[0].source_hash == original.files[0].source_hash
    assert len(loaded.files[0].lines) == len(original.files[0].lines)
    assert loaded.files[0].lines[0].line == original.files[0].lines[0].line
    assert (
        loaded.files[0].lines[1].branch_type
        == original.files[0].lines[1].branch_type
    )


def test_read_plan_json_missing_files_field(tmp_path):
    """read_plan_json raises CoveragePlanError when 'files' field is missing."""
    from gd_tools.errors import CoveragePlanError

    json_data = {"version": 1, "generated_by": "gd-tools"}
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


def test_read_plan_json_data_not_dict(tmp_path):
    """read_plan_json raises CoveragePlanError when JSON root is not an object."""
    from gd_tools.errors import CoveragePlanError

    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


def test_read_plan_json_files_not_list(tmp_path):
    """read_plan_json raises CoveragePlanError when 'files' is not a list."""
    from gd_tools.errors import CoveragePlanError

    json_data = {
        "version": 1,
        "generated_by": "gd-tools",
        "files": "not_a_list",
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


def test_read_plan_json_file_entry_missing_field(tmp_path):
    """read_plan_json raises CoveragePlanError when a file entry is missing a required field."""
    from gd_tools.errors import CoveragePlanError

    json_data = {
        "version": 1,
        "generated_by": "gd-tools",
        "files": [{"file_id": 0, "path": "res://x.gd"}],
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


def test_read_plan_json_file_entry_not_dict(tmp_path):
    """read_plan_json raises CoveragePlanError when a file entry is not a dict."""
    from gd_tools.errors import CoveragePlanError

    json_data = {
        "version": 1,
        "generated_by": "gd-tools",
        "files": ["not_a_dict"],
    }
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(json_data))
    with pytest.raises(CoveragePlanError):
        read_plan_json(str(plan_file))


# --- parse_gdscript ---


def test_parse_gdscript_valid_source():
    """parse_gdscript returns a Lark Tree for valid GDScript source."""
    source = "extends Node\nfunc _ready():\n    pass\n"
    tree = parse_gdscript(source)
    assert tree is not None
    assert hasattr(tree, "meta")


def test_parse_gdscript_empty_string():
    """parse_gdscript handles empty string gracefully."""
    tree = parse_gdscript("")
    assert tree is not None


# --- Statement classification ---


def test_assignment_is_expr_stmt():
    """An assignment statement produces an expr_stmt trackable point."""
    source = "extends Node\n" "func _ready():\n" "    var x = 5\n"
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    types = [p.type for p in visitor.points]
    assert "statement" in types


def test_func_var_with_assignment_tracked():
    """func_var_assigned, func_var_typed_assgnd, func_var_inf are all tracked."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    var a = 1\n"
        "    var b: int = 2\n"
        "    var c := 3\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    # At least 3 trackable statements (the three var assignments)
    assert len(visitor.points) >= 3


def test_declarations_not_tracked():
    """const, signal, enum, class_var, func_var_typed (no assignment) are NOT tracked."""
    source = (
        "extends Node\n"
        "const SPEED = 100\n"
        "signal hit\n"
        "enum State { IDLE, RUN }\n"
        "var health: int = 100\n"
        "class_name Player\n"
        "func _ready():\n"
        "    var x: int\n"
        "    pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    # class_var_stmt, const_stmt, signal_stmt, enum_stmt are all
    # declarative and not tracked. No executable statements present.
    assert len(visitor.points) == 0


def test_empty_file_produces_empty_plan():
    """Source with only declarations produces zero trackable points."""
    source = (
        "extends Node\n"
        "class_name Player\n"
        "const SPEED = 100\n"
        "signal hit\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    assert len(visitor.points) == 0


# --- Branch classification ---


def test_if_else_produces_two_branch_entries():
    """if/else produces if_true and if_false branch points."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    if true:\n"
        "        pass\n"
        "    else:\n"
        "        pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    assert "if_true" in branch_types
    assert "if_false" in branch_types


def test_elif_produces_additional_branch():
    """elif adds an elif_true branch point."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    if true:\n"
        "        pass\n"
        "    elif false:\n"
        "        pass\n"
        "    else:\n"
        "        pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    assert "if_true" in branch_types
    assert "elif_true" in branch_types
    assert "if_false" in branch_types


def test_while_loop_body_tracked():
    """while produces a loop_body branch point."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    var i = 0\n"
        "    while i < 10:\n"
        "        i += 1\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    assert "loop_body" in branch_types


def test_for_loop_body_tracked():
    """for and for_typed produce loop_body branch points."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    for i in range(5):\n"
        "        pass\n"
        "    for j: int in range(3):\n"
        "        pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    loop_count = branch_types.count("loop_body")
    assert loop_count == 2


def test_match_each_case_tracked():
    """Each match branch produces a match_case branch point."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    var x = 1\n"
        "    match x:\n"
        "        1:\n"
        "            pass\n"
        "        2:\n"
        "            pass\n"
        "        3:\n"
        "            pass\n"
        "        _:\n"
        "            pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    match_count = branch_types.count("match_case")
    assert match_count == 4


def test_nested_control_flow():
    """Nested branches produce correct branch types and unique IDs."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    for i in range(3):\n"
        "        if i > 1:\n"
        "            if i == 2:\n"
        "                match i:\n"
        "                    2:\n"
        "                        continue\n"
        "            else:\n"
        "                pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    branch_types = [p.branch_type for p in visitor.points if p.type == "branch"]
    assert "loop_body" in branch_types
    assert "if_true" in branch_types
    assert "if_false" in branch_types
    assert "match_case" in branch_types


def test_branch_ids_are_unique_per_file():
    """All point IDs within a file are unique."""
    source = (
        "extends Node\n"
        "func _ready():\n"
        "    if true:\n"
        "        pass\n"
        "    else:\n"
        "        pass\n"
        "    while false:\n"
        "        pass\n"
    )
    from gd_tools.coverage.plan_generator import CoverageVisitor

    tree = parse_gdscript(source)
    visitor = CoverageVisitor()
    visitor.visit(tree)
    ids = [p.id for p in visitor.points]
    assert len(ids) == len(set(ids))


# --- generate_plan ---


def test_generate_plan_multiple_files(tmp_path):
    """Multiple .gd files produce multiple FilePlan entries with sequential file_ids."""
    (tmp_path / "player.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    (tmp_path / "enemy.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )

    cp = generate_plan(str(tmp_path))
    assert len(cp.files) == 2
    assert cp.files[0].file_id == 0
    assert cp.files[1].file_id == 1


def test_generate_plan_source_hash_computed(tmp_path):
    """Each file entry has correct sha256: prefixed source hash."""
    source = "extends Node\n"
    (tmp_path / "player.gd").write_text(source)

    cp = generate_plan(str(tmp_path))
    assert cp.files[0].source_hash.startswith("sha256:")


def test_generate_plan_excludes_addons(tmp_path):
    """addons/ directory is excluded from coverage by default."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text("extends Node\n")

    cp = generate_plan(str(tmp_path))
    assert len(cp.files) == 1
    assert cp.files[0].path == "res://player.gd"


def test_generate_plan_excludes_test_dirs(tmp_path):
    """Files in test_dirs are excluded from coverage targets."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test_player.gd").write_text("extends Node\n")

    cp = generate_plan(str(tmp_path))
    assert len(cp.files) == 1
    assert cp.files[0].path == "res://player.gd"


def test_generate_plan_res_prefix(tmp_path):
    """File paths use res:// prefix."""
    (tmp_path / "player.gd").write_text("extends Node\n")

    cp = generate_plan(str(tmp_path))
    assert cp.files[0].path.startswith("res://")


def test_generate_plan_with_custom_exclude_dirs(tmp_path):
    """Custom exclude_dirs are respected."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "custom_excluded").mkdir()
    (tmp_path / "custom_excluded" / "plugin.gd").write_text("extends Node\n")

    cp = generate_plan(str(tmp_path), exclude_dirs=["custom_excluded"])
    assert len(cp.files) == 1
    assert cp.files[0].path == "res://player.gd"


def test_generate_plan_with_custom_test_dirs(tmp_path):
    """Custom test_dirs are respected for exclusion."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "spec").mkdir()
    (tmp_path / "spec" / "spec_player.gd").write_text("extends Node\n")

    cp = generate_plan(str(tmp_path), test_dirs=["spec"])
    assert len(cp.files) == 1
    assert cp.files[0].path == "res://player.gd"


# --- Expected plan fixtures ---


_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "gdscript"
_PLANS_DIR = Path(__file__).parent.parent / "fixtures" / "plans"


@pytest.mark.parametrize(
    "fixture_name",
    ["simple", "branches", "loops", "match_stmt", "nested", "edge_cases"],
)
def test_plan_generation_matches_expected(tmp_path, fixture_name):
    """Generated plan matches expected JSON fixture for each .gd fixture."""
    gd_source = (_FIXTURES_DIR / f"{fixture_name}.gd").read_text(
        encoding="utf-8"
    )
    (tmp_path / f"{fixture_name}.gd").write_text(gd_source, encoding="utf-8")

    generated = generate_plan(str(tmp_path))
    expected = read_plan_json(str(_PLANS_DIR / f"{fixture_name}.expected.json"))

    assert generated == expected


# --- Performance ---


_GD_TEMPLATE = """\
extends Node

func _ready() -> void:
    var count = 0
    for i in range(10):
        count += i
    if count > 5:
        print(count)
    else:
        print("low")
    return count
"""


def test_performance_100_files(tmp_path):
    """Generating a plan for 100 .gd files completes in <1 second."""
    for i in range(100):
        (tmp_path / f"script_{i:03d}.gd").write_text(
            _GD_TEMPLATE, encoding="utf-8"
        )

    import time

    start = time.perf_counter()
    cp = generate_plan(str(tmp_path))
    elapsed = time.perf_counter() - start

    assert len(cp.files) == 100
    assert elapsed < 1.0, f"Plan generation took {elapsed:.3f}s (>1s)"
