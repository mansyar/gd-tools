"""Tests for how reporters surface ``# gd-tools: no cover`` exclusions.

Covers spec FR5: the HTML report renders excluded lines in a distinct
style, the terminal report shows a compact excluded-lines count only
when exclusions exist, and the ``--min`` gate evaluates the
post-exclusion denominator (excluded lines are absent from the plan's
tracked lines, so they never enter the totals).
"""

import pytest

from gd_tools.coverage.html_reporter import generate_html_report
from gd_tools.coverage.lcov_reporter import generate_lcov_report
from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    FilePlan,
    generate_plan,
)
from gd_tools.coverage.reporter import (
    CoverageData,
    FileCoverage,
    compute_summary,
    generate_report,
)
from gd_tools.coverage.terminal_reporter import generate_terminal_report

pytestmark = pytest.mark.unit

_SOURCE = (
    "extends Node\n"
    "func _ready():\n"
    "    var a = 1\n"
    "    # gd-tools: no cover start\n"
    "    if OS.is_debug_build():\n"
    "        var dbg = 2\n"
    "    # gd-tools: no cover end\n"
    "    var b = 3\n"
)

_NO_ANNOTATION_SOURCE = (
    "extends Node\n" "func _ready():\n" "    var a = 1\n" "    var b = 3\n"
)


def _plan_for(tmp_path, source, name="player.gd"):
    """Write *source* into *tmp_path* and generate its plan."""
    (tmp_path / name).write_text(source, encoding="utf-8")
    return generate_plan(str(tmp_path))


def _full_data(plan):
    """Coverage data hitting every tracked point in *plan*."""
    files = [
        FileCoverage(
            file_id=fp.file_id,
            hits={str(lp.id): 1 for lp in fp.lines},
        )
        for fp in plan.files
    ]
    return CoverageData(
        version=1,
        generated_at="2026-09-30T00:00:00",
        files=files,
    )


class TestHtmlExcludedLines:
    """The HTML report renders excluded lines in a distinct style."""

    def test_excluded_lines_get_the_excluded_css_class(
        self, tmp_path, monkeypatch
    ):
        """Excluded lines appear with the ``excluded`` CSS class."""
        monkeypatch.chdir(tmp_path)
        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)
        out = tmp_path / "html"

        generate_html_report(plan, data, out)

        content = (out / "file_0.html").read_text(encoding="utf-8")
        assert content.count("source-line excluded") == 4
        # Tracked lines keep their usual classes.
        assert "source-line covered" in content

    def test_excluded_lines_show_source_in_order(self, tmp_path, monkeypatch):
        """Excluded rows interleave with tracked rows in source order."""
        monkeypatch.chdir(tmp_path)
        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)
        out = tmp_path / "html"

        generate_html_report(plan, data, out)

        content = (out / "file_0.html").read_text(encoding="utf-8")
        assert content.index("var a = 1") < content.index("var dbg = 2")
        assert content.index("var dbg = 2") < content.index("var b = 3")

    def test_no_exclusions_adds_no_excluded_rows(self, tmp_path, monkeypatch):
        """Files without annotations produce no excluded rows."""
        monkeypatch.chdir(tmp_path)
        plan = _plan_for(tmp_path, _NO_ANNOTATION_SOURCE)
        data = _full_data(plan)
        out = tmp_path / "html"

        generate_html_report(plan, data, out)

        content = (out / "file_0.html").read_text(encoding="utf-8")
        assert "source-line excluded" not in content


class TestTerminalExcludedCount:
    """The terminal report shows a compact count only when relevant."""

    def test_count_shown_when_exclusions_exist(self, tmp_path):
        """A plan with exclusions gets a summary line with counts."""
        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)

        result = generate_terminal_report(plan, data)

        assert "Excluded: 4 lines across 1 file" in result

    def test_no_count_when_no_exclusions(self):
        """A plan without exclusions mentions nothing about exclusions."""
        plan = CoveragePlan(
            version=2,
            generated_by="gd-tools",
            files=[
                FilePlan(
                    file_id=0,
                    path="res://player.gd",
                    source_hash="sha256:abc",
                    lines=[],
                    excluded_lines=[],
                )
            ],
        )
        data = CoverageData(version=1, generated_at="t", files=[])

        result = generate_terminal_report(plan, data)

        assert "Excluded" not in result


class TestMinGatePostExclusionDenominator:
    """The --min gate evaluates coverage over post-exclusion totals."""

    def test_gate_passes_with_exclusions_even_if_omitted_lines_were_counted(
        self, tmp_path
    ):
        """Excluded lines do not dilute the rate: 2/2 tracked hits = 100%.

        If the four excluded lines were counted in the denominator, two
        covered statements would only reach 2/6 = 33%.
        """
        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)

        summary = compute_summary(plan, data)
        assert summary.total_lines == 2
        assert summary.line_rate == 1.0

        # The full gate accepts 100% against a strict threshold.
        result = generate_report(
            plan, data, tmp_path, format="text", min_threshold=0.80
        )
        assert result.threshold_met is True

    def test_uncovered_list_never_contains_excluded_lines(self, tmp_path):
        """Excluded lines are never reported as uncovered."""
        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)

        result = generate_report(plan, data, tmp_path, format="text")

        fs = result.file_summaries[0]
        for line in (4, 5, 6, 7):
            assert line not in fs.uncovered_lines


class TestMachineFormatsUnchanged:
    """LCOV/Cobertura only ever see tracked lines, exclusions or not."""

    def test_lcov_contains_only_tracked_lines(self, tmp_path):
        """The lcov report has no data for excluded lines."""
        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)
        out = tmp_path / "coverage.info"

        generate_lcov_report(plan, data, out)

        content = out.read_text(encoding="utf-8")
        # Tracked statements: line 3 (var a) and line 8 (var b).
        assert "DA:3,1" in content
        assert "DA:8,1" in content
        assert "DA:4" not in content
        assert "DA:5" not in content
        assert "DA:6" not in content
        assert "DA:7" not in content

    def test_cobertura_contains_only_tracked_lines(self, tmp_path):
        """The cobertura report has no line elements for excluded lines."""
        from gd_tools.coverage.cobertura_reporter import (
            generate_cobertura_report,
        )

        plan = _plan_for(tmp_path, _SOURCE)
        data = _full_data(plan)
        out = tmp_path / "cobertura.xml"

        generate_cobertura_report(plan, data, out)

        content = out.read_text(encoding="utf-8")
        assert 'line number="3"' in content
        assert 'line number="8"' in content
        assert 'line number="4"' not in content
        assert 'line number="5"' not in content
        assert 'line number="6"' not in content
        assert 'line number="7"' not in content
