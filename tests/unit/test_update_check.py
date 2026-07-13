"""Unit tests for the PyPI update check module."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from gd_tools.update_check import check_for_update

pytestmark = pytest.mark.unit


# --- Helpers ---


def _make_cache_entry(version: str, hours_ago: float = 0) -> dict:
    """Create a cache entry dict with the given version and age."""
    timestamp = (
        datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    ).isoformat()
    return {"last_check": timestamp, "latest_version": version}


def _write_cache(cache_dir, version: str, hours_ago: float = 0) -> None:
    """Write a cache file in the given directory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "update-check.json"
    entry = _make_cache_entry(version, hours_ago)
    cache_file.write_text(json.dumps(entry), encoding="utf-8")


# --- Version comparison and PyPI query ---


def test_returns_newer_version_when_pypi_reports_update(
    tmp_path, mock_requests_get
):
    """FR1.1, FR1.2: Returns latest version when PyPI reports newer."""
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "1.0.0"}}),
    ):
        result = check_for_update()
    assert result == "1.0.0"


def test_returns_none_when_installed_is_current(tmp_path, mock_requests_get):
    """FR1.1: Returns None when installed equals latest."""
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "0.1.0"}}),
    ):
        result = check_for_update()
    assert result is None


def test_returns_none_when_installed_is_newer(tmp_path, mock_requests_get):
    """FR1.1: Returns None when installed is newer than PyPI latest."""
    with (
        patch("gd_tools.update_check.__version__", "2.0.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "1.0.0"}}),
    ):
        result = check_for_update()
    assert result is None


def test_skips_check_for_dev_install(tmp_path, mock_requests_get):
    """FR1.5: Returns None when __version__ is '0.0.0'."""
    with (
        patch("gd_tools.update_check.__version__", "0.0.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "1.0.0"}}) as mock_get,
    ):
        result = check_for_update()
    assert result is None
    mock_get.assert_not_called()


# --- Error handling ---


def test_returns_none_on_request_exception(tmp_path):
    """FR3.2: Returns None on requests.RequestException."""
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        patch("requests.get", side_effect=requests.RequestException("timeout")),
    ):
        result = check_for_update()
    assert result is None


def test_returns_none_on_json_parse_error(tmp_path):
    """FR3.2: Returns None on ValueError (JSON parse error)."""
    response = MagicMock()
    response.json.side_effect = ValueError("invalid JSON")
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        patch("requests.get", return_value=response),
    ):
        result = check_for_update()
    assert result is None


def test_returns_none_on_key_error(tmp_path, mock_requests_get):
    """FR3.2: Returns None on KeyError (missing 'info.version')."""
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {}}),
    ):
        result = check_for_update()
    assert result is None


# --- Caching ---


def test_cache_used_when_fresh(tmp_path, mock_requests_get):
    """FR2.3: Cache is used when < 24h old; no network call."""
    _write_cache(tmp_path, "1.0.0", hours_ago=1)
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}) as mock_get,
    ):
        result = check_for_update()
    assert result == "1.0.0"
    mock_get.assert_not_called()


def test_network_call_when_cache_stale(tmp_path, mock_requests_get):
    """FR2.4: Fresh request when cache is older than 24h."""
    _write_cache(tmp_path, "1.0.0", hours_ago=25)
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}) as mock_get,
    ):
        result = check_for_update()
    assert result == "2.0.0"
    mock_get.assert_called_once()


def test_network_call_when_cache_missing(tmp_path, mock_requests_get):
    """FR2.4: Fresh request when cache file is missing."""
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}) as mock_get,
    ):
        result = check_for_update()
    assert result == "2.0.0"
    mock_get.assert_called_once()


def test_cache_written_after_successful_query(tmp_path, mock_requests_get):
    """FR2.4: Cache file is written after a successful PyPI query."""
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}),
    ):
        check_for_update()
    cache_file = tmp_path / "update-check.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert data["latest_version"] == "2.0.0"
    assert "last_check" in data


def test_cache_directory_created_if_not_exists(tmp_path, mock_requests_get):
    """FR2.5: Cache directory is created if it does not exist."""
    cache_dir = tmp_path / ".gd-tools"
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", cache_dir),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}),
    ):
        check_for_update()
    assert cache_dir.exists()
    assert (cache_dir / "update-check.json").exists()


def test_corrupt_cache_treated_as_miss(tmp_path, mock_requests_get):
    """FR3.3: Corrupt cache file is treated as a cache miss."""
    cache_file = tmp_path / "update-check.json"
    cache_file.write_text("not valid json {{{", encoding="utf-8")
    with (
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}) as mock_get,
    ):
        result = check_for_update()
    assert result == "2.0.0"
    mock_get.assert_called_once()


# --- Environment variable disable ---


def test_env_var_disables_check(tmp_path, mock_requests_get):
    """FR4.1: GD_TOOLS_NO_UPDATE_CHECK=1 skips check entirely."""
    with (
        patch.dict("os.environ", {"GD_TOOLS_NO_UPDATE_CHECK": "1"}),
        patch("gd_tools.update_check.__version__", "0.1.0"),
        patch("gd_tools.update_check.CACHE_DIR", tmp_path),
        mock_requests_get(json_data={"info": {"version": "2.0.0"}}) as mock_get,
    ):
        result = check_for_update()
    assert result is None
    mock_get.assert_not_called()
