"""Unit tests for the native import-freshness content-hash cache."""

import json
from unittest.mock import patch

import pytest

from gd_tools.native_test.import_cache import (
    IMPORT_CACHE_SCHEMA_VERSION,
    check_import_cache,
    compute_import_cache_key,
    store_import_freshness,
)

pytestmark = pytest.mark.unit


def _write_project(
    root, *, godot_content="[application]\n", script_content="# player\n"
):
    """Create a minimal Godot project with import-relevant files."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "scenes").mkdir(exist_ok=True)
    (root / "addons" / "gd-tools-test").mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text(godot_content, encoding="utf-8")
    (root / "src" / "player.gd").write_text(script_content, encoding="utf-8")
    (root / "scenes" / "arena.tscn").write_text("[node]\n", encoding="utf-8")
    (root / "scenes" / "arena.tscn.import").write_text(
        "[remap]\n", encoding="utf-8"
    )
    (root / "addons" / "gd-tools-test" / "gd_tools_test.gd").write_text(
        "# addon\n", encoding="utf-8"
    )


def test_import_cache_key_is_deterministic_for_identical_inputs(tmp_path):
    """The same project state produces the same cache key across calls."""
    _write_project(tmp_path)
    first = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    second = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize(
    "mutate",
    [
        lambda root: (root / "src" / "player.gd").write_text(
            "# player v2\n", encoding="utf-8"
        ),
        lambda root: (root / "scenes" / "arena.tscn").write_text(
            "[node]\n# changed\n", encoding="utf-8"
        ),
        lambda root: (root / "scenes" / "arena.tscn.import").write_text(
            "[remap]\nuid=1\n", encoding="utf-8"
        ),
        lambda root: (root / "project.godot").write_text(
            "[application]\nconfig_version=6\n", encoding="utf-8"
        ),
        lambda root: (
            root / "addons" / "gd-tools-test" / "gd_tools_test.gd"
        ).write_text("# addon v2\n", encoding="utf-8"),
        lambda root: (root / "src" / "new_scene.tscn").write_text(
            "[node]\n", encoding="utf-8"
        ),
    ],
    ids=[
        "script-file",
        "scene-file",
        "import-file",
        "project-godot",
        "addon-file",
        "added-file",
    ],
)
def test_import_cache_key_changes_when_project_inputs_change(tmp_path, mutate):
    """Any content change to import-relevant inputs invalidates the key."""
    _write_project(tmp_path)
    before = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    mutate(tmp_path)
    after = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert before != after


def test_import_cache_key_ignores_excluded_directories(tmp_path):
    """Files under cache/VCS/tooling directories do not affect the key."""
    _write_project(tmp_path)
    baseline = compute_import_cache_key(tmp_path, godot_version="4.5.2")

    godot_dir = tmp_path / ".godot"
    godot_dir.mkdir()
    (godot_dir / "imported.dat").write_text("x", encoding="utf-8")
    tools_dir = tmp_path / ".gd-tools"
    tools_dir.mkdir()
    (tools_dir / "artifacts.json").write_text("{}", encoding="utf-8")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")

    assert compute_import_cache_key(tmp_path, godot_version="4.5.2") == (
        baseline
    )


def test_import_cache_key_ignores_irrelevant_extensions(tmp_path):
    """Files with no bearing on the import step do not affect the key."""
    _write_project(tmp_path)
    baseline = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    (tmp_path / "notes.md").write_text("readme", encoding="utf-8")
    assert compute_import_cache_key(tmp_path, godot_version="4.5.2") == (
        baseline
    )


def test_import_cache_key_changes_with_godot_version(tmp_path):
    """A different resolved Godot binary invalidates the key."""
    _write_project(tmp_path)
    baseline = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert compute_import_cache_key(tmp_path, godot_version="4.6.1") != baseline


def test_import_cache_key_is_stable_when_a_file_disappears(tmp_path):
    """A deleted input hashes deterministically instead of raising."""
    _write_project(tmp_path)
    (tmp_path / "src" / "player.gd").unlink()
    first = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    second = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert first == second


def test_check_reports_miss_with_reason_on_missing_cache(tmp_path):
    """A fresh project is a miss explaining there is no cached entry."""
    _write_project(tmp_path)
    key = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    status = check_import_cache(
        tmp_path / ".gd-tools" / "native" / "import-cache", key
    )
    assert status.hit is False
    assert status.reason


def test_store_then_check_roundtrips_to_hit(tmp_path):
    """A stored import freshness reads back as a hit for the same key."""
    _write_project(tmp_path)
    cache_dir = tmp_path / ".gd-tools" / "native" / "import-cache"
    key = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert store_import_freshness(cache_dir, key) is True
    status = check_import_cache(cache_dir, key)
    assert status.hit is True


def test_check_reports_miss_after_project_change(tmp_path):
    """A project change after a stored import yields a miss with a reason."""
    _write_project(tmp_path)
    cache_dir = tmp_path / ".gd-tools" / "native" / "import-cache"
    key = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert store_import_freshness(cache_dir, key) is True
    (tmp_path / "src" / "player.gd").write_text(
        "# player v2\n", encoding="utf-8"
    )
    new_key = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    status = check_import_cache(cache_dir, new_key)
    assert status.hit is False


def test_check_fails_open_on_corrupt_cache_file(tmp_path):
    """A corrupt cache file is a miss, never an error."""
    cache_dir = tmp_path / "import-cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "state.json").write_text("not json", encoding="utf-8")
    status = check_import_cache(cache_dir, "ab" * 32)
    assert status.hit is False


def test_check_rejects_wrong_schema_version(tmp_path):
    """A cache payload from an older schema version is treated as a miss."""
    cache_dir = tmp_path / "import-cache"
    cache_dir.mkdir(parents=True)
    payload = {
        "schema_version": IMPORT_CACHE_SCHEMA_VERSION - 1,
        "cache_key": "ab" * 32,
    }
    (cache_dir / "state.json").write_text(json.dumps(payload), encoding="utf-8")
    status = check_import_cache(cache_dir, "ab" * 32)
    assert status.hit is False


def test_check_rejects_key_mismatch(tmp_path):
    """Freshness stored under a different key is never served as a hit."""
    cache_dir = tmp_path / "import-cache"
    key = "ab" * 32
    assert store_import_freshness(cache_dir, key) is True
    status = check_import_cache(cache_dir, "cd" * 32)
    assert status.hit is False


def test_store_fails_open_on_unwritable_cache(tmp_path):
    """An unwritable cache location returns False instead of raising."""
    cache_dir = tmp_path / "import-cache"
    key = "ab" * 32
    with patch(
        "gd_tools.native_test.import_cache.write_json_atomic",
        side_effect=OSError("disk full"),
    ):
        assert store_import_freshness(cache_dir, key) is False


def test_store_leaves_no_temporary_files(tmp_path):
    """Cache writes are atomic: only the final payload file remains."""
    cache_dir = tmp_path / "import-cache"
    key = "ab" * 32
    assert store_import_freshness(cache_dir, key) is True
    assert [p.name for p in cache_dir.iterdir()] == ["state.json"]
