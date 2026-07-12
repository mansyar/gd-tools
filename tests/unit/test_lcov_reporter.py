"""Unit tests for the LCOV reporter module.

Covers LCOV .info file generation: record format, ordering,
zero-coverage file inclusion, and compatibility with LCOV parsers.
"""

from pathlib import Path

import pytest

from gd_tools.coverage.lcov_reporter import generate_lcov_report
from gd_tools.coverage.plan_generator import read_plan_json
from gd_tools.coverage.reporter import read_coverage_json

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PLAN_FIXTURE = _FIXTURES_DIR / "coverage_plans" / "test_plan.json"
_FULL_COV = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
_PARTIAL_COV = _FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
_ZERO_COV = _FIXTURES_DIR / "coverage_data" / "zero_coverage.json"


def test_lcov_contains_test_name_record(tmp_path):
    """LCOV output contains a TN: (test name) record."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    assert any(line.startswith("TN:") for line in content.splitlines())


def test_lcov_contains_source_file_records(tmp_path):
    """LCOV output contains SF:<res_path> for each file in the plan."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()
    sf_lines = [ln for ln in lines if ln.startswith("SF:")]
    assert len(sf_lines) == 2
    assert "SF:res://player.gd" in sf_lines
    assert "SF:res://enemy.gd" in sf_lines


def test_lcov_contains_line_data_records(tmp_path):
    """LCOV output contains DA:<line>,<hit_count> for all tracked lines."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()
    da_lines = [ln for ln in lines if ln.startswith("DA:")]

    # File 0 (player.gd) has 5 lines, File 1 (enemy.gd) has 3 lines = 8 total
    assert len(da_lines) == 8

    # Check specific DA records for file 0
    assert "DA:5,3" in da_lines
    assert "DA:7,2" in da_lines
    assert "DA:10,1" in da_lines
    assert "DA:12,1" in da_lines
    assert "DA:15,3" in da_lines

    # Check specific DA records for file 1
    assert "DA:3,2" in da_lines
    assert "DA:5,5" in da_lines
    assert "DA:8,2" in da_lines


def test_lcov_contains_branch_data_records(tmp_path):
    """LCOV output contains BRDA:<line>,<block>,<branch>,<taken> for branch lines."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()
    brda_lines = [ln for ln in lines if ln.startswith("BRDA:")]

    # File 0 has 2 branches (lines 10, 12), File 1 has 1 branch (line 5) = 3 total
    assert len(brda_lines) == 3

    # Each BRDA should have 4 comma-separated fields after the prefix
    for brda in brda_lines:
        fields = brda[5:].split(",")
        assert len(fields) == 4

    # Check specific BRDA records
    assert any(b.startswith("BRDA:10,") for b in brda_lines)
    assert any(b.startswith("BRDA:12,") for b in brda_lines)
    assert any(b.startswith("BRDA:5,") for b in brda_lines)


def test_lcov_contains_summary_records(tmp_path):
    """LCOV output contains BRF, BRH, LF, LH summary records per file."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()

    # File 0: 5 lines (all hit), 2 branches (all hit)
    # File 1: 3 lines (all hit), 1 branch (all hit)
    brf_lines = [ln for ln in lines if ln.startswith("BRF:")]
    brh_lines = [ln for ln in lines if ln.startswith("BRH:")]
    lf_lines = [ln for ln in lines if ln.startswith("LF:")]
    lh_lines = [ln for ln in lines if ln.startswith("LH:")]

    assert len(brf_lines) == 2
    assert len(brh_lines) == 2
    assert len(lf_lines) == 2
    assert len(lh_lines) == 2

    # File 0: BRF:2, BRH:2, LF:5, LH:5
    # File 1: BRF:1, BRH:1, LF:3, LH:3
    assert "BRF:2" in brf_lines
    assert "BRH:2" in brh_lines
    assert "LF:5" in lf_lines
    assert "LH:5" in lh_lines
    assert "BRF:1" in brf_lines
    assert "BRH:1" in brh_lines
    assert "LF:3" in lf_lines
    assert "LH:3" in lh_lines


def test_lcov_contains_end_of_record(tmp_path):
    """LCOV output contains end_of_record after each file section."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()
    eor_count = sum(1 for ln in lines if ln == "end_of_record")
    assert eor_count == 2


def test_lcov_includes_zero_coverage_files(tmp_path):
    """Zero-coverage files are included with all DA entries showing hit_count=0."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Both files should still be present
    sf_lines = [ln for ln in lines if ln.startswith("SF:")]
    assert len(sf_lines) == 2

    # All DA entries should have hit_count=0
    da_lines = [ln for ln in lines if ln.startswith("DA:")]
    assert len(da_lines) == 8
    for da in da_lines:
        hit_count = int(da.split(",")[1])
        assert hit_count == 0

    # Summary records should show 0 hits
    lh_lines = [ln for ln in lines if ln.startswith("LH:")]
    for lh in lh_lines:
        assert lh == "LH:0"

    brh_lines = [ln for ln in lines if ln.startswith("BRH:")]
    for brh in brh_lines:
        assert brh == "BRH:0"


def test_lcov_valid_format_and_ordering(tmp_path):
    """LCOV output is valid: correct record ordering within each file section."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    output = generate_lcov_report(plan, data, tmp_path / "coverage.info")

    content = output.read_text(encoding="utf-8")
    lines = content.splitlines()

    # TN: should be the first line
    assert lines[0].startswith("TN:")

    # Parse file sections
    sections = []
    current_section = []
    for line in lines:
        if line.startswith("SF:"):
            current_section = [line]
        elif line == "end_of_record":
            current_section.append(line)
            sections.append(current_section)
            current_section = []
        elif current_section:
            current_section.append(line)

    assert len(sections) == 2

    # Verify ordering within each section: SF, DA, BRDA, BRF, BRH, LF, LH, end_of_record
    for section in sections:
        prefixes = [ln.split(":")[0] for ln in section]
        expected_order = [
            "SF",
            "DA",
            "BRDA",
            "BRF",
            "BRH",
            "LF",
            "LH",
            "end_of_record",
        ]

        # Get unique prefixes in order of first appearance
        seen = []
        for p in prefixes:
            if p not in seen:
                seen.append(p)

        # DA and BRDA can have multiple entries, but the section types must be in order
        assert (
            seen == expected_order
        ), f"Expected order {expected_order}, got {seen} for section {section[0]}"

    # Verify partial coverage hits are correctly reflected
    # File 0 partial: hits {0:3, 1:0, 2:1, 3:0, 4:3}
    # Lines: 5->id0=3, 7->id1=0, 10->id2=1, 12->id3=0, 15->id4=3
    player_section = sections[0]
    da_player = [ln for ln in player_section if ln.startswith("DA:")]
    assert "DA:5,3" in da_player
    assert "DA:7,0" in da_player
    assert "DA:10,1" in da_player
    assert "DA:12,0" in da_player
    assert "DA:15,3" in da_player

    # LH should be 3 (lines 5, 10, 15 have hits > 0)
    lh_player = [ln for ln in player_section if ln.startswith("LH:")]
    assert lh_player[0] == "LH:3"
