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
        version=1,
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
    assert document["plan"]["version"] == 1
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
