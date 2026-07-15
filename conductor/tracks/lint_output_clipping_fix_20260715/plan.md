<protect>
# Implementation Plan: Track 24.6 - Lint Output Clipping Fix

## Phase 1: TDD - Update Tests for New Format (Red Phase)

- [x] Task: Read `spec.md` and `conductor/workflow.md` to review requirements and TDD methodology before starting this phase
- [x] Task: Update unit tests in `tests/unit/test_lint_runner.py` for flat format
    - [x] Update `test_format_lint_text_with_violations` to assert on `file:line:col:` prefix instead of table column headers
    - [x] Update `test_format_lint_text_color_coding` to verify ANSI color codes present on severity tag (`[ERROR]` red, `[WARN]` yellow)
    - [x] Update `test_format_lint_text_summary` to assert colored summary (red for errors, yellow for warnings-only, green for clean)
    - [x] Update clean/no-files tests for green-colored `[OK]` message and unchanged `No GDScript files found.`

- [x] Task: Add new unit test case for long paths/rules not truncated
    - [x] Add `test_format_lint_text_long_paths_not_truncated` verifying a 76-char file path and 52-char rule name appear in full (no `…` character)

- [x] Task: Update integration test in `tests/integration/test_lint_integration.py`
    - [x] Update `test_lint_full_run_text_output` to remove truncation workaround comment and assert on full rule name and longer message fragment

- [x] Task: Run test suite and confirm Red phase (updated tests fail as expected, implementation not yet changed) [5299fe4]
    - [x] Run `CI=true pytest tests/unit/test_lint_runner.py tests/integration/test_lint_integration.py`
    - [x] Verify tests fail due to format mismatch (table output vs. expected flat format)

- [x] Task: Conductor - User Manual Verification 'TDD - Update Tests for New Format (Red Phase)' (Protocol in workflow.md) [checkpoint: f7e2b1a]

## Phase 2: TDD - Implement Flat Format (Green Phase)

- [x] Task: Read `spec.md` and `conductor/workflow.md` to review requirements and TDD methodology before starting this phase
- [x] Task: Replace Rich Table with flat line-based format in `format_lint_text` (`src/gd_tools/lint_runner.py`) [e3b1227]
    - [x] Remove `Table` import/usage and `console.capture()` block
    - [x] Replace `Console(force_terminal=True)` with plain `Console()`
    - [x] Render each issue as: `{file}:{line}:{col}: {rule}: {message}  [{SEVERITY}]`
    - [x] Style `[ERROR]` red and `[WARN]` yellow via Rich markup

- [x] Task: Implement issue sorting by file path, then line, then column [e3b1227]
    - [x] Combine errors and warnings into a single list
    - [x] Sort by `(file, line, column)` before rendering

- [x] Task: Implement summary line coloring [e3b1227]
    - [x] Color summary red if errors > 0
    - [x] Color summary yellow if only warnings (no errors)
    - [x] Color summary green if clean (no errors, no warnings)
    - [x] Color `[OK] No lint issues found.` green

- [x] Task: Run test suite and confirm Green phase (all tests pass) [e3b1227]
    - [x] Run `CI=true pytest tests/unit/test_lint_runner.py tests/integration/test_lint_integration.py`
    - [x] Verify all tests pass

- [x] Task: Conductor - User Manual Verification 'TDD - Implement Flat Format (Green Phase)' (Protocol in workflow.md) [checkpoint: 7f7c091]

## Phase 3: Quality Gates & Verification

- [ ] Task: Read `spec.md` and `conductor/workflow.md` to review requirements and TDD methodology before starting this phase
- [ ] Task: Verify code coverage meets requirements
    - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
    - [ ] Confirm >80% line coverage and >70% branch coverage for `lint_runner.py`

- [ ] Task: Run linting and formatting checks
    - [ ] Run `ruff check src/ tests/`
    - [ ] Run `black --check src/ tests/`

- [ ] Task: Run full test suite to confirm no regressions
    - [ ] Run `CI=true pytest`
    - [ ] Confirm all tests pass

- [ ] Task: Conductor - User Manual Verification 'Quality Gates & Verification' (Protocol in workflow.md)
</protect>
