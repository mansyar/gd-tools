<protect>

# Track 14: Test Suite Implementation — Implementation Plan

## Phase 1: Test Infrastructure Setup

### Task 1.0: Read spec.md and workflow.md
- [x] Read `conductor/tracks/test_suite_20260712/spec.md` to review requirements
- [x] Read `conductor/workflow.md` to review TDD methodology and task workflow

### Task 1.1: Configure pyproject.toml pytest/coverage settings [sha: ef95a1d]
- [x] Read current pyproject.toml to understand existing configuration
- [x] Register pytest markers: `unit`, `integration`, `e2e`, `slow`
- [x] Add `--strict-markers`, `--strict-config` to `addopts`
- [x] Add `--cov=gd_tools`, `--cov-branch`, `--cov-report=term-missing`, `--cov-report=html` to `addopts`
- [x] Set `fail_under = 80` in `[tool.coverage.report]`
- [x] Configure `[tool.coverage.run]` with `source = ["gd_tools"]`, `omit = ["*/tests/*", "*/addons/*"]`
- [x] Verify: `pytest --co` collects all tests without errors
- [x] Verify: `pytest --strict-markers` runs without marker warnings

### Task 1.2: Create root conftest.py
- [ ] Create `conftest.py` at project root
- [ ] Implement `.env` loading via `os.environ.setdefault`
- [ ] Implement `GODOT_BIN` environment variable detection
- [ ] Implement `godot_bin` fixture (returns path or `None`)
- [ ] Implement CI auto-skip logic for integration/e2e when Godot not found
- [ ] Verify: `pytest --co` still collects all tests
- [ ] Verify: Integration tests skip when `GODOT_BIN` not set

### Task 1.3: Create per-tier conftest.py files
- [ ] Create `tests/unit/conftest.py` with shared mock fixtures (subprocess.run, requests.get, shutil.which mock factories per §8)
- [ ] Create `tests/integration/conftest.py` with `godot_bin` fixture (auto-skip), sample project path fixture
- [ ] Create `tests/e2e/conftest.py` with `godot_bin` fixture (auto-skip), sample project fixture, E2E setup
- [ ] Verify: Unit tests still pass with new conftest
- [ ] Verify: Integration/e2e auto-skip works without Godot

### Task 1.4: Create .env.example and update .gitignore
- [ ] Create `.env.example` with `GODOT_BIN` placeholder
- [ ] Ensure `.env` is in `.gitignore` (add if missing)
- [ ] Verify: `.env.example` exists, `.env` is gitignored

### Task 1.5: Conductor - User Manual Verification 'Phase 1: Test Infrastructure Setup' (Protocol in workflow.md)

---

## Phase 2: Test Marker Annotation

### Task 2.0: Read spec.md and workflow.md
- [ ] Read `conductor/tracks/test_suite_20260712/spec.md` to review requirements
- [ ] Read `conductor/workflow.md` to review TDD methodology and task workflow

### Task 2.1: Annotate unit test files
- [ ] Add `@pytest.mark.unit` to all 20 files in `tests/unit/` (test_cli.py, test_cobertura_reporter.py, test_config.py, test_doctor.py, test_errors.py, test_file_discovery.py, test_format_runner.py, test_generate_expected_plans.py, test_godot.py, test_html_reporter.py, test_init.py, test_lcov_reporter.py, test_lint_runner.py, test_main.py, test_orchestrator.py, test_package.py, test_plan_generator.py, test_reporter.py, test_terminal_reporter.py, test_test_runner.py)
- [ ] Verify: `pytest -m unit` runs only unit tests

### Task 2.2: Annotate integration test files
- [ ] Add `@pytest.mark.integration` to all 8 files in `tests/integration/` (test_coverage_cli_integration.py, test_coverage_hooks.py, test_coverage_tracker_integration.py, test_doctor_integration.py, test_format_integration.py, test_init_integration.py, test_lint_integration.py, test_test_runner_integration.py)
- [ ] Verify: `pytest -m integration` runs only integration tests

### Task 2.3: Annotate e2e test files
- [ ] Add `@pytest.mark.e2e` to `test_coverage_e2e.py` (and `test_full_workflow.py` when created in Phase 5)
- [ ] Verify: `pytest -m e2e` runs only e2e tests

### Task 2.4: Conductor - User Manual Verification 'Phase 2: Test Marker Annotation' (Protocol in workflow.md)

---

## Phase 3: Unit Test Audit & Gap-Fill

### Task 3.0: Read spec.md and workflow.md
- [ ] Read `conductor/tracks/test_suite_20260712/spec.md` to review requirements
- [ ] Read `conductor/workflow.md` to review TDD methodology and task workflow

### Task 3.1: Audit and gap-fill config.py tests (§4.1)
- [ ] Audit `test_config.py` against §4.1 specs
- [ ] Write missing test cases: load valid config, defaults, CLI overrides, invalid TOML, negative min_percent, project root detection, exclude replace semantics
- [ ] Run tests: `pytest tests/unit/test_config.py -v` — all pass
- [ ] Verify coverage for `config.py` module ≥80%

### Task 3.2: Audit and gap-fill godot.py tests (§4.2)
- [ ] Audit `test_godot.py` against §4.2 specs
- [ ] Write missing test cases: binary detection chain, version parsing, version comparison, run_godot args, timeout, not found
- [ ] Run tests: `pytest tests/unit/test_godot.py -v` — all pass
- [ ] Verify coverage for `godot.py` module ≥80%

### Task 3.3: Audit and gap-fill plan_generator.py tests (§4.3)
- [ ] Audit `test_plan_generator.py` against §4.3 specs
- [ ] Write missing test cases: each GDScript construct, line numbers, branch types, declarations excluded, multiple files, empty file, nested structures
- [ ] Run tests: `pytest tests/unit/test_plan_generator.py -v` — all pass
- [ ] Verify coverage for `plan_generator.py` module ≥80%

### Task 3.4: Audit and gap-fill reporter.py tests (§4.4)
- [ ] Audit `test_reporter.py` against §4.4 specs
- [ ] Write missing test cases: line/branch coverage %, per-file aggregation, threshold pass/fail, source hash mismatch, zero/full coverage
- [ ] Run tests: `pytest tests/unit/test_reporter.py -v` — all pass
- [ ] Verify coverage for `reporter.py` module ≥80%

### Task 3.5: Audit and gap-fill reporter format tests (§4.5)
- [ ] Audit `test_html_reporter.py`, `test_lcov_reporter.py`, `test_cobertura_reporter.py`, `test_terminal_reporter.py` against §4.5 specs
- [ ] Write missing test cases: format compliance, valid XML, CSS classes, color thresholds
- [ ] Run tests: `pytest tests/unit/test_html_reporter.py tests/unit/test_lcov_reporter.py tests/unit/test_cobertura_reporter.py tests/unit/test_terminal_reporter.py -v` — all pass
- [ ] Verify coverage for reporter modules ≥80%

### Task 3.6: Audit and gap-fill lint_runner.py & format_runner.py tests (§4.6)
- [ ] Audit `test_lint_runner.py` and `test_format_runner.py` against §4.6 specs
- [ ] Write missing test cases: subprocess invocation, excludes, --check, exit codes, stderr, no files found
- [ ] Run tests: `pytest tests/unit/test_lint_runner.py tests/unit/test_format_runner.py -v` — all pass
- [ ] Verify coverage for `lint_runner.py` and `format_runner.py` ≥80%

### Task 3.7: Audit and gap-fill init.py tests (§4.7)
- [ ] Audit `test_init.py` against §4.7 specs
- [ ] Write missing test cases: GUT install/already-present, coverage addon copy, plugin enabling idempotent, gutconfig create/merge, toml create/preserve, .gd-tools dir + gitignore, network failure
- [ ] Run tests: `pytest tests/unit/test_init.py -v` — all pass
- [ ] Verify coverage for `init.py` module ≥80%

### Task 3.8: Audit and gap-fill doctor.py tests (§4.8)
- [ ] Audit `test_doctor.py` against §4.8 specs
- [ ] Write missing test cases: 9 checks pass/fail independently, suggestions, exit codes, severity levels, run_doctor never raises
- [ ] Run tests: `pytest tests/unit/test_doctor.py -v` — all pass
- [ ] Verify coverage for `doctor.py` module ≥80%

### Task 3.9: Audit and gap-fill cli.py tests (§4.9)
- [ ] Audit `test_cli.py` against §4.9 specs
- [ ] Write missing test cases: commands exist, help text, exit codes propagate, --version, --help, non-interactive mode (Click CliRunner)
- [ ] Run tests: `pytest tests/unit/test_cli.py -v` — all pass
- [ ] Verify coverage for `cli.py` module ≥80%

### Task 3.10: Verify full unit test suite
- [ ] Run `pytest -m unit -v` — all tests pass
- [ ] Verify unit test runtime <5s
- [ ] Run `ruff check tests/unit/` — clean
- [ ] Run `black --check tests/unit/` — clean

### Task 3.11: Conductor - User Manual Verification 'Phase 3: Unit Test Audit & Gap-Fill' (Protocol in workflow.md)

---

## Phase 4: Integration Test Audit & Gap-Fill

### Task 4.0: Read spec.md and workflow.md
- [ ] Read `conductor/tracks/test_suite_20260712/spec.md` to review requirements
- [ ] Read `conductor/workflow.md` to review TDD methodology and task workflow

### Task 4.1: Audit and gap-fill test runner integration tests (§5.2)
- [ ] Audit `test_test_runner_integration.py` against §5.2 specs
- [ ] Write missing test cases: GUT orchestration, JUnit XML, suite/test filters, exit codes, no-exit-code, Godot crashes
- [ ] Run tests: `pytest tests/integration/test_test_runner_integration.py -v` (when Godot available) — all pass

### Task 4.2: Audit and gap-fill coverage integration tests (§5.3)
- [ ] Audit existing coverage integration tests (`test_coverage_cli_integration.py`, `test_coverage_hooks.py`, `test_coverage_tracker_integration.py`) against §5.3 specs
- [ ] Write missing test cases: full coverage pipeline (plan→instrument→test→collect→report), partial coverage, branch tracking, report formats, threshold enforcement
- [ ] Run tests: `pytest tests/integration/ -k coverage -v` (when Godot available) — all pass

### Task 4.3: Audit and gap-fill init integration tests (§5.4)
- [ ] Audit `test_init_integration.py` against §5.4 specs
- [ ] Write missing test cases: real bootstrapping on fresh/existing/idempotent
- [ ] Run tests: `pytest tests/integration/test_init_integration.py -v` (when Godot available) — all pass

### Task 4.4: Audit and gap-fill remaining integration tests
- [ ] Audit `test_lint_integration.py`, `test_format_integration.py`, `test_doctor_integration.py`
- [ ] Write any missing test cases identified in audit
- [ ] Run tests: `pytest -m integration -v` (when Godot available) — all pass
- [ ] Verify integration test runtime <60s

### Task 4.5: Conductor - User Manual Verification 'Phase 4: Integration Test Audit & Gap-Fill' (Protocol in workflow.md)

---

## Phase 5: E2E Full-Workflow Test

### Task 5.0: Read spec.md and workflow.md
- [ ] Read `conductor/tracks/test_suite_20260712/spec.md` to review requirements
- [ ] Read `conductor/workflow.md` to review TDD methodology and task workflow

### Task 5.1: Create test_full_workflow.py
- [ ] Write `tests/e2e/test_full_workflow.py` implementing TESTING_STRATEGY §6:
  - Test: doctor before init (baseline check)
  - Test: init command on sample project
  - Test: doctor after init (should show green)
  - Test: lint command
  - Test: format command
  - Test: test --coverage command
  - Test: coverage show command
  - Test: coverage report command
  - Test: full workflow sequence (init → lint → format → test --coverage → coverage show → coverage report)
- [ ] Run tests: `pytest tests/e2e/test_full_workflow.py -v` (when Godot available) — all pass
- [ ] Annotate with `@pytest.mark.e2e`
- [ ] Verify E2E test runtime <120s

### Task 5.2: Conductor - User Manual Verification 'Phase 5: E2E Full-Workflow Test' (Protocol in workflow.md)

---

## Phase 6: Coverage Gate, Flakiness & Quality Verification

### Task 6.0: Read spec.md and workflow.md
- [ ] Read `conductor/tracks/test_suite_20260712/spec.md` to review requirements
- [ ] Read `conductor/workflow.md` to review TDD methodology and task workflow

### Task 6.1: Verify coverage gate
- [ ] Run `pytest --cov=gd_tools --cov-branch --cov-fail-under=80`
- [ ] Verify exit code 0
- [ ] Verify ≥80% line coverage
- [ ] Verify ≥70% branch coverage
- [ ] If coverage insufficient, add tests to cover missing lines/branches

### Task 6.2: Flakiness verification (10× runs)
- [ ] Run full test suite 10× consecutively
- [ ] Verify all 10 runs pass with zero failures
- [ ] Document results

### Task 6.3: Code quality verification
- [ ] Run `ruff check tests/` — clean
- [ ] Run `black --check tests/` — clean
- [ ] Fix any style issues found

### Task 6.4: Final acceptance criteria verification
- [ ] AC-1: `pytest -m unit` passes <5s
- [ ] AC-2: `pytest -m integration` passes <60s (when Godot available)
- [ ] AC-3: `pytest -m e2e` passes <120s (when Godot available)
- [ ] AC-4: `pytest --cov=gd_tools --cov-branch --cov-fail-under=80` passes
- [ ] AC-5: 10× runs all pass
- [ ] AC-6: All conftest.py files exist and function
- [ ] AC-7: All test files annotated with markers
- [ ] AC-8: Auto-skip works without Godot
- [ ] AC-9: `.env.example` exists, `.env` gitignored
- [ ] AC-10: `test_full_workflow.py` exists and passes
- [ ] AC-11: ruff and black clean on `tests/`
- [ ] AC-12: Unit test audit complete

### Task 6.5: Conductor - User Manual Verification 'Phase 6: Coverage Gate, Flakiness & Quality Verification' (Protocol in workflow.md)

</protect>
