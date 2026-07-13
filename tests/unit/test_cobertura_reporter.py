"""Unit tests for the Cobertura XML coverage reporter.

Covers Cobertura XML generation: structure, attributes, branch
condition-coverage, zero-coverage file inclusion, and rate accuracy.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from gd_tools.coverage.cobertura_reporter import (
    _format_rate,
    generate_cobertura_report,
)
from gd_tools.coverage.plan_generator import read_plan_json
from gd_tools.coverage.reporter import read_coverage_json

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PLAN_FIXTURE = _FIXTURES_DIR / "coverage_plans" / "test_plan.json"
_FULL_COV = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
_PARTIAL_COV = _FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
_ZERO_COV = _FIXTURES_DIR / "coverage_data" / "zero_coverage.json"


def _generate_and_parse(plan, data, tmp_path):
    """Helper: generate Cobertura report and parse the XML tree."""
    output = generate_cobertura_report(plan, data, tmp_path / "cobertura.xml")
    tree = ET.parse(output)
    return tree


def test_cobertura_xml_well_formed(tmp_path):
    """Cobertura output is well-formed XML parseable by ElementTree."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)
    assert tree is not None


def test_cobertura_root_has_line_and_branch_rate(tmp_path):
    """Root <coverage> element has line-rate and branch-rate attributes."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)
    root = tree.getroot()

    assert root.tag == "coverage"
    assert "line-rate" in root.attrib
    assert "branch-rate" in root.attrib


def test_cobertura_has_class_per_file(tmp_path):
    """A <class> element exists for each file in the plan."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)

    classes = tree.findall(".//class")
    assert len(classes) == 2

    # Check filenames match res:// paths
    filenames = [c.get("filename") for c in classes]
    assert "res://player.gd" in filenames
    assert "res://enemy.gd" in filenames


def test_cobertura_line_elements_have_attributes(tmp_path):
    """<line> elements have number, hits, and branch attributes."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)

    lines = tree.findall(".//line")
    # File 0 has 5 lines, File 1 has 3 lines = 8 total
    assert len(lines) == 8

    for line_elem in lines:
        assert "number" in line_elem.attrib
        assert "hits" in line_elem.attrib
        assert "branch" in line_elem.attrib


def test_cobertura_branch_lines_have_condition_coverage(tmp_path):
    """Branch <line> elements have condition-coverage attribute."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)

    lines = tree.findall(".//line")
    branch_lines = [ln for ln in lines if ln.get("branch") == "true"]
    statement_lines = [ln for ln in lines if ln.get("branch") == "false"]

    # File 0 has 2 branches, File 1 has 1 branch = 3 total
    assert len(branch_lines) == 3
    assert len(statement_lines) == 5

    # All branch lines must have condition-coverage
    for bl in branch_lines:
        assert "condition-coverage" in bl.attrib

    # Statement lines must NOT have condition-coverage
    for sl in statement_lines:
        assert "condition-coverage" not in sl.attrib


def test_cobertura_includes_zero_coverage_files(tmp_path):
    """Zero-coverage files are included with all hits=0."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    tree = _generate_and_parse(plan, data, tmp_path)

    # Both files should still be present
    classes = tree.findall(".//class")
    assert len(classes) == 2

    # All lines should have hits=0
    lines = tree.findall(".//line")
    assert len(lines) == 8
    for line_elem in lines:
        assert line_elem.get("hits") == "0"

    # Root line-rate should be 0.0
    root = tree.getroot()
    assert float(root.get("line-rate")) == 0.0


def test_cobertura_rates_match_computed_metrics(tmp_path):
    """line-rate and branch-rate values match computed coverage metrics."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)
    root = tree.getroot()

    # Partial coverage: file 0 has 3/5 lines hit, 1/2 branches hit
    # File 1 has 2/3 lines hit, 0/1 branches hit
    # Overall: 5/8 lines = 0.625, 1/3 branches = 0.333...
    line_rate = float(root.get("line-rate"))
    branch_rate = float(root.get("branch-rate"))

    assert abs(line_rate - 0.625) < 0.001
    assert abs(branch_rate - (1.0 / 3.0)) < 0.001

    # Check per-class rates for file 0 (player.gd)
    classes = tree.findall(".//class")
    player_cls = [c for c in classes if c.get("filename") == "res://player.gd"][
        0
    ]
    player_line_rate = float(player_cls.get("line-rate"))
    player_branch_rate = float(player_cls.get("branch-rate"))

    # File 0: 3/5 lines = 0.6, 1/2 branches = 0.5
    assert abs(player_line_rate - 0.6) < 0.001
    assert abs(player_branch_rate - 0.5) < 0.001


def test_cobertura_line_hits_correct(tmp_path):
    """<line> hits values match the coverage data per file."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    tree = _generate_and_parse(plan, data, tmp_path)

    classes = tree.findall(".//class")

    # File 0 (player.gd) hits: {0:3, 1:2, 2:1, 3:1, 4:3}
    # Lines: id0->line5, id1->line7, id2->line10, id3->line12, id4->line15
    player_cls = [c for c in classes if c.get("filename") == "res://player.gd"][
        0
    ]
    player_lines = player_cls.findall(".//line")
    player_hits = {
        int(ln.get("number")): int(ln.get("hits")) for ln in player_lines
    }
    assert player_hits[5] == 3
    assert player_hits[7] == 2
    assert player_hits[10] == 1
    assert player_hits[12] == 1
    assert player_hits[15] == 3

    # File 1 (enemy.gd) hits: {0:2, 1:5, 2:2}
    # Lines: id0->line3, id1->line5, id2->line8
    enemy_cls = [c for c in classes if c.get("filename") == "res://enemy.gd"][0]
    enemy_lines = enemy_cls.findall(".//line")
    enemy_hits = {
        int(ln.get("number")): int(ln.get("hits")) for ln in enemy_lines
    }
    assert enemy_hits[3] == 2
    assert enemy_hits[5] == 5
    assert enemy_hits[8] == 2


def test_format_rate_zero_total():
    """_format_rate returns '0.0000' when total is zero (zero-division guard)."""
    assert _format_rate(0, 0) == "0.0000"
