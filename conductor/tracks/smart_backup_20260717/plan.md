# Implementation Plan: Smart Backup of Coverage Addon Files Before Overwrite

## Phase 1: Smart Backup for Coverage Addon Files

- [x] Task: Write failing unit tests for smart backup behavior in `tests/unit/test_init.py`
    - [ ] Add test: first-time install (no existing addon files) creates no `.bak` files and prints no warnings
    - [ ] Add test: re-init with unmodified files (identical to bundled) creates no `.bak` files and prints no warnings
    - [ ] Add test: re-init with modified `pre_run_hook.gd` creates backup at `.backups/pre_run_hook.gd.bak`, overwrites with bundled version, and prints yellow warning
    - [ ] Add test: re-init with modified `post_run_hook.gd` creates backup at `.backups/post_run_hook.gd.bak`, overwrites with bundled version, and prints yellow warning
    - [ ] Add test: re-init with modified `coverage.gd` creates backup at `.backups/coverage.gd.bak`, overwrites with bundled version, and prints yellow warning
    - [ ] Add test: `.backups/` subdirectory is auto-created if it does not exist
    - [ ] Update existing test `test_install_coverage_addon_overwrites_stale_files` to also assert backup is created (stale content differs from bundled)
    - [ ] Run `CI=true pytest tests/unit/test_init.py` and confirm new tests fail (Red phase)

- [x] Task: Implement smart backup logic in `install_coverage_addon` (`src/gd_tools/init.py`)
    - [ ] Add content comparison before overwrite: read existing target file bytes and compare to bundled source file bytes
    - [ ] Create `.backups/` subdirectory (`addons/gd-tools-coverage/.backups/`) if it does not exist
    - [ ] Copy modified existing file to `.backups/<filename>.bak` before overwriting
    - [ ] Print yellow warning via `console.print` when a backup is created (include filename and backup path)
    - [ ] Update function docstring to document backup behavior
    - [ ] Run `CI=true pytest tests/unit/test_init.py` and confirm all tests pass (Green phase)
    - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` and verify coverage meets thresholds (>80% line, >70% branch)

- [ ] Task: Conductor - User Manual Verification 'Smart Backup for Coverage Addon Files' (Protocol in workflow.md)
