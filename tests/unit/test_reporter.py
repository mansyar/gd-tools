"""Unit tests for the coverage reporter module.

Covers data structures (CoverageData, FileCoverage, CoverageSummary,
FileSummary, ReportResult), JSON I/O (read_coverage_json,
merge_coverage_data), and version validation.
"""

import json
from pathlib import Path

import pytest

from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    FilePlan,
    LinePlan,
    read_plan_json,
)
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileCoverage,
    FileSummary,
    ReportResult,
    compute_file_summary,
    compute_summary,
    generate_report,
    merge_coverage_data,
    read_coverage_json,
)
from gd_tools.errors import CoveragePlanError, CoverageThresholdError

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PLAN_FIXTURE = _FIXTURES_DIR / "coverage_plans" / "test_plan.json"
_FULL_COV = _FIXTURES_DIR / "coverage_data" / "full_coverage.json"
_PARTIAL_COV = _FIXTURES_DIR / "coverage_data" / "partial_coverage.json"
_ZERO_COV = _FIXTURES_DIR / "coverage_data" / "zero_coverage.json"


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


def test_read_coverage_json_data_not_dict(tmp_path):
    """read_coverage_json raises CoveragePlanError when top-level is not a dict."""
    f = tmp_path / "list.json"
    f.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(CoveragePlanError, match="JSON object"):
        read_coverage_json(f)


def test_read_coverage_json_files_not_list(tmp_path):
    """read_coverage_json raises CoveragePlanError when 'files' is not a list."""
    data = {"version": 1, "files": "not_a_list"}
    f = tmp_path / "files_not_list.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError, match="must be a list"):
        read_coverage_json(f)


def test_read_coverage_json_file_entry_not_dict(tmp_path):
    """read_coverage_json raises CoveragePlanError when a file entry is not a dict."""
    data = {"version": 1, "files": ["not_a_dict"]}
    f = tmp_path / "entry_not_dict.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError, match="Invalid coverage file entry"):
        read_coverage_json(f)


def test_read_coverage_json_missing_file_id(tmp_path):
    """read_coverage_json raises CoveragePlanError when file_id is missing."""
    data = {"version": 1, "files": [{"hits": {"0": 1}}]}
    f = tmp_path / "no_file_id.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError, match="file_id"):
        read_coverage_json(f)


def test_read_coverage_json_missing_hits(tmp_path):
    """read_coverage_json raises CoveragePlanError when hits is missing."""
    data = {"version": 1, "files": [{"file_id": 0}]}
    f = tmp_path / "no_hits.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError, match="hits"):
        read_coverage_json(f)


def test_read_coverage_json_hits_not_dict(tmp_path):
    """read_coverage_json raises CoveragePlanError when hits is not a dict."""
    data = {"version": 1, "files": [{"file_id": 0, "hits": "not_a_dict"}]}
    f = tmp_path / "hits_not_dict.json"
    f.write_text(json.dumps(data))
    with pytest.raises(CoveragePlanError, match="must be a dict"):
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


# --- Coverage computation (FR-2) ---


def test_compute_file_summary_full_coverage():
    """compute_file_summary returns 100% rates when all lines are hit."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    fs = compute_file_summary(plan.files[0], data.files[0])
    assert fs.line_rate == 1.0
    assert fs.branch_rate == 1.0
    assert fs.covered_lines == 5
    assert fs.total_lines == 5
    assert fs.covered_branches == 2
    assert fs.total_branches == 2
    assert fs.uncovered_lines == []
    assert fs.path == "res://player.gd"


def test_compute_file_summary_partial_coverage():
    """compute_file_summary computes correct rates for partial coverage."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    fs = compute_file_summary(plan.files[0], data.files[0])
    # File 0: 5 lines total (3 statements + 2 branches)
    # Partial hits: {0:3, 1:0, 2:1, 3:0, 4:3} -> 3 covered
    assert fs.covered_lines == 3
    assert fs.total_lines == 5
    assert fs.line_rate == pytest.approx(0.6)
    # Branches: id 2 (hit 1), id 3 (hit 0) -> 1 of 2
    assert fs.covered_branches == 1
    assert fs.total_branches == 2
    assert fs.branch_rate == 0.5


def test_compute_file_summary_zero_coverage():
    """compute_file_summary returns 0% rates when all hits are zero."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    fs = compute_file_summary(plan.files[0], data.files[0])
    assert fs.line_rate == 0.0
    assert fs.branch_rate == 0.0
    assert fs.covered_lines == 0
    assert fs.total_lines == 5
    assert fs.covered_branches == 0
    assert fs.total_branches == 2


def test_compute_file_summary_uncovered_lines():
    """compute_file_summary identifies line numbers with zero hits."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    fs = compute_file_summary(plan.files[0], data.files[0])
    # ids 1 (line 7) and 3 (line 12) have 0 hits
    assert fs.uncovered_lines == [7, 12]


def test_compute_file_summary_if_true_if_false_branches():
    """compute_file_summary handles if_true/if_false branch types."""
    file_plan = FilePlan(
        file_id=0,
        path="res://test.gd",
        source_hash="sha256:test",
        lines=[
            LinePlan(line=5, id=0, type="statement"),
            LinePlan(line=8, id=1, type="branch", branch_type="if_true"),
            LinePlan(line=10, id=2, type="branch", branch_type="if_false"),
        ],
    )
    # Both branches covered
    full_data = FileCoverage(file_id=0, hits={"0": 1, "1": 2, "2": 1})
    fs = compute_file_summary(file_plan, full_data)
    assert fs.branch_rate == 1.0
    assert fs.covered_branches == 2
    assert fs.total_branches == 2
    assert fs.uncovered_lines == []

    # Only if_true covered
    partial_data = FileCoverage(file_id=0, hits={"0": 1, "1": 2, "2": 0})
    fs = compute_file_summary(file_plan, partial_data)
    assert fs.branch_rate == 0.5
    assert fs.covered_branches == 1
    assert fs.uncovered_lines == [10]


def test_compute_file_summary_elif_loop_match_branches():
    """compute_file_summary handles elif_true, loop_body, match_case types."""
    file_plan = FilePlan(
        file_id=0,
        path="res://test.gd",
        source_hash="sha256:test",
        lines=[
            LinePlan(line=3, id=0, type="branch", branch_type="elif_true"),
            LinePlan(line=5, id=1, type="branch", branch_type="loop_body"),
            LinePlan(line=8, id=2, type="branch", branch_type="match_case"),
        ],
    )
    data = FileCoverage(file_id=0, hits={"0": 1, "1": 0, "2": 3})
    fs = compute_file_summary(file_plan, data)
    assert fs.total_branches == 3
    assert fs.covered_branches == 2  # elif_true and match_case covered
    assert fs.branch_rate == pytest.approx(2 / 3)
    # All are branches, so total_lines is also 3
    assert fs.total_lines == 3
    assert fs.covered_lines == 2
    assert fs.uncovered_lines == [5]  # loop_body line


def test_compute_file_summary_uncovered_branches_zero_hits():
    """compute_file_summary collects branch-type lines with zero hits into uncovered_branches."""
    file_plan = FilePlan(
        file_id=0,
        path="res://test.gd",
        source_hash="sha256:test",
        lines=[
            LinePlan(line=5, id=0, type="statement"),
            LinePlan(line=8, id=1, type="branch", branch_type="if_true"),
            LinePlan(line=10, id=2, type="branch", branch_type="if_false"),
        ],
    )
    # if_true covered, if_false not
    data = FileCoverage(file_id=0, hits={"0": 1, "1": 2, "2": 0})
    fs = compute_file_summary(file_plan, data)
    assert fs.uncovered_branches == [10]


def test_compute_file_summary_uncovered_branches_excludes_statements():
    """compute_file_summary excludes non-branch uncovered lines from uncovered_branches."""
    file_plan = FilePlan(
        file_id=0,
        path="res://test.gd",
        source_hash="sha256:test",
        lines=[
            LinePlan(line=5, id=0, type="statement"),
            LinePlan(line=8, id=1, type="branch", branch_type="if_true"),
            LinePlan(line=12, id=2, type="statement"),
        ],
    )
    # statement at line 5 uncovered, branch at line 8 covered, statement at line 12 uncovered
    data = FileCoverage(file_id=0, hits={"0": 0, "1": 1, "2": 0})
    fs = compute_file_summary(file_plan, data)
    assert fs.uncovered_lines == [5, 12]
    assert fs.uncovered_branches == []  # the only branch is covered


def test_compute_file_summary_uncovered_branches_all_covered():
    """compute_file_summary returns empty uncovered_branches when all branches hit."""
    file_plan = FilePlan(
        file_id=0,
        path="res://test.gd",
        source_hash="sha256:test",
        lines=[
            LinePlan(line=3, id=0, type="branch", branch_type="if_true"),
            LinePlan(line=5, id=1, type="branch", branch_type="if_false"),
        ],
    )
    data = FileCoverage(file_id=0, hits={"0": 1, "1": 1})
    fs = compute_file_summary(file_plan, data)
    assert fs.uncovered_branches == []


def test_compute_file_summary_uncovered_branches_all_uncovered():
    """compute_file_summary returns all branch line numbers when none are hit."""
    file_plan = FilePlan(
        file_id=0,
        path="res://test.gd",
        source_hash="sha256:test",
        lines=[
            LinePlan(line=3, id=0, type="branch", branch_type="if_true"),
            LinePlan(line=5, id=1, type="branch", branch_type="loop_body"),
            LinePlan(line=8, id=2, type="branch", branch_type="match_case"),
        ],
    )
    data = FileCoverage(file_id=0, hits={"0": 0, "1": 0, "2": 0})
    fs = compute_file_summary(file_plan, data)
    assert fs.uncovered_branches == [3, 5, 8]


def test_compute_summary_aggregates_multiple_files():
    """compute_summary aggregates coverage across all files."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    summary = compute_summary(plan, data)
    # File 0: 5 lines, 2 branches; File 1: 3 lines, 1 branch
    assert summary.total_lines == 8
    assert summary.covered_lines == 8
    assert summary.line_rate == 1.0
    assert summary.total_branches == 3
    assert summary.covered_branches == 3
    assert summary.branch_rate == 1.0


def test_compute_summary_includes_zero_coverage_files():
    """compute_summary includes files with zero coverage in totals."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    summary = compute_summary(plan, data)
    # Both files counted even though all hits are 0
    assert summary.total_lines == 8
    assert summary.covered_lines == 0
    assert summary.line_rate == 0.0
    assert summary.total_branches == 3
    assert summary.covered_branches == 0
    assert summary.branch_rate == 0.0


def test_compute_summary_missing_file_in_coverage_data():
    """compute_summary treats files missing from coverage data as 0 hits."""
    plan = read_plan_json(_PLAN_FIXTURE)
    # Coverage data only has file 0, not file 1
    data = CoverageData(
        version=1,
        generated_at="2025-01-01",
        files=[
            FileCoverage(
                file_id=0, hits={"0": 3, "1": 2, "2": 1, "3": 1, "4": 3}
            ),
        ],
    )
    summary = compute_summary(plan, data)
    # File 0: all 5 lines covered; File 1: 3 lines, 0 covered
    assert summary.total_lines == 8
    assert summary.covered_lines == 5
    assert summary.line_rate == pytest.approx(5 / 8)
    assert summary.total_branches == 3
    assert summary.covered_branches == 2
    assert summary.branch_rate == pytest.approx(2 / 3)


# --- Report dispatch and threshold (FR-3) ---


def test_generate_report_text_format(tmp_path):
    """generate_report with format=text returns ReportResult with correct format."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_report(plan, data, tmp_path, format="text")
    assert result.format == "text"
    assert result.output_path.exists()


def test_generate_report_lcov_format(tmp_path):
    """generate_report with format=lcov dispatches to LCOV reporter."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_report(plan, data, tmp_path, format="lcov")
    assert result.format == "lcov"
    assert result.output_path.exists()


def test_generate_report_cobertura_format(tmp_path):
    """generate_report with format=cobertura dispatches to Cobertura reporter."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_report(plan, data, tmp_path, format="cobertura")
    assert result.format == "cobertura"
    assert result.output_path.exists()


def test_generate_report_html_format(tmp_path):
    """generate_report with format=html dispatches to HTML reporter."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_report(plan, data, tmp_path, format="html")
    assert result.format == "html"
    assert result.output_path.exists()


def test_generate_report_unsupported_format(tmp_path):
    """generate_report with unsupported format raises CoveragePlanError."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    with pytest.raises(CoveragePlanError):
        generate_report(plan, data, tmp_path, format="xml")


def test_generate_report_threshold_below_raises(tmp_path):
    """generate_report raises CoverageThresholdError when coverage is below threshold."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_PARTIAL_COV)
    # partial_coverage: line_rate = 5/8 = 0.625, below 0.80
    with pytest.raises(CoverageThresholdError) as exc_info:
        generate_report(plan, data, tmp_path, format="text", min_threshold=0.80)

    # Verify report_result is attached so callers can display coverage
    # without recomputation (FR-2 / NFR-2).
    assert exc_info.value.report_result is not None
    assert exc_info.value.report_result.summary is not None


def test_generate_report_threshold_at_minimum_no_raise(tmp_path):
    """generate_report does NOT raise when line_rate equals threshold."""
    # 5 lines, 4 covered -> line_rate = 0.80, threshold = 0.80
    plan = CoveragePlan(
        version=1,
        generated_by="test",
        files=[
            FilePlan(
                file_id=0,
                path="res://test.gd",
                source_hash="sha256:test",
                lines=[
                    LinePlan(line=1, id=0, type="statement"),
                    LinePlan(line=2, id=1, type="statement"),
                    LinePlan(line=3, id=2, type="statement"),
                    LinePlan(line=4, id=3, type="statement"),
                    LinePlan(line=5, id=4, type="statement"),
                ],
            ),
        ],
    )
    data = CoverageData(
        version=1,
        files=[
            FileCoverage(
                file_id=0, hits={"0": 1, "1": 1, "2": 1, "3": 1, "4": 0}
            ),
        ],
    )
    result = generate_report(
        plan, data, tmp_path, format="text", min_threshold=0.80
    )
    assert result.threshold_met is True


def test_generate_report_no_threshold_never_raises(tmp_path):
    """generate_report with min_threshold=None never raises threshold error."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_ZERO_COV)
    # zero_coverage: line_rate = 0.0, but no threshold -> no raise
    result = generate_report(plan, data, tmp_path, format="text")
    assert result.threshold_met is True


def test_generate_report_result_fields(tmp_path):
    """generate_report returns ReportResult with correct summary, file_summaries, and threshold_met."""
    plan = read_plan_json(_PLAN_FIXTURE)
    data = read_coverage_json(_FULL_COV)
    result = generate_report(plan, data, tmp_path, format="text")

    assert isinstance(result.summary, CoverageSummary)
    assert result.summary.line_rate == 1.0
    assert result.summary.covered_lines == 8
    assert result.summary.total_lines == 8

    assert len(result.file_summaries) == 2
    assert isinstance(result.file_summaries[0], FileSummary)
    assert result.file_summaries[0].file_id == 0
    assert result.file_summaries[0].path == "res://player.gd"

    assert result.threshold_met is True


# --- Line range formatting (Phase 2) ---


def test_format_line_ranges_consecutive():
    """_format_line_ranges groups consecutive numbers into ranges."""
    from gd_tools.coverage.reporter import _format_line_ranges

    assert _format_line_ranges([1, 2, 3, 5, 6]) == "1-3, 5-6"


def test_format_line_ranges_empty():
    """_format_line_ranges returns empty string for empty list."""
    from gd_tools.coverage.reporter import _format_line_ranges

    assert _format_line_ranges([]) == ""


def test_format_line_ranges_single():
    """_format_line_ranges returns single number without range syntax."""
    from gd_tools.coverage.reporter import _format_line_ranges

    assert _format_line_ranges([4]) == "4"


def test_format_line_ranges_non_consecutive():
    """_format_line_ranges handles mix of ranges and singles."""
    from gd_tools.coverage.reporter import _format_line_ranges

    assert _format_line_ranges([10, 11, 15]) == "10-11, 15"


# --- Uncovered panel rendering (Phase 2) ---


def test_render_uncovered_panels_shows_file_path_and_lines():
    """_render_uncovered_panels includes file path as title and uncovered line ranges."""
    from io import StringIO

    from rich.console import Console

    from gd_tools.coverage.reporter import _render_uncovered_panels

    file_summaries = [
        FileSummary(
            file_id=0,
            path="res://player.gd",
            line_rate=0.6,
            branch_rate=0.5,
            covered_lines=3,
            total_lines=5,
            covered_branches=1,
            total_branches=2,
            uncovered_lines=[7, 12, 15, 16],
            uncovered_branches=[12],
        ),
    ]
    plan = CoveragePlan(
        version=1,
        generated_by="test",
        files=[
            FilePlan(
                file_id=0,
                path="res://player.gd",
                source_hash="sha256:test",
                lines=[
                    LinePlan(line=5, id=0, type="statement"),
                    LinePlan(line=7, id=1, type="statement"),
                    LinePlan(line=10, id=2, type="statement"),
                    LinePlan(
                        line=12, id=3, type="branch", branch_type="if_true"
                    ),
                    LinePlan(line=15, id=4, type="statement"),
                    LinePlan(line=16, id=5, type="statement"),
                ],
            ),
        ],
    )

    panels = _render_uncovered_panels(file_summaries, plan)
    assert panels is not None

    console = Console(file=StringIO(), width=120, force_terminal=False)
    console.print(panels)
    output = console.file.getvalue()

    assert "res://player.gd" in output
    assert "7" in output
    assert "15-16" in output
    assert "12 (if)" in output


def test_render_uncovered_panels_omits_full_coverage_files():
    """_render_uncovered_panels skips files with no uncovered lines or branches."""
    from gd_tools.coverage.reporter import _render_uncovered_panels

    file_summaries = [
        FileSummary(
            file_id=0,
            path="res://full.gd",
            line_rate=1.0,
            branch_rate=1.0,
            covered_lines=5,
            total_lines=5,
            covered_branches=2,
            total_branches=2,
            uncovered_lines=[],
            uncovered_branches=[],
        ),
    ]
    plan = CoveragePlan(
        version=1,
        generated_by="test",
        files=[
            FilePlan(
                file_id=0,
                path="res://full.gd",
                source_hash="sha256:test",
                lines=[
                    LinePlan(line=5, id=0, type="statement"),
                    LinePlan(
                        line=8, id=1, type="branch", branch_type="if_true"
                    ),
                ],
            ),
        ],
    )

    panels = _render_uncovered_panels(file_summaries, plan)
    assert panels is None


def test_render_uncovered_panels_branch_type_annotations():
    """_render_uncovered_panels annotates branches with their type."""
    from io import StringIO

    from rich.console import Console

    from gd_tools.coverage.reporter import _render_uncovered_panels

    file_summaries = [
        FileSummary(
            file_id=0,
            path="res://test.gd",
            line_rate=0.0,
            branch_rate=0.0,
            covered_lines=0,
            total_lines=3,
            covered_branches=0,
            total_branches=3,
            uncovered_lines=[5, 8, 10],
            uncovered_branches=[5, 8, 10],
        ),
    ]
    plan = CoveragePlan(
        version=1,
        generated_by="test",
        files=[
            FilePlan(
                file_id=0,
                path="res://test.gd",
                source_hash="sha256:test",
                lines=[
                    LinePlan(
                        line=5, id=0, type="branch", branch_type="if_true"
                    ),
                    LinePlan(
                        line=8, id=1, type="branch", branch_type="loop_body"
                    ),
                    LinePlan(
                        line=10, id=2, type="branch", branch_type="match_case"
                    ),
                ],
            ),
        ],
    )

    panels = _render_uncovered_panels(file_summaries, plan)
    assert panels is not None

    console = Console(file=StringIO(), width=120, force_terminal=False)
    console.print(panels)
    output = console.file.getvalue()

    assert "5 (if)" in output
    assert "8 (loop)" in output
    assert "10 (match)" in output


def test_render_uncovered_panels_only_lines_no_branches():
    """_render_uncovered_panels shows only uncovered lines when no branches are uncovered."""
    from io import StringIO

    from rich.console import Console

    from gd_tools.coverage.reporter import _render_uncovered_panels

    file_summaries = [
        FileSummary(
            file_id=0,
            path="res://stmts.gd",
            line_rate=0.5,
            branch_rate=1.0,
            covered_lines=2,
            total_lines=4,
            covered_branches=1,
            total_branches=1,
            uncovered_lines=[3, 7],
            uncovered_branches=[],
        ),
    ]
    plan = CoveragePlan(
        version=1,
        generated_by="test",
        files=[
            FilePlan(
                file_id=0,
                path="res://stmts.gd",
                source_hash="sha256:test",
                lines=[
                    LinePlan(line=1, id=0, type="statement"),
                    LinePlan(line=3, id=1, type="statement"),
                    LinePlan(
                        line=5, id=2, type="branch", branch_type="if_true"
                    ),
                    LinePlan(line=7, id=3, type="statement"),
                ],
            ),
        ],
    )

    panels = _render_uncovered_panels(file_summaries, plan)
    assert panels is not None

    console = Console(file=StringIO(), width=120, force_terminal=False)
    console.print(panels)
    output = console.file.getvalue()

    assert "res://stmts.gd" in output
    assert "3" in output
    assert "7" in output
    assert "Uncovered branches" not in output
