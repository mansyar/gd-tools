<protect>

# Track 6: Test Runner (GUT Wrapper) — Implementation Plan

## Track ID
`test_runner_20260710`

## Spec Reference
See [spec.md](./spec.md) for full requirements.

## Overview

This plan implements `src/gd_tools/test_runner.py` following TDD methodology (Red → Green → Refactor → Verify). Each task follows the Standard Task Workflow from `workflow.md`: write failing tests, implement to pass, verify coverage, commit with git notes, update plan.

---

## Phase 1: Data Structures & Error Verification

- [ ] Task: Read spec.md and workflow.md before starting phase implementation
    - [ ] Read `conductor/tracks/test_runner_20260710/spec.md` to refresh requirements
    - [ ] Read `conductor/workflow.md` to review TDD lifecycle and quality gates

- [ ] Task: Define TestResult and TestDetail dataclasses
    - [ ] Write failing tests in `tests/test_test_runner.py` for `TestResult` dataclass (verify fields: total, passed, failed, skipped, duration, junit_xml_path, coverage_data_path, stdout, stderr, test_details)
    - [ ] Write failing tests for `TestDetail` dataclass (verify fields: name, suite, status, message, duration)
    - [ ] Implement `TestResult` and `TestDetail` dataclasses in `src/gd_tools/test_runner.py`
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Verify `GUTNotInstalledError` exists in `src/gd_tools/errors.py` (should exist from Track 1 — add if missing)
    - [ ] Verify `junitparser` is listed in `pyproject.toml` dependencies (should exist from Track 1 — add if missing)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch for `test_runner.py`
    - [ ] Commit with message `feat(test_runner): Define TestResult and TestDetail dataclasses`
    - [ ] Attach git note with task summary (files changed, key decisions)
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Conductor - User Manual Verification 'Data Structures & Error Verification' (Protocol in workflow.md)

---

## Phase 2: Core Functions (Argument Builder, GUT Check, JUnit Parser)

- [ ] Task: Read spec.md and workflow.md before starting phase implementation
    - [ ] Read `conductor/tracks/test_runner_20260710/spec.md` to refresh requirements
    - [ ] Read `conductor/workflow.md` to review TDD lifecycle and quality gates

- [ ] Task: Implement `build_gut_args()` — GUT CLI argument construction
    - [ ] Write failing tests for base command args (`-s addons/gut/gut_cmdln.gd -d --path <project_root> -gexit`)
    - [ ] Write failing tests for test dir args (`-gdirs=res://test/` conversion from config)
    - [ ] Write failing tests for prefix/suffix args (`-gprefix=test_`, `-gsuffix=.gd`)
    - [ ] Write failing tests for suite filter (`-gselect=<suite>` when `--suite` provided)
    - [ ] Write failing tests for test name filter (`-gname=<test_name>` when `--test` provided)
    - [ ] Write failing tests for JUnit XML path arg (`-gjunit_xml_file=<absolute_path>` — verify path is absolute)
    - [ ] Write failing tests for default JUnit XML path (`.gd-tools/results.xml` when not specified)
    - [ ] Implement `build_gut_args(config, project_root, suite, test_name, junit_xml, coverage) -> list[str]` in `test_runner.py`
    - [ ] Verify exact GUT CLI flag names against GUT 9.x documentation (spike used `.gutconfig.json` — verify CLI equivalents)
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(test_runner): Implement build_gut_args for GUT CLI construction`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Implement `check_gut_installed()` — proactive GUT presence verification
    - [ ] Write failing test: GUT present (`addons/gut/gut_cmdln.gd` exists) → returns True / no error
    - [ ] Write failing test: GUT missing → raises `GUTNotInstalledError` (exit code 2) with actionable message
    - [ ] Implement `check_gut_installed(project_root: Path) -> None` in `test_runner.py`
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(test_runner): Implement GUT installation check with GUTNotInstalledError`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Implement `parse_junit_xml()` — JUnit XML parsing with junitparser
    - [ ] Create fixture JUnit XML file in `tests/fixtures/junit/` (valid XML with pass/fail/skip test cases)
    - [ ] Write failing test: parse valid JUnit XML → correct totals (total/passed/failed/skipped)
    - [ ] Write failing test: parse valid JUnit XML → correct per-test details (name, suite, status, message, duration)
    - [ ] Write failing test: missing JUnit XML file → raises `GdToolsError` (exit code 2) with clear message
    - [ ] Write failing test: malformed/unparseable JUnit XML → raises `GdToolsError` (exit code 2)
    - [ ] Write failing test: empty test suite (0 tests) → returns zeroed TestResult fields
    - [ ] Implement `parse_junit_xml(path: Path) -> tuple[int, int, int, int, float, list[TestDetail]]` in `test_runner.py`
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(test_runner): Implement JUnit XML parsing with junitparser`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Conductor - User Manual Verification 'Core Functions' (Protocol in workflow.md)

---

## Phase 3: run_tests() Orchestration & Coverage Infrastructure

- [ ] Task: Read spec.md and workflow.md before starting phase implementation
    - [ ] Read `conductor/tracks/test_runner_20260710/spec.md` to refresh requirements
    - [ ] Read `conductor/workflow.md` to review TDD lifecycle and quality gates

- [ ] Task: Implement `run_tests()` — main orchestration function
    - [ ] Write failing test: `run_tests()` calls `check_gut_installed()` — raises `GUTNotInstalledError` when GUT missing (mock filesystem)
    - [ ] Write failing test: `run_tests()` calls `find_godot()` — raises `GodotNotFoundError` when Godot missing (mock)
    - [ ] Write failing test: `run_tests()` calls `build_gut_args()` — correct args passed to `run_godot()` (mock `run_godot`)
    - [ ] Write failing test: `run_tests()` calls `run_godot()` — captures stdout/stderr from subprocess (mock `run_godot` with CompletedProcess)
    - [ ] Write failing test: `run_tests()` calls `parse_junit_xml()` — assembles TestResult from parsed data + stdout/stderr
    - [ ] Write failing test: all tests pass → TestResult.failed == 0, no `TestFailureError` raised
    - [ ] Write failing test: tests fail → `TestFailureError` raised (exit code 1) when `no_exit_code=False`
    - [ ] Write failing test: tests fail + `no_exit_code=True` → no `TestFailureError`, TestResult returned normally
    - [ ] Write failing test: Godot subprocess timeout → raises `GdToolsError` (exit code 2)
    - [ ] Write failing test: Godot exits non-zero (crash) → raises `GdToolsError` (exit code 2) with stderr
    - [ ] Implement `run_tests(config, coverage, min_percent, suite, test_name, junit_xml, no_exit_code) -> TestResult` in `test_runner.py`
    - [ ] Ensure `.gd-tools/` directory exists before GUT run (create if missing)
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(test_runner): Implement run_tests orchestration with exit code logic`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Implement `--coverage` flag infrastructure (Phase 2 stub)
    - [ ] Write failing test: `coverage=True` sets `GD_TOOLS_COVERAGE_ACTIVE=1` in subprocess env (verify env dict passed to `run_godot`)
    - [ ] Write failing test: `coverage=True` adds `-gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd` to GUT args
    - [ ] Write failing test: `coverage=True` adds `-gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd` to GUT args
    - [ ] Write failing test: `coverage=False` → no coverage env vars, no hook args in GUT command
    - [ ] Write failing test: `coverage=True` sets `TestResult.coverage_data_path` to `.gd-tools/coverage/coverage.json` path
    - [ ] Write failing test: `coverage=False` → `TestResult.coverage_data_path` is None
    - [ ] Implement coverage env var + hook arg logic in `build_gut_args()` and `run_tests()`
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(test_runner): Implement --coverage flag infrastructure (env vars + hook args)`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Conductor - User Manual Verification 'run_tests() Orchestration & Coverage Infrastructure' (Protocol in workflow.md)

---

## Phase 4: Rich Terminal Output & CLI Integration

- [ ] Task: Read spec.md and workflow.md before starting phase implementation
    - [ ] Read `conductor/tracks/test_runner_20260710/spec.md` to refresh requirements
    - [ ] Read `conductor/workflow.md` to review TDD lifecycle and quality gates

- [ ] Task: Implement Rich summary output — `format_test_results()`
    - [ ] Write failing test: `format_test_results()` with all-passing tests → Rich table with total/passed/failed/skipped/duration, no stderr output
    - [ ] Write failing test: `format_test_results()` with failures → Rich table + GUT stdout/stderr surfaced (truncated if >5000 chars)
    - [ ] Write failing test: `format_test_results()` with zero tests → table showing 0/0/0/0
    - [ ] Write failing test: output contains color coding (green for pass count, red for fail count) — use `force_terminal=True` for testability
    - [ ] Implement `format_test_results(result: TestResult) -> None` using `rich.console.Console` and `rich.table.Table` in `test_runner.py`
    - [ ] Call `format_test_results()` at end of `run_tests()` before returning
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_test_runner.py` and confirm all pass
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(test_runner): Implement Rich terminal output for test results`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Wire `test` command in `cli.py` — CLI integration
    - [ ] Write failing test: `gd-tools test --help` shows all flags (`--coverage`, `--min`, `--suite`, `--test`, `--junit-xml`, `--no-exit-code`)
    - [ ] Write failing test: `gd-tools test` with mocked `run_tests()` → calls with correct args from config
    - [ ] Write failing test: `gd-tools test --suite MySuite` passes `suite="MySuite"` to `run_tests()`
    - [ ] Write failing test: `gd-tools test --test MyTest` passes `test_name="MyTest"` to `run_tests()`
    - [ ] Write failing test: `gd-tools test --coverage` passes `coverage=True` to `run_tests()`
    - [ ] Write failing test: `gd-tools test --junit-xml /path/to.xml` passes `junit_xml="/path/to.xml"`
    - [ ] Write failing test: `gd-tools test --no-exit-code` passes `no_exit_code=True`
    - [ ] Write failing test: `gd-tools test` → all pass → exit code 0
    - [ ] Write failing test: `gd-tools test` → test failures → exit code 1
    - [ ] Write failing test: `gd-tools test` → GUT not installed → exit code 2
    - [ ] Replace `NotImplementedError` stub in `cli.py` `test` command with actual `run_tests()` call
    - [ ] Handle `TestFailureError` → exit code 1, `GdToolsError` → exit code 2
    - [ ] Run tests and confirm they pass (Green phase)
    - [ ] Run `CI=true pytest tests/test_cli.py` and confirm all pass (including existing tests)
    - [ ] Run `CI=true pytest` to ensure no regressions across full suite
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Commit with message `feat(cli): Wire test command to run_tests with all flags`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Conductor - User Manual Verification 'Rich Terminal Output & CLI Integration' (Protocol in workflow.md)

---

## Phase 5: Integration Tests

- [ ] Task: Read spec.md and workflow.md before starting phase implementation
    - [ ] Read `conductor/tracks/test_runner_20260710/spec.md` to refresh requirements
    - [ ] Read `conductor/workflow.md` to review TDD lifecycle and quality gates

- [ ] Task: Write integration tests with real Godot + GUT
    - [ ] Create or verify sample Godot project fixture in `tests/fixtures/projects/sample_project/` (with `project.godot`, `scripts/calculator.gd`, `test/test_calculator.gd`, GUT installed)
    - [ ] Write integration test: `gd-tools test` runs GUT → tests execute → JUnit XML produced (marked `@pytest.mark.integration`)
    - [ ] Write integration test: all-passing tests → exit code 0, TestResult.failed == 0
    - [ ] Write integration test: failing test → exit code 1, TestResult.failed > 0, GUT stderr captured
    - [ ] Write integration test: `--suite` filter → only named suite runs
    - [ ] Write integration test: `--test` filter → only matching tests run
    - [ ] Write integration test: `--no-exit-code` → exit 0 even with failures
    - [ ] Write integration test: `--coverage` → env vars set, hook args passed (verify via mock or GUT output)
    - [ ] Add `pytest.mark.integration` to all integration tests; ensure they are skipped when Godot binary not available (conftest fixture)
    - [ ] Run `CI=true pytest tests/test_test_runner_integration.py -m integration` and confirm all pass (requires Godot + GUT)
    - [ ] Run full test suite `CI=true pytest` to ensure no regressions
    - [ ] Run `ruff check src/ tests/ && black --check src/ tests/`
    - [ ] Commit with message `test(test_runner): Add integration tests with real Godot + GUT`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA

- [ ] Task: Conductor - User Manual Verification 'Integration Tests' (Protocol in workflow.md)

</protect>
