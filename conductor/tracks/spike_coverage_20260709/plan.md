# Implementation Plan: Coverage Instrumentation Spike

**Track ID:** `spike_coverage_20260709`
**Track Type:** Feature (Spike / Proof of Concept)
**Spec:** [./spec.md](./spec.md)
**Workflow:** [../../workflow.md](../../workflow.md)

---

## Overview

This plan implements a spike to validate the core hypothesis of Architecture C (Hybrid coverage): that GDScript files can be instrumented at runtime via `Script.source_code` modification and `Script.reload()`, and that the instrumented code executes correctly when GUT runs tests against it.

The spike is structured in 6 phases. Each phase follows the TDD workflow where practical (Red → Green → Refactor) for `.gd` source files. Integration-tested components are validated in Phase 6.

**Spike project location:** `spike/` (relative to project root)

---

## Phase 1: Spike Project Scaffolding [checkpoint: c359fb0]

> Create the Godot project structure, install GUT, and prepare the hand-written instrumentation plan.

- [x] Task: Create spike project directory structure [1cd1e13]
    - [x] Create `spike/` directory with subdirectories: `addons/`, `addons/gd-tools-coverage/`, `scripts/`, `test/`
- [x] Task: Create `spike/project.godot` with Godot 4.5 project configuration [52c9989]
    - [x] Configure project name, main scene (none needed for CLI), and renderer
    - [x] Add `_GDTCoverage` autoload entry pointing to `res://addons/gd-tools-coverage/tracker.gd`
    - [x] Verify: `project.godot` is valid Godot 4.5 config format
- [x] Task: Install GUT addon into spike project [d181297]
    - [x] Download or copy GUT addon into `spike/addons/gut/`
    - [x] Enable GUT plugin in `project.godot` (`[editor_plugins]` section)
    - [x] Verify: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -gexit` runs without error (GUT loads)
- [x] Task: Create hand-written instrumentation plan (`spike/plan.json`) [f0dd5d0]
    - [x] Write JSON with version, generated_by, files array
    - [x] Include `res://scripts/calculator.gd` with file_id 0 and 3 line entries (lines 8, 9, 11)
    - [x] Verify: `plan.json` is valid JSON (parse with `python -c "import json; json.load(open('spike/plan.json'))"`)

- [x] Task: Conductor - User Manual Verification 'Spike Project Scaffolding' (Protocol in workflow.md)

---

## Phase 2: Test Target (calculator.gd) — TDD [checkpoint: 9bb1715]

> Implement the calculator GDScript file using TDD. This is the file that will be instrumented. Both branches of the if/else must be exercised by tests.

- [x] Task: Write GUT test for calculator (Red Phase) [03da2e2]
    - [x] Create `spike/test/test_calculator.gd` extending `GutTest`
    - [x] Implement `before_each()` to load and instantiate `calculator.gd`
    - [x] Implement `after_each()` to clean up
    - [x] Write `test_divide_normal()` — asserts `result["result"] == 5.0` for `divide(10.0, 2.0)`
    - [x] Write `test_divide_by_zero()` — asserts `result["error"] == "division by zero"` for `divide(10.0, 0.0)`
    - [x] Run: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -gexit` and confirm tests FAIL (calculator.gd does not exist yet)
- [x] Task: Implement calculator.gd (Green Phase) [241b23f]
    - [x] Create `spike/scripts/calculator.gd` extending `RefCounted`
    - [x] Add class docstring: "A simple calculator for spike testing."
    - [x] Implement `func divide(a: float, b: float) -> Dictionary` with if/else branch
        - **Note:** Do NOT use `self` as a parameter name — it is a GDScript keyword
    - [x] If-true branch returns `{"error": "division by zero"}`
    - [x] Else branch returns `{"result": a / b}`
    - [x] Run: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -gexit` and confirm both tests PASS
- [x] Task: Verify GUT tests pass without instrumentation (baseline) [3f10582]
    - [x] Run GUT without any hooks
    - [x] Confirm exit code 0 and both tests passing
    - [x] Record baseline output for comparison after instrumentation

- [x] Task: Conductor - User Manual Verification 'Test Target Implementation' (Protocol in workflow.md)

---

## Phase 3: Tracker Autoload (tracker.gd) — TDD [checkpoint: e662560]

> Implement the coverage tracker singleton. It records hit counts per (file_id, line_id) pair and is no-op when inactive.

- [x] Task: Write GUT test for tracker (Red Phase) [9e83cd9]
    - [x] Create `spike/test/test_tracker.gd` extending `GutTest`
    - [x] Write `test_hit_records_count()` — call `hit(0, 1)` twice, assert `get_hits()["0:1"] == 2`
    - [x] Write `test_reset_clears_hits()` — call `hit(0, 1)`, then `reset()`, assert `get_hits()` is empty
    - [x] Write `test_get_hits_returns_copy()` — call `hit(0, 1)`, get hits, modify returned dict, assert tracker's internal dict unchanged
    - [x] Run: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -gexit -gselect=test_tracker` and confirm tests FAIL (tracker.gd does not exist yet)
- [x] Task: Implement tracker.gd (Green Phase) [77ca936]
    - [x] Create `spike/addons/gd-tools-coverage/tracker.gd` extending `Node`
    - [x] Add class docstring explaining autoload behavior and env var activation
    - [x] Implement `_ready()` — check `OS.has_environment("GD_TOOLS_COVERAGE_ACTIVE")`, set `_active`, print status
    - [x] Implement `hit(file_id: int, line_id: int)` — no-op if inactive, else increment `_hits["file_id:line_id"]` count
    - [x] Implement `get_hits()` — return `_hits.duplicate(true)` (deep copy)
    - [x] Implement `reset()` — clear `_hits`
    - [x] Implement `is_active()` — return `_active`
    - [x] Verify: `_GDTCoverage` autoload is registered in `project.godot` (from Phase 1)
    - [x] Run: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -gexit -gselect=test_tracker` and confirm all tests PASS
- [x] Task: Refactor tracker.gd (Optional) [480ffaa]
    - [x] Review code for clarity and consistency with GDScript style guide
    - [x] Ensure all public methods have docstrings
    - [x] Re-run tests to confirm still passing

- [x] Task: Conductor - User Manual Verification 'Tracker Autoload Implementation' (Protocol in workflow.md)

---

## Phase 4: Pre-Run Hook (pre_run_hook.gd) — TDD [checkpoint: 009ac8a]

> Implement the GUT pre_run_hook that reads the instrumentation plan, injects tracker calls into source code, and reloads scripts. The `_inject_trackers()` function is pure string manipulation and can be unit tested.

- [x] Task: Write GUT test for _inject_trackers (Red Phase) [2229913]
    - [x] Create `spike/test/test_pre_run_hook.gd` extending `GutTest`
    - [x] Load `pre_run_hook.gd` script (use `load("res://addons/gd-tools-coverage/pre_run_hook.gd")`)
    - [x] Write `test_inject_single_line()` — pass simple source + one line entry, assert tracker call inserted with correct indentation
    - [x] Write `test_inject_multiple_lines_preserves_order()` — pass source with 3 line entries, assert all injected, line numbers preserved
    - [x] Write `test_inject_bottom_to_top()` — verify injection goes bottom-to-top (line numbers don't shift)
    - [x] Write `test_inject_preserves_indentation()` — verify tracker call matches indentation of target line (tabs and spaces)
    - [x] Run tests and confirm they FAIL (pre_run_hook.gd does not exist yet)
- [x] Task: Implement pre_run_hook.gd (Green Phase) [681c2e5]
    - [x] Create `spike/addons/gd-tools-coverage/pre_run_hook.gd` extending `RefCounted`
    - [x] Add class docstring explaining GUT pre_run_hook purpose
    - [x] Define `const TRACKER_NAME = "_GDTCoverage"`
    - [x] Implement `_init()`:
        - [x] Read plan path from `OS.get_environment("GD_TOOLS_COVERAGE_PLAN")`
        - [x] If empty, warn and return (skip instrumentation)
        - [x] Open and parse JSON plan file
        - [x] On parse error, push error and return
        - [x] Call `_instrument_all()`
    - [x] Implement `_instrument_all()`:
        - [x] Iterate over `_plan["files"]` array
        - [x] Call `_instrument_script()` for each file entry
    - [x] Implement `_instrument_script(script_path, file_id, lines)`:
        - [x] `load()` the script as `GDScript`
        - [x] Get `script.source_code` (original)
        - [x] Call `_inject_trackers()` to produce instrumented source
        - [x] Store original source in `_instrumented_scripts` array for restoration
        - [x] Set `script.source_code = instrumented_source`
        - [x] Call `script.reload()` and check return code
        - [x] On reload failure: restore original source, reload, push error
        - [x] On success: print instrumentation summary
    - [x] Implement `_inject_trackers(source, file_id, lines)`:
        - [x] Split source into lines
        - [x] Sort line entries descending (bottom-to-top)
        - [x] For each entry: get target line, extract indentation, build tracker call, insert before target line
        - [x] Return joined source
    - [x] Run: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -gexit -gselect=test_pre_run_hook` and confirm all tests PASS
- [x] Task: Refactor pre_run_hook.gd (Optional) [e0d1f9f]
    - [x] Review code for clarity
    - [x] Ensure error messages follow product guidelines (actionable + fix hints)
    - [x] Re-run tests to confirm still passing

- [x] Task: Conductor - User Manual Verification 'Pre-Run Hook Implementation' (Protocol in workflow.md)

---

## Phase 5: Post-Run Hook (post_run_hook.gd) [checkpoint: ccd94e3]

> Implement the GUT post_run_hook that reads tracker hit data and serializes it to JSON. This component is simple (serialize dict to JSON) and validated primarily via integration in Phase 6.

- [x] Task: Implement post_run_hook.gd [9acbcb6]
    - [x] Create `spike/addons/gd-tools-coverage/post_run_hook.gd` extending `RefCounted`
    - [x] Add class docstring explaining GUT post_run_hook purpose
    - [x] Implement `_init()`:
        - [x] Get tracker autoload via `_get_tracker()` (access `SceneTree.root.get_node_or_null("_GDTCoverage")`)
        - [x] If tracker not found, push error and return
        - [x] If tracker not active, return silently
        - [x] Read output path from `OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")` (default: `user://coverage.json`)
        - [x] Get hits from `tracker.get_hits()`
        - [x] Build data dict: `{"version": 1, "generated_at": <ISO timestamp>, "hits": <hits>}`
        - [x] Open output file for writing
        - [x] Write `JSON.stringify(data, "  ")` to file
        - [x] Print summary: output path and total hit points
    - [x] Implement `_get_tracker()`:
        - [x] Get `Engine.get_main_loop()` as `SceneTree`
        - [x] Return `tree.root.get_node_or_null("_GDTCoverage")`
        - [x] Return null if SceneTree not available
    - [x] Verify: file exists and code has no syntax errors (load via `load()`)
    - [x] Note: Full validation of this hook occurs in Phase 6 integration test

- [x] Task: Conductor - User Manual Verification 'Post-Run Hook Implementation' (Protocol in workflow.md)

---

## Phase 6: Integration, Execution & Validation [checkpoint: b354382]

> Run the full spike flow end-to-end and validate all 6 success criteria. This is the critical validation phase.

- [x] Task: Configure `.gutconfig.json` with hook paths [723c816]
    - [x] Create `spike/.gutconfig.json`
    - [x] Configure `pre_run_script` to `res://addons/gd-tools-coverage/pre_run_hook.gd`
    - [x] Configure `post_run_script` to `res://addons/gd-tools-coverage/post_run_hook.gd`
    - [x] Configure test directory (`res://test/`)
    - [x] Configure exit after tests (`"exit": true`)
- [x] Task: Set up execution environment [6ad9c28]
    - [x] Set `GD_TOOLS_COVERAGE_ACTIVE=1`
    - [x] Set `GD_TOOLS_COVERAGE_PLAN` to absolute path of `spike/plan.json`
    - [x] Set `GD_TOOLS_COVERAGE_OUTPUT` to absolute path of `spike/coverage.json`
- [x] Task: Run full spike flow [6c3eaca]
    - [x] Execute: `godot --headless --path spike/ -s addons/gut/gut_cmdln.gd -d -gexit -gselect=test_calculator` (hooks via .gutconfig.json; -gselect to avoid tracker tests clearing coverage)
    - [x] Capture full stdout output to `spike/spike_output.log`
    - [x] Check for GDScript parse/compile errors in output (none found)
- [x] Task: Verify success criteria [6c3eaca]
    - [x] Criterion 1 (Source modification compiles): "[gd-tools] Instrumented: res://scripts/calculator.gd (3 lines)" - no errors
    - [x] Criterion 2 (Instrumented code executes): coverage.json exists, hits non-empty (3 hit points)
    - [x] Criterion 3 (Correct lines recorded): hits match `{"0:0": 2, "0:1": 1, "0:2": 1}`
    - [x] Criterion 4 (Original behavior preserved): 2 passing, 0 failing, "All tests passed!"
    - [x] Criterion 5 (Coverage data serializable): Valid JSON with version/generated_at/hits keys
    - [x] Criterion 6 (Works in CLI mode): Entire flow via godot -s ... -d without editor
- [x] Task: Document spike results [f75ab05]
    - [x] Write spike result report to `spike/SPIKE_RESULTS.md` — pass/fail for each criterion with evidence (stdout excerpts, coverage.json content)
    - [x] Record architecture decision — Architecture C CONFIRMED (all 6 criteria passed)
    - [x] Document known limitations discovered during the spike (7 limitations documented)
    - [x] Estimate effort for full coverage implementation (8-11 days estimated)

- [x] Task: Conductor - User Manual Verification 'Integration, Execution & Validation' (Protocol in workflow.md)
