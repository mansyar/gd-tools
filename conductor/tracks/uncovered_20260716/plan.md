<protect>
# Implementation Plan: Show Uncovered Lines and Branches in Coverage Output

## Phase 1: Data Model Enhancement [checkpoint: b7b714c]

- [x] Task: Read `spec.md` and `workflow.md` to align with current requirements and TDD methodology
- [x] Task: Add `uncovered_branches` field to `FileSummary` and update `compute_file_summary()` [76ad4b1]
    - [x] Write failing unit tests for `uncovered_branches` computation in `compute_file_summary()` — test that branch-type lines with zero hits are collected, and non-branch uncovered lines are excluded from this list
    - [x] Add `uncovered_branches: list[int]` field to `FileSummary` dataclass in `reporter.py`
    - [x] Update `compute_file_summary()` to compute `uncovered_branches` by cross-referencing the plan's branch-type lines against coverage hits
    - [x] Run tests and verify >80% line, >70% branch coverage for `reporter.py`
- [x] Task: Conductor - User Manual Verification 'Phase 1: Data Model Enhancement' (Protocol in workflow.md)

## Phase 2: Rendering Utilities [checkpoint: 98925a3]

- [x] Task: Read `spec.md` and `workflow.md` to align with current requirements and TDD methodology
- [x] Task: Implement line range formatting helper [e15f4ae]
    - [x] Write failing unit tests for range formatting: `[1,2,3,5,6]` → `"1-3, 5-6"`; `[]` → `""`; `[4]` → `"4"`; `[10,11,15]` → `"10-11, 15"`
    - [x] Implement `_format_line_ranges(lines: list[int]) -> str` helper function
    - [x] Run tests and verify coverage
- [x] Task: Implement uncovered detail panel rendering function [e15f4ae]
    - [x] Write failing unit tests for panel rendering — verify Rich panel content includes file path as title, uncovered line ranges, and branch annotations with type (e.g., `42 (if)`)
    - [x] Implement `_render_uncovered_panels(file_summaries, plan)` function using Rich `Panel`/`Group`
    - [x] Run tests and verify >80% line, >70% branch coverage for changed files
- [x] Task: Conductor - User Manual Verification 'Phase 2: Rendering Utilities' (Protocol in workflow.md)

## Phase 3: CLI Flag and Output Integration

- [x] Task: Read `spec.md` and `workflow.md` to align with current requirements and TDD methodology
- [x] Task: Add `--show-uncovered` flag to `test` CLI command [54a39bb]
    - [x] Write failing CLI tests for `--show-uncovered` flag (flag present with `--coverage`, flag absent, `--show-uncovered` without `--coverage`)
    - [x] Implement `--show-uncovered` option in `cli.py` `test` command with a descriptive `help` string for `--help` output, and thread `show_uncovered` parameter to `run_coverage_test()`
    - [x] Run tests and verify coverage
- [ ] Task: Integrate uncovered panels into `test --coverage` inline output (FR-1)
    - [ ] Write failing tests for `_print_coverage_inline()` with `show_uncovered=True` — verify panels are printed when coverage < 100% and omitted when 100%
    - [ ] Implement rendering call in `_print_coverage_inline()` when `show_uncovered` is True
    - [ ] Run tests and verify coverage
- [ ] Task: Integrate uncovered panels into `coverage show` output (FR-2)
    - [ ] Write failing tests for `show_coverage_summary()` — verify uncovered panels appear below the summary table when coverage < 100%
    - [ ] Implement rendering call in `show_coverage_summary()` to always show uncovered panels
    - [ ] Run tests and verify >80% line, >70% branch coverage for all changed files
- [ ] Task: Conductor - User Manual Verification 'Phase 3: CLI Flag and Output Integration' (Protocol in workflow.md)

## Phase 4: Documentation Updates

- [ ] Task: Read `spec.md` and `workflow.md` to align with current requirements and TDD methodology
- [ ] Task: Update documentation for `--show-uncovered` flag and enhanced `coverage show` output
    - [ ] Update README.md — add `--show-uncovered` to test command usage examples
    - [ ] Update docs/PRD.md — add `--show-uncovered` to the command reference flags table
    - [ ] Update docs/USER_GUIDE.md — add `--show-uncovered` usage example and sample uncovered panel output
    - [ ] Update skills/gd-tools/SKILL.md — add `--show-uncovered` to CLI flag documentation
    - [ ] Add CHANGELOG.md feature entry for uncovered lines/branches display
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Documentation Updates' (Protocol in workflow.md)
</protect>
