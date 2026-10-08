"""Unit tests for patch coverage computation (``coverage diff --patch``)."""

from pathlib import Path

import pytest

from gd_tools.coverage.patch import (
    PatchCoverageResult,
    PatchFileMetric,
    build_patch_json,
    build_patch_table,
    compute_patch_coverage,
    patch_verdict,
)
from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    PLAN_VERSION,
    FilePlan,
    LinePlan,
)
from gd_tools.coverage.reporter import CoverageData, FileCoverage

pytestmark = pytest.mark.unit


# --- Helpers ---


def _plan() -> CoveragePlan:
    """Two files: player.gd with statements on 5, 6, 10; enemy.gd on 2."""
    return CoveragePlan(
        version=PLAN_VERSION,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://player.gd",
                source_hash="sha256:abc",
                lines=[
                    LinePlan(line=5, id=0, type="statement"),
                    LinePlan(line=6, id=1, type="statement"),
                    LinePlan(line=10, id=2, type="statement"),
                ],
            ),
            FilePlan(
                file_id=1,
                path="res://src/enemy.gd",
                source_hash="sha256:def",
                lines=[LinePlan(line=2, id=0, type="statement")],
            ),
        ],
    )


def _data(hits_by_file: dict[int, dict[str, int]]) -> CoverageData:
    """Build coverage data from per-file-id hit maps."""
    return CoverageData(
        version=1,
        generated_at=None,
        files=[
            FileCoverage(file_id=file_id, hits=hits)
            for file_id, hits in sorted(hits_by_file.items())
        ],
    )


# --- Tests ---


def test_intersect_ranges_with_plan_lines():
    """Only executable plan lines inside changed ranges are counted."""
    data = _data({0: {"0": 0, "1": 3, "2": 0}, 1: {"0": 1}})
    result = compute_patch_coverage(
        _plan(),
        data,
        {Path("player.gd"): [(6, 10)]},
    )

    assert result.files == [
        PatchFileMetric(
            path="player.gd", changed=2, covered=1, uncovered=1, rate=0.5
        )
    ]
    assert result.total == 2
    assert result.covered == 1
    assert result.rate == 0.5


def test_subdir_path_matching_uses_res_prefix():
    """Plan ``res://`` paths match repo-relative changed paths."""
    data = _data({1: {"0": 0}})
    result = compute_patch_coverage(
        _plan(),
        data,
        {Path("src/enemy.gd"): [(2, 2)]},
    )

    assert result.total == 1
    assert result.covered == 0
    assert result.files[0].path == "src/enemy.gd"


def test_changed_file_missing_from_coverage_data_all_uncovered():
    """A planned file absent from coverage data counts as uncovered."""
    result = compute_patch_coverage(
        _plan(),
        _data({}),
        {Path("player.gd"): [(5, 6)]},
    )

    assert result.total == 2
    assert result.covered == 0
    assert result.files[0].uncovered == 2


def test_file_without_changed_plan_lines_excluded():
    """A changed file with no executable plan lines in its ranges is
    excluded from metrics entirely."""
    # Range (1, 4) covers no plan line (plan points are 5, 6, 10).
    result = compute_patch_coverage(
        _plan(),
        _data({0: {"0": 1, "1": 1, "2": 1}}),
        {Path("player.gd"): [(1, 4)]},
    )

    assert result.files == []
    assert result.total == 0
    assert result.rate == 0.0


def test_changed_file_absent_from_plan_excluded():
    """A changed file with no plan entry is excluded (never fails gate)."""
    result = compute_patch_coverage(
        _plan(),
        _data({}),
        {Path("unplanned.gd"): [(1, 20)]},
    )

    assert result.files == []
    assert result.total == 0


def test_totals_aggregate_across_files():
    """Totals sum per-file changed/covered counts; rate is aggregate."""
    data = _data({0: {"0": 0, "1": 3, "2": 3}, 1: {"0": 0}})
    result = compute_patch_coverage(
        _plan(),
        data,
        {
            Path("player.gd"): [(5, 6)],
            Path("src/enemy.gd"): [(1, 2)],
        },
    )

    assert result.total == 3
    assert result.covered == 1
    assert result.rate == pytest.approx(1 / 3)
    assert [f.path for f in result.files] == [
        "player.gd",
        "src/enemy.gd",
    ]


def test_empty_patch_yields_zero_totals():
    """No changed files at all gives empty files and a 0.0 rate."""
    result = compute_patch_coverage(_plan(), _data({0: {"0": 1}}), {})

    assert isinstance(result, PatchCoverageResult)
    assert result.files == []
    assert result.total == 0
    assert result.covered == 0
    assert result.rate == 0.0


# --- Rendering (Phase 3) ---


def _result(**overrides):
    """Build a two-file PatchCoverageResult (1/2 and 2/2 -> 3/4 = 75%)."""
    defaults = dict(
        files=[
            PatchFileMetric(
                path="player.gd", changed=2, covered=1, uncovered=1, rate=0.5
            ),
            PatchFileMetric(
                path="src/enemy.gd", changed=2, covered=2, uncovered=0, rate=1.0
            ),
        ],
        covered=3,
        total=4,
        rate=0.75,
    )
    defaults.update(overrides)
    return PatchCoverageResult(**defaults)


EMPTY_RESULT = PatchCoverageResult(files=[], covered=0, total=0, rate=0.0)


def _table_text(table) -> str:
    """Render a Rich table to plain text with a fixed-width console."""
    from io import StringIO

    from rich.console import Console

    io = StringIO()
    Console(file=io, width=140).print(table)
    return io.getvalue()


def test_build_patch_table_lists_per_file_rows_and_total():
    """The table lists per-file rows with counts, rates, and a total."""
    text = _table_text(build_patch_table(_result(), None))

    assert "player.gd" in text
    assert "src/enemy.gd" in text
    assert "1/2 (50%)" in text
    assert "2/2 (100%)" in text
    assert "TOTAL" in text
    assert "3/4 (75%)" in text


def test_build_patch_table_shows_gate_verdict():
    """The caption carries the gate verdict for the configured threshold."""
    fail_text = _table_text(build_patch_table(_result(), 80.0))
    assert "FAIL" in fail_text

    pass_text = _table_text(
        build_patch_table(
            PatchCoverageResult(
                files=_result().files, covered=4, total=4, rate=1.0
            ),
            80.0,
        )
    )
    assert "PASS" in pass_text

    info_text = _table_text(build_patch_table(_result(), None))
    assert "informational" in info_text.lower()


def test_build_patch_table_empty_patch_notice():
    """An empty patch renders a no-changed-lines notice, not a gate verdict."""
    text = _table_text(build_patch_table(EMPTY_RESULT, 80.0))

    assert "No changed executable lines" in text
    assert "FAIL" not in text


def test_build_patch_json_structure():
    """The JSON payload has per-file entries, totals, threshold, verdict."""
    payload = build_patch_json(_result(), 80.0)

    assert payload["files"] == [
        {
            "path": "player.gd",
            "changed": 2,
            "covered": 1,
            "uncovered": 1,
            "rate": 0.5,
        },
        {
            "path": "src/enemy.gd",
            "changed": 2,
            "covered": 2,
            "uncovered": 0,
            "rate": 1.0,
        },
    ]
    assert payload["totals"] == {"covered": 3, "total": 4, "rate": 0.75}
    assert payload["threshold"] == 80.0
    assert payload["verdict"] == "fail"
    assert payload["empty"] is False


def test_build_patch_json_empty_patch():
    """An empty patch reports empty=True and never a failing verdict."""
    payload = build_patch_json(EMPTY_RESULT, 80.0)

    assert payload["files"] == []
    assert payload["totals"] == {"covered": 0, "total": 0, "rate": 0.0}
    assert payload["empty"] is True
    assert payload["verdict"] == "pass"


def test_patch_verdict_boundary_and_informational():
    """Rate exactly at the threshold passes; no threshold is informational."""
    assert patch_verdict(_result(), 75.0) == "pass"
    assert patch_verdict(_result(), 75.1) == "fail"
    assert patch_verdict(_result(), None) == "informational"
    assert patch_verdict(EMPTY_RESULT, None) == "informational"
    assert patch_verdict(EMPTY_RESULT, 80.0) == "pass"
