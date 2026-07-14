<protect>
# Track 24.5: Autoload-Based Coverage Instrumentation — Implementation Plan

## Phase 1: Plan Generator — Remove Autoload Exclusion [checkpoint: e6732eb]

**Goal:** Remove the autoload exclusion filter in `plan_generator.py` so autoload scripts are included in the coverage plan.

**Files:** `src/gd_tools/coverage/plan_generator.py`, `tests/unit/test_plan_generator.py`

- [x] Task: Read `./spec.md` and `../../workflow.md` to refresh context before starting this phase
- [x] Task: Write tests for autoload inclusion in plan [1878b0d]
    - [x] Write test: autoload scripts appear in `generate_plan()` output when `project.godot` has `[autoload]` section
    - [x] Write test: autoload scripts get instrumented lines (file_id, lines array) in the plan
    - [x] Write test: non-autoload scripts are still included (regression check)
    - [x] Write test: project with no `[autoload]` section still works (no crash, all scripts included)
- [x] Task: Remove autoload exclusion from plan_generator.py [1878b0d]
    - [x] Remove the autoload filter block (lines ~395-405: `autoload_paths = resolve_autoload_paths(...)`, the `autoload_set` construction, and the list comprehension filtering `gd_files`)
    - [x] Check if `resolve_autoload_paths()` is still used elsewhere; if not, remove it and its import
    - [x] Run `tools/generate_expected_plans.py` to regenerate expected plan JSON fixtures if any fixture project has autoloads
    - [x] Run tests to confirm autoload scripts now appear in plan
- [x] Task: Conductor - User Manual Verification 'Phase 1: Plan Generator' (Protocol in workflow.md)

## Phase 2: Init — Autoload Registration (Prepend + Auto-fix)

**Goal:** Change `register_coverage_autoload()` from APPEND to PREPEND, and auto-fix `_GDTCoverage` to position 0 if not first.

**Files:** `src/gd_tools/init.py`, `tests/unit/test_init.py`

- [x] Task: Read `./spec.md` and `../../workflow.md` to refresh context before starting this phase
- [x] Task: Write tests for prepend behavior [8a2b766]
    - [x] Write test: `register_coverage_autoload()` inserts `_GDTCoverage` as the FIRST entry in `[autoload]` (before existing autoloads)
    - [x] Write test: when no `[autoload]` section exists, creates one with `_GDTCoverage` as the only entry
    - [x] Write test: idempotent — calling twice doesn't create duplicate entries
    - [x] Write test: when `_GDTCoverage` is already first, no change (idempotent)
- [x] Task: Write tests for auto-fix ordering [8a2b766]
    - [x] Write test: when `_GDTCoverage` is registered but not in position 0, it gets moved to position 0
    - [x] Write test: a warning is printed to stderr when auto-fixing: `Moved _GDTCoverage to first autoload position for coverage to work correctly.`
    - [x] Write test: no warning when already in position 0
- [x] Task: Implement prepend + auto-fix in register_coverage_autoload() [8a2b766]
    - [x] Change the insertion logic from APPEND (insert after `[autoload]` header) to PREPEND (insert as first entry under `[autoload]`)
    - [x] Add detection: if `_GDTCoverage` exists but is not the first autoload entry, move it to position 0
    - [x] Print warning to stderr when auto-fixing
    - [x] Run tests to confirm prepend and auto-fix behavior
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Init — Autoload Registration' (Protocol in workflow.md)

## Phase 3: Coverage Addon — Move Instrumentation to _ready() + Simplify Pre-run Hook

**Goal:** Move all instrumentation logic from `pre_run_hook.gd` into `coverage.gd._ready()`, and simplify `pre_run_hook.gd` to a single `set_active(true)` call.

**Files:** `src/gd_tools/addons/gd-tools-coverage/coverage.gd`, `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`, `tests/integration/test_coverage_hooks.py`

- [ ] Task: Read `./spec.md` and `../../workflow.md` to refresh context before starting this phase
- [ ] Task: Write tests for instrumentation in _ready()
    - [ ] Write integration test: `_ready()` reads `GD_TOOLS_COVERAGE_PLAN` env var (not `GD_TOOLS_COVERAGE_ACTIVE`)
    - [ ] Write integration test: when `GD_TOOLS_COVERAGE_PLAN` is set, all files in the plan are instrumented
    - [ ] Write integration test: `_active` remains `false` after instrumentation in `_ready()`
    - [ ] Write integration test: when `GD_TOOLS_COVERAGE_PLAN` is not set, no instrumentation occurs
    - [ ] Write integration test: `reload()` failure (`ERR_ALREADY_IN_USE`) is handled gracefully (skip file with warning)
- [ ] Task: Move instrumentation logic to coverage.gd._ready()
    - [ ] Move `_load_plan()`, `_validate_plan()`, `_validate_file_entry()`, `_instrument_files()`, `_instrument_file()`, `_inject_trackers()`, `_extract_indent()`, `_detect_body_indent()`, `_log_error()` from `pre_run_hook.gd` to `coverage.gd`
    - [ ] Rewrite `_ready()`: read `GD_TOOLS_COVERAGE_PLAN` env var, load plan, instrument all files, leave `_active = false`
    - [ ] Add defensive `ERR_ALREADY_IN_USE` handling in `_instrument_file()` (skip with warning, already exists but ensure it's preserved)
    - [ ] Update file header comment to reflect new behavior
- [ ] Task: Write test for simplified pre_run_hook.gd
    - [ ] Write integration test: `pre_run_hook.gd` calls `_GDTCoverage.set_active(true)` only
    - [ ] Write integration test: `pre_run_hook.gd` no longer contains instrumentation logic (no `_load_plan`, `_instrument_files`, etc.)
- [ ] Task: Simplify pre_run_hook.gd
    - [ ] Replace entire `run()` function body with: `_GDTCoverage.set_active(true)`
    - [ ] Remove all instrumentation helper functions (moved to coverage.gd)
    - [ ] Keep `_log_error()` only if still needed for error reporting in the simplified hook
    - [ ] Update file header comment
- [ ] Task: Update existing integration tests
    - [ ] Review `tests/integration/test_coverage_hooks.py` for assumptions about pre_run_hook instrumentation
    - [ ] Update tests that assumed instrumentation happens in pre-run hook
    - [ ] Run full test suite to check for regressions
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Coverage Addon Changes' (Protocol in workflow.md)

## Phase 4: Test Runner — Remove GD_TOOLS_COVERAGE_ACTIVE env var

**Goal:** Stop setting `GD_TOOLS_COVERAGE_ACTIVE` env var in `test_runner.py`.

**Files:** `src/gd_tools/test_runner.py`, `tests/unit/test_test_runner.py`

- [ ] Task: Read `./spec.md` and `../../workflow.md` to refresh context before starting this phase
- [ ] Task: Write tests for env var removal
    - [ ] Write test: `GD_TOOLS_COVERAGE_ACTIVE` is NOT in the env dict when `coverage=True`
    - [ ] Write test: `GD_TOOLS_COVERAGE_PLAN` is still set when `coverage=True`
    - [ ] Write test: `GD_TOOLS_COVERAGE_OUTPUT` is still set when `coverage=True`
    - [ ] Write test: `-gpre_run_script` is still in GUT args when `coverage=True`
- [ ] Task: Remove GD_TOOLS_COVERAGE_ACTIVE from test_runner.py
    - [ ] Remove the `"GD_TOOLS_COVERAGE_ACTIVE": "1",` line from the env dict (line ~413)
    - [ ] Run tests to confirm env var is no longer set
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Test Runner Changes' (Protocol in workflow.md)

## Phase 5: E2E Fixture & Integration Test

**Goal:** Create a minimal fixture Godot project that simulates the autoload-creates-instances pattern, and write an E2E test verifying autoload-instantiated scripts get coverage.

**Files:** `tests/fixtures/autoload_coverage/` (new), `tests/e2e/test_autoload_coverage_e2e.py` (new)

- [ ] Task: Read `./spec.md` and `../../workflow.md` to refresh context before starting this phase
- [ ] Task: Create minimal fixture Godot project
    - [ ] Create `tests/fixtures/autoload_coverage/project.godot` with `_GDTCoverage` as first autoload + a second autoload (`GameState`)
    - [ ] Create `tests/fixtures/autoload_coverage/scripts/game_state.gd` — autoload that instantiates `ChimeraData` in `_ready()`
    - [ ] Create `tests/fixtures/autoload_coverage/scripts/chimera_data.gd` — script instantiated by the autoload (the one that was previously showing 0% coverage)
    - [ ] Create `tests/fixtures/autoload_coverage/tests/test_chimera_data.gd` — GUT test that exercises `ChimeraData` methods
- [ ] Task: Write E2E test
    - [ ] Write test: running coverage on the fixture produces non-zero coverage for `chimera_data.gd`
    - [ ] Write test: autoload initialization code (`game_state.gd._ready()`) is NOT recorded as coverage
    - [ ] Write test: existing non-autoload coverage still works (regression check)
- [ ] Task: Conductor - User Manual Verification 'Phase 5: E2E Fixture & Integration Test' (Protocol in workflow.md)
</protect>
