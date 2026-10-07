"""Unit tests for the HTML reporter module.

Covers HTML report generation: index page with summary table, per-file
source listing pages, CSS coverage classes, zero-coverage file inclusion,
``res://`` path convention, and HTML validity.
"""

from html.parser import HTMLParser
from pathlib import Path

import pytest

from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    FilePlan,
    LinePlan,
    read_plan_json,
)
from gd_tools.coverage.reporter import FileCoverage, read_coverage_json

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PLAN_FIXTURE = _FIXTURES_DIR / "coverage_plans" / "test_plan.json"
_FULL_COV = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
_PARTIAL_COV = _FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
_ZERO_COV = _FIXTURES_DIR / "coverage_data" / "zero_coverage.json"


class _ValidHTMLChecker(HTMLParser):
    """HTML parser that records unclosed or mismatched tags."""

    def __init__(self):
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        void_tags = {"meta", "link", "br", "hr", "input", "img"}
        if tag not in void_tags:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append(f"Unclosed tag: {self.stack[-1]}")
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"Unexpected closing tag: {tag}")


def _assert_valid_html(content: str):
    """Assert that *content* is well-formed HTML."""
    checker = _ValidHTMLChecker()
    checker.feed(content)
    checker.close()
    assert not checker.errors, f"HTML errors: {checker.errors}"
    assert not checker.stack, f"Unclosed tags: {checker.stack}"


def test_html_creates_index_file(tmp_path):
    """generate_html_report creates index.html in the output directory."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_html_report(plan, data, tmp_path)

    assert result.name == "index.html"
    assert result.exists()


def test_html_creates_file_per_source(tmp_path):
    """generate_html_report creates one HTML page per source file."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    generate_html_report(plan, data, tmp_path)

    html_files = list(tmp_path.glob("file_*.html"))
    assert len(html_files) == 2


def test_html_index_has_summary_table(tmp_path):
    """Index page contains a summary table with file, line %, branch % columns."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_html_report(plan, data, tmp_path)

    content = result.read_text(encoding="utf-8")
    assert "<table" in content
    assert "File" in content
    assert "Line %" in content
    assert "Branch %" in content


def test_html_index_shows_overall_coverage(tmp_path):
    """Index page displays overall line and branch coverage percentages."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_html_report(plan, data, tmp_path)

    content = result.read_text(encoding="utf-8")
    assert "100.0%" in content


def test_html_file_page_has_line_numbers(tmp_path):
    """Per-file page contains line numbers from the plan."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    generate_html_report(plan, data, tmp_path)

    file_page = (tmp_path / "file_0.html").read_text(encoding="utf-8")
    assert "5" in file_page
    assert "7" in file_page
    assert "10" in file_page
    assert "12" in file_page
    assert "15" in file_page


def test_html_file_page_has_css_classes(tmp_path):
    """Per-file page has covered, uncovered, and partial CSS classes."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    generate_html_report(plan, data, tmp_path)

    file_page = (tmp_path / "file_0.html").read_text(encoding="utf-8")
    assert "covered" in file_page
    assert "uncovered" in file_page
    assert "partial" in file_page


def test_html_zero_coverage_files_in_index(tmp_path):
    """Zero-coverage files appear in the index with 0% metrics."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    result = generate_html_report(plan, data, tmp_path)

    content = result.read_text(encoding="utf-8")
    assert "0.0%" in content
    assert "res://player.gd" in content
    assert "res://enemy.gd" in content


def test_html_uses_res_protocol_paths(tmp_path):
    """File paths in the report use the res:// convention."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_html_report(plan, data, tmp_path)

    content = result.read_text(encoding="utf-8")
    assert "res://player.gd" in content
    assert "res://enemy.gd" in content


def test_html_output_is_valid(tmp_path):
    """HTML output is well-formed (no unclosed or mismatched tags)."""
    from gd_tools.coverage.html_reporter import generate_html_report

    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    generate_html_report(plan, data, tmp_path)

    for html_file in tmp_path.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        _assert_valid_html(content)


# --- Enriched view model (HTML report overhaul) ---


def _view_model_plan() -> CoveragePlan:
    """Plan exercising every branch type, exclusions, and a zero-branch file."""
    return CoveragePlan(
        version=7,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://branches.gd",
                source_hash="sha256:aaa",
                lines=[
                    LinePlan(line=5, id=0, type="statement"),
                    LinePlan(
                        line=10, id=1, type="branch", branch_type="if_true"
                    ),
                    LinePlan(
                        line=10, id=2, type="branch", branch_type="if_false"
                    ),
                    LinePlan(
                        line=14, id=3, type="branch", branch_type="and_site"
                    ),
                    LinePlan(
                        line=14, id=4, type="branch", branch_type="and_right"
                    ),
                    LinePlan(
                        line=14, id=5, type="branch", branch_type="and_short"
                    ),
                    LinePlan(
                        line=18, id=6, type="branch", branch_type="ternary_true"
                    ),
                    LinePlan(
                        line=18,
                        id=7,
                        type="branch",
                        branch_type="ternary_false",
                    ),
                    LinePlan(
                        line=22, id=8, type="branch", branch_type="assert_true"
                    ),
                    LinePlan(
                        line=22, id=9, type="branch", branch_type="assert_false"
                    ),
                    LinePlan(
                        line=26, id=10, type="branch", branch_type="elif_true"
                    ),
                ],
                excluded_lines=[3, 30],
            ),
            FilePlan(
                file_id=1,
                path="res://plain.gd",
                source_hash="sha256:bbb",
                lines=[LinePlan(line=2, id=0, type="statement")],
            ),
        ],
    )


def _view_model_data(hits: dict[str, int], file_id: int = 0) -> FileCoverage:
    """Coverage data for one file with the given hit counts."""
    return FileCoverage(file_id=file_id, hits=hits)


def test_branch_lines_expose_arms_with_labels_and_state():
    """Branch lines carry per-arm entries with terminal-parity labels."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({"1": 1, "3": 5, "6": 2, "8": 1})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }

    line10 = lines[10]["branches"]
    assert [(a["label"], a["covered"]) for a in line10] == [
        ("if", True),
        ("else", False),
    ]

    line14 = lines[14]["branches"]
    assert [(a["label"], a["covered"]) for a in line14] == [
        ("and site", True),
        ("and right operand", False),
        ("and short-circuit arm", False),
    ]

    line18 = lines[18]["branches"]
    assert [(a["label"], a["covered"]) for a in line18] == [
        ("ternary true", True),
        ("ternary false", False),
    ]

    line22 = lines[22]["branches"]
    assert [(a["label"], a["covered"]) for a in line22] == [
        ("assert_true", True),
        ("assert_false", False),
    ]

    line26 = lines[26]["branches"]
    assert [(a["label"], a["covered"]) for a in line26] == [("elif", False)]


def test_arm_entries_carry_type_and_hits():
    """Arm entries expose the raw branch type and hit count."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({"3": 5, "5": 1})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }

    arms = {a["branch_type"]: a for a in lines[14]["branches"]}
    assert arms["and_site"]["hits"] == 5
    assert arms["and_right"]["hits"] == 0
    assert arms["and_short"]["hits"] == 1


def test_statement_lines_have_no_branches():
    """Statement lines carry an empty branch list."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({})

    lines = build_line_views(plan.files[0], data)
    statements = [entry for entry in lines if entry["number"] == 5]
    assert len(statements) == 1
    assert statements[0]["branches"] == []


def test_excluded_lines_flagged_with_annotation():
    """Excluded lines carry the excluded flag and annotation context."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }

    for number in (3, 30):
        assert lines[number]["excluded"] is True
        assert "no cover" in lines[number]["annotation"]
        assert lines[number]["hits"] is None

    assert lines[5]["excluded"] is False


def test_view_lines_are_sorted_by_number():
    """Line views are sorted by line number, excluded lines included in place."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({})

    numbers = [
        entry["number"] for entry in build_line_views(plan.files[0], data)
    ]
    assert numbers == sorted(numbers)
    assert 3 in numbers
    assert 30 in numbers


def test_zero_branch_file_is_flagged():
    """Files without branch points are flagged for the no-branch-points note."""
    from gd_tools.coverage.html_reporter import file_has_branch_points

    plan = _view_model_plan()
    assert file_has_branch_points(plan.files[0]) is True
    assert file_has_branch_points(plan.files[1]) is False


def test_unknown_branch_type_label_falls_back_to_raw():
    """Unknown branch types fall back to the raw type string (terminal parity)."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    plan.files[0].lines.append(
        LinePlan(line=40, id=11, type="branch", branch_type="future_kind")
    )
    data = _view_model_data({})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }
    assert lines[40]["branches"][0]["label"] == "future_kind"


def test_statement_and_branch_on_same_line_merge():
    """A line hosting both a statement and branch points yields one merged entry."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    plan.files[0].lines.insert(0, LinePlan(line=10, id=12, type="statement"))
    data = _view_model_data({"12": 3})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }

    merged = lines[10]
    assert merged["hits"] == 3
    assert merged["css_class"] == "partial"
    assert len(merged["branches"]) == 2
    assert len([e for e in lines.values() if e["number"] == 10]) == 1


def test_excluded_plan_line_is_flagged():
    """A plan-point line listed in excluded_lines renders as excluded."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    plan.files[0].excluded_lines.append(5)
    data = _view_model_data({"0": 2})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }

    assert lines[5]["excluded"] is True
    assert lines[5]["hits"] is None
    assert lines[5]["css_class"] == "excluded"
    assert "no cover" in lines[5]["annotation"]


def test_covered_statement_line_css_class():
    """A statement line with hits gets the covered class."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({"0": 2})

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data)
    }

    assert lines[5]["css_class"] == "covered"
    assert lines[5]["hits"] == 2


def test_source_lines_populate_source_text():
    """Source lines fill each entry's source text when provided."""
    from gd_tools.coverage.html_reporter import build_line_views

    plan = _view_model_plan()
    data = _view_model_data({})
    source_lines = [f"line {n}" for n in range(1, 31)]

    lines = {
        entry["number"]: entry
        for entry in build_line_views(plan.files[0], data, source_lines)
    }

    assert lines[5]["source"] == "line 5"
    assert lines[3]["source"] == "line 3"
    assert lines[30]["source"] == "line 30"
