<protect>
# Implementation Plan: Standardize Terminal Output

## Phase 1: Shared Output Module (FR-1) [checkpoint: f290132]

- [x] Task: Read spec.md and workflow.md for context
    - [x] Read `conductor/tracks/stdout_20260715/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write tests for `src/gd_tools/output.py`
    - [x] Create `tests/unit/test_output.py`
    - [x] Test `print_success(message)` renders `[OK]` marker in green
    - [x] Test `print_error(message)` renders `[FAIL]` marker in red
    - [x] Test `print_warning(message)` renders message in yellow
    - [x] Test `print_info(message)` renders message in cyan
    - [x] Test `print_summary(status, counts, files_checked, extra_info)` renders summary footer with correct color coding (green=pass, red=fail, yellow=warning)
    - [x] Test `print_table(table)` renders a Rich Table via shared console
    - [x] Test shared Console instance auto-detects terminal capabilities (no ANSI when piped)
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement `src/gd_tools/output.py` (9ec33d8)
    - [x] Create module with shared `Console` instance (or factory function)
    - [x] Implement `print_success(message)` — `[OK]` marker in green via `Text.assemble`
    - [x] Implement `print_error(message)` — `[FAIL]` marker in red via `Text.assemble`
    - [x] Implement `print_warning(message)` — yellow text
    - [x] Implement `print_info(message)` — cyan text
    - [x] Implement `print_summary(status, counts, files_checked, extra_info)` — summary footer with color based on status
    - [x] Implement `print_table(table)` — wrapper around `console.print(table)`
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/gd_tools/output.py` and `black --check src/gd_tools/output.py`
    - [x] Run `CI=true pytest --cov=gd_tools.output --cov-branch --cov-report=term-missing` and verify ≥80% line, ≥70% branch

- [x] Task: Conductor - User Manual Verification 'Shared Output Module' (Protocol in workflow.md)

## Phase 2: Lint Command Output Standardization (FR-2) [checkpoint: 494a919]

- [x] Task: Read spec.md and workflow.md for context
    - [x] Read `conductor/tracks/stdout_20260715/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write/update tests for lint output using shared module (080dc55)
    - [x] Update `tests/unit/test_lint_runner.py` — tests for `format_lint_text()` using shared output helpers
    - [x] Test that clean state uses `print_success()` with `[OK]` marker
    - [x] Test that summary footer uses `print_summary()` with correct status color
    - [x] Test that detail format remains `file:line:col: rule: message  [ERROR/WARN]`
    - [x] Test that JSON output (`format_lint_json()`) is unchanged
    - [x] Update `tests/unit/test_cli.py` — CLI integration tests for lint command output (no changes needed, existing tests pass)
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement lint output changes (080dc55)
    - [x] Refactor `format_lint_text()` in `src/gd_tools/lint_runner.py` to use shared `print_success()` for clean state
    - [x] Replace `Console().capture()` + inline `Text()` summary with shared `print_summary()` call
    - [x] Keep detail format unchanged (`file:line:col: rule: message  [ERROR/WARN]`)
    - [x] Keep `format_lint_json()` unchanged
    - [x] Update `src/gd_tools/cli.py` lint command to use shared console for output
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/gd_tools/lint_runner.py src/gd_tools/cli.py` and `black --check`
    - [x] Run `CI=true pytest tests/unit/test_lint_runner.py tests/unit/test_cli.py --cov-branch --cov-report=term-missing`

- [x] Task: Conductor - User Manual Verification 'Lint Command Output' (Protocol in workflow.md)

## Phase 3: Format Command Output Standardization (FR-3) [checkpoint: 86f6086]

- [x] Task: Read spec.md and workflow.md for context
    - [x] Read `conductor/tracks/stdout_20260715/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write/update tests for format output using shared module (4d8c8e7)
    - [x] Update `tests/unit/test_format_runner.py` — tests for format output using shared helpers (no changes needed, existing tests pass)
    - [x] Test `--check` mode: files needing format listed with `dim` style, summary via `print_summary()`
    - [x] Test `--diff` mode: diffs rendered via shared console with `Syntax`
    - [x] Test default mode: formatted count via `print_summary()`, clean state via `print_success()`
    - [x] Test "no files found" message
    - [x] Update `tests/unit/test_cli.py` — CLI integration tests for format command output
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement format output changes (4d8c8e7)
    - [x] Refactor `src/gd_tools/cli.py` format command to replace `click.echo()` with shared output helpers
    - [x] Use `print_success()` for "all files formatted" clean state
    - [x] Use `print_summary()` for file count summaries (formatted/checked, needing format/checked)
    - [x] Render file paths in `--check` mode with `dim` style via shared console
    - [x] Route `--diff` mode `Syntax` rendering through shared console
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/gd_tools/cli.py` and `black --check`
    - [x] Run `CI=true pytest tests/unit/test_format_runner.py tests/unit/test_cli.py --cov-branch --cov-report=term-missing`

- [x] Task: Conductor - User Manual Verification 'Format Command Output' (Protocol in workflow.md)

## Phase 4: Test Command Output Standardization (FR-4) [checkpoint: a55fcaf]

- [x] Task: Read spec.md and workflow.md for context
    - [x] Read `conductor/tracks/stdout_20260715/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write/update tests for test output using shared module (d0a2db7)
    - [x] Update `tests/unit/test_test_runner.py` — tests for `format_test_results()` using shared helpers
    - [x] Test summary table rendered via `print_table()`
    - [x] Test per-test failure details shown when tests fail (test name, suite, ✗ marker, message)
    - [x] Test per-test details NOT shown when all tests pass
    - [x] Test summary footer via `print_summary()` with pass/fail status
    - [x] Test clean state uses `print_success()` when all tests pass
    - [x] Test GUT stdout/stderr still printed on failure (truncated to 5000 chars)
    - [x] Update `tests/unit/test_cli.py` — CLI integration tests for test command output (no changes needed, existing tests pass)
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement test output changes (d0a2db7)
    - [x] Refactor `format_test_results()` in `src/gd_tools/test_runner.py` to use `print_table()` for summary table
    - [x] Add per-test failure detail rendering: list failed tests with name, suite, ✗ marker, and failure message
    - [x] Add `print_summary()` footer line below table with pass/fail status
    - [x] Use `print_success()` when all tests pass
    - [x] Keep GUT stdout/stderr on-failure behavior unchanged
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/gd_tools/test_runner.py` and `black --check`
    - [x] Run `CI=true pytest tests/unit/test_test_runner.py tests/unit/test_cli.py --cov-branch --cov-report=term-missing`

- [x] Task: Conductor - User Manual Verification 'Test Command Output' (Protocol in workflow.md)

## Phase 5: Coverage Command Output Standardization (FR-5)

- [x] Task: Read spec.md and workflow.md for context
    - [x] Read `conductor/tracks/stdout_20260715/spec.md`
    - [x] Read `conductor/workflow.md`

- [x] Task: Write/update tests for `coverage show` output
    - [x] Update `tests/unit/test_orchestrator.py` — tests for `show_coverage_summary()` using shared helpers
    - [x] Test Rich table with line coverage %, branch coverage %
    - [x] Test color-coded threshold status (green ≥ threshold, red < threshold)
    - [x] Test summary footer via `print_summary()` for threshold pass/fail
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement `coverage show` output changes
    - [x] Refactor `show_coverage_summary()` in `src/gd_tools/coverage/orchestrator.py` to render Rich table via `print_table()`
    - [x] Add line %, branch % columns with color coding
    - [x] Add threshold status column (green ≥ threshold, red < threshold)
    - [x] Use `print_summary()` for threshold pass/fail footer
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/gd_tools/coverage/orchestrator.py` and `black --check`
    - [x] Run `CI=true pytest tests/unit/test_orchestrator.py --cov-branch --cov-report=term-missing`

- [x] Task: Write/update tests for `test --coverage` inline summary
    - [x] Update `tests/unit/test_orchestrator.py` — tests for inline coverage summary (implemented in orchestrator's `run_coverage_test()`)
    - [x] Test coverage summary line printed after test summary table (line %, branch %)
    - [x] Test color coding by threshold (green ≥ threshold, red < threshold)
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement `test --coverage` inline summary
    - [x] Add `_print_coverage_inline()` in `orchestrator.py` — called by `run_coverage_test()` after `run_tests()` returns
    - [x] Print line %, branch % using `print_info()` / `print_summary()` with threshold color coding
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/gd_tools/coverage/orchestrator.py` and `black --check`
    - [x] Run `CI=true pytest tests/unit/test_orchestrator.py --cov-branch --cov-report=term-missing`

- [ ] Task: Conductor - User Manual Verification 'Coverage Command Output' (Protocol in workflow.md)

## Phase 6: Final Verification and Consistency Check (FR-6, FR-7, NFRs)

- [ ] Task: Read spec.md and workflow.md for context
    - [ ] Read `conductor/tracks/stdout_20260715/spec.md`
    - [ ] Read `conductor/workflow.md`

- [ ] Task: Verify cross-command consistency
    - [ ] Run full test suite: `CI=true pytest`
    - [ ] Run full coverage: `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
    - [ ] Verify ≥80% line, ≥70% branch coverage for all modified source code
    - [ ] Run lint: `ruff check src/ tests/`
    - [ ] Run format check: `black --check src/ tests/`
    - [ ] Verify JSON output modes unaffected (`--report-format json` for lint, `--junit-xml` for test)
    - [ ] Verify color semantics consistent across all four commands (green/red/yellow/cyan/dim)
    - [ ] Verify markers consistent across all four commands (`[OK]`, `[FAIL]`, `✓`, `✗`)

- [ ] Task: Conductor - User Manual Verification 'Final Verification and Consistency Check' (Protocol in workflow.md)
</protect>
