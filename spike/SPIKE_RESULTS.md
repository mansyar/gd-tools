# Coverage Instrumentation Spike — Results

**Track:** `spike_coverage_20260709`  
**Date:** 2026-07-09  
**Godot Version:** 4.6.2.stable  
**GUT Version:** 9.6.0  

---

## Summary

The spike validated **Architecture C (Hybrid Coverage)**: Python generates an instrumentation plan (JSON), GDScript runtime hooks modify `Script.source_code` and call `Script.reload()`, a tracker autoload records hit data, and Python generates reports.

**All 6 success criteria PASSED.** Architecture C is confirmed as the implementation path forward.

---

## Success Criteria Results

### Criterion 1: Source modification compiles — PASS

**Evidence:** GUT stdout shows:
```
[gd-tools] Instrumented: res://scripts/calculator.gd (3 lines)
```
No GDScript parse/compile errors. `Script.reload()` returned OK.

### Criterion 2: Instrumented code executes — PASS

**Evidence:** `coverage.json` exists at `spike/coverage.json`. The `hits` dictionary is non-empty (3 hit points recorded).

### Criterion 3: Correct lines recorded — PASS

**Evidence:** `coverage.json` hits match the expected values exactly:
```json
{
  "hits": {"0:0": 2, "0:1": 1, "0:2": 1}
}
```
- `0:0` (line 8, `if b == 0.0`): 2 hits — called twice (once with b=2.0, once with b=0.0)
- `0:1` (line 9, `return {"error": ...}`): 1 hit — only when b=0.0
- `0:2` (line 11, `return {"result": a/b}`): 1 hit — only when b=2.0

### Criterion 4: Original behavior preserved — PASS

**Evidence:** GUT test results:
```
Tests: 2, Passing: 2, Failing: 0, Asserts: 2
All tests passed!
```
The instrumented calculator.gd maintained identical behavior to the original.

### Criterion 5: Coverage data serializable — PASS

**Evidence:** `coverage.json` is valid JSON with correct structure:
```json
{
  "generated_at": "2026-07-09T05:43:50Z",
  "hits": {"0:0": 2, "0:1": 1, "0:2": 1},
  "version": 1
}
```
Parsed successfully with `python -c "import json; json.load(open('spike/coverage.json'))"`.

### Criterion 6: Works in CLI mode — PASS

**Evidence:** Entire flow executed via:
```
godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -d -gexit -gselect=test_calculator
```
No editor required. Hooks loaded automatically via `.gutconfig.json`.

---

## Architecture Decision

**Architecture C (Hybrid Coverage) is CONFIRMED.**

All 6 success criteria passed, validating the core mechanism:
1. Python-generated plan JSON can be consumed by GDScript hooks
2. `Script.source_code` modification + `Script.reload()` works at runtime
3. Autoload tracker records hits correctly
4. Post-run hook serializes data to JSON
5. Instrumented code preserves original behavior
6. Full flow works in headless CLI mode

---

## Known Limitations

### 1. Tracker tests interfere with coverage measurement

The tracker autoload's `reset()` method is called in test `before_each()` hooks. When running all tests together, tracker tests clear coverage data recorded by calculator tests.

**Workaround:** Use `-gselect=test_calculator` to run only the target test file during coverage measurement.

**Production fix:** The full implementation should exclude the tracker's own tests from coverage runs, or use a separate test invocation for coverage measurement.

### 2. Hook scripts must extend GutHookScript

GUT's `_validate_hook_script` (in `gut.gd`) requires hook scripts to:
- Extend `GutHookScript` (not `RefCounted`)
- Implement a `run()` method (not `_init()`)
- Accept a `gut` property (set by GUT before calling `run()`)

**Impact:** Any future changes to GUT's hook validation API could break integration. The full implementation should pin GUT version and add integration tests.

### 3. GUT config key names

The `.gutconfig.json` keys must match GUT's `default_options` in `gut_config.gd`:
- `should_exit` (not `exit`)
- `dirs` (not `dir`)
- `pre_run_script` / `post_run_script`

### 4. Godot `--import` required for new addons

When adding a new addon or autoload, Godot must be run with `--headless --import` first to cache class_name imports and generate `.uid` files. Without this, GUT class_names are unresolved.

### 5. GUT CLI flag: `-gdir` (not `-gdirs`)

The GUT 9.6.0 CLI flag for test directories is `-gdir`, not `-gdirs`. Using the wrong flag produces an "unrecognized option" error.

### 6. JSON key ordering

Godot's `JSON.stringify()` serializes Dictionary keys in alphabetical order, not insertion order. This is cosmetic only — JSON consumers should not depend on key order.

### 7. Godot version deviation

The spec references Godot 4.5; the spike used 4.6.2. The `Script.source_code` and `Script.reload()` APIs are stable across Godot 4.x. No functional impact.

---

## Spike Flow Command

```powershell
# Set environment variables
$env:GD_TOOLS_COVERAGE_ACTIVE = "1"
$env:GD_TOOLS_COVERAGE_PLAN = "<absolute_path>/spike/plan.json"
$env:GD_TOOLS_COVERAGE_OUTPUT = "<absolute_path>/spike/coverage.json"

# Run GUT with hooks (hooks auto-loaded via .gutconfig.json)
& "C:\Godot\Godot_v4.6.2-stable_win64.exe" --headless --path spike/ `
    -s addons/gut/gut_cmdln.gd -d -gexit -gselect=test_calculator
```

---

## Effort Estimate for Full Implementation

Based on spike learnings, estimated effort for a production coverage tool:

| Component | Estimate | Notes |
|---|---|---|
| Python instrumentation plan generator | 2-3 days | Parse GDScript, identify statement/branch lines, generate plan.json |
| Python report generator | 1-2 days | Parse coverage.json, generate HTML/text reports |
| GUT integration | 1 day | Already proven in spike — productionize hook scripts |
| Production tracker.gd | 0.5 day | Already proven — harden edge cases, add validation |
| Edge case handling | 2-3 days | Nested functions, match statements, lambdas, inner classes |
| Testing | 2 days | Unit + integration tests for all components |
| **Total** | **8-11 days** | |

---

## Files Produced

| File | Purpose |
|---|---|
| `spike/scripts/calculator.gd` | Test target (instrumented at runtime) |
| `spike/test/test_calculator.gd` | GUT tests for calculator |
| `spike/test/test_tracker.gd` | GUT tests for tracker |
| `spike/test/test_pre_run_hook.gd` | GUT tests for _inject_trackers |
| `spike/addons/gd-tools-coverage/tracker.gd` | Autoload coverage tracker |
| `spike/addons/gd-tools-coverage/pre_run_hook.gd` | GUT pre-run hook (instrumentation) |
| `spike/addons/gd-tools-coverage/post_run_hook.gd` | GUT post-run hook (serialization) |
| `spike/plan.json` | Hand-written instrumentation plan |
| `spike/.gutconfig.json` | GUT configuration with hook paths |
| `spike/coverage.json` | Generated coverage data (gitignored) |
| `spike/spike_output.log` | Captured stdout from spike run (gitignored) |
