# Specification: Coverage Instrumentation Spike

**Track ID:** `spike_coverage_20260709`
**Track Type:** Feature (Spike / Proof of Concept)
**Status:** New
**Parent Documents:** `docs/PRD.md` (Section 10: Coverage Architecture), `docs/ROADMAP.md` (Phase 0, Track 0), `docs/SPIKE_coverage_instrumentation.md`
**Risk Level:** HIGH — this validates the riskiest component of the entire project

---

## 1. Summary

Prove that GDScript files can be instrumented at runtime via Godot's `Script.source_code` property and `Script.reload()` method, and that the instrumented code executes correctly when GUT runs tests against it.

This spike validates the core hypothesis of **Architecture C (Hybrid coverage)**: Python generates an instrumentation plan (JSON) → GDScript runtime hooks modify source code and reload scripts → tracker records hit data → Python generates reports.

If the spike fails, one of three fallback architectures will be adopted before investing in full implementation.

---

## 2. Background & Rationale

The `gd-tools` CLI's differentiating feature is a custom coverage system for GDScript. Unlike Python's `coverage.py`, GDScript has no existing coverage tool that works with GUT in CLI mode. The proposed approach (Architecture C) relies on an unproven mechanism: modifying `Script.source_code` at runtime and calling `Script.reload()` to recompile instrumented code.

This is the **highest-risk assumption** in the entire project. Validating it first — before building the Python CLI, config system, or report generators — de-risks the architecture and prevents wasted effort if the approach is fundamentally flawed.

---

## 3. Hypothesis

> **Given** an instrumentation plan (JSON) that identifies executable lines in a GDScript file,
> **when** a GUT `pre_run_hook` modifies `Script.source_code` to inject tracker calls and calls `Script.reload()`,
> **then** the instrumented code compiles, executes when tests run, and the tracker records which lines were hit.

### Sub-hypotheses

1. `Script.source_code` can be read and set at runtime (GDScript → GDScript).
2. `Script.reload()` recompiles the modified source without error.
3. The recompiled script replaces the cached version — subsequent `load()` calls and existing references use the instrumented code.
4. Injected tracker calls (`_GDTCoverage.hit(file_id, line_id)`) fire when the instrumented code executes.
5. This works in CLI mode (`godot -s addons/gut/gut_cmdln.gd -d`), not just in the editor.
6. The original test behavior is preserved (tests still pass with instrumentation).

---

## 4. Scope

### In Scope

- One simple GDScript file with an `if/else` branch structure (`calculator.gd`)
- One GUT test that exercises both branches (`test_calculator.gd`)
- A tracker autoload that records hit counts (`tracker.gd`)
- A `pre_run_hook` that instruments the file using string manipulation (`pre_run_hook.gd`)
- A `post_run_hook` that serializes tracker data to JSON (`post_run_hook.gd`)
- A hand-written instrumentation plan (`plan.json`)
- Running the full flow via GUT CLI and verifying results

### Out of Scope

- Full Lark-based plan generation (Python side) — the spike uses a hand-written plan
- Branch coverage logic (only line/statement tracking in the spike)
- Multiple files, inheritance, inner classes, `@tool` scripts
- Performance benchmarking
- Report generation (HTML/LCOV/Cobertura)
- Error recovery / source restoration after crash
- The Python CLI itself

These are deferred to the Technical Design Document and implementation phases (Tracks 1-17).

---

## 5. Success Criteria

| # | Criterion | Pass Condition | Failure Action |
|---|-----------|----------------|----------------|
| 1 | Source modification compiles | `script.reload()` returns `OK` | Check for syntax errors in injected code |
| 2 | Instrumented code executes | Tracker `_hits` dict is non-empty after test run | Verify reload updated cached resource |
| 3 | Correct lines recorded | Hits match expected values (0:0=2, 0:1=1, 0:2=1) | Debug injection positions |
| 4 | Original behavior preserved | Both GUT tests pass | Check instrumentation didn't alter logic |
| 5 | Coverage data serializable | `coverage.json` is valid JSON with correct structure | Debug JSON serialization in post_run_hook |
| 6 | Works in CLI mode | Entire spike runs via `godot -s ... -d` without editor | N/A — fundamental blocker |

### Overall Verdict

- **All 6 pass** → Architecture C is validated. Proceed to TDD and full implementation (Tracks 1-17).
- **1-2 fail but fixable** → Fix the issue, re-run spike. Document the fix.
- **3+ fail or unfixable** → Execute fallback plan (see Section 8).

---

## 6. Technical Design

### Architecture Under Test

```
┌─────────────────────────────────────────────────────┐
│ SPIKE COMPONENTS                                     │
│                                                      │
│  ┌─────────────┐    ┌──────────────┐               │
│  │ plan.json   │    │ tracker.gd   │               │
│  │ (hand-written)│    │ (autoload)   │               │
│  └──────┬──────┘    └──────┬───────┘               │
│         │                  │                          │
│         │    ┌─────────────▼────────────┐           │
│         └───►│ pre_run_hook.gd          │           │
│              │  1. Read plan            │           │
│              │  2. For each file:       │           │
│              │     - load script        │           │
│              │     - inject trackers    │           │
│              │     - source_code = mod  │           │
│              │     - reload()           │           │
│              └────────────┬─────────────┘           │
│                           │                          │
│              ┌────────────▼─────────────┐           │
│              │ GUT runs tests           │           │
│              │  (instrumented code      │           │
│              │   fires _GDTCoverage.hit)│           │
│              └────────────┬─────────────┘           │
│                           │                          │
│              ┌────────────▼─────────────┐           │
│              │ post_run_hook.gd         │           │
│              │  1. Read tracker hits    │           │
│              │  2. Serialize to JSON    │           │
│              │  3. Write to file        │           │
│              └──────────────────────────┘           │
└─────────────────────────────────────────────────────┘
```

### Components

#### 6.1 Test Target: `scripts/calculator.gd`

A minimal GDScript file with both branches of an if/else. **Note:** The SPIKE doc's original draft used `self` as a parameter name — this is a GDScript keyword and must be corrected to just `a` and `b`.

```gdscript
extends RefCounted

## A simple calculator for spike testing.
##
## This file will be instrumented at runtime by the coverage spike.

func divide(a: float, b: float) -> Dictionary:
    if b == 0.0:
        return {"error": "division by zero"}
    else:
        return {"result": a / b}
```

#### 6.2 GUT Test: `test/test_calculator.gd`

```gdscript
extends GutTest

var _calc: Object

func before_each():
    _calc = load("res://scripts/calculator.gd").new()

func after_each():
    _calc = null

func test_divide_normal():
    var result = _calc.divide(10.0, 2.0)
    assert_eq(result["result"], 5.0)

func test_divide_by_zero():
    var result = _calc.divide(10.0, 0.0)
    assert_eq(result["error"], "division by zero")
```

Both tests must pass — this proves original behavior is preserved after instrumentation.

#### 6.3 Instrumentation Plan: `plan.json`

Hand-written for the spike. In production, Python generates this via gdtoolkit/Lark.

```json
{
  "version": 1,
  "generated_by": "spike",
  "files": [
    {
      "path": "res://scripts/calculator.gd",
      "file_id": 0,
      "lines": [
        {"line": 8, "id": 0, "type": "statement", "desc": "if condition"},
        {"line": 9, "id": 1, "type": "branch_true", "desc": "b == 0 branch"},
        {"line": 11, "id": 2, "type": "branch_false", "desc": "else branch"}
      ]
    }
  ]
}
```

#### 6.4 Tracker Autoload: `addons/gd-tools-coverage/tracker.gd`

```gdscript
extends Node

## Coverage tracker singleton (autoload).
##
## No-op when GD_TOOLS_COVERAGE_ACTIVE env var is not set.
## Records hit counts per (file_id, line_id) pair.

var _active: bool = false
var _hits: Dictionary = {}

func _ready() -> void:
    _active = OS.has_environment("GD_TOOLS_COVERAGE_ACTIVE")
    if _active:
        print("[gd-tools] Coverage tracking active")

func hit(file_id: int, line_id: int) -> void:
    if not _active:
        return
    var key: String = "%d:%d" % [file_id, line_id]
    _hits[key] = _hits.get(key, 0) + 1

func get_hits() -> Dictionary:
    return _hits.duplicate(true)

func reset() -> void:
    _hits.clear()

func is_active() -> bool:
    return _active
```

**Autoload registration in `project.godot`:**
```ini
[autoload]

_GDTCoverage="*res://addons/gd-tools-coverage/tracker.gd"
```

#### 6.5 Pre-Run Hook: `addons/gd-tools-coverage/pre_run_hook.gd`

Reads the instrumentation plan, injects `_GDTCoverage.hit(file_id, line_id)` calls before each tracked line (bottom-to-top to preserve line numbers), sets `script.source_code`, and calls `script.reload()`.

Key implementation details:
- Reads plan path from `GD_TOOLS_COVERAGE_PLAN` env var
- Injects tracker calls with matching indentation
- Sorts lines descending (bottom-to-top) to avoid line number shifts
- Stores original source for restoration on failure
- On `reload()` failure, restores original source and reloads

#### 6.6 Post-Run Hook: `addons/gd-tools-coverage/post_run_hook.gd`

Reads tracker hit data and serializes to JSON.

Key implementation details:
- Accesses tracker autoload via `SceneTree.root.get_node_or_null("_GDTCoverage")`
- Skips if tracker is not active
- Output path from `GD_TOOLS_COVERAGE_OUTPUT` env var (default: `user://coverage.json`)
- Writes JSON with version, timestamp, and hits dictionary

---

## 7. Expected Results

### Expected Instrumentation Output

Given `calculator.gd` and the plan, the pre_run_hook should produce:

```gdscript
extends RefCounted

## A simple calculator for spike testing.
##
## This file will be instrumented at runtime by the coverage spike.

func divide(a: float, b: float) -> Dictionary:
    _GDTCoverage.hit(0, 0)
    if b == 0.0:
        _GDTCoverage.hit(0, 1)
        return {"error": "division by zero"}
    else:
        _GDTCoverage.hit(0, 2)
        return {"result": a / b}
```

### Expected Coverage Data

After both tests run:

```json
{
  "version": 1,
  "generated_at": "2026-07-09T12:00:00Z",
  "hits": {
    "0:0": 2,
    "0:1": 1,
    "0:2": 1
  }
}
```

- `0:0` (if condition) — hit 2 times (both tests enter the function)
- `0:1` (if-true branch) — hit 1 time (`test_divide_by_zero`)
- `0:2` (else branch) — hit 1 time (`test_divide_normal`)

---

## 8. Fallback Plans

### Fallback 1: File Modification on Disk

**Trigger:** `reload()` doesn't update cached resources, or `source_code` modification doesn't take effect.

**Approach:** Python modifies `.gd` files on disk before launching Godot. Godot loads the modified files naturally. After tests complete, Python restores original files.

**Trade-off:** Simpler instrumentation, but modifies user's files. Need robust backup/restore mechanism. Risk of leaving files modified on crash.

### Fallback 2: Fork jamie-pate/godot-code-coverage

**Trigger:** Runtime instrumentation via Script API is fundamentally broken.

**Approach:** Fork jamie-pate's repository, update for Godot 4.5 API changes, keep Python reporting layer.

**Trade-off:** Depends on someone else's code. May have Godot 4.5 compatibility issues.

### Fallback 3: Architecture A (Pure Python)

**Trigger:** All runtime instrumentation approaches fail.

**Approach:** Python generates instrumented copies of all `.gd` files in a temp directory, modifies GUT config to point at temp directory, GUT runs tests against instrumented copies, Python reads coverage data. No GDScript addon needed.

**Trade-off:** Most invasive. Test files need to be redirected. Class name resolution may break. But simplest to implement and doesn't depend on Godot's Script API at all.

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `reload()` doesn't work in CLI mode | Low | Critical | Test early; Fallback 1 (file mod) doesn't need reload |
| Cached resource not updated after reload | Medium | Critical | Test with `load()` after reload; Fallback 1 bypasses caching |
| Injected code has syntax errors | Medium | Medium | Start with simple injection; validate with `reload()` return code |
| `preload()` const references not updated | Low | High | Test with both `preload` and `load` in test file |
| Autoload not accessible from instrumented code | Low | Medium | Test autoload access pattern early |
| String manipulation breaks indentation | Medium | Low | Use regex or careful whitespace handling; validate output |
| `source_code` empty for binary-tokenized scripts | Very Low | Low | Only affects exported projects; dev workflow uses source files |
| GUT doubles interfere with instrumentation | Medium | Medium | Test with doubled classes; doubles are separate scripts |

---

## 10. Deliverables

After the spike is executed, produce:

1. **Spike result report** — pass/fail for each success criterion, with evidence (stdout logs, coverage.json output)
2. **Updated architecture decision** — confirm Architecture C, or document which fallback was chosen and why
3. **Known limitations** — edge cases discovered during the spike that need handling in full implementation
4. **Estimated effort** — rough estimate for full coverage implementation based on spike learnings

---

## 11. Execution Environment

### Spike Project Structure

```
spike/
├── project.godot              # Godot 4.5 project, GUT + tracker autoload
├── addons/
│   ├── gut/                   # GUT (installed)
│   └── gd-tools-coverage/
│       ├── tracker.gd
│       ├── pre_run_hook.gd
│       └── post_run_hook.gd
├── scripts/
│   └── calculator.gd         # Target file to instrument
├── test/
│   └── test_calculator.gd    # GUT test
├── .gutconfig.json           # GUT config with hook paths
└── plan.json                 # Hand-written instrumentation plan
```

### Environment Variables

```
GD_TOOLS_COVERAGE_ACTIVE=1
GD_TOOLS_COVERAGE_PLAN=/absolute/path/to/plan.json
GD_TOOLS_COVERAGE_OUTPUT=/absolute/path/to/coverage.json
```

### Run Command

```bash
godot -s addons/gut/gut_cmdln.gd -d --path "$PWD" \
  -gpre_run_script="res://addons/gd-tools-coverage/pre_run_hook.gd" \
  -gpost_run_script="res://addons/gd-tools-coverage/post_run_hook.gd" \
  -gexit
```

---

## 12. Timeline

| Phase | Duration | Output |
|-------|----------|--------|
| Set up spike project (Godot + GUT + files) | 1-2 hours | Running GUT without coverage |
| Implement tracker + hooks | 2-3 hours | Instrumentation runs, data collected |
| Debug and validate | 1-2 hours | All success criteria pass |
| Document results | 1 hour | Spike result report |

**Total: ~1 day**

If the spike takes more than 2 days, it's a signal to evaluate fallback plans rather than continuing to debug.
