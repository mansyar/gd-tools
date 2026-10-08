"""Unit tests for patch coverage computation (``coverage diff --patch``)."""

from pathlib import Path

import pytest

from gd_tools.coverage.patch import (
    PatchCoverageResult,
    PatchFileMetric,
    compute_patch_coverage,
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
