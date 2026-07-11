<protect>
# Implementation Plan: Coverage Hooks (Instrumentation Engine)

## Phase 1: Project Setup [checkpoint: d1d0668]

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [x] Read `conductor/workflow.md` for TDD methodology and quality gates
- [x] Task: Create pre_run_hook.gd stub
    - [x] Create `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`
    - [x] Add `extends GutHookScript` and empty `run()` method
- [x] Task: Create post_run_hook.gd stub
    - [x] Create `src/gd_tools/addons/gd-tools-coverage/post_run_hook.gd`
    - [x] Add `extends GutHookScript` and empty `run()` method
- [x] Task: Set up GUT test fixtures for hooks
    - [x] Created GUT test stubs in `tests/fixtures/gdscript/test_pre_run_hook.gd` and `test_post_run_hook.gd` (existing `simple.gd` and `simple.expected.json` fixtures reused for instrumentation targets)
    - [x] Fixture plan JSON files already exist in `tests/fixtures/plans/` (simple.expected.json, etc.)
- [x] Task: Set up Python integration test structure
    - [x] Create `tests/integration/test_coverage_hooks.py` (skeleton with 5 test stubs, skip markers, and setup function)
    - [x] Reuses existing `tests/fixtures/projects/sample_project` fixture for end-to-end tests
- [x] Task: Conductor - User Manual Verification 'Phase 1: Project Setup' (Protocol in workflow.md)

## Phase 2: pre_run_hook.gd — Plan Loading (TDD)

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [x] Read `conductor/workflow.md` for TDD methodology and quality gates
- [x] Task: Write GUT tests for plan loading (Red) [4e5849e]
    - [x] Test: env var `GD_TOOLS_COVERAGE_PLAN` not set -> warning logged, no instrumentation
    - [x] Test: env var set to valid plan path -> plan parsed correctly, returns Dictionary with expected structure
    - [x] Test: env var set to non-existent path -> error logged with Cause/Fix hints
    - [x] Test: env var set to malformed JSON -> error logged with Cause/Fix hints
    - [x] Test: plan with empty files array -> warning, no instrumentation
- [x] Task: Implement plan loading in pre_run_hook.gd (Green) [4e5849e]
    - [x] Implement `run()` entry point: read env var, call `_load_plan()`
    - [x] Implement `_load_plan(path) -> Dictionary`: open file, parse JSON, validate structure
    - [x] Implement env var reading with empty/missing checks
    - [x] Add error messages with Cause/Fix format per product guidelines
- [x] Task: Refactor plan loading (Refactor) [4e5849e]
    - [x] Review code for clarity and consistency with product guidelines
    - [x] Ensure all error messages are ASCII-only with Cause/Fix hints
- [x] Task: Conductor - User Manual Verification 'Phase 2: pre_run_hook.gd — Plan Loading' [4e5849e]

## Phase 3: pre_run_hook.gd — Source Instrumentation (TDD)

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [x] Read `conductor/workflow.md` for TDD methodology and quality gates
- [x] Task: Write GUT tests for `_extract_indent()` (Red) [eb5a897]
    - [x] Test: line with tab indentation -> returns tab characters
    - [x] Test: line with space indentation -> returns space characters
    - [x] Test: line with no indentation -> returns empty string
    - [x] Test: line with mixed tabs and spaces -> returns all leading whitespace
- [x] Task: Implement `_extract_indent()` (Green) [eb5a897]
    - [x] Implement static method to extract leading whitespace from a line
- [x] Task: Write GUT tests for `_inject_trackers()` (Red) [eb5a897]
    - [x] Test: single line injection -> tracker call inserted before line with matching indent
    - [x] Test: multiple lines injected bottom-to-top -> line numbers preserved
    - [x] Test: indentation matches surrounding context for each injected line
    - [x] Test: empty lines list -> source unchanged
    - [x] Test: lines list with duplicate line numbers -> handled correctly
- [x] Task: Implement `_inject_trackers()` (Green) [eb5a897]
    - [x] Implement static method: split source by lines, sort lines descending, insert tracker calls with matching indentation
- [x] Task: Write GUT tests for `_instrument_file()` (Red) [eb5a897]
    - [x] Test: valid script path -> source modified, reload() called
    - [x] Test: invalid script path -> error logged, file skipped, other files unaffected
    - [x] Test: reload() failure -> error logged with Cause/Fix, file skipped
    - [x] Test: file with no tracked lines -> source unchanged, reload() not called
- [x] Task: Implement `_instrument_file()` (Green) [eb5a897]
    - [x] Implement: load script, get source_code, call `_inject_trackers()`, set source_code, call reload()
    - [x] Add error handling: push_error on load failure, push_error on reload failure, skip file
- [x] Task: Write GUT tests for tracker activation (Red) [eb5a897]
    - [x] Test: `_GDTCoverage.set_active(true)` called after all files instrumented
    - [x] Test: tracker not activated if no files were instrumented
- [x] Task: Implement tracker activation in `run()` (Green) [eb5a897]
    - [x] Call `_GDTCoverage.set_active(true)` after instrumentation loop completes
- [x] Task: Refactor source instrumentation (Refactor) [eb5a897]
    - [x] Review injection logic for edge cases (empty source, single-line files)
    - [x] Ensure error messages follow Cause/Fix format
- [x] Task: Conductor - User Manual Verification 'Phase 3: pre_run_hook.gd — Source Instrumentation' [eb5a897]

## Phase 4: post_run_hook.gd — Data Collection and Output (TDD)

- [x] Task: Read spec.md and workflow.md before starting this phase [5b119ec]
    - [x] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [x] Read `conductor/workflow.md` for TDD methodology and quality gates
- [x] Task: Write GUT tests for `_get_tracker()` (Red) [5b119ec]
    - [x] Test: `_GDTCoverage` autoload present -> returns tracker Node
    - [x] Test: `_GDTCoverage` autoload missing -> error logged with Cause/Fix, returns null
- [x] Task: Implement `_get_tracker()` (Green) [5b119ec]
    - [x] Implement: access `_GDTCoverage` autoload via SceneTree, return Node or null with error
- [x] Task: Write GUT tests for `_build_coverage_json()` (Red) [5b119ec]
    - [x] Test: empty hits -> valid JSON structure with version and generated_at
    - [x] Test: hits with data -> correct file_id and hit counts in output
    - [x] Test: multiple files in hits -> all files present in output
- [x] Task: Implement `_build_coverage_json()` (Green) [5b119ec]
    - [x] Implement: build Dictionary with version, generated_at, files array containing file_id and hits
- [x] Task: Write GUT tests for `_write_json()` (Red) [5b119ec]
    - [x] Test: valid path -> file created with correct JSON content
    - [x] Test: parent directories missing -> created automatically
    - [x] Test: output path not set -> error logged with Cause/Fix
    - [x] Test: path not writable -> error logged with Cause/Fix
- [x] Task: Implement `_write_json()` (Green) [5b119ec]
    - [x] Implement: read env var, create parent dirs, serialize JSON with indentation, write to file
    - [x] Add error handling for missing env var and write failures
- [x] Task: Write GUT tests for summary logging (Red) [5b119ec]
    - [x] Test: summary contains total files instrumented
    - [x] Test: summary contains total lines tracked
    - [x] Test: summary contains output path
- [x] Task: Implement summary logging in `run()` (Green) [5b119ec]
    - [x] Implement: log summary to stdout with file count, line count, output path
- [x] Task: Implement `run()` entry point for post_run_hook.gd (Green) [5b119ec]
    - [x] Wire together: `_get_tracker()` -> `_build_coverage_json()` -> `_write_json()` -> summary log
- [x] Task: Refactor data collection and output (Refactor) [5b119ec]
    - [x] Review code for clarity and error handling consistency
    - [x] Ensure all error messages follow Cause/Fix format and are ASCII-only
- [x] Task: Conductor - User Manual Verification 'Phase 4: post_run_hook.gd — Data Collection and Output' [5b119ec]

## Phase 5: Python Integration Tests

- [x] Task: Read spec.md and workflow.md before starting this phase [af3a36c]
    - [x] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [x] Read `conductor/workflow.md` for TDD methodology and quality gates
- [x] Task: Write Python integration test for end-to-end flow [af3a36c]
    - [x] Set env vars: `GD_TOOLS_COVERAGE_PLAN`, `GD_TOOLS_COVERAGE_OUTPUT`, `GD_TOOLS_COVERAGE_ACTIVE`
    - [x] Create fixture plan JSON with tracked lines
    - [x] Run Godot headless with GUT hooks configured
    - [x] Assert output JSON file exists at expected path
    - [x] Assert output JSON has correct structure: version, generated_at, files array
    - [x] Assert hit data contains expected line IDs with non-zero counts
- [x] Task: Write Python integration test for error scenarios [af3a36c]
    - [x] Test: missing `GD_TOOLS_COVERAGE_PLAN` env var -> no instrumentation, warning in Godot output
    - [x] Test: missing `GD_TOOLS_COVERAGE_OUTPUT` env var -> error in Godot output
    - [x] Test: plan references non-existent script -> error logged, file skipped, other files still instrumented
    - [x] Test: malformed plan JSON -> error logged, instrumentation aborted
- [x] Task: Write Python integration test for headless mode [af3a36c]
    - [x] Test: full flow works with `--headless` flag
    - [x] Test: Godot exits cleanly after tests with `-gexit`
- [x] Task: Conductor - User Manual Verification 'Phase 5: Python Integration Tests' (Protocol in workflow.md) [af3a36c]

## Phase 6: Performance and Edge Cases

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage_hooks_20260711/spec.md` for context
    - [x] Read `conductor/workflow.md` for TDD methodology and quality gates
- [x] Task: Write performance test for 50-file instrumentation [ed65874]
    - [x] Create fixture with 50 GDScript files, each with multiple tracked lines
    - [x] Create plan JSON referencing all 50 files
    - [x] Time the pre_run_hook instrumentation
    - [x] Assert instrumentation completes in under 5 seconds
- [x] Task: Test edge cases [ed65874]
    - [x] Test: empty plan (no files) -> warning logged, no instrumentation, tracker not activated
    - [x] Test: plan with files but no tracked lines -> files loaded, no injection, reload not called
    - [x] Test: script with existing syntax errors -> error logged clearly, file skipped
    - [x] Test: very long file (1000+ lines) with many tracked lines -> correct injection
- [x] Task: Conductor - User Manual Verification 'Phase 6: Performance and Edge Cases' (Protocol in workflow.md) [ed65874]

## Phase: Review Fixes
- [x] Task: Apply review suggestions [47ed18a]
</protect>
