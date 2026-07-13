<protect>
# Implementation Plan: PyPI Update Notification

## Phase 1: Update Check Module

- [ ] Task: Read spec.md and workflow.md before starting Phase 1
    - [ ] Read the track's `spec.md` to review all functional requirements
    - [ ] Read `conductor/workflow.md` to review the TDD workflow and quality gates

- [ ] Task: Add `packaging` dependency
    - [ ] Add `packaging` to the `dependencies` list in `pyproject.toml`
    - [ ] Install updated dependencies (`pip install -e ".[dev]"`)

- [ ] Task: Write tests for version comparison and PyPI query
    - [ ] Test `check_for_update()` returns newer version string when PyPI reports a newer version
    - [ ] Test `check_for_update()` returns `None` when installed version is current
    - [ ] Test `check_for_update()` returns `None` when `__version__` is `"0.0.0"` (dev install skip)
    - [ ] Test `check_for_update()` returns `None` on `requests.RequestException`
    - [ ] Test `check_for_update()` returns `None` on JSON parse error (`ValueError`)
    - [ ] Confirm all tests fail as expected (Red phase)

- [ ] Task: Implement `check_for_update()` with PyPI query and version comparison
    - [ ] Implement PyPI JSON API query (`https://pypi.org/pypi/gd-tools-cli/json`) with 3s timeout
    - [ ] Implement version comparison using `packaging.version.parse()`
    - [ ] Implement dev install (`"0.0.0"`) skip — return `None` immediately
    - [ ] Implement silent error handling (catch `RequestException`, `ValueError`, `KeyError`)
    - [ ] Run tests and confirm all pass (Green phase)

- [ ] Task: Write tests for caching logic
    - [ ] Test cache file is read and used when fresh (< 24h old)
    - [ ] Test network call is made when cache is stale (> 24h old)
    - [ ] Test network call is made when cache file is missing
    - [ ] Test cache file is written after a successful PyPI query
    - [ ] Test cache directory (`~/.gd-tools/`) is created if it does not exist
    - [ ] Test corrupt/unreadable cache file is treated as a cache miss
    - [ ] Confirm all tests fail as expected (Red phase)

- [ ] Task: Implement caching logic
    - [ ] Implement cache file read with 24h TTL check
    - [ ] Implement cache file write (store `last_check` timestamp and `latest_version`)
    - [ ] Implement cache directory creation (`Path.home() / ".gd-tools"`)
    - [ ] Implement corrupt cache handling (treat as cache miss)
    - [ ] Run tests and confirm all pass (Green phase)

- [ ] Task: Write tests for environment variable disable
    - [ ] Test `check_for_update()` returns `None` and makes no network call when `GD_TOOLS_NO_UPDATE_CHECK=1`
    - [ ] Confirm test fails as expected (Red phase)

- [ ] Task: Implement environment variable check
    - [ ] Check `os.environ.get("GD_TOOLS_NO_UPDATE_CHECK")` at the start of `check_for_update()`; return `None` if set to `"1"`
    - [ ] Run tests and confirm all pass (Green phase)

- [ ] Task: Verify coverage for Phase 1
    - [ ] Run `CI=true pytest --cov=gd_tools.update_check --cov-branch --cov-report=term-missing`
    - [ ] Confirm >80% line coverage and >70% branch coverage for `update_check.py`

- [ ] Task: Conductor - User Manual Verification 'Update Check Module'

## Phase 2: CLI Integration

- [ ] Task: Read spec.md and workflow.md before starting Phase 2
    - [ ] Read the track's `spec.md` to review all functional requirements
    - [ ] Read `conductor/workflow.md` to review the TDD workflow and quality gates

- [ ] Task: Write tests for CLI integration
    - [ ] Test notification message is printed to stderr when an update is available
    - [ ] Test no notification is printed when no update is available
    - [ ] Test notification does not affect the exit code of the command
    - [ ] Test `GD_TOOLS_NO_UPDATE_CHECK=1` disables notification in CLI context
    - [ ] Confirm all tests fail as expected (Red phase)

- [ ] Task: Implement CLI hook in `GdToolsGroup.invoke()`
    - [ ] Import `check_for_update` from `.update_check` in `cli.py`
    - [ ] Call `check_for_update()` in `GdToolsGroup.invoke()` before `super().invoke()`
    - [ ] Print notification to stderr via `click.echo(..., err=True)` when a new version is found
    - [ ] Run tests and confirm all pass (Green phase)

- [ ] Task: Verify coverage for Phase 2
    - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
    - [ ] Confirm >80% line coverage and >70% branch coverage overall
    - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/`

- [ ] Task: Conductor - User Manual Verification 'CLI Integration'
</protect>
