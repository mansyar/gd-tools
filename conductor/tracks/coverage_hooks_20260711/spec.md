# Track 11: Coverage Hooks (Instrumentation Engine)

## Overview

This track implements the GUT pre-run and post-run hooks that form the core instrumentation engine of the coverage system. The `pre_run_hook.gd` reads a coverage plan JSON, injects `_GDTCoverage.hit(file_id, line_id)` calls into GDScript source code at runtime, and reloads the modified scripts. The `post_run_hook.gd` collects hit data from the coverage tracker, serializes it to JSON, and writes it to the output path.

This is the core innovation of the gd-tools coverage system: runtime source code instrumentation via Godot's `reload()` mechanism. The approach was validated in the Spike (Track 0, Architecture C) and builds upon the plan format (Track 9) and coverage tracker (Track 10).

**Phase:** 3 — MVP2  
**Risk:** HIGH — core innovation, source injection + reload  
**Effort:** 3-4 days  
**Dependencies:** Track 0 (spike), Track 9 (plan generator), Track 10 (tracker)

## Functional Requirements

### FR-1: pre_run_hook.gd — Plan Loading
- The hook MUST read the plan path from the `GD_TOOLS_COVERAGE_PLAN` environment variable.
- The hook MUST parse the plan JSON and validate it contains the expected structure: `{version, files: [{file_id, path, lines: [{line, id, ...}]}]}`.
- If the env var is not set or empty, the hook MUST log a clear warning and exit without instrumentation.
- If the plan JSON cannot be read or parsed, the hook MUST log a clear error with Cause/Fix hints and abort.

### FR-2: pre_run_hook.gd — Source Code Instrumentation
- For each file entry in the plan, the hook MUST:
  1. Load the script using `load()`.
  2. Retrieve the current `source_code`.
  3. Inject `_GDTCoverage.hit(file_id, line_id)` calls before each tracked line.
  4. Set the modified `source_code` back on the script.
  5. Call `reload()` on the script to activate the instrumented code.
- Injection MUST proceed bottom-to-top (descending line order) to preserve line number correctness.
- Injected code MUST match the indentation of the surrounding context.
- If `load()` fails for a file, the hook MUST log an error (Cause/Fix format) and skip that file.
- If `reload()` fails for a file, the hook MUST log an error and skip that file. Previously instrumented files remain instrumented.

### FR-3: pre_run_hook.gd — Tracker Activation
- After all files are instrumented, the hook MUST activate the coverage tracker by calling `_GDTCoverage.set_active(true)`.
- This ensures the tracker only records hits after instrumentation is complete.

### FR-4: post_run_hook.gd — Data Collection
- The hook MUST retrieve the `_GDTCoverage` autoload singleton from the SceneTree.
- The hook MUST call `get_data()` on the tracker to retrieve hit counts.
- If the tracker is not found (autoload missing), the hook MUST log a clear error with Cause/Fix hints and abort.

### FR-5: post_run_hook.gd — JSON Serialization and Output
- The hook MUST read the output path from the `GD_TOOLS_COVERAGE_OUTPUT` environment variable.
- The hook MUST serialize coverage data to JSON with the structure: `{version, generated_at, files: [{file_id, hits: {"line_id": count}}]}`.
- The hook MUST create parent directories if they do not exist.
- The hook MUST write the JSON to the output path with human-readable indentation.
- If the output path is not set or the file cannot be written, the hook MUST log a clear error with Cause/Fix hints.

### FR-6: post_run_hook.gd — Summary Logging
- The hook MUST log a summary to stdout including: total files instrumented, total lines tracked, and output path.

## Non-Functional Requirements

### NFR-1: Error Handling
- All error messages MUST be actionable with Cause/Fix hints (per product guidelines).
- All error messages MUST be ASCII-only (no emoji, per product guidelines).
- Errors in one file MUST NOT prevent instrumentation of other files (fail-safe, skip-and-continue).

### NFR-2: Performance
- Instrumentation of 50 files MUST complete in under 5 seconds.
- JSON serialization and file output MUST complete in under 1 second.

### NFR-3: Code Quality
- GDScript code MUST follow PascalCase for classes, snake_case for functions/variables (per product guidelines).
- Both hooks MUST `extends GutHookScript` and use the `run()` entry point (per spike learnings).
- The hooks MUST work in headless mode (`godot -s ... --headless`).

### NFR-4: No Side Effects
- Source code modification happens in-memory only via `source_code` property and `reload()`.
- No restoration of original source is needed because the Godot process exits after test execution (validated by spike).
- Original project files on disk MUST NOT be modified.

## Acceptance Criteria

1. Plan JSON is read and parsed correctly from `GD_TOOLS_COVERAGE_PLAN`.
2. Each file in the plan is instrumented (source modified in-memory + reloaded).
3. Tracker calls (`_GDTCoverage.hit()`) fire during test execution, verified by hit data in output.
4. Coverage JSON is written to the correct path from `GD_TOOLS_COVERAGE_OUTPUT`.
5. No side effects on project files on disk (in-memory modification only, no restoration needed).
6. Instrumentation preserves code semantics — tests pass on instrumented code.
7. Indentation of injected code matches the surrounding context.
8. Compile errors in instrumented code are caught and reported clearly with Cause/Fix hints.
9. Works in headless mode (`godot --headless -s ... -gexit`).
10. Performance: instrumentation of 50 files completes in under 5 seconds.
11. GUT tests cover hook logic: plan parsing, tracker injection logic, JSON serialization.
12. Python integration tests verify end-to-end flow: env vars set -> Godot headless -> output JSON verified.

## Out of Scope

- Source code restoration after instrumentation (process exits, not needed — validated by spike).
- Branch coverage (deferred to future track).
- Coverage report generation/visualization (separate track).
- Integration with the CLI `coverage` command (separate track).
- Error recovery that restores previously instrumented files on mid-run failure (skip-and-continue is sufficient).
- Multi-file dependency ordering (files are independent; plan order is used).
