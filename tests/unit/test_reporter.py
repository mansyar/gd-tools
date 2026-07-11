"""Unit tests for the coverage reporter module.

Covers data structures (CoverageData, FileCoverage, CoverageSummary,
FileSummary, ReportResult), JSON I/O (read_coverage_json,
merge_coverage_data), and version validation.
"""

import json
from pathlib import Path

import pytest

from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileCoverage,
    FileSummary,
    ReportResult,
    merge_coverage_data,
    read_coverage_json,
)
from gd_tools.errors import CoveragePlanError

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# --- Data structures ---


def test_file_coverage_construction():
    """FileCoverage stores file_id and hits dict."""
    fc = FileCoverage(file_id=0, hits={"0": 3, "1": 0})
    assert fc.file_id == 0
    assert fc.hits == {"0": 3, "1": 0}


def test_file_coverage_empty_hits():
    """FileCoverage accepts empty hits dict."""
    fc = FileCoverage(file_id=1, hits={})
    assert fc.hits == {}


def test_coverage_data_construction_defaults():
    """CoverageData defaults generated_at to None and files to empty."""
    cd = CoverageData(version=1)
    assert cd.version == 1
    assert cd.generated_at is None
    assert cd.files == []


def test_coverage_data_construction_with_files():
    """CoverageData accepts a list of FileCoverage objects."""
    fc = FileCoverage(file_id=0, hits={"0": 1})
    cd = CoverageData(version=1, generated_at="2025-01-01", files=[fc])
    assert cd.generated_at == "2025-01-01"
    assert len(cd.files) == 1
    assert cd.files[0].file_id == 0


def test_coverage_summary_construction():
    """CoverageSummary stores coverage rates and counts."""
    cs = CoverageSummary(
        line_rate=0.8,
        branch_rate=0.5,
        covered_lines=8,
        total_lines=10,
        covered_branches=2,
        total_branches=4,
    )
    assert cs.line_rate == 0.8
    assert cs.branch_rate == 0.5
    assert cs.covered_lines == 8
    assert cs.total_lines == 10
    assert cs.covered_branches == 2
    assert cs.total_branches == 4


def test_file_summary_construction():
    """FileSummary stores per-file metrics including uncovered_lines."""
    fs = FileSummary(
        file_id=0,
        path="res://player.gd",
        line_rate=0.6,
        branch_rate=0.5,
        covered_lines=3,
        total_lines=5,
        covered_branches=1,
        total_branches=2,
        uncovered_lines=[7, 12],
    )
    assert fs.file_id == 0
    assert fs.path == "res://player.gd"
    assert fs.line_rate == 0.6
    assert fs.uncovered_lines == [7, 12]


def test_report_result_construction():
    """ReportResult stores output info and threshold status."""
    cs = CoverageSummary(
        line_rate=1.0,
        branch_rate=1.0,
        covered_lines=5,
        total_lines=5,
        covered_branches=2,
        total_branches=2,
    )
    rr = ReportResult(
        output_path=Path("/tmp/report"),
        format="html",
        summary=cs,
        file_summaries=[],
        threshold_met=True,
    )
    assert rr.format == "html"
    assert rr.threshold_met is True
    assert rr.summary.line_rate == 1.0


# --- read_coverage_json ---


def test_read_coverage_json_full(tmp_path):
    """read_coverage_json loads a valid full coverage file."""
    fixture = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
    cd = read_coverage_json(fixture)
    assert cd.version == 1
    assert cd.generated_at is not None
    assert len(cd.files) == 2
    assert cd.files[0].file_id == 0
    assert cd.files[0].hits["0"] == 3
    assert cd.files[1].file_id == 1
    assert cd.files[1].hits["2"] == 2


def test_read_coverage_json_partial():
    """read_coverage_json loads a partial coverage file with zero-hit lines."""
    fixture = _FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
    cd = read_coverage_json(fixture)
    assert len(cd.files) == 2
    assert cd.files[0].hits["1"] == 0
    assert cd.files[0].hits["0"] == 3


def test_read_coverage_json_zero():
    """read_coverage_json loads a zero coverage file (all hits = 0)."""
    fixture = _FIXTURES_DIR / "coverage_data" / "zero_coverage.json"
    cd = read_coverage_json(fixture)
    assert len(cd.files) == 2
    for fc in cd.files:
        for count in fc.hits.values():
            assert count == 0


def test_read_coverage_json_string_keys():
    """read_coverage_json stores hits keys as strings (Track 11 format)."""
    fixture = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
    cd = read_coverage_json(fixture)
    for key in cd.files[0].hits:
        assert isinstance(key, str)


def test_read_coverage_json_missing_file(tmp_path):
    """read_coverage_json raises CoveragePlanError for missing file."""
    with pytest.raises(CoveragePlanError):
        read_coverage_json(tmp_path / "nonexistent.json")


def test_read_coverage_json_invalid_json(tmp_path):
    """read_coverage_json raises CoveragePlanError for malformed JSON."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json")
    with pytest.raises(CoveragePlanError):
        read_coverage_json(bad_file)


def test_read_coverage_json_wrong_version(tmp_path):
    """read_coverage_json raises CoveragePlanError on version mismatch."""
    data = {"version": 99, "files": []}
    f = tmp_path / "wrong_ver.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError):
        read_coverage_json(f)


def test_read_coverage_json_no_path_required(tmp_path):
    """read_coverage_json does NOT require a 'path' field in file entries."""
    data = {
        "version": 1,
        "files": [{"file_id": 0, "hits": {"0": 5}}],
    }
    f = tmp_path / "no_path.json"
    f.write_text(json.dumps(data))
    cd = read_coverage_json(f)
    assert cd.files[0].file_id == 0
    assert cd.files[0].hits["0"] == 5


def test_read_coverage_json_missing_files_field(tmp_path):
    """read_coverage_json raises CoveragePlanError when 'files' is missing."""
    data = {"version": 1}
    f = tmp_path / "no_files.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError):
        read_coverage_json(f)


def test_read_coverage_json_missing_version(tmp_path):
    """read_coverage_json raises CoveragePlanError when 'version' is missing."""
    data = {"files": []}
    f = tmp_path / "no_version.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError):
        read_coverage_json(f)


def test_read_coverage_json_generated_at_optional(tmp_path):
    """read_coverage_json does not require 'generated_at' field."""
    data = {
        "version": 1,
        "files": [{"file_id": 0, "hits": {"0": 1}}],
    }
    f = tmp_path / "no_generated_at.json"
    f.write_text(json.dumps(data))
    cd = read_coverage_json(f)
    assert cd.generated_at is None


# --- merge_coverage_data ---


def test_merge_coverage_data_sums_hits(tmp_path):
    """merge_coverage_data sums hit counts for same file_id/line_id."""
    data1 = {
        "version": 1,
        "files": [{"file_id": 0, "hits": {"0": 3, "1": 2}}],
    }
    data2 = {
        "version": 1,
        "files": [{"file_id": 0, "hits": {"0": 5, "1": 1}}],
    }
    f1 = tmp_path / "shard1.json"
    f2 = tmp_path / "shard2.json"
    f1.write_text(json.dumps(data1))
    f2.write_text(json.dumps(data2))

    merged = merge_coverage_data([f1, f2])
    assert len(merged.files) == 1
    assert merged.files[0].hits["0"] == 8
    assert merged.files[0].hits["1"] == 3


def test_merge_coverage_data_multiple_files(tmp_path):
    """merge_coverage_data merges different file_ids."""
    data1 = {
        "version": 1,
        "files": [{"file_id": 0, "hits": {"0": 3}}],
    }
    data2 = {
        "version": 1,
        "files": [{"file_id": 1, "hits": {"0": 5}}],
    }
    f1 = tmp_path / "shard1.json"
    f2 = tmp_path / "shard2.json"
    f1.write_text(json.dumps(data1))
    f2.write_text(json.dumps(data2))

    merged = merge_coverage_data([f1, f2])
    assert len(merged.files) == 2
    file_ids = {fc.file_id for fc in merged.files}
    assert file_ids == {0, 1}


def test_merge_coverage_data_empty_list():
    """merge_coverage_data with empty list returns empty CoverageData."""
    merged = merge_coverage_data([])
    assert merged.files == []
    assert merged.version == 1


def test_merge_coverage_data_single_file(tmp_path):
    """merge_coverage_data with a single file returns equivalent data."""
    data = {
        "version": 1,
        "files": [{"file_id": 0, "hits": {"0": 3, "1": 2}}],
    }
    f = tmp_path / "single.json"
    f.write_text(json.dumps(data))

    merged = merge_coverage_data([f])
    assert len(merged.files) == 1
    assert merged.files[0].hits["0"] == 3
    assert merged.files[0].hits["1"] == 2
