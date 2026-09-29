"""Unit tests for coverage exclusion annotations (`# gd-tools: no cover`).

Covers the three annotation forms (single-line, block start/end, and
func-line exclusion), the plan JSON ``excluded_lines`` field, and the
no-annotation default (spec: coverage_exclusions_20260930, FR1/FR4).
"""

import json

import pytest

from gd_tools.coverage.plan_generator import (
    generate_plan,
    read_plan_json,
    write_plan_json,
)

pytestmark = pytest.mark.unit

ANNOTATION = "# gd-tools: no cover"
BLOCK_START = "# gd-tools: no cover start"
BLOCK_END = "# gd-tools: no cover end"


def _plan_for(tmp_path, name, source):
    """Write a .gd file into tmp_path and generate its plan."""
    (tmp_path / name).write_text(source, encoding="utf-8")
    return generate_plan(str(tmp_path))


def _point_lines(plan):
    """Return the set of instrumented line numbers for the sole file."""
    assert len(plan.files) == 1
    return {lp.line for lp in plan.files[0].lines}


def _excluded_lines(plan):
    """Return the excluded line numbers recorded for the sole file."""
    assert len(plan.files) == 1
    return plan.files[0].excluded_lines


# --- Line form ---


class TestLineAnnotation:
    """`# gd-tools: no cover` on a line excludes that line only."""

    def test_excluded_statement_not_instrumented(self, tmp_path):
        """A statement carrying the annotation is absent from plan lines."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            "    var kept = 1\n"
            f"    var noisy = 2  {ANNOTATION}\n"
            "    var kept2 = 3\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 3 in lines  # kept
        assert 5 in lines  # kept2
        assert 4 not in lines  # annotated statement excluded
        assert _excluded_lines(plan) == [4]

    def test_annotated_if_line_excludes_branch_point(self, tmp_path):
        """An annotated if-line drops its branch point but not its body."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            f"    if OS.is_debug_build():  {ANNOTATION}\n"
            '        print("debug")\n'
            "    var after = 1\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 3 not in lines  # annotated if-line excluded
        assert 4 in lines  # body statement still instrumented
        assert 5 in lines
        assert _excluded_lines(plan) == [3]

    def test_annotation_only_affects_its_own_line(self, tmp_path):
        """Surrounding statements remain instrumented."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            "    var a = 1\n"
            f"    {ANNOTATION}\n"
            "    var b = 2\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 3 in lines
        assert 4 not in lines  # bare annotation on comment-only line
        assert 5 in lines


# --- Block form ---


class TestBlockAnnotation:
    """`no cover start` ... `no cover end` excludes the inclusive block."""

    def test_block_excludes_inclusive_range(self, tmp_path):
        """Lines from start through end are excluded, nothing else."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            "    var before = 1\n"
            f"    {BLOCK_START}\n"
            "    var inside1 = 2\n"
            "    if true:\n"
            "        pass\n"
            f"    {BLOCK_END}\n"
            "    var after = 3\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 3 in lines  # before
        assert 5 not in lines  # inside1
        assert 6 not in lines  # if branch point
        assert 7 not in lines  # body pass
        assert 9 in lines  # after
        assert _excluded_lines(plan) == [4, 5, 6, 7, 8]

    def test_two_disjoint_blocks(self, tmp_path):
        """Two independent start/end blocks are both honored."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            f"    {BLOCK_START}\n"
            "    var a = 1\n"
            f"    {BLOCK_END}\n"
            "    var keep = 2\n"
            f"    {BLOCK_START}\n"
            "    var b = 3\n"
            f"    {BLOCK_END}\n"
            "    var keep2 = 4\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 6 in lines
        assert 10 in lines
        assert 4 not in lines
        assert 8 not in lines
        assert _excluded_lines(plan) == [3, 4, 5, 7, 8, 9]


# --- Function form ---


class TestFunctionAnnotation:
    """Annotation on a `func` line excludes the entire function body."""

    def test_whole_function_excluded(self, tmp_path):
        """All points in the annotated function are excluded."""
        source = (
            "extends Node\n"
            f"func _debug_only():  {ANNOTATION}\n"
            "    var a = 1\n"
            "    if true:\n"
            "        pass\n"
            "\n"
            "func _ready():\n"
            "    var kept = 2\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 3 not in lines  # var a
        assert 4 not in lines  # if branch
        assert 5 not in lines  # body pass
        assert 8 in lines  # kept in the other function

        excluded = _excluded_lines(plan)
        assert 3 in excluded
        assert 4 in excluded
        assert 5 in excluded
        # The func line itself and the other function are not excluded.
        assert 2 in excluded
        assert 8 not in excluded


# --- Plan JSON transparency (FR4) ---


class TestPlanJsonExcludedLines:
    """Excluded lines are recorded in the plan JSON."""

    def test_file_plan_dataclass_has_excluded_lines(self, tmp_path):
        """FilePlan exposes excluded_lines, defaulting to an empty list."""
        from gd_tools.coverage.plan_generator import FilePlan

        fp = FilePlan(file_id=0, path="res://a.gd", source_hash="sha256:x")
        assert fp.excluded_lines == []

    def test_write_plan_json_includes_excluded_lines(self, tmp_path):
        """write_plan_json serializes excluded_lines per file."""
        from gd_tools.coverage.plan_generator import (
            CoveragePlan,
            FilePlan,
        )

        fp = FilePlan(
            file_id=0,
            path="res://a.gd",
            source_hash="sha256:x",
            excluded_lines=[3, 4, 5],
        )
        output = tmp_path / "plan.json"
        write_plan_json(
            CoveragePlan(version=2, generated_by="gd-tools", files=[fp]),
            str(output),
        )

        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["files"][0]["excluded_lines"] == [3, 4, 5]

    def test_read_plan_json_round_trips_excluded_lines(self, tmp_path):
        """read_plan_json restores excluded_lines from JSON."""
        from gd_tools.coverage.plan_generator import (
            CoveragePlan,
            FilePlan,
        )

        fp = FilePlan(
            file_id=0,
            path="res://a.gd",
            source_hash="sha256:x",
            excluded_lines=[7],
        )
        plan_file = tmp_path / "plan.json"
        write_plan_json(
            CoveragePlan(version=2, generated_by="gd-tools", files=[fp]),
            str(plan_file),
        )

        loaded = read_plan_json(str(plan_file))
        assert loaded.files[0].excluded_lines == [7]

    def test_read_plan_json_missing_excluded_lines_defaults_empty(
        self, tmp_path
    ):
        """Older JSON without excluded_lines loads with an empty list."""
        json_data = {
            "version": 2,
            "generated_by": "gd-tools",
            "files": [
                {
                    "file_id": 0,
                    "path": "res://a.gd",
                    "source_hash": "sha256:x",
                    "lines": [],
                },
            ],
        }
        plan_file = tmp_path / "plan.json"
        plan_file.write_text(json.dumps(json_data), encoding="utf-8")

        loaded = read_plan_json(str(plan_file))
        assert loaded.files[0].excluded_lines == []


# --- Edge cases (flat semantics, FR2/FR3) ---


class TestBlockEdgeCases:
    """Flat first-match block semantics and warn-and-continue behavior."""

    def test_nested_start_ignored_with_warning(self, tmp_path, capsys):
        """A second `start` inside an open block is ignored with a warning."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            "    var before = 1\n"
            f"    {BLOCK_START}\n"
            f"    {BLOCK_START}\n"
            "    var inside = 2\n"
            f"    {BLOCK_END}\n"
            "    var after = 3\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 3 in lines
        assert 4 not in lines
        assert 6 not in lines
        assert 8 in lines
        assert _excluded_lines(plan) == [4, 5, 6, 7]

        err = capsys.readouterr().err
        assert "line 5" in err
        assert "ignored" in err

    def test_unterminated_start_excludes_to_eof_with_warning(
        self, tmp_path, capsys
    ):
        """A `start` with no `end` excludes to end of file and warns."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            f"    {BLOCK_START}\n"
            "    var a = 1\n"
            "    var b = 2\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert _point_lines(plan) == set()
        assert _excluded_lines(plan) == [3, 4, 5]

        err = capsys.readouterr().err
        assert "line 3" in err

    def test_stray_end_ignored_with_warning(self, tmp_path, capsys):
        """An `end` without an open block is ignored with a warning."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            f"    {BLOCK_END}\n"
            "    var a = 1\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        lines = _point_lines(plan)
        assert 4 in lines
        assert _excluded_lines(plan) == []

        err = capsys.readouterr().err
        assert "line 3" in err
        assert "ignored" in err

    def test_warning_goes_to_stderr_not_stdout(self, tmp_path, capsys):
        """Annotation warnings are emitted on stderr only."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            f"    {BLOCK_END}\n"
            "    var a = 1\n"
        )
        _plan_for(tmp_path, "player.gd", source)

        captured = capsys.readouterr()
        assert captured.err != ""
        assert "no cover" in captured.err
        assert "ignored" not in captured.out

    def test_annotation_inside_multiline_string_is_inert(self, tmp_path):
        """Annotation-looking text inside string literals is never matched."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            '    var doc = """# gd-tools: no cover\n'
            "# gd-tools: no cover start\n"
            '"""\n'
            '    var s = "# gd-tools: no cover"\n'
            "    var a = 1\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert _excluded_lines(plan) == []
        lines = _point_lines(plan)
        assert 3 in lines
        assert 6 in lines
        assert 7 in lines

    def test_annotations_inside_excluded_function_do_not_leak(
        self, tmp_path, capsys
    ):
        """Annotations inside an already-excluded function are inert."""
        source = (
            "extends Node\n"
            f"func _excluded():  {ANNOTATION}\n"
            f"    {BLOCK_START}\n"
            "    var a = 1\n"
            "\n"
            "func _ready():\n"
            f"    {BLOCK_END}\n"
            "    var b = 2\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert _excluded_lines(plan) == [2, 3, 4]
        lines = _point_lines(plan)
        assert 4 not in lines
        assert 8 in lines

        # The stray `end` (line 7) still warns — it has no open block.
        err = capsys.readouterr().err
        assert "line 7" in err

    def test_start_annotation_on_func_line_excludes_function(self, tmp_path):
        """`no cover start` on a func line excludes the whole function."""
        source = (
            "extends Node\n"
            f"func _debug():  {BLOCK_START}\n"
            "    var a = 1\n"
            "\n"
            "func _ready():\n"
            "    var b = 2\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert _excluded_lines(plan) == [2, 3]
        lines = _point_lines(plan)
        assert 3 not in lines
        assert 6 in lines

    def test_malformed_annotation_never_fails_generation(self, tmp_path):
        """Warn-and-continue: malformed annotations never abort generation."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            f"    {BLOCK_END}\n"
            "    var a = 1\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert len(plan.files) == 1
        assert plan.files[0].lines  # generation produced a plan


# --- No-annotation default ---


class TestNoAnnotations:
    """Files without annotations behave exactly as before."""

    def test_no_annotations_yields_empty_excluded_lines(self, tmp_path):
        """A file without annotations records no excluded lines."""
        source = (
            "extends Node\n"
            "func _ready():\n"
            "    if true:\n"
            "        pass\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert _excluded_lines(plan) == []
        assert len(plan.files[0].lines) > 0

    def test_unrelated_comments_are_inert(self, tmp_path):
        """Ordinary comments (not the exact token) change nothing."""
        source = (
            "extends Node\n"
            "# gd-tools: no coverage here\n"
            "# nocovertest\n"
            "func _ready():\n"
            "    var x = 1  # gd-tools: no cover extrasuffix\n"
        )
        plan = _plan_for(tmp_path, "player.gd", source)

        assert _excluded_lines(plan) == []
        lines = _point_lines(plan)
        assert 5 in lines


class TestScannerStringHandling:
    """The line lexer ignores annotation text embedded in strings."""

    @staticmethod
    def _scan(source):
        from gd_tools.coverage.plan_generator import find_excluded_lines

        return find_excluded_lines(source)

    def test_escaped_quote_does_not_open_string_state(self):
        r"""An escaped quote inside a string keeps the lexer in string state."""
        excluded, warnings = self._scan(
            'var s = "a \\"# gd-tools: no cover\\" b"\n'
        )
        assert excluded == []
        assert warnings == []

    def test_closed_triple_quote_is_skipped_in_one_line(self):
        """A triple-quoted string opened and closed on one line is skipped."""
        excluded, warnings = self._scan('var s = """# gd-tools: no cover"""\n')
        assert excluded == []
        assert warnings == []

    def test_unterminated_quote_never_yields_a_comment(self):
        """An unterminated string means no comment is read from that line."""
        excluded, warnings = self._scan(
            'var s = "unterminated # gd-tools: no cover\n'
        )
        assert excluded == []
        assert warnings == []
