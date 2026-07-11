<protect>
# Implementation Plan: Coverage Hooks (Instrumentation Engine)

## Phase 1: Project Setup

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [ ] Read `conductor/workflow.md` for TDD methodology and quality gates
- [ ] Task: Create pre_run_hook.gd stub
    - [ ] Create `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`
    - [ ] Add `extends GutHookScript` and empty `run()` method
- [ ] Task: Create post_run_hook.gd stub
    - [ ] Create `src/gd_tools/addons/gd-tools-coverage/post_run_hook.gd`
    - [ ] Add `extends GutHookScript` and empty `run()` method
- [ ] Task: Set up GUT test fixtures for hooks
    - [ ] Create test directory `src/gd_tools/addons/gd-tools-coverage/tests/`
    - [ ] Create fixture GDScript files for instrumentation targets
    - [ ] Create fixture plan JSON files for testing
- [ ] Task: Set up Python integration test structure
    - [ ] Create `tests/integration/test_coverage_hooks.py`
    - [ ] Create fixture Godot project for end-to-end tests
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Project Setup' (Protocol in workflow.md)

## Phase 2: pre_run_hook.gd — Plan Loading (TDD)

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [ ] Read `conductor/workflow.md` for TDD methodology and quality gates
- [ ] Task: Write GUT tests for plan loading (Red)
    - [ ] Test: env var `GD_TOOLS_COVERAGE_PLAN` not set -> warning logged, no instrumentation
    - [ ] Test: env var set to valid plan path -> plan parsed correctly, returns Dictionary with expected structure
    - [ ] Test: env var set to non-existent path -> error logged with Cause/Fix hints
    - [ ] Test: env var set to malformed JSON -> error logged with Cause/Fix hints
    - [ ] Test: plan with empty files array -> warning, no instrumentation
- [ ] Task: Implement plan loading in pre_run_hook.gd (Green)
    - [ ] Implement `run()` entry point: read env var, call `_load_plan()`
    - [ ] Implement `_load_plan(path) -> Dictionary`: open file, parse JSON, validate structure
    - [ ] Implement env var reading with empty/missing checks
    - [ ] Add error messages with Cause/Fix format per product guidelines
- [ ] Task: Refactor plan loading (Refactor)
    - [ ] Review code for clarity and consistency with product guidelines
    - [ ] Ensure all error messages are ASCII-only with Cause/Fix hints
- [ ] Task: Conductor - User Manual Verification 'Phase 2: pre_run_hook.gd — Plan Loading' (Protocol in workflow.md)

## Phase 3: pre_run_hook.gd — Source Instrumentation (TDD)

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [ ] Read `conductor/workflow.md` for TDD methodology and quality gates
- [ ] Task: Write GUT tests for `_extract_indent()` (Red)
    - [ ] Test: line with tab indentation -> returns tab characters
    - [ ] Test: line with space indentation -> returns space characters
    - [ ] Test: line with no indentation -> returns empty string
    - [ ] Test: line with mixed tabs and spaces -> returns all leading whitespace
- [ ] Task: Implement `_extract_indent()` (Green)
    - [ ] Implement static method to extract leading whitespace from a line
- [ ] Task: Write GUT tests for `_inject_trackers()` (Red)
    - [ ] Test: single line injection -> tracker call inserted before line with matching indent
    - [ ] Test: multiple lines injected bottom-to-top -> line numbers preserved
    - [ ] Test: indentation matches surrounding context for each injected line
    - [ ] Test: empty lines list -> source unchanged
    - [ ] Test: lines list with duplicate line numbers -> handled correctly
- [ ] Task: Implement `_inject_trackers()` (Green)
    - [ ] Implement static method: split source by lines, sort lines descending, insert tracker calls with matching indentation
- [ ] Task: Write GUT tests for `_instrument_file()` (Red)
    - [ ] Test: valid script path -> source modified, reload() called
    - [ ] Test: invalid script path -> error logged, file skipped, other files unaffected
    - [ ] Test: reload() failure -> error logged with Cause/Fix, file skipped
    - [ ] Test: file with no tracked lines -> source unchanged, reload() not called
- [ ] Task: Implement `_instrument_file()` (Green)
    - [ ] Implement: load script, get source_code, call `_inject_trackers()`, set source_code, call reload()
    - [ ] Add error handling: push_error on load failure, push_error on reload failure, skip file
- [ ] Task: Write GUT tests for tracker activation (Red)
    - [ ] Test: `_GDTCoverage.set_active(true)` called after all files instrumented
    - [ ] Test: tracker not activated if no files were instrumented
- [ ] Task: Implement tracker activation in `run()` (Green)
    - [ ] Call `_GDTCoverage.set_active(true)` after instrumentation loop completes
- [ ] Task: Refactor source instrumentation (Refactor)
    - [ ] Review injection logic for edge cases (empty source, single-line files)
    - [ ] Ensure error messages follow Cause/Fix format
- [ ] Task: Conductor - User Manual Verification 'Phase 3: pre_run_hook.gd — Source Instrumentation' (Protocol in workflow.md)

## Phase 4: post_run_hook.gd — Data Collection and Output (TDD)

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [ ] Read `conductor/workflow.md` for TDD methodology and quality gates
- [ ] Task: Write GUT tests for `_get_tracker()` (Red)
    - [ ] Test: `_GDTCoverage` autoload present -> returns tracker Node
    - [ ] Test: `_GDTCoverage` autoload missing -> error logged with Cause/Fix, returns null
- [ ] Task: Implement `_get_tracker()` (Green)
    - [ ] Implement: access `_GDTCoverage` autoload via SceneTree, return Node or null with error
- [ ] Task: Write GUT tests for `_build_coverage_json()` (Red)
    - [ ] Test: empty hits -> valid JSON structure with version and generated_at
    - [ ] Test: hits with data -> correct file_id and hit counts in output
    - [ ] Test: multiple files in hits -> all files present in output
- [ ] Task: Implement `_build_coverage_json()` (Green)
    - [ ] Implement: build Dictionary with version, generated_at, files array containing file_id and hits
- [ ] Task: Write GUT tests for `_write_json()` (Red)
    - [ ] Test: valid path -> file created with correct JSON content
    - [ ] Test: parent directories missing -> created automatically
    - [ ] Test: output path not set -> error logged with Cause/Fix
    - [ ] Test: path not writable -> error logged with Cause/Fix
- [ ] Task: Implement `_write_json()` (Green)
    - [ ] Implement: read env var, create parent dirs, serialize JSON with indentation, write to file
    - [ ] Add error handling for missing env var and write failures
- [ ] Task: Write GUT tests for summary logging (Red)
    - [ ] Test: summary contains total files instrumented
    - [ ] Test: summary contains total lines tracked
    - [ ] Test: summary contains output path
- [ ] Task: Implement summary logging in `run()` (Green)
    - [ ] Implement: log summary to stdout with file count, line count, output path
- [ ] Task: Implement `run()` entry point for post_run_hook.gd (Green)
    - [ ] Wire together: `_get_tracker()` -> `_build_coverage_json()` -> `_write_json()` -> summary log
- [ ] Task: Refactor data collection and output (Refactor)
    - [ ] Review code for clarity and error handling consistency
    - [ ] Ensure all error messages follow Cause/Fix format and are ASCII-only
- [ ] Task: Conductor - User Manual Verification 'Phase 4: post_run_hook.gd — Data Collection and Output' (Protocol in workflow.md)

## Phase 5: Python Integration Tests

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [ ] Read `conductor/workflow.md` for TDD methodology and quality gates
- [ ] Task: Write Python integration test for end-to-end flow
    - [ ] Set env vars: `GD_TOOLS_COVERAGE_PLAN`, `GD_TOOLS_COVERAGE_OUTPUT`, `GD_TOOLS_COVERAGE_ACTIVE`
    - [ ] Create fixture plan JSON with tracked lines
    - [ ] Run Godot headless with GUT hooks configured
    - [ ] Assert output JSON file exists at expected path
    - [ ] Assert output JSON has correct structure: version, generated_at, files array
    - [ ] Assert hit data contains expected line IDs with non-zero counts
- [ ] Task: Write Python integration test for error scenarios
    - [ ] Test: missing `GD_TOOLS_COVERAGE_PLAN` env var -> no instrumentation, warning in Godot output
    - [ ] Test: missing `GD_TOOLS_COVERAGE_OUTPUT` env var -> error in Godot output
    - [ ] Test: plan references non-existent script -> error logged, file skipped, other files still instrumented
    - [ ] Test: malformed plan JSON -> error logged, instrumentation aborted
- [ ] Task: Write Python integration test for headless mode
    - [ ] Test: full flow works with `--headless` flag
    - [ ] Test: Godot exits cleanly after tests with `-gexit`
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Python Integration Tests' (Protocol in workflow.md)

## Phase 6: Performance and Edge Cases

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [ ] Read `conductor/workflow.md` for TDD methodology and quality gates
- [ ] Task: Write performance test for 50-file instrumentation
    - [ ] Create fixture with 50 GDScript files, each with multiple tracked lines
    - [ ] Create plan JSON referencing all 50 files
    - [ ] Time the pre_run_hook instrumentation
    - [ ] Assert instrumentation completes in under 5 seconds
- [ ] Task: Test edge cases
    - [ ] Test: empty plan (no files) -> warning logged, no instrumentation, tracker not activated
    - [ ] Test: plan with files but no tracked lines -> files loaded, no injection, reload not called
    - [ ] Test: script with existing syntax errors -> error logged clearly, file skipped
    - [ ] Test: very long file (1000+ lines) with many tracked lines -> correct injection
- [ ] Task: Conductor - User Manual Verification 'Phase 6: Performance and Edge Cases' (Protocol in workflow.md)
</protect>
