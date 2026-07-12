<protect>

# Track 14: Test Suite Implementation

## Overview

Track 14 formalizes and gap-fills the gd-tools test suite to fully comply with `docs/TESTING_STRATEGY.md`. The test suite already contains ~547 tests with ~98% coverage across unit, integration, and e2e tiers. The directory structure already matches the prescribed layout (`tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`). This track focuses on **auditing existing tests against TESTING_STRATEGY §4 specs, filling gaps, adding missing infrastructure (conftest.py files, pytest markers, CI auto-skip, .env support), creating the missing E2E full-workflow test, and enforcing coverage gates.**

**Phase:** 4 — Polish & Release  
**Risk:** LOW  
**Dependencies:** All MVP1 tracks (4-8) and MVP2 tracks (9-13) — all archived/complete.

## Functional Requirements

### FR-1: Conftest Infrastructure
- **FR-1.1:** Create root `conftest.py` that loads `.env` file (via `os.environ.setdefault`), detects `GODOT_BIN` environment variable, and provides a `godot_bin` fixture that returns the path or `None`.
- **FR-1.2:** Create `tests/unit/conftest.py` with shared unit-test fixtures (mock factories for subprocess.run, requests.get, shutil.which — per TESTING_STRATEGY §8 mocking strategy).
- **FR-1.3:** Create `tests/integration/conftest.py` with the `godot_bin` fixture (auto-skip if not found), sample project path fixture, and integration-specific fixtures.
- **FR-1.4:** Create `tests/e2e/conftest.py` with the `godot_bin` fixture (auto-skip if not found), sample project fixture, and E2E-specific setup.

### FR-2: pytest Configuration
- **FR-2.1:** Register pytest markers in `pyproject.toml`: `unit`, `integration`, `e2e`, `slow`. Add `--strict-markers` and `--strict-config` to `addopts`.
- **FR-2.2:** Annotate ALL existing test files with appropriate `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e` markers (either at module level or per-class/per-function).
- **FR-2.3:** Configure `--cov=gd_tools`, `--cov-branch`, `--cov-report=term-missing`, `--cov-report=html` in `addopts`.
- **FR-2.4:** Set `fail_under = 80` in `[tool.coverage.report]`.
- **FR-2.5:** Configure CI auto-skip: integration/e2e tests skip automatically when `GODOT_BIN` is not set or Godot binary is not found.

### FR-3: Unit Test Audit & Gap-Fill
- **FR-3.1:** Audit each existing unit test file against TESTING_STRATEGY §4 specs (§4.1–§4.9) and identify missing test cases.
- **FR-3.2:** Implement missing test cases for each module:
  - `config.py` (§4.1): load valid config, defaults, CLI overrides, invalid TOML, negative min_percent, project root detection, exclude replace semantics
  - `godot.py` (§4.2): binary detection chain, version parsing, version comparison, run_godot args, timeout, not found
  - `plan_generator.py` (§4.3): each GDScript construct, line numbers, branch types, declarations excluded, multiple files, empty file, nested structures
  - `reporter.py` (§4.4): line/branch coverage %, per-file aggregation, threshold pass/fail, source hash mismatch, zero/full coverage
  - Reporters HTML/LCOV/Cobertura/Terminal (§4.5): format compliance, valid XML, CSS classes, color thresholds
  - `lint_runner.py` & `format_runner.py` (§4.6): subprocess invocation, excludes, --check, exit codes, stderr, no files found
  - `init.py` (§4.7): GUT install/already-present, coverage addon copy, plugin enabling idempotent, gutconfig create/merge, toml create/preserve, .gd-tools dir + gitignore, network failure
  - `doctor.py` (§4.8): 9 checks pass/fail independently, suggestions, exit codes, severity levels, run_doctor never raises
  - `cli.py` (§4.9): commands exist, help text, exit codes propagate, --version, --help, non-interactive mode (Click CliRunner)
- **FR-3.3:** Ensure all unit tests run without Godot (fully mocked per §8).

### FR-4: Integration Test Audit & Gap-Fill
- **FR-4.1:** Audit existing integration tests against TESTING_STRATEGY §5 specs.
- **FR-4.2:** Fill missing integration test cases:
  - `test_test_runner.py` (§5.2): GUT orchestration, JUnit XML, suite/test filters, exit codes, no-exit-code, Godot crashes
  - `test_coverage_e2e.py` (§5.3): full coverage pipeline (plan→instrument→test→collect→report), partial coverage, branch tracking, report formats, threshold enforcement
  - `test_init.py` (§5.4): real bootstrapping on fresh/existing/idempotent

### FR-5: E2E Full-Workflow Test
- **FR-5.1:** Create `tests/e2e/test_full_workflow.py` implementing TESTING_STRATEGY §6:
  - Full workflow: `init → lint → format → test --coverage → coverage show → coverage report`
  - `doctor` before/after init
  - Uses sample project fixture
  - Verifies end-to-end CLI orchestration

### FR-6: .env Template
- **FR-6.1:** Create `.env.example` with `GODOT_BIN` placeholder (e.g., `GODOT_BIN=C:\Godot\Godot_v4.6.2-stable_win64.exe`).
- **FR-6.2:** Ensure `.env` is in `.gitignore` (add if missing).

## Non-Functional Requirements

### NFR-1: Performance
- Unit tests complete in <5 seconds
- Integration tests complete in <60 seconds
- E2E tests complete in <120 seconds

### NFR-2: Coverage
- ≥80% line coverage on `gd_tools` package (enforced via `--cov-fail-under=80`)
- ≥70% branch coverage (enforced via `--cov-branch`)

### NFR-3: Stability
- No flaky tests: running the full suite 10× produces all passes every time

### NFR-4: Code Quality
- All test code passes `ruff check tests/`
- All test code passes `black --check tests/`
- Test code follows existing project conventions

## Acceptance Criteria

1. **AC-1:** All unit tests pass (<5s) with `pytest -m unit`
2. **AC-2:** All integration tests pass (<60s) with `pytest -m integration` (when Godot available)
3. **AC-3:** All E2E tests pass (<120s) with `pytest -m e2e` (when Godot available)
4. **AC-4:** `pytest --cov=gd_tools --cov-branch --cov-fail-under=80` passes (exit code 0)
5. **AC-5:** Full test suite run 10× consecutively — all pass with zero flaky failures
6. **AC-6:** Root and per-tier `conftest.py` files exist and function correctly
7. **AC-7:** pytest markers registered in `pyproject.toml` and all test files annotated
8. **AC-8:** Integration/e2e tests auto-skip when Godot binary not found (CI-safe)
9. **AC-9:** `.env.example` exists and `.env` is gitignored
10. **AC-10:** `test_full_workflow.py` exists and passes (when Godot available)
11. **AC-11:** `ruff check tests/` and `black --check tests/` pass clean
12. **AC-12:** Unit test audit complete — all TESTING_STRATEGY §4 test cases verified present or added

## Out of Scope

- Restructuring or renaming existing test files (audit + gap-fill only, no reorganization)
- Adding new source code features (tests only)
- Performance benchmarking beyond timing constraints
- Setting up CI/CD pipeline configuration (separate track)
- Godot/GUT version upgrades

</protect>
