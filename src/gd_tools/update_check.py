"""PyPI update notification module.

Checks PyPI for a newer version of ``gd-tools-cli`` and caches the
result locally (24h TTL) to avoid network calls on every invocation.
Fails silently on any error and can be disabled via the
``GD_TOOLS_NO_UPDATE_CHECK`` environment variable.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests
from packaging.version import parse as parse_version

from gd_tools import __version__

PYPI_URL = "https://pypi.org/pypi/gd-tools-cli/json"
REQUEST_TIMEOUT = 3
CACHE_TTL_HOURS = 24
CACHE_DIR = Path.home() / ".gd-tools"
CACHE_FILENAME = "update-check.json"


def check_for_update() -> Optional[str]:
    """Check PyPI for a newer version of gd-tools-cli.

    Returns the latest version string if an update is available,
    or ``None`` otherwise.  The check is cached for 24 hours and
    fails silently on any error.

    Returns:
        The latest version string from PyPI if an update is
        available, or ``None``.
    """
    # FR4.1: Environment variable disables check entirely.
    if os.environ.get("GD_TOOLS_NO_UPDATE_CHECK") == "1":
        return None

    # FR1.5: Skip dev install (editable install without metadata).
    if __version__ == "0.0.0":
        return None

    # Check cache first; fall back to a fresh PyPI request.
    latest_version = _read_cached_version()
    if latest_version is None:
        latest_version = _fetch_latest_version()
        if latest_version is not None:
            _write_cache(latest_version)

    if latest_version is None:
        return None

    # FR1.4: Compare versions using packaging.version.parse().
    if parse_version(latest_version) > parse_version(__version__):
        return latest_version
    return None


def _read_cached_version() -> Optional[str]:
    """Read the cached latest version if the cache is fresh (< 24h).

    Returns ``None`` on cache miss, stale cache, or corrupt cache
    file (FR3.3 — corrupt cache is treated as a cache miss).
    """
    cache_file = CACHE_DIR / CACHE_FILENAME
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        last_check = datetime.fromisoformat(data["last_check"])
        if last_check.tzinfo is None:
            last_check = last_check.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - last_check
        if age < timedelta(hours=CACHE_TTL_HOURS):
            return data["latest_version"]
        return None
    except (ValueError, KeyError, OSError, TypeError):
        return None


def _fetch_latest_version() -> Optional[str]:
    """Fetch the latest version from the PyPI JSON API.

    Returns ``None`` on any network or parsing error (FR3.1, FR3.2).
    """
    try:
        response = requests.get(PYPI_URL, timeout=REQUEST_TIMEOUT)
        data = response.json()
        return data["info"]["version"]
    except (requests.RequestException, ValueError, KeyError):
        return None


def _write_cache(version: str) -> None:
    """Write the cache file with the current timestamp and version.

    Creates the cache directory if it does not exist (FR2.5).
    Silently ignores write errors — the main functionality is
    unaffected if the cache cannot be persisted.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / CACHE_FILENAME
        entry = {
            "last_check": datetime.now(timezone.utc).isoformat(),
            "latest_version": version,
        }
        cache_file.write_text(json.dumps(entry), encoding="utf-8")
    except OSError:
        pass
