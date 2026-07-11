<protect>
# Track 10: Coverage Tracker Addon (GDScript) — Implementation Plan

## Phase 1: Coverage Tracker Implementation (GDScript)

- [x] Task: Read spec.md and workflow.md to load context for this phase
    - [x] Read `conductor/tracks/coverage_tracker_20260711/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write GUT integration test for tracker behavior
    - [x] Create GUT test script testing `hit()`, `get_hits()`, `reset()`, `set_active()`, `is_active()`
    - [x] Create Python integration test wrapper marked `@pytest.mark.integration`

- [x] Task: Implement `coverage.gd` tracker
    - [x] Replace 3-line placeholder with full implementation (`extends Node`, `_hits`, `_active`, `_ready()`, `hit()`, `get_hits()`, `reset()`, `set_active()`, `is_active()`)
    - [x] Implement `_ready()` with `GD_TOOLS_COVERAGE_ACTIVE` env var validation (true only for `"1"` or `"true"`, case-insensitive)
    - [x] Implement `hit()` with single bool check for `_active` (no-op when inactive, minimal overhead)
    - [x] Implement `get_hits()` returning raw `_hits` Dictionary with int keys
    - [x] Implement `reset()`, `set_active()`, `is_active()`
    - [x] Run `gdlint` on `coverage.gd`
    - [x] Run `gdformat` on `coverage.gd`

- [x] Task: Conductor - User Manual Verification 'Coverage Tracker Implementation' (Protocol in workflow.md)

## Phase 2: Autoload Registration (Python)

- [x] Task: Read spec.md and workflow.md to load context for this phase
    - [x] Read `conductor/tracks/coverage_tracker_20260711/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write failing pytest tests for `register_coverage_autoload`
    - [x] Test: registers `_GDTCoverage` autoload in `project.godot` `[autoload]` section
    - [x] Test: idempotent (does not duplicate on repeat calls)
    - [x] Test: creates `[autoload]` section if missing

- [x] Task: Implement `register_coverage_autoload` in `init.py`
    - [x] Implement function: parse `project.godot`, add `_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"` to `[autoload]`
    - [x] Wire into `run_init()` after `install_coverage_addon()`
    - [x] Run `ruff check` and `black` on `init.py`

- [x] Task: Verify test coverage for `init.py` changes
    - [x] Run `CI=true pytest --cov=gd_tools.init --cov-branch --cov-report=term-missing`
    - [x] Verify >80% line and >70% branch coverage for new code

- [x] Task: Conductor - User Manual Verification 'Autoload Registration' (Protocol in workflow.md)

## Phase 3: Integration & Finalization

- [x] Task: Read spec.md and workflow.md to load context for this phase
    - [x] Read `conductor/tracks/coverage_tracker_20260711/spec.md`
    - [x] Read `conductor/workflow.md`

- [~] Task: Update `install_coverage_addon` tests
    - [ ] Update existing test to verify deployed `coverage.gd` contains real implementation (not placeholder TODO)

- [ ] Task: Run full test suite and quality gates
    - [ ] Run `CI=true pytest` (all unit tests pass)
    - [ ] Run `ruff check src/ tests/`
    - [ ] Run `black --check src/ tests/`
    - [ ] Verify no regressions (existing 437+ tests still pass)

- [ ] Task: Conductor - User Manual Verification 'Integration & Finalization' (Protocol in workflow.md)
</protect>
