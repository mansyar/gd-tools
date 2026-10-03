"""Unit tests for the coverage diff reporter module.

Covers the baseline snapshot contract: a self-contained document nesting
the existing ``plan.json`` and ``coverage.json`` payloads plus an advisory
``baseline_meta`` block, and its save/load behavior as defined in the
Coverage Diff track specification (FR-1).
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.coverage.diff_reporter import (
    BaselineMeta,
    BaselineSnapshot,
    DiffResult,
    FileDiff,
    build_diff_detail,
    build_diff_json,
    build_diff_table,
    compute_diff,
    load_baseline,
    save_baseline,
)
from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    FilePlan,
    LinePlan,
)
from gd_tools.coverage.reporter import CoverageData, FileCoverage
from gd_tools.errors import CoveragePlanError

pytestmark = pytest.mark.unit


# --- Helpers ---


def _make_plan() -> CoveragePlan:
    """Build a small two-line plan fixture."""
    return CoveragePlan(
        version=4,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://player.gd",
                source_hash="sha256:abc123",
                lines=[
                    LinePlan(line=5, id=0, type="statement"),
                    LinePlan(
                        line=10, id=1, type="branch", branch_type="if_true"
                    ),
                ],
            )
        ],
    )


def _make_data(covered: bool = True) -> CoverageData:
    """Build a small coverage data fixture for the plan above."""
    hits = {"0": 3, "1": 1} if covered else {"0": 0, "1": 0}
    return CoverageData(
        version=1,
        generated_at="2026-09-28T00:00:00Z",
        files=[FileCoverage(file_id=0, hits=hits)],
    )


@pytest.fixture
def coverage_dir(tmp_path: Path) -> Path:
    """Write plan.json and coverage.json into a temporary coverage dir."""
    directory = tmp_path / ".gd-tools" / "coverage"
    directory.mkdir(parents=True)
    from gd_tools.coverage.plan_generator import write_plan_json
    from gd_tools.coverage.reporter import write_coverage_json

    write_plan_json(_make_plan(), str(directory / "plan.json"))
    write_coverage_json(_make_data(), str(directory / "coverage.json"))
    return directory


def _mock_git_process(stdout: str) -> MagicMock:
    """Build a fake completed-process result for git metadata calls."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = stdout
    return result


# --- save_baseline ---


def test_save_baseline_writes_self_contained_document(
    coverage_dir: Path, tmp_path: Path
):
    """The baseline nests the plan and data payloads plus baseline_meta."""
    baseline_path = tmp_path / "baseline.json"
    save_baseline(
        plan_path=coverage_dir / "plan.json",
        data_path=coverage_dir / "coverage.json",
        baseline_path=baseline_path,
    )

    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert "baseline_meta" in document
    assert "plan" in document
    assert "data" in document

    # Nested payloads are the existing formats, verbatim in structure.
    assert document["plan"]["version"] == 4
    assert document["plan"]["files"][0]["path"] == "res://player.gd"
    assert document["data"]["version"] == 1
    assert document["data"]["files"][0]["hits"] == {"0": 3, "1": 1}


def test_save_baseline_stamps_utc_saved_at(coverage_dir: Path, tmp_path: Path):
    """baseline_meta.saved_at is a timezone-aware ISO timestamp."""
    baseline_path = tmp_path / "baseline.json"
    meta = save_baseline(
        plan_path=coverage_dir / "plan.json",
        data_path=coverage_dir / "coverage.json",
        baseline_path=baseline_path,
    )

    parsed = datetime.fromisoformat(meta.saved_at)
    assert parsed.tzinfo is not None


def test_save_baseline_stamps_git_metadata(coverage_dir: Path, tmp_path: Path):
    """Git branch and commit are stamped when git succeeds."""
    responses = [_mock_git_process("main\n"), _mock_git_process("abc1234\n")]
    baseline_path = tmp_path / "baseline.json"
    with patch(
        "gd_tools.coverage.diff_reporter.subprocess.run",
        side_effect=responses,
    ):
        meta = save_baseline(
            plan_path=coverage_dir / "plan.json",
            data_path=coverage_dir / "coverage.json",
            baseline_path=baseline_path,
        )

    assert meta.git_branch == "main"
    assert meta.git_commit == "abc1234"


def test_save_baseline_git_failure_is_not_fatal(
    coverage_dir: Path, tmp_path: Path
):
    """Git detection failure never blocks saving the baseline."""
    baseline_path = tmp_path / "baseline.json"
    with patch(
        "gd_tools.coverage.diff_reporter.subprocess.run",
        side_effect=FileNotFoundError("git not found"),
    ):
        meta = save_baseline(
            plan_path=coverage_dir / "plan.json",
            data_path=coverage_dir / "coverage.json",
            baseline_path=baseline_path,
        )

    assert meta.git_branch is None
    assert meta.git_commit is None
    assert baseline_path.exists()


def test_save_baseline_missing_coverage_data_raises(
    tmp_path: Path,
):
    """A missing coverage data file raises the exit-2 error class."""
    baseline_path = tmp_path / "baseline.json"
    with pytest.raises(CoveragePlanError):
        save_baseline(
            plan_path=tmp_path / "plan.json",
            data_path=tmp_path / "coverage.json",
            baseline_path=baseline_path,
        )
    assert not baseline_path.exists()


def test_save_baseline_missing_plan_raises(tmp_path: Path):
    """A missing plan file raises the exit-2 error class."""
    baseline_path = tmp_path / "baseline.json"
    data_path = tmp_path / "coverage.json"
    from gd_tools.coverage.reporter import write_coverage_json

    write_coverage_json(_make_data(), str(data_path))
    with pytest.raises(CoveragePlanError):
        save_baseline(
            plan_path=tmp_path / "plan.json",
            data_path=data_path,
            baseline_path=baseline_path,
        )
    assert not baseline_path.exists()


def test_save_baseline_overwrites_previous(coverage_dir: Path, tmp_path: Path):
    """Re-saving replaces the previous baseline document entirely."""
    baseline_path = tmp_path / "baseline.json"
    save_baseline(
        plan_path=coverage_dir / "plan.json",
        data_path=coverage_dir / "coverage.json",
        baseline_path=baseline_path,
    )

    from gd_tools.coverage.reporter import write_coverage_json

    write_coverage_json(
        _make_data(covered=False), str(coverage_dir / "coverage.json")
    )
    save_baseline(
        plan_path=coverage_dir / "plan.json",
        data_path=coverage_dir / "coverage.json",
        baseline_path=baseline_path,
    )

    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert document["data"]["files"][0]["hits"] == {"0": 0, "1": 0}


# --- load_baseline ---


def test_load_baseline_round_trips(coverage_dir: Path, tmp_path: Path):
    """A saved baseline loads back into plan, data, and metadata objects."""
    baseline_path = tmp_path / "baseline.json"
    save_baseline(
        plan_path=coverage_dir / "plan.json",
        data_path=coverage_dir / "coverage.json",
        baseline_path=baseline_path,
    )

    snapshot = load_baseline(baseline_path)
    assert isinstance(snapshot, BaselineSnapshot)
    assert snapshot.plan.files[0].path == "res://player.gd"
    assert snapshot.plan.files[0].lines[1].type == "branch"
    assert snapshot.data.files[0].hits == {"0": 3, "1": 1}
    assert isinstance(snapshot.meta, BaselineMeta)
    assert snapshot.meta.saved_at


def test_load_baseline_missing_file_raises(tmp_path: Path):
    """A missing baseline file raises the exit-2 error class."""
    with pytest.raises(CoveragePlanError):
        load_baseline(tmp_path / "missing.json")


def test_load_baseline_invalid_json_raises(tmp_path: Path):
    """Invalid JSON in the baseline raises the exit-2 error class."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CoveragePlanError):
        load_baseline(baseline_path)


def test_load_baseline_rejects_missing_plan_payload(tmp_path: Path):
    """A baseline without a 'plan' payload is rejected."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps({"version": 1, "baseline_meta": {}, "data": {}}),
        encoding="utf-8",
    )
    with pytest.raises(CoveragePlanError):
        load_baseline(baseline_path)


def test_load_baseline_rejects_missing_data_payload(tmp_path: Path):
    """A baseline without a 'data' payload is rejected."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps({"version": 1, "baseline_meta": {}, "plan": {}}),
        encoding="utf-8",
    )
    with pytest.raises(CoveragePlanError):
        load_baseline(baseline_path)


def test_load_baseline_rejects_malformed_nested_data(tmp_path: Path):
    """A baseline whose nested payloads fail loader validation is rejected."""
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "version": 1,
                "baseline_meta": {},
                "plan": {"version": 99, "files": []},
                "data": {"version": 1, "files": []},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CoveragePlanError):
        load_baseline(baseline_path)


# --- compute_diff: helpers ---


def _make_file_plan(
    file_id: int,
    path: str,
    statements: int = 2,
    branches: int = 0,
) -> FilePlan:
    """Build a FilePlan with sequential statement and branch lines."""
    lines = [
        LinePlan(line=i + 1, id=i, type="statement") for i in range(statements)
    ]
    for j in range(branches):
        lines.append(
            LinePlan(
                line=statements + j + 1,
                id=statements + j,
                type="branch",
                branch_type="if_true",
            )
        )
    return FilePlan(
        file_id=file_id,
        path=path,
        source_hash=f"sha256:{file_id:03d}",
        lines=lines,
    )


def _make_file_data(
    file_id: int,
    covered_ids: list[int],
    total_ids: int,
) -> FileCoverage:
    """Build FileCoverage where only *covered_ids* carry hits."""
    hits = {str(i): (1 if i in covered_ids else 0) for i in range(total_ids)}
    return FileCoverage(file_id=file_id, hits=hits)


def _make_snapshot(
    file_plans: list[FilePlan],
    file_datas: list[FileCoverage],
) -> BaselineSnapshot:
    """Build a BaselineSnapshot from matching file plans and data."""
    return BaselineSnapshot(
        plan=CoveragePlan(version=4, generated_by="gd-tools", files=file_plans),
        data=CoverageData(version=1, files=file_datas),
        meta=BaselineMeta(),
    )


def _find_file_diff(result: DiffResult, path: str) -> FileDiff:
    """Return the FileDiff entry for *path* from a diff result."""
    for fd in result.files:
        if fd.path == path:
            return fd
    raise AssertionError(f"no diff entry for {path}")


# --- compute_diff ---


def test_compute_diff_improved_file():
    """A file with more coverage in head is classified as improved."""
    base = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2, branches=1)],
        [_make_file_data(0, [0], 3)],
    )
    head = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2, branches=1)],
        [_make_file_data(0, [0, 1, 2], 3)],
    )
    result = compute_diff(base, head)
    fd = _find_file_diff(result, "res://a.gd")
    assert fd.classification == "improved"
    assert fd.covered_line_delta == 2
    assert fd.line_rate_delta == pytest.approx(2 / 3)
    assert fd.head_line_rate == pytest.approx(1.0)
    assert fd.base_line_rate == pytest.approx(1 / 3)


def test_compute_diff_regressed_file_reports_newly_uncovered():
    """A regressed file lists lines covered in base but uncovered in head."""
    base = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2, branches=1)],
        [_make_file_data(0, [0, 1, 2], 3)],
    )
    head = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2, branches=1)],
        [_make_file_data(0, [0], 3)],
    )
    result = compute_diff(base, head)
    fd = _find_file_diff(result, "res://a.gd")
    assert fd.classification == "regressed"
    assert fd.newly_uncovered_lines == [2, 3]


def test_compute_diff_unchanged_when_identical():
    """Identical snapshots classify as unchanged with zero deltas."""
    snapshot = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2, branches=1)],
        [_make_file_data(0, [0, 1], 3)],
    )
    result = compute_diff(snapshot, snapshot)
    fd = _find_file_diff(result, "res://a.gd")
    assert fd.classification == "unchanged"
    assert fd.covered_line_delta == 0
    assert fd.line_rate_delta == 0.0
    assert fd.covered_branch_delta == 0
    assert fd.newly_uncovered_lines == []


def test_compute_diff_new_and_removed_files_sorted():
    """Head-only files are new, base-only removed; output sorted by path."""
    base = _make_snapshot(
        [
            _make_file_plan(0, "res://b.gd", statements=2),
            _make_file_plan(1, "res://c.gd", statements=2),
        ],
        [
            _make_file_data(0, [0, 1], 2),
            _make_file_data(1, [0, 1], 2),
        ],
    )
    head = _make_snapshot(
        [
            _make_file_plan(0, "res://a.gd", statements=2),
            _make_file_plan(1, "res://b.gd", statements=2),
        ],
        [
            _make_file_data(0, [0, 1], 2),
            _make_file_data(1, [0, 1], 2),
        ],
    )
    result = compute_diff(base, head)
    assert [fd.path for fd in result.files] == [
        "res://a.gd",
        "res://b.gd",
        "res://c.gd",
    ]
    new_fd = _find_file_diff(result, "res://a.gd")
    assert new_fd.classification == "new"
    assert new_fd.base_line_rate is None
    assert new_fd.head_line_rate == pytest.approx(1.0)
    removed_fd = _find_file_diff(result, "res://c.gd")
    assert removed_fd.classification == "removed"
    assert removed_fd.head_line_rate is None
    assert removed_fd.base_line_rate == pytest.approx(1.0)


def test_compute_diff_matches_by_path_not_file_id():
    """Files are matched by res:// path even when file_ids differ."""
    base = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2)],
        [_make_file_data(0, [0], 2)],
    )
    head = _make_snapshot(
        [_make_file_plan(7, "res://a.gd", statements=2)],
        [_make_file_data(7, [0, 1], 2)],
    )
    result = compute_diff(base, head)
    assert len(result.files) == 1
    fd = result.files[0]
    assert fd.classification == "improved"
    assert fd.base_covered_lines == 1
    assert fd.head_covered_lines == 2


def test_compute_diff_regression_is_rate_based():
    """A rate decrease is a regression even when covered counts increase."""
    base = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=2)],
        [_make_file_data(0, [0, 1], 2)],
    )
    head = _make_snapshot(
        [_make_file_plan(0, "res://a.gd", statements=4)],
        [_make_file_data(0, [0, 1, 2], 4)],
    )
    result = compute_diff(base, head)
    fd = _find_file_diff(result, "res://a.gd")
    assert fd.classification == "regressed"
    assert fd.covered_line_delta == 1
    assert fd.line_rate_delta == pytest.approx(-0.25)
    assert result.has_regression


def test_compute_diff_totals_aggregate_each_side():
    """DiffResult carries overall summaries for base and head."""
    base = _make_snapshot(
        [
            _make_file_plan(0, "res://a.gd", statements=2),
            _make_file_plan(1, "res://b.gd", statements=2),
        ],
        [
            _make_file_data(0, [0, 1], 2),
            _make_file_data(1, [0], 2),
        ],
    )
    head = _make_snapshot(
        [
            _make_file_plan(0, "res://a.gd", statements=2),
            _make_file_plan(1, "res://b.gd", statements=2),
        ],
        [
            _make_file_data(0, [0, 1], 2),
            _make_file_data(1, [0, 1], 2),
        ],
    )
    result = compute_diff(base, head)
    assert result.base_summary.covered_lines == 3
    assert result.base_summary.total_lines == 4
    assert result.head_summary.covered_lines == 4
    assert result.head_summary.total_lines == 4
    assert result.head_summary.line_rate == pytest.approx(1.0)


def test_compute_diff_has_regression_false_without_regression():
    """has_regression is False for improvements, new and removed files only."""
    base = _make_snapshot(
        [
            _make_file_plan(0, "res://a.gd", statements=2),
            _make_file_plan(1, "res://gone.gd", statements=2),
        ],
        [
            _make_file_data(0, [0], 2),
            _make_file_data(1, [0, 1], 2),
        ],
    )
    head = _make_snapshot(
        [
            _make_file_plan(0, "res://a.gd", statements=2),
            _make_file_plan(1, "res://fresh.gd", statements=2),
        ],
        [
            _make_file_data(0, [0, 1], 2),
            _make_file_data(1, [0, 1], 2),
        ],
    )
    result = compute_diff(base, head)
    assert not result.has_regression


def test_compute_diff_zero_executable_lines_is_unchanged():
    """A file with no executable lines on both sides never divides by zero."""
    base = _make_snapshot(
        [_make_file_plan(0, "res://empty.gd", statements=0)],
        [_make_file_data(0, [], 0)],
    )
    head = _make_snapshot(
        [_make_file_plan(0, "res://empty.gd", statements=0)],
        [_make_file_data(0, [], 0)],
    )
    result = compute_diff(base, head)
    fd = _find_file_diff(result, "res://empty.gd")
    assert fd.classification == "unchanged"
    assert fd.head_line_rate == 0.0
    assert not result.has_regression


# ---------------------------------------------------------------------------
# Rendering: build_diff_table / build_diff_detail / build_diff_json
# ---------------------------------------------------------------------------


def _mixed_diff() -> DiffResult:
    """Build a diff containing improved, regressed, new, and removed files."""
    base = _make_snapshot(
        [
            _make_file_plan(0, "res://improved.gd", statements=4),
            _make_file_plan(1, "res://regressed.gd", statements=4),
            _make_file_plan(2, "res://gone.gd", statements=2),
        ],
        [
            _make_file_data(0, [0, 1], 4),
            _make_file_data(1, [0, 1, 2, 3], 4),
            _make_file_data(2, [0, 1], 2),
        ],
    )
    head = _make_snapshot(
        [
            _make_file_plan(5, "res://improved.gd", statements=4),
            _make_file_plan(6, "res://regressed.gd", statements=4),
            _make_file_plan(7, "res://brand_new.gd", statements=3),
        ],
        [
            _make_file_data(5, [0, 1, 2, 3], 4),
            _make_file_data(6, [0, 1], 4),
            _make_file_data(7, [0, 1], 3),
        ],
    )
    return compute_diff(base, head)


def _table_text(table) -> str:
    """Render a Rich table to plain text with a fixed-width console."""
    from io import StringIO

    from rich.console import Console

    io = StringIO()
    Console(file=io, width=140).print(table)
    return io.getvalue()


def test_build_diff_table_lists_per_file_rows_and_total():
    """The table lists per-file rows with counts, rates, change, and a total."""
    text = _table_text(build_diff_table(_mixed_diff(), BaselineMeta()))
    # Per-file rows show base/head counts and rates.
    assert "res://improved.gd" in text
    assert "res://regressed.gd" in text
    assert "2/4 (50%)" in text
    assert "4/4 (100%)" in text
    # Changes are rendered as signed deltas.
    assert "+2 lines" in text
    assert "-2 lines" in text
    # New and removed files are labeled, not confused with deltas.
    assert "new" in text
    assert "removed" in text
    # A total row aggregates both sides.
    assert "TOTAL" in text


def test_build_diff_table_shows_baseline_metadata_in_title():
    """The table title carries the baseline's advisory metadata when present."""
    meta = BaselineMeta(
        saved_at="2026-09-28T00:00:00+00:00",
        git_branch="main",
        git_commit="abc1234",
    )
    text = _table_text(build_diff_table(_mixed_diff(), meta))
    assert "main" in text
    assert "abc1234" in text


def test_build_diff_table_renders_without_metadata():
    """An empty BaselineMeta still renders a usable table."""
    text = _table_text(build_diff_table(_mixed_diff(), BaselineMeta()))
    assert "res://improved.gd" in text
    assert "TOTAL" in text


def test_build_diff_detail_lists_newly_uncovered_for_regressed_only():
    """Detail lines name newly-uncovered lines for regressed files only."""
    lines = build_diff_detail(_mixed_diff())
    assert len(lines) == 1
    assert lines[0] == ("res://regressed.gd: newly uncovered lines 3, 4")


def test_build_diff_json_structure():
    """The JSON payload covers files, totals, regression flag, metadata."""
    meta = BaselineMeta(
        saved_at="2026-09-28T00:00:00+00:00",
        git_branch="main",
        git_commit="abc1234",
    )
    payload = build_diff_json(_mixed_diff(), meta)

    assert payload["has_regression"] is True
    assert payload["baseline_meta"]["git_branch"] == "main"
    assert payload["baseline_meta"]["git_commit"] == "abc1234"

    paths = [f["path"] for f in payload["files"]]
    assert paths == sorted(paths)

    new_entry = next(
        f for f in payload["files"] if f["path"] == "res://brand_new.gd"
    )
    assert new_entry["classification"] == "new"
    assert new_entry["base"] is None
    assert new_entry["head"]["covered_lines"] == 2

    removed_entry = next(
        f for f in payload["files"] if f["path"] == "res://gone.gd"
    )
    assert removed_entry["classification"] == "removed"
    assert removed_entry["head"] is None

    regressed_entry = next(
        f for f in payload["files"] if f["path"] == "res://regressed.gd"
    )
    assert regressed_entry["classification"] == "regressed"
    assert regressed_entry["newly_uncovered_lines"] == [3, 4]

    assert payload["totals"]["base"]["covered_lines"] == 8
    assert payload["totals"]["head"]["covered_lines"] == 8
    assert payload["totals"]["head"]["total_lines"] == 11


def test_build_diff_json_is_deterministic():
    """Two serializations of the same diff produce identical JSON."""
    import json

    meta = BaselineMeta(saved_at="2026-09-28T00:00:00+00:00")
    first = json.dumps(build_diff_json(_mixed_diff(), meta), indent=2)
    second = json.dumps(build_diff_json(_mixed_diff(), meta), indent=2)
    assert first == second
