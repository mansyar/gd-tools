# Track 23: Stale Addon Detection — Implementation Plan

## Overview

This plan implements the stale addon detection feature (Track 23) following the project's TDD workflow (Red → Green → Refactor) as defined in `conductor/workflow.md`.

**Modules affected:**
- `src/gd_tools/init.py` (version file creation)
- `src/gd_tools/addon_check.py` (new — stale detection logic)
- `src/gd_tools/cli.py` (check integration into `GdToolsGroup.invoke()`)
- `src/gd_tools/doctor.py` (version status reporting)
- `tests/unit/test_addon_check.py` (new)
- `tests/unit/test_init.py` (extend)
- `tests/unit/test_doctor.py` (extend)

---

## Phase 1: Version File Creation During Init

- [ ] Task: Write tests for version file creation during init
    - [ ] Test that `install_coverage_addon()` writes a `_version.txt` file to `addons/gd-tools-coverage/`
    - [ ] Test that the file content matches `gd_tools.__version__` (with trailing newline)
    - [ ] Test that re-running init overwrites an existing version file with the current version
    - [ ] Test that `run_init()` action summary includes a version file entry (e.g., "Wrote addon version file (v0.3.0)")
- [ ] Task: Implement version file writing in init.py
    - [ ] Extend `install_coverage_addon()` to write `_version.txt` with `__version__` after copying `.gd` files
    - [ ] Add action summary entry in `run_init()` for the version file write
- [ ] Task: Conductor - User Manual Verification 'Version File Creation During Init' (Protocol in workflow.md)

---

## Phase 2: Stale Addon Detection Module

- [ ] Task: Write unit tests for addon_check.py
    - [ ] Test: no warning when addon version == package version (versions match)
    - [ ] Test: stale warning printed to stderr when addon version < package version
    - [ ] Test: missing file warning printed when version file is absent
    - [ ] Test: no warning when addon version > package version (downgrade scenario)
    - [ ] Test: stale warning printed when version string is unparseable (raw string shown)
    - [ ] Test: check is fully suppressed when `GD_TOOLS_NO_UPDATE_CHECK=1`
    - [ ] Test: check fails silently (no exception, no crash) on unexpected file system errors
- [ ] Task: Implement addon_check.py module
    - [ ] Create `src/gd_tools/addon_check.py` with `check_addon_version()` function
    - [ ] Implement `GD_TOOLS_NO_UPDATE_CHECK=1` env var suppression (return early)
    - [ ] Implement project root resolution (reuse `find_project_root()` from `config.py`, catch `ConfigError` to skip silently)
    - [ ] Implement `_version.txt` file read and version string parsing
    - [ ] Implement version comparison using `packaging.version.parse()`
    - [ ] Implement stderr warning output via `click.echo(..., err=True)` for missing, stale, and unparseable cases
- [ ] Task: Integrate check into cli.py
    - [ ] Import and call `check_addon_version()` from `GdToolsGroup.invoke()` alongside the existing `check_for_update()` call
- [ ] Task: Conductor - User Manual Verification 'Stale Addon Detection Module' (Protocol in workflow.md)

---

## Phase 3: Doctor Integration

- [ ] Task: Write tests for doctor addon version reporting
    - [ ] Test: `check_coverage_addon()` reports deployed version when addon files and version file are present
    - [ ] Test: `check_coverage_addon()` warns when addon files are present but version file is missing
    - [ ] Test: `check_coverage_addon()` warns with both versions when addon version is stale (addon < package)
- [ ] Task: Implement doctor version status in check_coverage_addon()
    - [ ] Read `_version.txt` from the coverage addon directory
    - [ ] Include deployed version in the `CheckResult.message` when version file exists (e.g., "Coverage addon installed (v0.3.0)")
    - [ ] Set `severity="warning"` and update `fix_hint` when version file is missing
    - [ ] Set `severity="warning"` and report both versions when addon version is stale
- [ ] Task: Conductor - User Manual Verification 'Doctor Integration' (Protocol in workflow.md)
