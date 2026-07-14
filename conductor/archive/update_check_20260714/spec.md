<protect>
# Specification: PyPI Update Notification

## Overview

When a user runs any `gd-tools` command, the CLI checks PyPI for a newer version of `gd-tools-cli` and prints a notification to stderr if one is available. The check is cached locally (24h TTL) to avoid network calls on every invocation, fails silently on any error, and can be disabled via an environment variable.

## Functional Requirements

### 1. Update Check Module (`src/gd_tools/update_check.py`)

- **FR1.1:** The module exposes a function `check_for_update()` that returns `Optional[str]` — the latest version string from PyPI if an update is available, or `None` otherwise.
- **FR1.2:** The function queries the PyPI JSON API at `https://pypi.org/pypi/gd-tools-cli/json` and reads the `info.version` field.
- **FR1.3:** The installed version is obtained from `gd_tools.__version__`.
- **FR1.4:** Version comparison uses `packaging.version.parse()` from the `packaging` library.
- **FR1.5:** If the installed version is `"0.0.0"` (editable/dev install without package metadata), the check is skipped entirely and returns `None`.

### 2. Caching

- **FR2.1:** The check result is cached in a JSON file at `Path.home() / ".gd-tools" / "update-check.json"`.
- **FR2.2:** The cache file stores `{"last_check": "<ISO 8601 timestamp>", "latest_version": "<version string>"}`.
- **FR2.3:** If the cache file exists and `last_check` is less than 24 hours old, the cached `latest_version` is used and no network call is made.
- **FR2.4:** If the cache is stale (older than 24h) or missing, a fresh PyPI request is made and the cache file is updated.
- **FR2.5:** The cache directory (`~/.gd-tools/`) is created if it does not exist.

### 3. Error Handling

- **FR3.1:** The HTTP request uses a 3-second timeout.
- **FR3.2:** Any `requests.RequestException`, `ValueError` (JSON parse error), or `KeyError` results in a silent return of `None` — no exception is raised, no message is printed.
- **FR3.3:** If the cache file exists but is corrupt or unreadable, it is treated as a cache miss (fresh request is made).

### 4. Environment Variable Disable

- **FR4.1:** If the environment variable `GD_TOOLS_NO_UPDATE_CHECK` is set to `"1"`, the entire check is skipped (no network call, no cache read, no notification).

### 5. CLI Integration

- **FR5.1:** The check is invoked in `GdToolsGroup.invoke()` in `src/gd_tools/cli.py`, before `super().invoke()` is called.
- **FR5.2:** If `check_for_update()` returns a version string, a notification is printed to stderr via `click.echo(..., err=True)`:
  ```
  A new version of gd-tools is available: <latest> (you have <current>).
  Run `pip install --upgrade gd-tools-cli` to update.
  ```
- **FR5.3:** The notification does not affect the exit code or the normal command execution.

### 6. Dependency

- **FR6.1:** The `packaging` library is added to the `dependencies` list in `pyproject.toml`.

## Non-Functional Requirements

- **NFR1:** The update check must never block or delay normal CLI execution by more than 3 seconds (the HTTP timeout). In practice, the cache means this only happens once per 24h period.
- **NFR2:** The notification must go to stderr, not stdout, so it does not interfere with piped output (e.g., `gd-tools lint --report-format json | jq`).
- **NFR3:** The feature must work cross-platform (Windows, macOS, Linux) — `Path.home()` handles this.

## Acceptance Criteria

1. **PyPI check + comparison:** Given a mocked PyPI response with a newer version, the notification message is printed to stderr.
2. **Cache TTL respected:** Given a cache file newer than 24h, no network call is made; the cached version is used.
3. **Env var disables check:** Given `GD_TOOLS_NO_UPDATE_CHECK=1`, no check or notification occurs.
4. **Network failure silent:** Given a network timeout or error, the CLI proceeds normally with no notification or error.
5. **Dev install skipped:** Given `__version__` is `"0.0.0"`, the check is skipped entirely.

## Out of Scope

- No configuration file option (only env var `GD_TOOLS_NO_UPDATE_CHECK`).
- No background threading (synchronous, once-daily latency is acceptable).
- No pre-release filtering (all versions from PyPI are considered).
- No update installation or auto-update functionality.
- No changelog or release notes display.
</protect>
