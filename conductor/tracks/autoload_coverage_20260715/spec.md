<protect>
# Track 24.5: Autoload-Based Coverage Instrumentation

**Type:** Bug Fix (Urgent)
**Status:** Planned

## Overview

When an autoload's `_ready()` creates instances of other scripts (e.g., `GameState._ready()` calls `_init_new_game()` which loads `ChimeraData` instances from `.tres` files), the GUT pre-run hook cannot instrument those scripts via `load()` + `reload()`. `reload()` fails with `ERR_ALREADY_IN_USE` because active instances already exist. The instrumented file is skipped, showing 0% coverage despite being exercised by tests. This dropped a real project's coverage from 93.8% to 75.3%.

**Root Cause:** Instrumentation happens too late. The pre-run hook runs AFTER all autoloads have initialized. By that point, autoload-created instances exist, and `reload()` refuses to recompile scripts with active instances.

**Solution:** Move instrumentation to `_GDTCoverage._ready()`, which runs as the **first** autoload (before any other autoload creates instances). At that point, no instances exist, so `reload()` succeeds. Tracker activation stays in the pre-run hook via `set_active(true)` to preserve current coverage semantics (test execution only, not autoload init).

**Empirical Verification (Pre-Implementation):** Verified on Godot 4.6.2 stable that `reload()` updates the GDScript resource **in-place** (same instance ID before and after). `load()`, `preload()`, and `class_name` all point to the same cached resource object, which `reload()` updates. New instances created after `reload()` execute the instrumented code. `reload()` with active instances fails with `ERR_ALREADY_IN_USE` (error code 22) — confirming instrumentation must happen before instances exist.

## Functional Requirements

### FR1: Autoload Registration (init.py)
- `register_coverage_autoload()` must register `_GDTCoverage` as the **first** entry in `[autoload]` (PREPEND, not APPEND).
- If `_GDTCoverage` is already registered but not in position 0, automatically move it to position 0 and print a warning: `Moved _GDTCoverage to first autoload position for coverage to work correctly.`
- If `_GDTCoverage` is already in position 0, no action needed (idempotent).

### FR2: Instrumentation in coverage.gd
- Move instrumentation logic from `pre_run_hook.gd` into `_GDTCoverage._ready()`.
- In `_ready()`, check `GD_TOOLS_COVERAGE_PLAN` env var (NOT `GD_TOOLS_COVERAGE_ACTIVE`) to determine if this is a coverage run.
- If plan path is set, instrument all files in the plan: `load(path)` → modify `source_code` → `reload()`.
- Leave `_active = false` after instrumentation — the pre-run hook will activate the tracker later.
- If `reload()` returns `ERR_ALREADY_IN_USE`, skip that file with a warning (defensive — shouldn't happen if `_GDTCoverage` is first).

### FR3: Simplified pre_run_hook.gd
- Remove instrumentation logic (moved to `coverage.gd`).
- Simplify to a single line: `_GDTCoverage.set_active(true)`.
- The tracker activates here, after all autoloads have initialized, so only test execution is recorded.

### FR4: Plan Generator (plan_generator.py)
- Remove the autoload exclusion (lines ~395-405). Autoloads can now be instrumented because `_GDTCoverage` runs first and instruments before instances are created.

### FR5: Test Runner (test_runner.py)
- Keep `-gpre_run_script` in `build_gut_args()` (still needed for `set_active(true)`).
- **Stop setting** `GD_TOOLS_COVERAGE_ACTIVE` env var — the pre-run hook handles activation.
- Keep `GD_TOOLS_COVERAGE_PLAN` and `GD_TOOLS_COVERAGE_OUTPUT` env vars.

## Non-Functional Requirements

### NFR1: Breaking Change — Env Var Removal
- `GD_TOOLS_COVERAGE_ACTIVE` is no longer set by `test_runner.py`.
- Users who relied on this env var in their production code (the workaround this track eliminates) will see it return empty. This is expected and documented in release notes.
- No runtime detection or proactive scanning for env var references in user code. Release notes are the sole migration communication.

### NFR2: Coverage Semantics Preservation
- Autoload initialization code is NOT recorded as coverage. The tracker activates via the pre-run hook (after autoloads init), so only test execution is recorded.
- Existing coverage results for non-autoload scripts must remain unchanged.

### NFR3: Defensive Error Handling
- `reload()` failure in `_GDTCoverage._ready()` should skip the file with a warning, not crash the game.
- Since `_GDTCoverage` is first, no instances should exist, making `ERR_ALREADY_IN_USE` unlikely. Defensive handling is a safety net.

## Acceptance Criteria

1. `_GDTCoverage` is registered as the first autoload in `project.godot` after `gd-tools init`
2. If `_GDTCoverage` is not first, `gd-tools init` auto-fixes it to position 0 with a warning
3. Autoload scripts (e.g., `game_state.gd`) appear in the coverage plan (no longer excluded)
4. Scripts instantiated by autoloads (e.g., `chimera_data.gd`) show non-zero coverage when exercised by tests
5. `reload()` never returns `ERR_ALREADY_IN_USE` during coverage runs (since `_GDTCoverage` runs first)
6. Users no longer need `GD_TOOLS_COVERAGE_ACTIVE` env-var checks in their `_ready()` methods
7. Autoload initialization code is NOT recorded as coverage (tracker activates via pre-run hook, after autoloads init)
8. Existing coverage results for non-autoload scripts are unchanged
9. All existing tests pass
10. The `reload()` in-place behavior is empirically verified (DONE — pre-implementation check passed)

## Out of Scope

- File-based pre-instrumentation (Approach B from ROADMAP) — not needed since `reload()` in-place behavior is confirmed
- Runtime detection/scanning of user code for `GD_TOOLS_COVERAGE_ACTIVE` references — release notes only
- Full chimera-gladiator-manager fixture replication — minimal fixture covers the core pattern
- Playtest coverage (Track 34) — separate future track
- Coverage exclusion annotations (Track 30) — separate future track

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `reload()` bug in pre-4.6 Godot (Issue #107869) | Low (we target 4.5+) | `_GDTCoverage` is first, no instances exist, `reload()` should never fail. Defensive error handling added. |
| Autoload ordering dependency — users manually reorder | Medium | `register_coverage_autoload()` auto-fixes to position 0 with warning on every `gd-tools init`. |
| Env var change for existing users | Low | Release notes document the change. Workaround becomes harmless dead code. |
</protect>
