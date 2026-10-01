"""Unit tests for cache-integrated preflight resolution in the test command."""

from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.native_test.preflight import NativePreflightError
from gd_tools.native_test.preflight_cache import (
    load_cached_preflight,
    run_preflight_cached,
)
from gd_tools.native_test.protocol import (
    NativeManifest,
    NativePreflightResult,
    NativeSuite,
    RuntimeMode,
    write_json_atomic,
)

pytestmark = pytest.mark.unit


def _project(root: Path) -> None:
    (root / "addons" / "gd-tools-test").mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text("[application]\n", encoding="utf-8")
    (
        root / "addons" / "gd-tools-test" / "gd_tools_test_preflight.gd"
    ).write_text("# addon\n", encoding="utf-8")
    (root / "test").mkdir(exist_ok=True)
    (root / "test" / "suite.gd").write_text(
        "extends GdToolsTest\n", encoding="utf-8"
    )


def _manifest(project_root: Path) -> NativeManifest:
    return NativeManifest(
        project_root=project_root,
        runtime=RuntimeMode.NATIVE,
        suites=[NativeSuite(name="Suite", path="res://test/suite.gd")],
    )


def _ok_result(manifest: NativeManifest) -> NativePreflightResult:
    return NativePreflightResult(status="ok", suites=manifest.suites)


def test_miss_runs_real_preflight_and_populates_cache(tmp_path):
    """A cold run invokes the real preflight once and stores the result."""
    _project(tmp_path)
    manifest = _manifest(tmp_path)
    run_dir = tmp_path / "artifacts" / "run-1" / "preflight"
    cache_dir = tmp_path / ".gd-tools" / "native" / "preflight-cache"

    def fake_run(project_root, manifest, **kwargs):
        write_json_atomic(
            Path(kwargs["run_dir"]) / "preflight.result.json",
            _ok_result(manifest),
        )
        return _ok_result(manifest)

    with patch(
        "gd_tools.native_test.preflight_cache.run_native_preflight",
        side_effect=fake_run,
    ) as run:
        result = run_preflight_cached(
            tmp_path,
            manifest,
            godot_binary="godot",
            godot_version="4.5.2",
            run_dir=run_dir,
            cache_dir=cache_dir,
            timeout_seconds=30.0,
        )
    assert run.call_count == 1
    assert result == _ok_result(manifest)
    cached = load_cached_preflight(cache_dir, _key_for(tmp_path, manifest))
    assert cached == _ok_result(manifest)


def _key_for(project_root: Path, manifest: NativeManifest) -> str:
    from gd_tools.native_test.preflight_cache import compute_cache_key

    return compute_cache_key(
        manifest.suites, project_root=project_root, godot_version="4.5.2"
    )


def test_use_cache_false_skips_load_and_store(tmp_path):
    """``use_cache=False`` runs the real preflight and writes no entry."""
    _project(tmp_path)
    manifest = _manifest(tmp_path)
    cache_dir = tmp_path / ".gd-tools" / "native" / "preflight-cache"

    with (
        patch(
            "gd_tools.native_test.preflight_cache.run_native_preflight"
        ) as run,
        patch(
            "gd_tools.native_test.preflight_cache.output.print_verbose"
        ) as verbose,
    ):
        run.return_value = _ok_result(manifest)
        first = run_preflight_cached(
            tmp_path,
            manifest,
            godot_binary="godot",
            godot_version="4.5.2",
            run_dir=tmp_path / "artifacts" / "r1" / "preflight",
            cache_dir=cache_dir,
            timeout_seconds=30.0,
            use_cache=False,
        )
        second = run_preflight_cached(
            tmp_path,
            manifest,
            godot_binary="godot",
            godot_version="4.5.2",
            run_dir=tmp_path / "artifacts" / "r2" / "preflight",
            cache_dir=cache_dir,
            timeout_seconds=30.0,
            use_cache=False,
        )

    assert run.call_count == 2
    assert first == second == _ok_result(manifest)
    assert not cache_dir.exists() or not list(cache_dir.iterdir())
    assert any("disabled" in str(call) for call in verbose.call_args_list)


def test_hit_skips_real_preflight_and_copies_artifacts(tmp_path):
    """A warm run spawns no preflight process and materializes artifacts."""
    _project(tmp_path)
    manifest = _manifest(tmp_path)
    cache_dir = tmp_path / ".gd-tools" / "native" / "preflight-cache"

    def fake_run(project_root, manifest, **kwargs):
        write_json_atomic(
            Path(kwargs["run_dir"]) / "preflight.result.json",
            _ok_result(manifest),
        )
        return _ok_result(manifest)

    with patch(
        "gd_tools.native_test.preflight_cache.run_native_preflight",
        side_effect=fake_run,
    ):
        run_preflight_cached(
            tmp_path,
            manifest,
            godot_binary="godot",
            godot_version="4.5.2",
            run_dir=tmp_path / "artifacts" / "cold" / "preflight",
            cache_dir=cache_dir,
            timeout_seconds=30.0,
        )

    run_dir = tmp_path / "artifacts" / "run-2" / "preflight"
    with patch(
        "gd_tools.native_test.preflight_cache.run_native_preflight"
    ) as run:
        result = run_preflight_cached(
            tmp_path,
            manifest,
            godot_binary="godot",
            godot_version="4.5.2",
            run_dir=run_dir,
            cache_dir=cache_dir,
            timeout_seconds=30.0,
        )
    assert run.call_count == 0
    assert result == _ok_result(manifest)
    assert (run_dir / "preflight.manifest.json").is_file()
    assert (run_dir / "preflight.result.json").is_file()
    restored = NativeManifest.model_validate_json(
        (run_dir / "preflight.manifest.json").read_text(encoding="utf-8")
    )
    assert restored == manifest


def test_preflight_error_is_never_cached(tmp_path):
    """A failed preflight propagates and leaves the cache empty."""
    _project(tmp_path)
    manifest = _manifest(tmp_path)
    cache_dir = tmp_path / ".gd-tools" / "native" / "preflight-cache"

    with patch(
        "gd_tools.native_test.preflight_cache.run_native_preflight",
        side_effect=NativePreflightError("preflight failed"),
    ):
        with pytest.raises(NativePreflightError):
            run_preflight_cached(
                tmp_path,
                manifest,
                godot_binary="godot",
                godot_version="4.5.2",
                run_dir=tmp_path / "artifacts" / "run" / "preflight",
                cache_dir=cache_dir,
                timeout_seconds=30.0,
            )
    assert not cache_dir.exists() or not list(cache_dir.iterdir())


def test_hit_with_failed_artifact_copy_falls_back_to_real_preflight(tmp_path):
    """A copy failure on a hit fails open by running the real preflight."""
    _project(tmp_path)
    manifest = _manifest(tmp_path)
    cache_dir = tmp_path / ".gd-tools" / "native" / "preflight-cache"

    def fake_run(project_root, manifest, **kwargs):
        write_json_atomic(
            Path(kwargs["run_dir"]) / "preflight.result.json",
            _ok_result(manifest),
        )
        return _ok_result(manifest)

    with patch(
        "gd_tools.native_test.preflight_cache.run_native_preflight",
        side_effect=fake_run,
    ):
        run_preflight_cached(
            tmp_path,
            manifest,
            godot_binary="godot",
            godot_version="4.5.2",
            run_dir=tmp_path / "artifacts" / "cold" / "preflight",
            cache_dir=cache_dir,
            timeout_seconds=30.0,
        )

    run_dir = tmp_path / "artifacts" / "run-2" / "preflight"
    with patch(
        "gd_tools.native_test.preflight_cache.write_json_atomic",
        side_effect=OSError("read-only volume"),
    ):
        with patch(
            "gd_tools.native_test.preflight_cache.run_native_preflight",
            side_effect=fake_run,
        ) as run:
            result = run_preflight_cached(
                tmp_path,
                manifest,
                godot_binary="godot",
                godot_version="4.5.2",
                run_dir=run_dir,
                cache_dir=cache_dir,
                timeout_seconds=30.0,
            )
    assert run.call_count == 1
    assert result == _ok_result(manifest)
