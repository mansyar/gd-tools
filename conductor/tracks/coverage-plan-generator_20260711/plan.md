<protect>
# Track 9: Coverage Plan Generator — Implementation Plan

## Phase 1: Data Structures & JSON I/O

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage-plan-generator_20260711/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Define plan data structures [baa3890]
    - [x] Write tests for `CoveragePlan`, `FilePlan`, `LinePlan` dataclasses (construction, field types, defaults)
    - [x] Implement dataclasses in `src/gd_tools/coverage/plan_generator.py` with type hints and docstrings
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): define plan data structures`

- [x] Task: Implement `write_plan_json` serialization [baa3890]
    - [x] Write tests for `write_plan_json` — valid plan → correct JSON structure (version, generated_by, files array with file_id, path, source_hash, lines)
    - [x] Write test for `write_plan_json` — empty plan (no files) produces valid JSON with empty files array
    - [x] Implement `write_plan_json(plan, output_path) -> None`
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): implement write_plan_json`

- [x] Task: Implement `read_plan_json` deserialization with error handling [baa3890]
    - [x] Write test for `read_plan_json` — valid JSON file → correct `CoveragePlan` object
    - [x] Write test for `read_plan_json` — missing file raises `CoveragePlanError`
    - [x] Write test for `read_plan_json` — invalid JSON raises `CoveragePlanError`
    - [x] Write test for `read_plan_json` — schema mismatch (wrong version, missing required fields) raises `CoveragePlanError`
    - [x] Write test for `read_plan_json` — round-trip (write then read produces equal plan)
    - [x] Implement `read_plan_json(path) -> CoveragePlan` with validation
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): implement read_plan_json with validation`

- [ ] Task: Conductor - User Manual Verification 'Data Structures & JSON I/O' (Protocol in workflow.md)

## Phase 2: GDScript Test Fixtures

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage-plan-generator_20260711/spec.md`
    - [ ] Read `conductor/workflow.md`

- [ ] Task: Create 6 GDScript fixture files
    - [ ] Create `tests/fixtures/gdscript/simple.gd` — basic statements (expr_stmt, return_stmt), var/const declarations
    - [ ] Create `tests/fixtures/gdscript/branches.gd` — if/elif/else branches, nested if/else
    - [ ] Create `tests/fixtures/gdscript/loops.gd` — for, while, for_typed with range
    - [ ] Create `tests/fixtures/gdscript/match_stmt.gd` — match with 4 cases
    - [ ] Create `tests/fixtures/gdscript/nested.gd` — deeply nested control flow (for→if→if→match→continue)
    - [ ] Create `tests/fixtures/gdscript/edge_cases.gd` — pass, break, continue, ternary, signal/enum, empty function
    - [ ] Verify fixtures are valid GDScript (parse with `gdtoolkit.parser.parse`)
    - [ ] Commit: `test(coverage): add GDScript fixture files for plan generator`

- [ ] Task: Conductor - User Manual Verification 'GDScript Test Fixtures' (Protocol in workflow.md)

## Phase 3: AST Parsing & Statement Classification

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage-plan-generator_20260711/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Implement `parse_gdscript` function [baa3890]
    - [x] Write test for `parse_gdscript` — valid source returns Lark Tree with metadata
    - [x] Write test for `parse_gdscript` — empty string returns valid tree
    - [x] Implement `parse_gdscript(source) -> Tree` using `gdtoolkit.parser.parse(source, gather_metadata=True)`
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): implement parse_gdscript`

- [x] Task: Implement `CoverageVisitor` — statement classification [baa3890]
    - [x] Write test: `test_assignment_is_expr_stmt` — `var x = 5` produces an `expr_stmt` trackable point
    - [x] Write test: `test_func_var_with_assignment_tracked` — `func_var_assigned`, `func_var_typed_assgnd`, `func_var_inf` all tracked
    - [x] Write test: `test_declarations_not_tracked` — `const_stmt`, `class_var_stmt`, `signal_stmt`, `enum_stmt`, `func_var_empty`, `func_var_typed` NOT tracked
    - [x] Write test: `test_empty_file_produces_empty_plan` — source with only declarations produces zero trackable points
    - [x] Implement `CoverageVisitor` class with statement methods: `expr_stmt`, `return_stmt`, `func_var_assigned`, `func_var_typed_assgnd`, `func_var_inf`, `break_stmt`, `continue_stmt`
    - [x] Implement `_add_point(tree, type, branch_type=None)` helper with per-file ID counter
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): implement CoverageVisitor statement classification`

- [x] Task: Implement `CoverageVisitor` — branch classification [baa3890]
    - [x] Write test: `test_if_else_produces_two_branch_entries` — if/else produces `if_true` and `if_false` branch points
    - [x] Write test: `test_elif_produces_additional_branch` — elif adds `elif_true` branch point
    - [x] Write test: `test_while_loop_body_tracked` — while produces `loop_body` branch point
    - [x] Write test: `test_for_loop_body_tracked` — for and for_typed produce `loop_body` branch points
    - [x] Write test: `test_match_each_case_tracked` — each match branch produces `match_case` branch point
    - [x] Write test: `test_nested_control_flow` — nested branches produce correct branch types and unique IDs
    - [x] Write test: `test_branch_ids_are_unique_per_file` — all IDs within a file are unique
    - [x] Implement branch methods in `CoverageVisitor`: `if_stmt` (iterates if_branch/elif_branch/else_branch), `while_stmt`, `for_stmt`, `for_stmt_typed`, `match_stmt` (iterates match_branch)
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): implement CoverageVisitor branch classification`

- [ ] Task: Conductor - User Manual Verification 'AST Parsing & Statement Classification' (Protocol in workflow.md)

## Phase 4: File Discovery & Plan Generation

- [x] Task: Read spec.md and workflow.md before starting this phase
    - [x] Read `conductor/tracks/coverage-plan-generator_20260711/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Implement `generate_plan` function [baa3890]
    - [x] Write test: `test_multiple_files_in_project` — multiple .gd files produce multiple `FilePlan` entries with sequential `file_id`s
    - [ ] Write test: `test_plan_generation_matches_expected` (parametrized across all 6 fixtures) — generated plan matches expected JSON fixture for each *(deferred to Phase 4 Task 3 after fixtures created)*
    - [x] Write test: `test_source_hash_computed` — each file entry has correct `sha256:` prefixed source hash
    - [x] Write test: file discovery excludes `addons/` directory by default
    - [x] Write test: file discovery excludes `test_dirs` from coverage targets
    - [x] Write test: file paths use `res://` prefix
    - [x] Implement `generate_plan(project_root, source_dirs, exclude_dirs, test_dirs) -> CoveragePlan` — reuses `discover_gd_files()`, filters test_dirs, parses each file, runs `CoverageVisitor`, assembles `CoveragePlan` with sequential `file_id`s
    - [x] Verify tests pass and coverage >80% line / >70% branch
    - [x] Commit: `feat(coverage): implement generate_plan with file discovery`

- [ ] Task: Generate expected plan JSON fixtures
    - [ ] Run `generate_plan` against each of the 6 `.gd` fixtures
    - [ ] Manually verify each generated plan JSON matches expected line IDs, branch types, and IDs
    - [ ] Write verified outputs to `tests/fixtures/plans/simple.expected.json`, `branches.expected.json`, `loops.expected.json`, `match_stmt.expected.json`, `nested.expected.json`, `edge_cases.expected.json`
    - [ ] Commit: `test(coverage): add expected plan JSON fixtures`

- [ ] Task: Conductor - User Manual Verification 'File Discovery & Plan Generation' (Protocol in workflow.md)

## Phase 5: Fixture Generation Tool

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage-plan-generator_20260711/spec.md`
    - [ ] Read `conductor/workflow.md`

- [ ] Task: Implement `tools/generate_expected_plans.py`
    - [ ] Write test: script runs and regenerates all 6 expected plan JSON fixtures from `.gd` fixtures
    - [ ] Write test: regenerated fixtures match committed fixtures (no drift)
    - [ ] Implement `tools/generate_expected_plans.py` — reads `.gd` fixtures, runs `generate_plan`, writes to `tests/fixtures/plans/`
    - [ ] Verify tests pass and coverage >80% line / >70% branch
    - [ ] Commit: `feat(coverage): add fixture generation script`

- [ ] Task: Conductor - User Manual Verification 'Fixture Generation Tool' (Protocol in workflow.md)

## Phase 6: Performance & Final Quality

- [ ] Task: Read spec.md and workflow.md before starting this phase
    - [ ] Read `conductor/tracks/coverage-plan-generator_20260711/spec.md`
    - [ ] Read `conductor/workflow.md`

- [ ] Task: Performance benchmark
    - [ ] Write test: `test_performance_100_files` — generate plan for 100 .gd files completes in <1 second
    - [ ] Create 100-file benchmark fixture (or use tmp_path with generated files)
    - [ ] Verify benchmark passes
    - [ ] Commit: `test(coverage): add performance benchmark`

- [ ] Task: Final quality gate verification
    - [ ] Run full test suite: `CI=true pytest` — all tests pass
    - [ ] Verify `plan_generator.py` coverage >80% line / >70% branch
    - [ ] Run `ruff check src/gd_tools/coverage/plan_generator.py` — passes
    - [ ] Run `ruff check tests/unit/test_plan_generator.py` — passes
    - [ ] Run `black --check src/gd_tools/coverage/plan_generator.py` — passes
    - [ ] Run `black --check tests/unit/test_plan_generator.py` — passes
    - [ ] Commit (if any formatting fixes needed): `style(coverage): format plan_generator code`

- [ ] Task: Conductor - User Manual Verification 'Performance & Final Quality' (Protocol in workflow.md)
</protect>
