"""Content-hash cache for the Godot import step.

Every ``gd-tools test`` invocation historically ran
``godot --headless --import`` unconditionally, but repeat runs on an
unchanged project resolve the same import result. The import freshness is
cached under ``.gd-tools/native/import-cache/`` keyed by a SHA-256 digest
of everything the import depends on: ``project.godot``, every
import-relevant project file (scripts, scenes, resources, imported asset
sources, bundled addon scripts), and the Godot binary version.

Like the preflight cache, this is a pure optimization. Every read or write
error fails open and behaves exactly like a cache miss so a broken cache
can never fail a run.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from gd_tools import output
from gd_tools.native_test.preflight_cache import _hash_file
from gd_tools.native_test.protocol import write_json_atomic

IMPORT_CACHE_SCHEMA_VERSION = 1

_STATE_FILENAME = "state.json"

_EXCLUDED_DIR_NAMES = frozenset(
    {".git", ".godot", ".gd-tools", ".vscode", ".idea", "__pycache__"}
)

# Everything Godot's import step consumes: scripts, scenes, resources,
# ``.import`` sidecars, project/addon metadata, and the asset sources that
# get imported (textures, audio, fonts, models, translations, shaders).
_IMPORT_FILE_SUFFIXES = frozenset(
    {
        ".bmp",
        ".cfg",
        ".csv",
        ".fbx",
        ".gd",
        ".gdextension",
        ".gdshader",
        ".gdshaderinc",
        ".gltf",
        ".glb",
        ".import",
        ".jpeg",
        ".jpg",
        ".mp3",
        ".obj",
        ".ogg",
        ".otf",
        ".png",
        ".res",
        ".scn",
        ".svg",
        ".theme",
        ".tres",
        ".tscn",
        ".toml",
        ".ttf",
        ".wav",
        ".webp",
        ".woff",
        ".woff2",
    }
)


class ImportCacheStatus(BaseModel):
    """Outcome of an import-freshness cache lookup."""

    hit: bool
    reason: str


class _CachedImportPayload(BaseModel):
    """Envelope persisted as the single import-freshness entry."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = IMPORT_CACHE_SCHEMA_VERSION
    cache_key: str


def _iter_import_inputs(project_root: Path) -> Iterator[Path]:
    """Yield import-relevant project files in deterministic order.

    Standard VCS/tooling/cache directories are pruned from the walk so
    their contents never participate in the cache key.
    """
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = sorted(
            name for name in dirnames if name not in _EXCLUDED_DIR_NAMES
        )
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.suffix in _IMPORT_FILE_SUFFIXES:
                yield path


def compute_import_cache_key(project_root: Path, *, godot_version: str) -> str:
    """Build the cache key for the project's import inputs.

    Args:
        project_root: Resolved Godot project root.
        godot_version: Version string of the resolved Godot binary.

    Returns:
        The SHA-256 hex digest of the canonical key components. A file
        that cannot be read hashes as ``absent`` so the key stays
        deterministic for the same project state.
    """
    components = [
        f"schema:{IMPORT_CACHE_SCHEMA_VERSION}",
        f"godot:{godot_version}",
        f"project.godot:{_hash_file(project_root / 'project.godot')}",
    ]
    for path in _iter_import_inputs(project_root):
        relative = path.relative_to(project_root).as_posix()
        components.append(f"{relative}:{_hash_file(path)}")
    digest = hashlib.sha256("\n".join(components).encode("utf-8"))
    return digest.hexdigest()


def check_import_cache(cache_dir: Path, cache_key: str) -> ImportCacheStatus:
    """Check whether the last successful import matches the current key.

    Args:
        cache_dir: Directory holding the import-freshness entry.
        cache_key: Key returned by ``compute_import_cache_key``.

    Returns:
        A hit when the recorded freshness matches ``cache_key``; any
        missing, unreadable, or mismatched entry is a miss with a
        human-readable reason.
    """
    entry_path = cache_dir / _STATE_FILENAME
    try:
        payload = _CachedImportPayload.model_validate_json(
            entry_path.read_text(encoding="utf-8")
        )
    except FileNotFoundError:
        reason = "no cached import entry"
    except (OSError, ValueError):
        reason = "cache entry unreadable"
    else:
        if payload.schema_version != IMPORT_CACHE_SCHEMA_VERSION:
            reason = "incompatible cache entry"
        elif payload.cache_key != cache_key:
            reason = "project changed since last import"
        else:
            output.print_verbose("Import cache hit: project unchanged")
            return ImportCacheStatus(
                hit=True, reason="project unchanged since last import"
            )
    output.print_verbose(f"Import cache miss: {reason}")
    return ImportCacheStatus(hit=False, reason=reason)


def store_import_freshness(cache_dir: Path, cache_key: str) -> bool:
    """Persist a successful import's freshness atomically, failing open.

    Args:
        cache_dir: Directory holding the import-freshness entry.
        cache_key: Key returned by ``compute_import_cache_key``.

    Returns:
        ``True`` when the entry was stored, ``False`` when storing failed.
    """
    payload = _CachedImportPayload(cache_key=cache_key)
    entry_path = cache_dir / _STATE_FILENAME
    try:
        write_json_atomic(entry_path, payload)
    except OSError as error:
        output.print_verbose(f"Import cache store failed: {error}")
        return False
    output.print_verbose("Import freshness stored in cache")
    return True
