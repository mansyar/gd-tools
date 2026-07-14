<protect>
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

## Phase 1: Version File Creation During Init [checkpoint: 1b3e312]

- [x] Task: Read `spec.md` and `conductor/workflow.md` to load context for this phase
- [x] Task: Write tests for version file creation during init
    - [x] Test that `install_coverage_addon()` writes a `_version.txt` file to `addons/gd-tools-coverage/`
    - [x] Test that the file content matches `gd_tools.__version__` (with trailing newline)
    - [x] Test that re-running init overwrites an existing version file with the current version
    - [x] Test that `run_init()` action summary includes a version file entry (e.g., "Wrote addon version file (v0.3.0)")
- [x] Task: Implement version file writing in init.py [2ee000a]
    - [x] Extend `install_coverage_addon()` to write `_version.txt` with `__version__` after copying `.gd` files
    - [x] Add action summary entry in `run_init()` for the version file write
- [x] Task: Conductor - User Manual Verification 'Version File Creation During Init' (Protocol in workflow.md)

---

## Phase 2: Stale Addon Detection Module [checkpoint: b44caba]

- [x] Task: Read `spec.md` and `conductor/workflow.md` to load context for this phase
- [x] Task: Write unit tests for addon_check.py [bec267b]
    - [x] Test: no warning when addon version == package version (versions match)
    - [x] Test: stale warning printed to stderr when addon version < package version
    - [x] Test: missing file warning printed when version file is absent
    - [x] Test: no warning when addon version > package version (downgrade scenario)
    - [x] Test: stale warning printed when version string is unparseable (raw string shown)
    - [x] Test: check is fully suppressed when `GD_TOOLS_NO_UPDATE_CHECK=1`
    - [x] Test: check fails silently (no exception, no crash) on unexpected file system errors
- [x] Task: Implement addon_check.py module [bec267b]
    - [x] Create `src/gd_tools/addon_check.py` with `check_addon_version()` function
    - [x] Implement `GD_TOOLS_NO_UPDATE_CHECK=1` env var suppression (return early)
    - [x] Implement project root resolution (reuse `find_project_root()` from `config.py`, catch `ConfigError` to skip silently)
    - [x] Implement `_version.txt` file read and version string parsing
    - [x] Implement version comparison using `packaging.version.parse()`
    - [x] Implement stderr warning output via `click.echo(..., err=True)` for missing, stale, and unparseable cases
- [x] Task: Integrate check into cli.py [bec267b]
    - [x] Import and call `check_addon_version()` from `GdToolsGroup.invoke()` alongside the existing `check_for_update()` call
- [x] Task: Conductor - User Manual Verification 'Stale Addon Detection Module' (Protocol in workflow.md)

---

## Phase 3: Doctor Integration [checkpoint: c4ad875]

- [x] Task: Read `spec.md` and `conductor/workflow.md` to load context for this phase
- [x] Task: Write tests for doctor addon version reporting [da97aec]
    - [x] Test: `check_coverage_addon()` reports deployed version when addon files and version file are present
    - [x] Test: `check_coverage_addon()` warns when addon files are present but version file is missing
    - [x] Test: `check_coverage_addon()` warns with both versions when addon version is stale (addon < package)
- [x] Task: Implement doctor version status in check_coverage_addon() [da97aec]
    - [x] Read `_version.txt` from the coverage addon directory
    - [x] Include deployed version in the `CheckResult.message` when version file exists (e.g., "Coverage addon installed (v0.3.0)")
    - [x] Set `severity="warning"` and update `fix_hint` when version file is missing
    - [x] Set `severity="warning"` and report both versions when addon version is stale
- [x] Task: Conductor - User Manual Verification 'Doctor Integration' (Protocol in workflow.md)
</protect>
