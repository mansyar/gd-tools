# Implementation Plan: Track 24.6 - Lint Output Clipping Fix

## Phase 1: TDD - Update Tests for New Format (Red Phase)

- [ ] Task: Update unit tests in `tests/unit/test_lint_runner.py` for flat format
    - [ ] Update `test_format_lint_text_with_violations` to assert on `file:line:col:` prefix instead of table column headers
    - [ ] Update `test_format_lint_text_color_coding` to verify ANSI color codes present on severity tag (`[ERROR]` red, `[WARN]` yellow)
    - [ ] Update `test_format_lint_text_summary` to assert colored summary (red for errors, yellow for warnings-only, green for clean)
    - [ ] Update clean/no-files tests for green-colored `[OK]` message and unchanged `No GDScript files found.`

- [ ] Task: Add new unit test case for long paths/rules not truncated
    - [ ] Add `test_format_lint_text_long_paths_not_truncated` verifying a 76-char file path and 52-char rule name appear in full (no `…` character)

- [ ] Task: Update integration test in `tests/integration/test_lint_integration.py`
    - [ ] Update `test_lint_full_run_text_output` to remove truncation workaround comment and assert on full rule name and longer message fragment

- [ ] Task: Run test suite and confirm Red phase (updated tests fail as expected, implementation not yet changed)
    - [ ] Run `CI=true pytest tests/unit/test_lint_runner.py tests/integration/test_lint_integration.py`
    - [ ] Verify tests fail due to format mismatch (table output vs. expected flat format)

- [ ] Task: Conductor - User Manual Verification 'TDD - Update Tests for New Format (Red Phase)' (Protocol in workflow.md)

## Phase 2: TDD - Implement Flat Format (Green Phase)

- [ ] Task: Replace Rich Table with flat line-based format in `format_lint_text` (`src/gd_tools/lint_runner.py`)
    - [ ] Remove `Table` import/usage and `console.capture()` block
    - [ ] Replace `Console(force_terminal=True)` with plain `Console()`
    - [ ] Render each issue as: `{file}:{line}:{col}: {rule}: {message}  [{SEVERITY}]`
    - [ ] Style `[ERROR]` red and `[WARN]` yellow via Rich markup

- [ ] Task: Implement issue sorting by file path, then line, then column
    - [ ] Combine errors and warnings into a single list
    - [ ] Sort by `(file, line, column)` before rendering

- [ ] Task: Implement summary line coloring
    - [ ] Color summary red if errors > 0
    - [ ] Color summary yellow if only warnings (no errors)
    - [ ] Color summary green if clean (no errors, no warnings)
    - [ ] Color `[OK] No lint issues found.` green

- [ ] Task: Run test suite and confirm Green phase (all tests pass)
    - [ ] Run `CI=true pytest tests/unit/test_lint_runner.py tests/integration/test_lint_integration.py`
    - [ ] Verify all tests pass

- [ ] Task: Conductor - User Manual Verification 'TDD - Implement Flat Format (Green Phase)' (Protocol in workflow.md)

## Phase 3: Quality Gates & Verification

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
