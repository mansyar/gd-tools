"""Unit tests for the ``gd-tools clean`` core module (``gd_tools.clean``).

Covers the ``run_clean`` contract from the track spec:
- per-flag targets (coverage / artifacts / baselines / cache),
- ``--all`` removing everything,
- missing targets reported as "nothing to remove" (no exception),
- ``--baselines``+``--coverage`` subsumption,
- ``--dry-run`` deleting nothing,
- no-flag inventory (deletes nothing, reports present/absent),
- ``CleanResult`` status and freed-byte accounting,
- removal failure surfaced with the failing path,
- protected paths never touched.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.clean import CleanResult, run_clean

# Byte sizes used to make freed-byte accounting deterministic.
COVERAGE_BYTES = 1200
BASELINE_BYTES = 300
ARTIFACT_BYTES = 500
CACHE_BYTES = 100


def _write(path: Path, size: int, fill: str = "x") -> None:
    """Create a parent directory and a file of an exact size."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fill * size, encoding="utf-8")


def _make_project(tmp_path: Path) -> Path:
    """Create a project with the full .gd-tools layout and protected files."""
    root = tmp_path / "project"
    gd = root / ".gd-tools"
    _write(gd / "coverage" / "coverage.json", COVERAGE_BYTES)
    _write(gd / "coverage" / "plan.json", 100)
    _write(gd / "coverage" / "baseline.json", BASELINE_BYTES)
    _write(
        gd / "artifacts" / "run_20260930_0000" / "result.xml", ARTIFACT_BYTES
    )
    _write(gd / "native" / "worker0" / "scratch.txt", CACHE_BYTES)
    _write(gd / "native" / "preflight-cache" / "abc123.json", 64)
    # Protected paths that must survive every destructive run.
    _write(
        root / "addons" / "gd-tools-test" / ".backups" / "plugin.cfg.bak", 50
    )
    _write(root / "gd-tools.toml", 200)
    _write(root / ".gutconfig.json", 40)
    return root


def _status(result: CleanResult, name: str):
    return result.target(name)


# ---------------------------------------------------------------------------
# Per-flag targets
# ---------------------------------------------------------------------------


def test_coverage_flag_removes_coverage_directory(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(coverage=True, project_root=root)
    entry = _status(result, "coverage")
    assert not (root / ".gd-tools" / "coverage").exists()
    assert entry.status == "removed"
    # coverage dir holds coverage.json + plan.json + baseline.json
    assert entry.freed_bytes == COVERAGE_BYTES + 100 + BASELINE_BYTES


def test_artifacts_flag_removes_artifacts_directory(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(artifacts=True, project_root=root)
    entry = _status(result, "artifacts")
    assert not (root / ".gd-tools" / "artifacts").exists()
    assert entry.status == "removed"
    assert entry.freed_bytes == ARTIFACT_BYTES


def test_cache_flag_removes_native_scratch_directory(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(cache=True, project_root=root)
    entry = _status(result, "cache")
    assert not (root / ".gd-tools" / "native").exists()
    assert entry.status == "removed"
    # native dir holds worker scratch + the preflight cache entry
    assert entry.freed_bytes == CACHE_BYTES + 64


def test_cache_flag_removes_the_preflight_cache(tmp_path):
    """The preflight cache lives under .gd-tools/native so --cache clears it."""
    root = _make_project(tmp_path)
    preflight_entry = (
        root / ".gd-tools" / "native" / "preflight-cache" / "abc123.json"
    )
    assert preflight_entry.exists()

    result = run_clean(cache=True, project_root=root)

    assert _status(result, "cache").status == "removed"
    assert not preflight_entry.exists()


def test_baselines_flag_removes_only_baseline_json(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(baselines=True, project_root=root)
    entry = _status(result, "baselines")
    assert not (root / ".gd-tools" / "coverage" / "baseline.json").exists()
    # The rest of the coverage output must survive.
    assert (root / ".gd-tools" / "coverage" / "coverage.json").exists()
    assert entry.status == "removed"
    assert entry.freed_bytes == BASELINE_BYTES


# ---------------------------------------------------------------------------
# --all and missing targets
# ---------------------------------------------------------------------------


def test_all_removes_every_target_directory(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(all=True, project_root=root)
    gd = root / ".gd-tools"
    assert not (gd / "coverage").exists()
    assert not (gd / "artifacts").exists()
    assert not (gd / "native").exists()
    assert result.freed_bytes == (
        COVERAGE_BYTES
        + 100
        + BASELINE_BYTES
        + ARTIFACT_BYTES
        + CACHE_BYTES
        + 64
    )


def test_all_keeps_protected_paths(tmp_path):
    root = _make_project(tmp_path)
    run_clean(all=True, project_root=root)
    assert (
        root / "addons" / "gd-tools-test" / ".backups" / "plugin.cfg.bak"
    ).exists()
    assert (root / "gd-tools.toml").exists()
    assert (root / ".gutconfig.json").exists()


def test_missing_target_reports_nothing_to_remove_without_error(tmp_path):
    root = tmp_path / "project"
    (root / ".gd-tools" / "coverage").mkdir(parents=True)
    result = run_clean(artifacts=True, project_root=root)
    entry = _status(result, "artifacts")
    assert entry.status == "nothing"
    assert entry.freed_bytes == 0


def test_missing_project_root_reports_nothing_to_remove(tmp_path):
    root = tmp_path / "empty"
    result = run_clean(coverage=True, project_root=root)
    assert _status(result, "coverage").status == "nothing"


# ---------------------------------------------------------------------------
# Subsumption
# ---------------------------------------------------------------------------


def test_baselines_subsumed_when_coverage_selected(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(coverage=True, baselines=True, project_root=root)
    baselines_entry = _status(result, "baselines")
    assert baselines_entry.status == "subsumed"
    # Baseline bytes counted exactly once, via the coverage target.
    assert _status(result, "coverage").freed_bytes == (
        COVERAGE_BYTES + 100 + BASELINE_BYTES
    )
    assert result.freed_bytes == COVERAGE_BYTES + 100 + BASELINE_BYTES


def test_all_subsumes_every_explicit_flag(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(
        all=True,
        coverage=True,
        artifacts=True,
        baselines=True,
        cache=True,
        project_root=root,
    )
    names = [
        entry.name for entry in result.targets if entry.status == "removed"
    ]
    assert names == ["coverage", "artifacts", "cache"]
    assert result.freed_bytes == (
        COVERAGE_BYTES
        + 100
        + BASELINE_BYTES
        + ARTIFACT_BYTES
        + CACHE_BYTES
        + 64
    )


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_dry_run_removes_nothing_and_reports_would_remove(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(coverage=True, all=True, dry_run=True, project_root=root)
    gd = root / ".gd-tools"
    assert (gd / "coverage" / "coverage.json").exists()
    assert (gd / "artifacts" / "run_20260930_0000" / "result.xml").exists()
    assert _status(result, "coverage").status == "would-remove"
    assert _status(result, "artifacts").status == "would-remove"
    # Sizes are still reported even though nothing is deleted.
    assert _status(result, "coverage").freed_bytes == (
        COVERAGE_BYTES + 100 + BASELINE_BYTES
    )


# ---------------------------------------------------------------------------
# No-flag inventory
# ---------------------------------------------------------------------------


def test_no_flags_returns_inventory_without_deleting(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(project_root=root)
    coverage_entry = _status(result, "coverage")
    assert coverage_entry.status == "present"
    assert coverage_entry.freed_bytes == COVERAGE_BYTES + 100 + BASELINE_BYTES
    assert _status(result, "artifacts").status == "present"
    # Absent targets are visible in the inventory too.
    (root / ".gd-tools" / "artifacts").exists()
    # Nothing was deleted.
    assert (root / ".gd-tools" / "coverage" / "coverage.json").exists()
    assert (root / ".gd-tools" / "artifacts").exists()
    assert (root / ".gd-tools" / "native").exists()


def test_no_flags_inventory_reports_absent_targets(tmp_path):
    root = tmp_path / "empty"
    result = run_clean(project_root=root)
    assert all(entry.status == "absent" for entry in result.targets)


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_removal_failure_is_reported_with_the_failing_path(tmp_path):
    root = _make_project(tmp_path)
    target = root / ".gd-tools" / "coverage"

    def boom(path, *args, **kwargs):
        if path == target:
            raise PermissionError(f"cannot remove {path}")

    with patch("gd_tools.clean._remove_path", side_effect=boom):
        result = run_clean(coverage=True, project_root=root)

    entry = _status(result, "coverage")
    assert entry.status == "failed"
    assert entry.error is not None
    assert str(target) in entry.error
    assert result.failed


# ---------------------------------------------------------------------------
# CleanResult surface
# ---------------------------------------------------------------------------


def test_clean_result_freed_bytes_sum_across_targets(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(artifacts=True, cache=True, project_root=root)
    assert result.freed_bytes == ARTIFACT_BYTES + CACHE_BYTES + 64
    assert not result.failed


@pytest.mark.parametrize(
    "kwargs",
    [
        {"coverage": True},
        {"artifacts": True},
        {"baselines": True},
        {"cache": True},
        {"all": True},
        {},
    ],
)
def test_every_mode_leaves_the_project_dir_itself_intact(tmp_path, kwargs):
    """The .gd-tools directory itself is never removed, only its contents."""
    root = _make_project(tmp_path)
    run_clean(project_root=root, **kwargs)
    assert (root / ".gd-tools").exists()


# --- Snapshots target ---


def test_snapshots_flag_removes_snapshots_directory(tmp_path):
    root = _make_project(tmp_path)
    snapshots_dir = root / ".gd-tools" / "snapshots" / "SuiteA" / "test_a"
    snapshots_dir.mkdir(parents=True)
    snapshot_file = snapshots_dir / "a_1.snap"
    snapshot_file.write_text("# gd-tools snapshot v1\n", encoding="utf-8")

    result = run_clean(snapshots=True, project_root=root)

    entry = _status(result, "snapshots")
    assert not snapshots_dir.exists()
    assert entry.status == "removed"
    assert entry.freed_bytes == len("# gd-tools snapshot v1\n".encode())


def test_snapshots_flag_absent_reports_nothing(tmp_path):
    root = _make_project(tmp_path)
    result = run_clean(snapshots=True, project_root=root)
    entry = _status(result, "snapshots")
    assert entry.status == "nothing"


def test_snapshots_survive_other_clean_flags(tmp_path):
    """--coverage must not delete stored snapshots."""
    root = _make_project(tmp_path)
    snapshots_dir = root / ".gd-tools" / "snapshots"
    snapshots_dir.mkdir(parents=True)
    run_clean(coverage=True, project_root=root)
    assert snapshots_dir.exists()


def test_all_flag_subsumes_snapshots(tmp_path):
    root = _make_project(tmp_path)
    snapshots_dir = root / ".gd-tools" / "snapshots"
    snapshots_dir.mkdir(parents=True)
    result = run_clean(all=True, project_root=root)
    assert _status(result, "snapshots").status == "removed"
    assert not snapshots_dir.exists()


def test_inventory_lists_snapshots_target(tmp_path):
    root = _make_project(tmp_path)
    snapshots_dir = root / ".gd-tools" / "snapshots"
    snapshots_dir.mkdir(parents=True)
    result = run_clean(project_root=root)
    entry = _status(result, "snapshots")
    assert entry.status == "present"
    assert entry.freed_bytes == 0
