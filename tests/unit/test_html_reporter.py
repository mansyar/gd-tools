"""Unit tests for the HTML reporter module.

Covers HTML report generation: index page with summary table, per-file
source listing pages, CSS coverage classes, zero-coverage file inclusion,
``res://`` path convention, and HTML validity.
"""

from html.parser import HTMLParser
from pathlib import Path

from gd_tools.coverage.plan_generator import read_plan_json
from gd_tools.coverage.reporter import read_coverage_json

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
