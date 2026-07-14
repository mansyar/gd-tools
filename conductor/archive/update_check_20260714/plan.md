<protect>
# Implementation Plan: PyPI Update Notification

## Phase 1: Update Check Module [checkpoint: e637149]

- [x] Task: Read spec.md and workflow.md before starting Phase 1
    - [x] Read the track's `spec.md` to review all functional requirements
    - [x] Read `conductor/workflow.md` to review the TDD workflow and quality gates

- [x] Task: Add `packaging` dependency (32fe75a)
    - [x] Add `packaging` to the `dependencies` list in `pyproject.toml`
    - [x] Install updated dependencies (`pip install -e ".[dev]"`)

- [x] Task: Write tests for version comparison and PyPI query (b75bc20)
    - [x] Test `check_for_update()` returns newer version string when PyPI reports a newer version
    - [x] Test `check_for_update()` returns `None` when installed version is current
    - [x] Test `check_for_update()` returns `None` when `__version__` is `"0.0.0"` (dev install skip)
    - [x] Test `check_for_update()` returns `None` on `requests.RequestException`
    - [x] Test `check_for_update()` returns `None` on JSON parse error (`ValueError`)
    - [x] Confirm all tests fail as expected (Red phase)

- [x] Task: Implement `check_for_update()` with PyPI query and version comparison (b75bc20)
    - [x] Implement PyPI JSON API query (`https://pypi.org/pypi/gd-tools-cli/json`) with 3s timeout
    - [x] Implement version comparison using `packaging.version.parse()`
    - [x] Implement dev install (`"0.0.0"`) skip — return `None` immediately
    - [x] Implement silent error handling (catch `RequestException`, `ValueError`, `KeyError`)
    - [x] Run tests and confirm all pass (Green phase)

- [x] Task: Write tests for caching logic (b75bc20)
    - [x] Test cache file is read and used when fresh (< 24h old)
    - [x] Test network call is made when cache is stale (> 24h old)
    - [x] Test network call is made when cache file is missing
    - [x] Test cache file is written after a successful PyPI query
    - [x] Test cache directory (`~/.gd-tools/`) is created if it does not exist
    - [x] Test corrupt/unreadable cache file is treated as a cache miss
    - [x] Confirm all tests fail as expected (Red phase)

- [x] Task: Implement caching logic (b75bc20)
    - [x] Implement cache file read with 24h TTL check
    - [x] Implement cache file write (store `last_check` timestamp and `latest_version`)
    - [x] Implement cache directory creation (`Path.home() / ".gd-tools"`)
    - [x] Implement corrupt cache handling (treat as cache miss)
    - [x] Run tests and confirm all pass (Green phase)

- [x] Task: Write tests for environment variable disable (b75bc20)
    - [x] Test `check_for_update()` returns `None` and makes no network call when `GD_TOOLS_NO_UPDATE_CHECK=1`
    - [x] Confirm test fails as expected (Red phase)

- [x] Task: Implement environment variable check (b75bc20)
    - [x] Check `os.environ.get("GD_TOOLS_NO_UPDATE_CHECK")` at the start of `check_for_update()`; return `None` if set to `"1"`
    - [x] Run tests and confirm all pass (Green phase)

- [x] Task: Verify coverage for Phase 1
    - [x] Run `CI=true pytest --cov=gd_tools.update_check --cov-branch --cov-report=term-missing`
    - [x] Confirm >80% line coverage and >70% branch coverage for `update_check.py`

- [x] Task: Conductor - User Manual Verification 'Update Check Module'

## Phase 2: CLI Integration [checkpoint: 6306397]

- [x] Task: Read spec.md and workflow.md before starting Phase 2
    - [x] Read the track's `spec.md` to review all functional requirements
    - [x] Read `conductor/workflow.md` to review the TDD workflow and quality gates

- [x] Task: Write tests for CLI integration (b740e34)
    - [x] Test notification message is printed to stderr when an update is available
    - [x] Test no notification is printed when no update is available
    - [x] Test notification does not affect the exit code of the command
    - [x] Test `GD_TOOLS_NO_UPDATE_CHECK=1` disables notification in CLI context
    - [x] Confirm all tests fail as expected (Red phase)

- [x] Task: Implement CLI hook in `GdToolsGroup.invoke()` (b740e34)
    - [x] Import `check_for_update` from `.update_check` in `cli.py`
    - [x] Call `check_for_update()` in `GdToolsGroup.invoke()` before `super().invoke()`
    - [x] Print notification to stderr via `click.echo(..., err=True)` when a new version is found
    - [x] Run tests and confirm all pass (Green phase)

- [x] Task: Verify coverage for Phase 2
    - [x] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
    - [x] Confirm >80% line coverage and >70% branch coverage overall
    - [x] Run `ruff check src/ tests/` and `black --check src/ tests/`

- [x] Task: Conductor - User Manual Verification 'CLI Integration'

## Phase: Review Fixes
- [x] Task: Apply review suggestions 5709ab1
</protect>
