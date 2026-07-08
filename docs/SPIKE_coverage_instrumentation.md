# Spike: Runtime GDScript Instrumentation via Source Code Modification

**Document type:** Spike / Proof of Concept
**Date:** 2026-07-08
**Status:** Ready for execution
**Parent PRD:** `docs/PRD.md` (Section 10: Coverage Architecture)
**Risk level:** HIGH — this is the riskiest component of the entire project

---

## 1. Objective

Prove that GDScript files can be instrumented at runtime via Godot's `Script.source_code` property and `Script.reload()` method, and that the instrumented code executes correctly when GUT runs tests against it.

This spike validates the core hypothesis of Architecture C (Hybrid coverage). If it fails, we fall back to an alternative architecture before investing in full implementation.

---

## 2. Hypothesis

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

## 3. Scope

### In Scope

- One simple GDScript file with an `if/else` branch structure
- One GUT test that exercises both branches
- A tracker autoload (no-op when inactive)
- A `pre_run_hook` that instruments the file using string manipulation
- A `post_run_hook` that serializes tracker data to JSON
- Running the full flow via GUT CLI and verifying results

### Out of Scope

- Full Lark-based plan generation (Python side) — the spike uses a hand-written plan
- Branch coverage logic (only line/statement tracking in the spike)
- Multiple files, inheritance, inner classes, `@tool` scripts
- Performance benchmarking
- Report generation (HTML/LCOV/Cobertura)
- Error recovery / source restoration after crash
- The Python CLI itself

These are deferred to the Technical Design Document and implementation phases.

---

## 4. Architecture Under Test

```
┌─────────────────────────────────────────────────────┐
│ SPIKE COMPONENTS                                     │
│                                                     │
│  ┌─────────────┐    ┌──────────────┐              │
│  │ plan.json   │    │ tracker.gd   │              │
│  │ (hand-written)│    │ (autoload)   │              │
│  └──────┬──────┘    └──────┬───────┘              │
│         │                  │                        │
│         │    ┌─────────────▼────────────┐          │
│         └───►│ pre_run_hook.gd          │          │
│              │  1. Read plan            │          │
│              │  2. For each file:       │          │
│              │     - load script        │          │
│              │     - inject trackers    │          │
│              │     - source_code = mod  │          │
│              │     - reload()           │          │
│              └────────────┬─────────────┘          │
│                           │                        │
│              ┌────────────▼─────────────┐          │
│              │ GUT runs tests           │          │
│              │  (instrumented code      │          │
│              │   fires _GDTCoverage.hit)│          │
│              └────────────┬─────────────┘          │
│                           │                        │
│              ┌────────────▼─────────────┐          │
│              │ post_run_hook.gd         │          │
│              │  1. Read tracker hits    │          │
│              │  2. Serialize to JSON    │          │
│              │  3. Write to file        │          │
│              └──────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## 5. Components

### 5.1 Test Target: `scripts/calculator.gd`

A minimal GDScript file with both branches of an if/else:

```gdscript
extends RefCounted

## A simple calculator for spike testing.
##
## This file will be instrumented at runtime by the coverage spike.

func divide(self, a: float, b: float) -> Dictionary:
	if b == 0.0:
		return {"error": "division by zero"}
	else:
		return {"result": a / b}
```

**Why this file:** It has an `if/else` branch (both branches testable), a `return` in each branch, and is simple enough that instrumentation is straightforward.

### 5.2 GUT Test: `test/test_calculator.gd`

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

**Both tests must pass** — this proves original behavior is preserved after instrumentation.

### 5.3 Instrumentation Plan: `plan.json`

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

### 5.4 Tracker Autoload: `addons/gd-tools-coverage/tracker.gd`

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

Tracker="*res://addons/gd-tools-coverage/tracker.gd"
```

Wait — the autoload name matters. Instrumented code will reference it by the autoload name. We use `_GDTCoverage`:

```ini
[autoload]

_GDTCoverage="*res://addons/gd-tools-coverage/tracker.gd"
```

Then injected code calls `_GDTCoverage.hit(0, 1)`.

### 5.5 Pre-Run Hook: `addons/gd-tools-coverage/pre_run_hook.gd`

```gdscript
extends RefCounted

## GUT pre_run_hook — instruments scripts before tests run.
##
## Reads instrumentation plan, injects tracker calls into source,
## and reloads scripts.

const TRACKER_NAME = "_GDTCoverage"

var _plan: Dictionary = {}
var _instrumented_scripts: Array = []

func _init():
	var plan_path: String = OS.get_environment("GD_TOOLS_COVERAGE_PLAN")
	if plan_path.is_empty():
		push_warning("[gd-tools] No coverage plan path set, skipping instrumentation")
		return

	var file = FileAccess.open(plan_path, FileAccess.READ)
	if file == null:
		push_error("[gd-tools] Cannot read coverage plan: " + plan_path)
		return

	var json = JSON.new()
	var err = json.parse(file.get_as_text())
	if err != OK:
		push_error("[gd-tools] Invalid coverage plan JSON")
		return

	_plan = json.data
	file.close()

	_instrument_all()

func _instrument_all() -> void:
	for file_entry in _plan.get("files", []):
		var script_path: String = file_entry["path"]
		var file_id: int = file_entry["file_id"]
		var lines: Array = file_entry["lines"]

		_instrument_script(script_path, file_id, lines)

func _instrument_script(script_path: String, file_id: int, lines: Array) -> void:
	var script = load(script_path) as GDScript
	if script == null:
		push_error("[gd-tools] Cannot load script: " + script_path)
		return

	var original_source: String = script.source_code
	var instrumented_source = _inject_trackers(original_source, file_id, lines)

	# Store original for restoration (though we exit after tests anyway)
	_instrumented_scripts.append({"path": script_path, "original": original_source})

	# Apply instrumented source and reload
	script.source_code = instrumented_source
	var err = script.reload()
	if err != OK:
		push_error("[gd-tools] Reload failed for %s (error %d)" % [script_path, err])
		# Restore original on failure
		script.source_code = original_source
		script.reload()
		return

	print("[gd-tools] Instrumented: %s (%d points)" % [script_path, lines.size()])

func _inject_trackers(source: String, file_id: int, lines: Array) -> String:
	# Simple line-by-line injection.
	# Works bottom-to-top to avoid line number shifts.
	# Each line entry: {"line": N, "id": I, "type": "..."}
	#
	# Injects: _GDTCoverage.hit(file_id, line_id)
	# before the target line, with matching indentation.

	var source_lines = source.split("\n")

	# Sort lines descending (bottom-to-top)
	var sorted_lines = lines.duplicate()
	sorted_lines.sort_custom(func(a, b): return a["line"] > b["line"])

	for entry in sorted_lines:
		var line_num: int = entry["line"]  # 1-indexed
		var line_id: int = entry["id"]
		var idx: int = line_num - 1  # Convert to 0-indexed

		if idx < 0 or idx >= source_lines.size():
			push_warning("[gd-tools] Line %d out of range for file_id %d" % [line_num, file_id])
			continue

		# Get indentation of the target line
		var target_line: String = source_lines[idx]
		var indent: String = ""
		for ch in target_line:
			if ch == " " or ch == "\t":
				indent += ch
			else:
				break

		# Build tracker call
		var tracker_line: String = "%s%s.hit(%d, %d)" % [indent, TRACKER_NAME, file_id, line_id]

		# Insert before the target line
		source_lines.insert(idx, tracker_line)

	return "\n".join(source_lines)
```

### 5.6 Post-Run Hook: `addons/gd-tools-coverage/post_run_hook.gd`

```gdscript
extends RefCounted

## GUT post_run_hook — saves coverage data to JSON.

func _init():
	var tracker = _get_tracker()
	if tracker == null:
		push_error("[gd-tools] Tracker autoload not found")
		return

	if not tracker.is_active():
		return

	var output_path: String = OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")
	if output_path.is_empty():
		output_path = "user://coverage.json"

	var hits: Dictionary = tracker.get_hits()

	var data = {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(false, true),
		"hits": hits
	}

	var file = FileAccess.open(output_path, FileAccess.WRITE)
	if file == null:
		push_error("[gd-tools] Cannot write coverage output: " + output_path)
		return

	file.store_string(JSON.stringify(data, "  "))
	file.close()

	print("[gd-tools] Coverage data written to: %s" % output_path)
	print("[gd-tools] Total hit points: %d" % hits.size())

func _get_tracker() -> Node:
	# Access the autoload by name
	var tree = Engine.get_main_loop() as SceneTree
	if tree == null:
		return null
	return tree.root.get_node_or_null("_GDTCoverage")
```

---

## 6. Expected Instrumentation Result

Given `calculator.gd` and the plan, the pre_run_hook should produce:

```gdscript
extends RefCounted

## A simple calculator for spike testing.
##
## This file will be instrumented at runtime by the coverage spike.

func divide(self, a: float, b: float) -> Dictionary:
	_GDTCoverage.hit(0, 0)
	if b == 0.0:
		_GDTCoverage.hit(0, 1)
		return {"error": "division by zero"}
	else:
		_GDTCoverage.hit(0, 2)
		return {"result": a / b}
```

(Note: `self` parameter is a GDScript keyword issue — the test file should use a different name. Updated in the actual spike project.)

### Expected Coverage Data

After both tests run:

```json
{
  "version": 1,
  "generated_at": "2026-07-08T12:00:00Z",
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

## 7. Execution Plan

### Step 1: Create the spike project

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

### Step 2: Configure environment

Set environment variables before running:
```
GD_TOOLS_COVERAGE_ACTIVE=1
GD_TOOLS_COVERAGE_PLAN=/absolute/path/to/plan.json
GD_TOOLS_COVERAGE_OUTPUT=/absolute/path/to/coverage.json
```

### Step 3: Run the spike

```bash
godot -s addons/gut/gut_cmdln.gd -d --path "$PWD" \
  -gpre_run_script="res://addons/gd-tools-coverage/pre_run_hook.gd" \
  -gpost_run_script="res://addons/gd-tools-coverage/post_run_hook.gd" \
  -gexit
```

### Step 4: Verify results

1. Check Godot stdout for `[gd-tools] Instrumented: ...` message
2. Check both GUT tests passed (no test failures)
3. Check `coverage.json` was created
4. Verify hits match expected:
   - `0:0` → 2 (both tests)
   - `0:1` → 1 (divide by zero test)
   - `0:2` → 1 (normal division test)
5. Check no GDScript parse/compile errors in output

---

## 8. Success Criteria

| # | Criterion | Pass Condition | Failure Action |
|---|-----------|----------------|----------------|
| 1 | Source modification compiles | `script.reload()` returns `OK` | Check for syntax errors in injected code |
| 2 | Instrumented code executes | Tracker `_hits` dict is non-empty after test run | Verify reload updated cached resource |
| 3 | Correct lines recorded | Hits match expected values (0:0=2, 0:1=1, 0:2=1) | Debug injection positions |
| 4 | Original behavior preserved | Both GUT tests pass | Check instrumentation didn't alter logic |
| 5 | Coverage data serializable | `coverage.json` is valid JSON with correct structure | Debug JSON serialization in post_run_hook |
| 6 | Works in CLI mode | Entire spike runs via `godot -s ... -d` without editor | N/A — fundamental blocker |

### Overall Verdict

- **All 6 pass** → Architecture C is validated. Proceed to TDD and full implementation.
- **1-2 fail but fixable** → Fix the issue, re-run spike. Document the fix.
- **3+ fail or unfixable** → Execute fallback plan.

---

## 9. Fallback Plans

### Fallback 1: File Modification on Disk

**Trigger:** `reload()` doesn't update cached resources, or `source_code` modification doesn't take effect.

**Approach:**
- Python modifies `.gd` files on disk before launching Godot
- Godot loads the modified files naturally (no `source_code`/`reload()` needed)
- After tests complete, Python restores original files
- Pre/post run hooks only handle data collection, not instrumentation

**Trade-off:** Simpler instrumentation, but modifies user's files. Need robust backup/restore mechanism. Risk of leaving files modified on crash.

**Implementation change:** Python CLI does instrumentation (using gdtoolkit) → writes modified files → runs GUT → restores files. The GDScript addon only handles data collection.

### Fallback 2: Fork jamie-pate/godot-code-coverage

**Trigger:** Runtime instrumentation via Script API is fundamentally broken.

**Approach:**
- Fork jamie-pate's repository
- Update for Godot 4.5 API changes
- Use their instrumentation mechanism (whatever it is)
- Keep our Python reporting layer (plan generation + report generation)

**Trade-off:** Depends on someone else's code. Their instrumentation approach may be less robust than Lark-based parsing. May have Godot 4.5 compatibility issues.

### Fallback 3: Architecture A (Pure Python)

**Trigger:** All runtime instrumentation approaches fail.

**Approach:**
- Python generates instrumented copies of all `.gd` files in a temp directory
- Python modifies the GUT config to point at the temp directory
- GUT runs tests against the instrumented copies
- Python reads coverage data from the temp files
- No GDScript addon needed at all

**Trade-off:** Most invasive. Test files need to be redirected to instrumented copies. Class name resolution may break. But it's the simplest to implement and doesn't depend on Godot's Script API at all.

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `reload()` doesn't work in CLI mode | Low | Critical | Test early; Fallback 1 (file mod) doesn't need reload |
| Cached resource not updated after reload | Medium | Critical | Test with `load()` after reload; Fallback 1 bypasses caching |
| Injected code has syntax errors | Medium | Medium | Start with simple injection; validate with `reload()` return code |
| `preload()` const references not updated | Low | High | Test with both `preload` and `load` in test file |
| Autoload not accessible from instrumented code | Low | Medium | Test autoload access pattern early |
| String manipulation breaks indentation | Medium | Low | Use regex or careful whitespace handling; validate output |
| `source_code` empty for binary-tokenized scripts | Very Low | Low | Only affects exported projects; dev workflow uses source files |
| GUT doubles interfere with instrumentation | Medium | Medium | Test with doubled classes; doubles are separate scripts, shouldn't conflict |

---

## 11. Deliverables

After the spike is executed, produce:

1. **Spike result report** — pass/fail for each success criterion, with evidence (stdout logs, coverage.json output)
2. **Updated architecture decision** — confirm Architecture C, or document which fallback was chosen and why
3. **Known limitations** — edge cases discovered during the spike that need handling in full implementation
4. **Estimated effort** — rough estimate for full coverage implementation based on spike learnings

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
