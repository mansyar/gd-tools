# Implementation Plan: Track 4 — Lint Wrapper

## Phase 1: Data Models & Config Fix

- [ ] Task: Define `LintIssue` and `LintResult` dataclasses
    - [ ] Write tests for `LintIssue` dataclass (construction, field types, severity values)
    - [ ] Write tests for `LintResult` dataclass (construction, empty lists, files_checked)
    - [ ] Implement `LintIssue` and `LintResult` dataclasses in `src/gd_tools/lint_runner.py`
- [ ] Task: Fix `generate_gdlintrc()` to YAML set format
    - [ ] Write tests for YAML set format output (`excluded_directories: !!set { addons: null, ... }`)
    - [ ] Write tests that generated gdlintrc is valid YAML parseable by gdtoolkit
    - [ ] Implement YAML set format in `generate_gdlintrc()` in `src/gd_tools/config.py`
    - [ ] Verify existing config tests still pass (regression check)
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Data Models & Config Fix' (Protocol in workflow.md)

## Phase 2: File Discovery & Lint Runner Core

- [ ] Task: Implement file discovery function
    - [ ] Write tests for recursive `.gd` file collection (nested directories)
    - [ ] Write tests for case-insensitive `.gd` extension matching (`.GD`, `.Gd`)
    - [ ] Write tests for exclude directory filtering (skip `addons/`, `.godot/`, `.git/`, `.gd-tools/` by name)
    - [ ] Write tests for no `.gd` files found (returns empty list)
    - [ ] Implement `discover_gd_files(path, excludes)` in `src/gd_tools/lint_runner.py`
- [ ] Task: Implement `run_lint()` core logic
    - [ ] Write tests for `run_lint` with clean files (no errors, no warnings, files_checked > 0)
    - [ ] Write tests for `run_lint` with lint errors (errors list populated, correct file/line/col/rule/message)
    - [ ] Write tests for `run_lint` with warnings (warnings list populated, severity=warning)
    - [ ] Write tests for `run_lint` respecting config excludes (excluded dirs not checked)
    - [ ] Write tests for `run_lint` with no `.gd` files (files_checked=0, empty lists, exit 0)
    - [ ] Implement `run_lint(config, path, report_format)` using gdtoolkit Python API import
- [ ] Task: Implement syntax error handling
    - [ ] Write tests for syntax error in a `.gd` file (reported as rule=SYNTAX_ERROR, severity=error)
    - [ ] Write tests for syntax error does not crash — continues linting other files
    - [ ] Write tests for syntax error results in exit code 1
    - [ ] Implement syntax error catch-and-report in `run_lint()`
- [ ] Task: Conductor - User Manual Verification 'Phase 2: File Discovery & Lint Runner Core' (Protocol in workflow.md)

## Phase 3: Output Formatting

- [ ] Task: Implement rich table terminal output
    - [ ] Write tests for text output with violations (table columns: File, Line, Column, Rule, Severity, Message)
    - [ ] Write tests for color coding (red for errors, yellow for warnings)
    - [ ] Write tests for summary line (X errors, Y warnings, Z files checked)
    - [ ] Write tests for clean files output (success message, exit 0)
    - [ ] Write tests for no `.gd` files output (informational message "No GDScript files found.")
    - [ ] Implement `format_lint_text(result)` using `rich.table.Table`
- [ ] Task: Implement JSON output format
    - [ ] Write tests for JSON output schema (`files_checked`, `errors[]`, `warnings[]` arrays)
    - [ ] Write tests for JSON serialization of `LintIssue` objects (all fields present)
    - [ ] Write tests for JSON output with no violations (empty arrays, not null)
    - [ ] Implement `format_lint_json(result)` returning valid JSON string
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Output Formatting' (Protocol in workflow.md)

## Phase 4: CLI Integration

- [ ] Task: Update `lint` command in `src/gd_tools/cli.py`
    - [ ] Write tests for `lint` command with default path (no path arg → defaults to `.`)
    - [ ] Write tests for `lint` command with `--report-format json`
    - [ ] Write tests for `lint` command with `--report-format text` (default)
    - [ ] Write tests for `--fix` flag (no-op, prints warning that gdlint is read-only)
    - [ ] Write tests for exit codes (0 clean, 1 lint errors, 2 config/env error)
    - [ ] Write tests for `lint` command wired to `run_lint()` end-to-end
    - [ ] Update `lint` command: `path` → `required=False, default="."`, add `click.Choice(["text","json"])` + `default="text"`, add `--fix` no-op flag, wire to `run_lint()` + formatters
    - [ ] Update `test_lint_stub_exit_code_2` test (replace stub behavior with real command tests)
- [ ] Task: Conductor - User Manual Verification 'Phase 4: CLI Integration' (Protocol in workflow.md)

## Phase 5: Integration Tests & Coverage

- [ ] Task: Integration tests with fixture `.gd` files
    - [ ] Create fixture `.gd` files in `tests/fixtures/` (clean file, file with errors, file with warnings, syntax error file)
    - [ ] Write integration test: full `lint` run on fixture project (text output)
    - [ ] Write integration test: full `lint` run on fixture project (JSON output)
    - [ ] Write integration test: excludes respected on fixture project (addon dir with `.gd` files skipped)
    - [ ] Write integration test: `--fix` flag no-op behavior
- [ ] Task: Coverage and code quality verification
    - [ ] Run `pytest --cov=gd_tools.lint_runner` — verify >80% line coverage
    - [ ] Run `ruff check src/gd_tools/lint_runner.py` — verify no lint issues
    - [ ] Run `black --check src/gd_tools/lint_runner.py` — verify formatting
    - [ ] Run full test suite — verify no regressions
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Integration Tests & Coverage' (Protocol in workflow.md)
