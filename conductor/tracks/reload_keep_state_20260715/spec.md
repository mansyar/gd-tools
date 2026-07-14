# Spec: Reload Keep-State Fix for Autoload Instrumentation

## Problem

Track 24.5 moved coverage instrumentation into `_GDTCoverage._ready()` as the first
autoload, assuming this would run before other autoloads create instances. However,
real-world testing revealed that **Godot creates ALL autoload instances during the
autoload registration phase, BEFORE calling `_ready()` on any of them**.

When `_GDTCoverage._ready()` calls `script.reload()` on autoload scripts that already
have instances (EventBus, GameState, SaveManager, CombatManager, etc.), Godot returns
`ERR_ALREADY_IN_USE` and instrumentation silently fails — those scripts show 0% coverage.

## Root Cause

`GDScript.reload()` with default `keep_state=false` refuses to reload when instances
exist, returning `ERR_ALREADY_IN_USE`. The current code handles this by skipping
instrumentation and printing a warning, but this means autoload scripts are never
instrumented in real projects.

## Solution

Use `reload(true)` (keep_state=true) instead of `reload()`. This reloads the script
source code while keeping existing instances intact — the instances pick up the
instrumented code. This is the same fix that was applied in the earlier spike/POC.

## Scope

### Files to Change
1. `src/gd_tools/addons/gd-tools-coverage/coverage.gd` — core fix + comment updates
2. `tests/fixtures/gdscript/test_coverage_instrumentation.gd` — rewrite tests that
   expected ERR_ALREADY_IN_USE skip behavior
3. `tests/fixtures/autoload_coverage/scripts/game_state.gd` — update stale comment
4. `tests/fixtures/autoload_coverage/scripts/chimera_data.gd` — update stale comment

### Out of Scope
- Documentation updates (will be done as a follow-up if needed)
- Python-side changes (none needed)

## Acceptance Criteria
- `reload(true)` is used for both instrumentation and error-recovery paths
- ERR_ALREADY_IN_USE dead code path removed
- GDScript tests verify instrumentation succeeds even when instances exist
- All existing tests pass
- Coverage remains >80% line, >70% branch
