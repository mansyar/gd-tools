"""Unit tests for native run-scoped artifact management."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.native_test.artifacts import (
    ArtifactPublishError,
    NativeArtifactLayout,
    publish_artifact_index,
)

pytestmark = pytest.mark.unit


def test_layout_uses_safe_run_scoped_stable_names(tmp_path):
    """A run ID maps to one predictable artifact tree."""
    layout = NativeArtifactLayout.create(tmp_path, "run-1")

    assert layout.run_dir == tmp_path / ".gd-tools" / "artifacts" / "run-1"
    assert layout.preflight_dir == layout.run_dir / "preflight"
    assert layout.native_dir == layout.run_dir / "native"
    assert layout.index_path == layout.run_dir / "artifacts.json"
    assert layout.suite_paths(0) == {
        "manifest": layout.native_dir / "suite-0000.manifest.json",
        "result": layout.native_dir / "suite-0000.result.json",
        "events": layout.native_dir / "suite-0000.events.ndjson",
        "log": layout.native_dir / "suite-0000.log",
        "coverage": layout.native_dir / "suite-0000.coverage.json",
        "screenshot_base": layout.native_dir / "suite-0000",
    }


@pytest.mark.parametrize("run_id", ["", ".", "..", "../escape", "a/b", "a\\b"])
def test_layout_rejects_unsafe_run_ids(tmp_path, run_id):
    """Run IDs cannot escape the fixed artifact root."""
    with pytest.raises(ValueError, match="run_id"):
        NativeArtifactLayout.create(tmp_path, run_id)


def _write_run(path: Path, marker: str) -> Path:
    """Create a run-shaped artifact directory for retention tests."""
    path.mkdir(parents=True)
    (path / "artifacts.json").write_text(marker, encoding="utf-8")
    return path


def test_publish_records_paths_and_prunes_only_after_publication(tmp_path):
    """The latest index is complete before older run directories are removed."""
    artifact_root = tmp_path / ".gd-tools" / "artifacts"
    old_run = _write_run(artifact_root / "old-run", "old")
    layout = NativeArtifactLayout.create(tmp_path, "run-1")
    suite_paths = layout.suite_paths(0)
    for key in ("manifest", "result", "events", "log"):
        suite_paths[key].write_text("{}", encoding="utf-8")

    index_path = publish_artifact_index(
        layout,
        status="passed",
        suite_names=["ExampleSuite"],
        suite_paths=[suite_paths],
        preflight_paths=layout.preflight_paths(),
    )

    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["protocol_version"] == 2
    assert index["run_id"] == "run-1"
    assert index["status"] == "passed"
    assert index["run_dir"] == str(layout.run_dir)
    assert index["preflight"]["result"] == str(
        layout.preflight_paths()["result"]
    )
    assert index["suites"][0]["suite"] == "ExampleSuite"
    assert index["suites"][0]["result"] == str(suite_paths["result"])
    assert all(
        Path(path).is_absolute()
        for key, path in index["suites"][0].items()
        if key != "suite"
    )
    assert not old_run.exists()
    assert layout.run_dir.exists()


def test_publish_omits_artifacts_that_were_never_written(tmp_path):
    """The index lists only artifact paths that exist on disk."""
    layout = NativeArtifactLayout.create(tmp_path, "run-1")
    suite_paths = layout.suite_paths(0)
    suite_paths["result"].write_text("{}", encoding="utf-8")
    suite_paths["coverage"].write_text("{}", encoding="utf-8")

    index_path = publish_artifact_index(
        layout,
        status="failed",
        suite_names=["ExampleSuite"],
        suite_paths=[suite_paths],
        preflight_paths=layout.preflight_paths(),
    )

    entry = json.loads(index_path.read_text(encoding="utf-8"))["suites"][0]
    assert entry["result"] == str(suite_paths["result"])
    assert entry["coverage"] == str(suite_paths["coverage"])
    assert "manifest" not in entry
    assert "screenshot_base" not in entry


def test_publish_records_only_screenshots_that_exist(tmp_path):
    """Per-test screenshot lists contain realized captures only."""
    layout = NativeArtifactLayout.create(tmp_path, "run-1")
    suite_paths = layout.suite_paths(0)
    suite_paths["result"].write_text("{}", encoding="utf-8")
    captured = layout.native_dir / "suite-0000.test_one.failure.png"
    captured.write_bytes(b"png")
    suite_paths["screenshots"] = [
        captured,
        layout.native_dir / "suite-0000.test_two.failure.png",
    ]

    index_path = publish_artifact_index(
        layout,
        status="failed",
        suite_names=["ExampleSuite"],
        suite_paths=[suite_paths],
        preflight_paths=layout.preflight_paths(),
    )

    entry = json.loads(index_path.read_text(encoding="utf-8"))["suites"][0]
    assert entry["screenshots"] == [str(captured)]


def test_prune_keeps_directories_that_are_not_runs(tmp_path):
    """Retention never removes a directory that is not a prior run."""
    artifact_root = tmp_path / ".gd-tools" / "artifacts"
    user_dir = artifact_root / "user-data"
    user_dir.mkdir(parents=True)
    (user_dir / "notes.txt").write_text("keep me", encoding="utf-8")
    _write_run(artifact_root / "old-run", "old")
    layout = NativeArtifactLayout.create(tmp_path, "run-1")

    publish_artifact_index(
        layout,
        status="passed",
        suite_names=[],
        suite_paths=[],
        preflight_paths=layout.preflight_paths(),
    )

    assert (user_dir / "notes.txt").read_text(encoding="utf-8") == "keep me"
    assert not (artifact_root / "old-run").exists()


def test_failed_publication_keeps_older_runs(tmp_path):
    """A failed index write never deletes the previous run."""
    old_run = _write_run(
        tmp_path / ".gd-tools" / "artifacts" / "old-run", "old"
    )
    layout = NativeArtifactLayout.create(tmp_path, "run-1")

    with patch(
        "gd_tools.native_test.artifacts._write_json_atomic",
        side_effect=OSError("disk full"),
    ):
        with pytest.raises(ArtifactPublishError, match="publish"):
            publish_artifact_index(
                layout,
                status="error",
                suite_names=[],
                suite_paths=[],
                preflight_paths=layout.preflight_paths(),
            )

    assert old_run.exists()
    assert not layout.index_path.exists()
