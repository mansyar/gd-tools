"""Content-hash cache for the native integration preflight.

Repeat ``gd-tools test`` runs on an unchanged project always resolve the
same integration preflight, so the enriched preflight result can be cached
under ``.gd-tools/native/preflight-cache/`` keyed by a SHA-256 digest of
everything the preflight depends on: the discovered suite set, the test
source files, ``project.godot``, the bundled addon scripts, and the Godot
binary version.

The cache is a pure optimization. Every read or write error fails open and
behaves exactly like a cache miss so a broken cache can never fail a run.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from gd_tools import output
from gd_tools.native_test.preflight import run_native_preflight
from gd_tools.native_test.protocol import (
    NativeManifest,
    NativePreflightResult,
    NativeSuite,
    write_json_atomic,
)

PREFLIGHT_CACHE_SCHEMA_VERSION = 1

_ADDON_SCRIPT_GLOB = "addons/gd-tools-test/*.gd"


class _CachedPreflightPayload(BaseModel):
    """Envelope persisted for one cached preflight entry."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = PREFLIGHT_CACHE_SCHEMA_VERSION
    cache_key: str
    result: NativePreflightResult


def _hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's bytes.

    A file that cannot be read hashes as ``absent`` so the key stays
    deterministic for the same project state.
    """
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return "absent"
    return digest.hexdigest()


def _resolve_res_path(value: str, project_root: Path) -> Path:
    """Resolve a ``res://`` path against the project root."""
    return project_root / value.removeprefix("res://")


def compute_cache_key(
    suites: list[NativeSuite],
    *,
    project_root: Path,
    godot_version: str,
) -> str:
    """Build the cache key for a native run's preflight inputs.

    Args:
        suites: Discovered suites in discovery order.
        project_root: Resolved Godot project root.
        godot_version: Version string of the resolved Godot binary.

    Returns:
        The SHA-256 hex digest of the canonical key components.
    """
    components = [
        f"schema:{PREFLIGHT_CACHE_SCHEMA_VERSION}",
        f"godot:{godot_version}",
    ]
    for suite in suites:
        components.append(suite.model_dump_json())
        source_hash = _hash_file(_resolve_res_path(suite.path, project_root))
        components.append(f"{suite.path}:{source_hash}")
    components.append(
        f"project.godot:{_hash_file(project_root / 'project.godot')}"
    )
    addon_scripts = sorted(project_root.glob(_ADDON_SCRIPT_GLOB))
    for script in addon_scripts:
        relative = script.relative_to(project_root).as_posix()
        components.append(f"{relative}:{_hash_file(script)}")
    digest = hashlib.sha256("\n".join(components).encode("utf-8"))
    return digest.hexdigest()


def load_cached_preflight(
    cache_dir: Path, cache_key: str
) -> NativePreflightResult | None:
    """Load a cached preflight result, failing open as a miss.

    Args:
        cache_dir: Directory holding the preflight cache entries.
        cache_key: Key returned by ``compute_cache_key``.

    Returns:
        The cached result on a hit, or ``None`` on a miss, unreadable
        entry, or incompatible schema.
    """
    entry_path = cache_dir / f"{cache_key}.json"
    try:
        payload = _CachedPreflightPayload.model_validate_json(
            entry_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        output.print_verbose("Preflight cache miss (no cached entry)")
        return None
    except (OSError, ValueError):
        output.print_verbose("Preflight cache miss (cache entry unreadable)")
        return None
    if (
        payload.schema_version != PREFLIGHT_CACHE_SCHEMA_VERSION
        or payload.cache_key != cache_key
    ):
        output.print_verbose("Preflight cache miss (incompatible cache entry)")
        return None
    output.print_verbose("Preflight cache hit")
    return payload.result


def store_cached_preflight(
    cache_dir: Path,
    cache_key: str,
    result: NativePreflightResult,
) -> bool:
    """Persist a preflight result atomically, failing open on errors.

    Args:
        cache_dir: Directory holding the preflight cache entries.
        cache_key: Key returned by ``compute_cache_key``.
        result: Successful preflight result to cache.

    Returns:
        ``True`` when the entry was stored, ``False`` when storing failed.
    """
    payload = _CachedPreflightPayload(cache_key=cache_key, result=result)
    entry_path = cache_dir / f"{cache_key}.json"
    try:
        write_json_atomic(entry_path, payload)
    except OSError as error:
        output.print_verbose(f"Preflight cache store failed: {error}")
        return False
    output.print_verbose("Preflight result stored in cache")
    return True


def run_preflight_cached(
    project_root: Path,
    manifest: NativeManifest,
    *,
    godot_binary: str,
    godot_version: str,
    run_dir: Path,
    cache_dir: Path,
    timeout_seconds: float,
    use_cache: bool = True,
) -> NativePreflightResult:
    """Resolve the integration preflight through the content-hash cache.

    On a cache hit the cached result is served and the preflight manifest
    and result artifacts are materialized in ``run_dir`` so the artifact
    index contract is unchanged. On a miss the real preflight runs and a
    successful result is stored. With ``use_cache=False`` both the lookup
    and the store are skipped and the real preflight always runs.

    Args:
        project_root: Resolved Godot project root.
        manifest: Preflight manifest built from suite discovery.
        godot_binary: Resolved Godot binary path.
        godot_version: Version string of the resolved Godot binary.
        run_dir: Preflight artifact directory for this run.
        cache_dir: Directory holding the preflight cache entries.
        timeout_seconds: Godot process timeout for a real preflight.

    Returns:
        The effective preflight result for this run.

    Raises:
        NativePreflightError: When the real preflight fails. Errors are
            never cached.
    """
    if not use_cache:
        output.print_verbose("Preflight cache disabled (--no-cache)")
        return run_native_preflight(
            project_root,
            manifest,
            godot_binary=godot_binary,
            run_dir=run_dir,
            timeout_seconds=timeout_seconds,
        )
    cache_key = compute_cache_key(
        manifest.suites, project_root=project_root, godot_version=godot_version
    )
    cached = load_cached_preflight(cache_dir, cache_key)
    if cached is not None:
        try:
            write_json_atomic(run_dir / "preflight.manifest.json", manifest)
            write_json_atomic(run_dir / "preflight.result.json", cached)
        except OSError as error:
            output.print_verbose(
                f"Preflight cache artifact copy failed: {error}"
            )
        else:
            return cached
    result = run_native_preflight(
        project_root,
        manifest,
        godot_binary=godot_binary,
        run_dir=run_dir,
        timeout_seconds=timeout_seconds,
    )
    if result.status == "ok":
        store_cached_preflight(cache_dir, cache_key, result)
    return result
