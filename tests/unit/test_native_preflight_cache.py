"""Unit tests for the native preflight content-hash cache."""

import json
from unittest.mock import patch

import pytest

from gd_tools.native_test.preflight_cache import (
    PREFLIGHT_CACHE_SCHEMA_VERSION,
    compute_cache_key,
    load_cached_preflight,
    store_cached_preflight,
)
from gd_tools.native_test.protocol import (
    NativePreflightResult,
    NativeSuite,
    NativeSuiteIntegration,
    RuntimeMode,
)

pytestmark = pytest.mark.unit


def _write_project(
    root, *, godot_content="[application]\n", addon_content="# addon\n"
):
    """Create a minimal Godot project with one bundled addon script."""
    (root / "addons" / "gd-tools-test").mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text(godot_content, encoding="utf-8")
    (
        root / "addons" / "gd-tools-test" / "gd_tools_test_preflight.gd"
    ).write_text(addon_content, encoding="utf-8")
    (root / "test").mkdir(exist_ok=True)
    (root / "test" / "suite.gd").write_text(
        "extends GdToolsTest\n", encoding="utf-8"
    )


def _suite(path: str = "res://test/suite.gd") -> NativeSuite:
    return NativeSuite(name="Suite", path=path, runtime=RuntimeMode.NATIVE)


def _result() -> NativePreflightResult:
    return NativePreflightResult(status="ok", suites=[_suite()])


def test_cache_key_is_deterministic_for_identical_inputs(tmp_path):
    """The same project state produces the same cache key across calls."""
    _write_project(tmp_path)
    first = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    second = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize(
    "mutate",
    [
        lambda root: (root / "test" / "suite.gd").write_text(
            "extends GdToolsTest\n# changed\n", encoding="utf-8"
        ),
        lambda root: (root / "project.godot").write_text(
            "[application]\nconfig_version=6\n", encoding="utf-8"
        ),
        lambda root: (
            root / "addons" / "gd-tools-test" / "gd_tools_test_preflight.gd"
        ).write_text("# addon v2\n", encoding="utf-8"),
    ],
    ids=["test-file", "project-godot", "addon-file"],
)
def test_cache_key_changes_when_project_inputs_change(tmp_path, mutate):
    """Any content change to hashed inputs invalidates the key."""
    _write_project(tmp_path)
    before = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    mutate(tmp_path)
    after = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    assert before != after


def _integration_suite(path: str = "res://test/suite.gd") -> NativeSuite:
    return NativeSuite(
        name="Suite",
        path=path,
        runtime=RuntimeMode.NATIVE,
        integration=NativeSuiteIntegration(
            scene="res://scenes/arena.tscn",
            resources={"Player": "res://scenes/player.tscn"},
        ),
    )


def test_cache_key_changes_when_integration_inputs_change(tmp_path):
    """Integration scene/resource content changes invalidate the key."""
    _write_project(tmp_path)
    scenes = tmp_path / "scenes"
    scenes.mkdir()
    (scenes / "arena.tscn").write_text("[node]\n", encoding="utf-8")
    (scenes / "player.tscn").write_text("[node]\n", encoding="utf-8")
    suite = _integration_suite()
    base = compute_cache_key(
        [suite], project_root=tmp_path, godot_version="4.5.2"
    )

    (scenes / "arena.tscn").write_text(
        "[node]\n# changed\n", encoding="utf-8"
    )
    changed_scene = compute_cache_key(
        [suite], project_root=tmp_path, godot_version="4.5.2"
    )
    assert changed_scene != base

    (scenes / "player.tscn").unlink()
    missing_resource = compute_cache_key(
        [suite], project_root=tmp_path, godot_version="4.5.2"
    )
    assert missing_resource != changed_scene


def test_cache_key_changes_with_godot_version_or_suite_set(tmp_path):
    """The Godot version and suite set participate in the key."""
    _write_project(tmp_path)
    baseline = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    new_godot = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.6.1"
    )
    new_suites = compute_cache_key(
        [_suite(), _suite("res://test/other.gd")],
        project_root=tmp_path,
        godot_version="4.5.2",
    )
    assert baseline != new_godot
    assert baseline != new_suites


def test_store_then_load_roundtrips_result(tmp_path):
    """A stored preflight result loads back equal to what was stored."""
    cache_dir = tmp_path / "preflight-cache"
    key = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    assert store_cached_preflight(cache_dir, key, _result()) is True
    loaded = load_cached_preflight(cache_dir, key)
    assert loaded == _result()


def test_load_returns_none_on_missing_cache(tmp_path):
    """A cache miss returns None instead of raising."""
    loaded = load_cached_preflight(tmp_path / "preflight-cache", "ab" * 32)
    assert loaded is None


def test_load_returns_none_on_corrupt_cache_file(tmp_path):
    """A corrupt cache file fails open as a miss, never an error."""
    cache_dir = tmp_path / "preflight-cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / f"{'ab' * 32}.json").write_text("not json", encoding="utf-8")
    assert load_cached_preflight(cache_dir, "ab" * 32) is None


def test_load_rejects_wrong_schema_version(tmp_path):
    """A cache payload from an older schema version is treated as a miss."""
    cache_dir = tmp_path / "preflight-cache"
    cache_dir.mkdir(parents=True)
    payload = {
        "schema_version": PREFLIGHT_CACHE_SCHEMA_VERSION - 1,
        "cache_key": "ab" * 32,
        "result": _result().model_dump(mode="json"),
    }
    (cache_dir / f"{'ab' * 32}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    assert load_cached_preflight(cache_dir, "ab" * 32) is None


def test_load_rejects_key_mismatch(tmp_path):
    """A payload stored under a different key is never served."""
    cache_dir = tmp_path / "preflight-cache"
    key = compute_cache_key(
        [_suite()], project_root=tmp_path, godot_version="4.5.2"
    )
    assert store_cached_preflight(cache_dir, key, _result()) is True
    assert load_cached_preflight(cache_dir, "cd" * 32) is None


def test_store_fails_open_on_unwritable_cache(tmp_path):
    """An unwritable cache location returns False instead of raising."""
    cache_dir = tmp_path / "preflight-cache"
    key = "ab" * 32
    with patch(
        "gd_tools.native_test.preflight_cache.write_json_atomic",
        side_effect=OSError("disk full"),
    ):
        assert store_cached_preflight(cache_dir, key, _result()) is False


def test_store_leaves_no_temporary_files(tmp_path):
    """Cache writes are atomic: only the final payload file remains."""
    cache_dir = tmp_path / "preflight-cache"
    key = "ab" * 32
    assert store_cached_preflight(cache_dir, key, _result()) is True
    assert [p.name for p in cache_dir.iterdir()] == [f"{key}.json"]
