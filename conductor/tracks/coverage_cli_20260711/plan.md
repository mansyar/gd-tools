<protect>

# Track 13: Coverage CLI Integration — Implementation Plan

## Overview

This plan implements Track 13: wiring coverage components into the CLI. All dependencies (Tracks 6, 9, 11, 12) are completed. Config integration (`CoverageConfig` in `config.py`) is already done — no changes needed to `config.py`.

**Key design decisions (from spec):**
- Orchestration logic lives in `src/gd_tools/coverage/orchestrator.py` (separate module)
- Error precedence: `TestFailureError` reported first, then `CoverageThresholdError`
- `generate_report()` `min_threshold` is 0.0–1.0 (convert from `min_percent` 0–100)
- `merge_coverage_data()` takes `list[Path]` (file paths, reads internally)
- `plan_generator` functions take `str` paths, not `Path`

---

## Phase 1: test_runner.py — Coverage Env Var Completion

**Goal:** Complete the coverage env var setup in `run_tests()` so hooks can find plan.json and write coverage.json.

- [x] Task: Read `spec.md` and `conductor/workflow.md` to refresh context before starting this phase
    - [x] Review spec.md FR-1 (test --coverage flow), NFR-2 (error precedence), NFR-4 (exit codes)
    - [x] Review workflow.md TDD lifecycle and Phase Completion Verification protocol

- [x] Task: Write failing unit tests for coverage env var setting
    - [x] Test that `GD_TOOLS_COVERAGE_PLAN` env var is set to the absolute path of `plan.json` when `coverage=True`
    - [x] Test that `GD_TOOLS_COVERAGE_OUTPUT` env var is set to the absolute path of `coverage.json` when `coverage=True`
    - [x] Test that `GD_TOOLS_COVERAGE_ACTIVE` is still set to `"1"` (existing behavior, regression guard)
    - [x] Test that env vars are NOT set when `coverage=False`
    - [x] Test that `coverage_data_path` uses `config.coverage.output_dir` instead of hardcoded `.gd-tools/coverage`
    - [x] Verify: `CI=true pytest tests/unit/test_test_runner.py -k "coverage_env" --no-header -q` fails as expected (RED)

- [x] Task: Implement env var completion in `run_tests()`
    - [x] Add `GD_TOOLS_COVERAGE_PLAN` env var pointing to `<output_dir>/plan.json` (absolute path) when `coverage=True`
    - [x] Add `GD_TOOLS_COVERAGE_OUTPUT` env var pointing to `<output_dir>/coverage.json` (absolute path) when `coverage=True`
    - [x] Replace hardcoded `project_root / ".gd-tools" / "coverage"` with `project_root / config.coverage.output_dir` for `coverage_data_path`
    - [x] Ensure env vars are added to the `env` dict passed to `run_godot()`
    - [x] Verify: `CI=true pytest tests/unit/test_test_runner.py -k "coverage_env" --no-header -q` passes (GREEN)

- [x] Task: Refactor and verify coverage
    - [x] Run `CI=true pytest tests/unit/test_test_runner.py --no-header -q` — all tests pass (53 passed)
    - [x] Run `ruff check src/gd_tools/test_runner.py` — no errors
    - [x] Run `black --check src/gd_tools/test_runner.py` — no errors
    - [x] Document any deviations in plan.md

- [x] Task: Conductor - User Manual Verification 'Phase 1: test_runner.py — Coverage Env Var Completion' (Protocol in workflow.md) — Approved by user. 53/53 tests pass, ruff/black clean, 98% line coverage on test_runner.py.

---

## Phase 2: Orchestrator Module (`coverage/orchestrator.py`)

**Goal:** Create the orchestration module with 4 functions that coordinate plan_generator → test_runner → reporter.

- [x] Task: Read `spec.md` and `conductor/workflow.md` to refresh context before starting this phase
    - [x] Review spec.md FR-1 through FR-4, NFR-1 (orchestrator module), NFR-2 (error precedence)
    - [x] Review workflow.md TDD lifecycle and Phase Completion Verification protocol

- [x] Task: Write failing unit tests for `run_coverage_test()`
    - [ ] Test that it generates a plan via `plan_generator.generate_plan()` when `coverage=True`
    - [ ] Test that it writes plan to `<output_dir>/plan.json` via `plan_generator.write_plan_json()`
    - [ ] Test that it calls `run_tests()` with `coverage=True` and correct env vars set
    - [ ] Test that it reads coverage data via `reporter.read_coverage_json()` after tests complete
    - [ ] Test that it generates reports via `reporter.generate_report()` with `min_threshold` converted from `min_percent` (80 → 0.8)
    - [ ] Test error precedence: when `TestFailureError` AND `CoverageThresholdError` both occur, `TestFailureError` is re-raised
    - [ ] Test that when only `CoverageThresholdError` occurs, it is raised
    - [ ] Test that when no errors occur, `TestResult` is returned
    - [ ] Test that when `no_exit_code=True`, `TestFailureError` is NOT raised but reports are still generated
    - [ ] Mock: `plan_generator`, `test_runner.run_tests`, `reporter.read_coverage_json`, `reporter.read_plan_json`, `reporter.generate_report`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "run_coverage" --no-header -q` fails as expected (RED)

- [x] Task: Implement `run_coverage_test()`
    - [ ] Signature: `run_coverage_test(config: GdToolsConfig, suite: str | None = None, test_name: str | None = None, junit_xml: str | None = None, no_exit_code: bool = False, min_percent: int | None = None, timeout: int | None = None) -> TestResult`
    - [ ] Derive `output_dir = project_root / config.coverage.output_dir`
    - [ ] Generate plan via `plan_generator.generate_plan(str(project_root), None, config.coverage.exclude, config.coverage.test_dirs)`
    - [ ] Write plan to `str(output_dir / "plan.json")` via `plan_generator.write_plan_json()`
    - [ ] Call `run_tests(config, coverage=True, ...)` — catch `TestFailureError`
    - [ ] Read coverage data via `reporter.read_coverage_json(output_dir / "coverage.json")`
    - [ ] Read plan via `plan_generator.read_plan_json(str(output_dir / "plan.json"))`
    - [ ] Convert `min_percent` (0–100) to `min_threshold` (0.0–1.0): `min_threshold = min_percent / 100 if min_percent is not None else None`
    - [ ] Call `reporter.generate_report(plan, data, output_dir, config.coverage.format, min_threshold)` — catch `CoverageThresholdError`
    - [ ] Re-raise `TestFailureError` first if both errors occurred
    - [ ] Re-raise `CoverageThresholdError` if only coverage error occurred
    - [ ] Return `TestResult`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "run_coverage" --no-header -q` passes (GREEN)

- [ ] Task: Write failing unit tests for `generate_coverage_report()`
    - [ ] Test that it reads plan from `<output_dir>/plan.json`
    - [ ] Test that it reads coverage data from `<output_dir>/coverage.json`
    - [ ] Test that it calls `reporter.generate_report()` with correct parameters
    - [ ] Test that `--format` flag overrides `config.coverage.format`
    - [ ] Test that `--output-dir` flag overrides `config.coverage.output_dir`
    - [ ] Test that missing coverage.json raises `CoveragePlanError` (exit code 2)
    - [ ] Test that missing plan.json raises `CoveragePlanError` (exit code 2)
    - [ ] Mock: `plan_generator.read_plan_json`, `reporter.read_coverage_json`, `reporter.generate_report`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "generate_report" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `generate_coverage_report()`
    - [ ] Signature: `generate_coverage_report(config: GdToolsConfig, format: str | None = None, output_dir: str | None = None) -> ReportResult`
    - [ ] Resolve effective `output_dir`: `--output-dir` flag > `config.coverage.output_dir` > default
    - [ ] Resolve effective `format`: `--format` flag > `config.coverage.format` > `"html"`
    - [ ] Read plan via `plan_generator.read_plan_json(str(output_dir / "plan.json"))`
    - [ ] Read coverage data via `reporter.read_coverage_json(output_dir / "coverage.json")`
    - [ ] Call `reporter.generate_report(plan, data, output_dir, format)`
    - [ ] Return `ReportResult`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "generate_report" --no-header -q` passes (GREEN)

- [ ] Task: Write failing unit tests for `merge_coverage_files()`
    - [ ] Test that it calls `reporter.merge_coverage_data(files)` with list of `Path` objects
    - [ ] Test that it writes merged data to `--output` path (default: `.gd-tools/coverage/coverage.json`)
    - [ ] Test that it prints merge summary (file count, total hits)
    - [ ] Test that empty file list raises `ValueError` or appropriate error
    - [ ] Mock: `reporter.merge_coverage_data`, `reporter.read_coverage_json`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "merge" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `merge_coverage_files()`
    - [ ] Signature: `merge_coverage_files(files: list[Path], output: Path | None = None) -> CoverageData`
    - [ ] Default output: `Path(".gd-tools/coverage/coverage.json")`
    - [ ] Call `reporter.merge_coverage_data(files)`
    - [ ] Write merged JSON to output path
    - [ ] Print merge summary via Rich console
    - [ ] Return merged `CoverageData`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "merge" --no-header -q` passes (GREEN)

- [ ] Task: Write failing unit tests for `show_coverage_summary()`
    - [ ] Test that it reads plan + coverage data from `<output_dir>/`
    - [ ] Test that it calls `reporter.compute_summary(plan, data)`
    - [ ] Test that it prints a Rich terminal summary table
    - [ ] Test that `--min N` threshold check exits 1 when below threshold
    - [ ] Test that `--min N` threshold check exits 0 when at or above threshold
    - [ ] Test that missing coverage data raises `CoveragePlanError`
    - [ ] Mock: `plan_generator.read_plan_json`, `reporter.read_coverage_json`, `reporter.compute_summary`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "show" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `show_coverage_summary()`
    - [ ] Signature: `show_coverage_summary(config: GdToolsConfig, min_percent: int | None = None) -> CoverageSummary`
    - [ ] Derive `output_dir = project_root / config.coverage.output_dir`
    - [ ] Read plan via `plan_generator.read_plan_json(str(output_dir / "plan.json"))`
    - [ ] Read coverage data via `reporter.read_coverage_json(output_dir / "coverage.json")`
    - [ ] Call `reporter.compute_summary(plan, data)`
    - [ ] Print Rich terminal table (file, lines found/hit/%, branches found/hit/%, overall)
    - [ ] If `min_percent` is set and `summary.line_rate * 100 < min_percent`, raise `CoverageThresholdError`
    - [ ] Return `CoverageSummary`
    - [ ] Verify: `CI=true pytest tests/unit/test_orchestrator.py -k "show" --no-header -q` passes (GREEN)

- [ ] Task: Update `coverage/__init__.py` with re-exports
    - [ ] Re-export `run_coverage_test`, `generate_coverage_report`, `merge_coverage_files`, `show_coverage_summary` from `orchestrator`
    - [ ] Verify: `python -c "from gd_tools.coverage import run_coverage_test"` succeeds

- [ ] Task: Refactor and verify coverage
    - [ ] Run `CI=true pytest tests/unit/test_orchestrator.py --no-header -q` — all tests pass
    - [ ] Run `ruff check src/gd_tools/coverage/orchestrator.py` — no errors
    - [ ] Run `black --check src/gd_tools/coverage/orchestrator.py` — no errors
    - [ ] Run `CI=true pytest --cov=gd_tools.coverage.orchestrator --cov-report=term-missing tests/unit/test_orchestrator.py` — verify ≥80% line coverage
    - [ ] Document any deviations in plan.md

- [ ] Task: Conductor - User Manual Verification 'Phase 2: Orchestrator Module' (Protocol in workflow.md)

---

## Phase 3: CLI Wiring — `test --coverage` Command

**Goal:** Wire the `test` command's `--coverage` flag to call `orchestrator.run_coverage_test()` instead of `run_tests()` directly.

- [ ] Task: Read `spec.md` and `conductor/workflow.md` to refresh context before starting this phase
    - [ ] Review spec.md FR-1 (test --coverage flow), NFR-2 (error precedence), NFR-4 (exit codes)
    - [ ] Review workflow.md TDD lifecycle and Phase Completion Verification protocol

- [ ] Task: Write failing unit tests for `test --coverage` CLI command
    - [ ] Test that `test --coverage` calls `orchestrator.run_coverage_test()` (not `run_tests()` directly)
    - [ ] Test that `test --coverage --min 80` passes `min_percent=80` to orchestrator
    - [ ] Test that `test` without `--coverage` still calls `run_tests()` directly (regression guard)
    - [ ] Test that `TestFailureError` from orchestrator exits with code 1
    - [ ] Test that `CoverageThresholdError` from orchestrator exits with code 1
    - [ ] Test that `CoveragePlanError` from orchestrator exits with code 2
    - [ ] Test that `--no-exit-code` flag is propagated to orchestrator
    - [ ] Mock: `orchestrator.run_coverage_test`, `test_runner.run_tests`
    - [ ] Use `click.testing.CliRunner` for CLI invocation
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "test_coverage" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `test --coverage` CLI wiring
    - [ ] In `cli.py:test()`, when `coverage=True`, call `orchestrator.run_coverage_test(config, suite, test, junit_xml, no_exit_code, min, timeout)` instead of `run_tests()`
    - [ ] When `coverage=False`, keep existing behavior (call `run_tests()` directly)
    - [ ] Ensure error handling catches `TestFailureError` (exit 1), `CoverageThresholdError` (exit 1), `CoveragePlanError` (exit 2), `GdToolsError` (exit e.exit_code)
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "test_coverage" --no-header -q` passes (GREEN)

- [ ] Task: Refactor and verify
    - [ ] Run `CI=true pytest tests/unit/test_cli.py --no-header -q` — all tests pass
    - [ ] Run `ruff check src/gd_tools/cli.py` — no errors
    - [ ] Run `black --check src/gd_tools/cli.py` — no errors
    - [ ] Document any deviations in plan.md

- [ ] Task: Conductor - User Manual Verification 'Phase 3: CLI Wiring — test --coverage' (Protocol in workflow.md)

---

## Phase 4: CLI Wiring — `coverage report/merge/show` Commands

**Goal:** Replace stub implementations with orchestrator calls for the `coverage` command group.

- [ ] Task: Read `spec.md` and `conductor/workflow.md` to refresh context before starting this phase
    - [ ] Review spec.md FR-2 (coverage report), FR-3 (coverage merge), FR-4 (coverage show)
    - [ ] Review workflow.md TDD lifecycle and Phase Completion Verification protocol

- [ ] Task: Write failing unit tests for `coverage report` command
    - [ ] Test that `coverage report` calls `orchestrator.generate_coverage_report()`
    - [ ] Test that `--format lcov` passes format to orchestrator
    - [ ] Test that `--output-dir /tmp/reports` passes output_dir to orchestrator
    - [ ] Test that default format comes from config when `--format` not specified
    - [ ] Test that `CoveragePlanError` exits with code 2 (missing coverage data)
    - [ ] Test that `GdToolsError` exits with code `e.exit_code`
    - [ ] Mock: `orchestrator.generate_coverage_report`
    - [ ] Use `click.testing.CliRunner`
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "coverage_report" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `coverage report` CLI command
    - [ ] Replace `raise NotImplementedError` with call to `orchestrator.generate_coverage_report(config, format, output_dir)`
    - [ ] Print report output path
    - [ ] Handle errors: `CoveragePlanError` (exit 2), `GdToolsError` (exit e.exit_code)
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "coverage_report" --no-header -q` passes (GREEN)

- [ ] Task: Write failing unit tests for `coverage merge` command
    - [ ] Test that `coverage merge file1.json file2.json` calls `orchestrator.merge_coverage_files([Path("file1.json"), Path("file2.json")], output)`
    - [ ] Test that `--output merged.json` passes output path to orchestrator
    - [ ] Test that default output is `.gd-tools/coverage/coverage.json`
    - [ ] Test that no files argument exits with error (Click handles this via `nargs=-1` + required check)
    - [ ] Mock: `orchestrator.merge_coverage_files`
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "coverage_merge" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `coverage merge` CLI command
    - [ ] Replace `raise NotImplementedError` with call to `orchestrator.merge_coverage_files([Path(f) for f in files], Path(output) if output else None)`
    - [ ] Print merge summary
    - [ ] Handle errors: `GdToolsError` (exit e.exit_code)
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "coverage_merge" --no-header -q` passes (GREEN)

- [ ] Task: Write failing unit tests for `coverage show` command
    - [ ] Test that `coverage show` calls `orchestrator.show_coverage_summary()`
    - [ ] Test that `--min 80` passes `min_percent=80` to orchestrator
    - [ ] Test that `CoverageThresholdError` exits with code 1
    - [ ] Test that `CoveragePlanError` exits with code 2 (missing coverage data)
    - [ ] Mock: `orchestrator.show_coverage_summary`
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "coverage_show" --no-header -q` fails as expected (RED)

- [ ] Task: Implement `coverage show` CLI command
    - [ ] Replace `raise NotImplementedError` with call to `orchestrator.show_coverage_summary(config, min)`
    - [ ] Handle errors: `CoverageThresholdError` (exit 1), `CoveragePlanError` (exit 2), `GdToolsError` (exit e.exit_code)
    - [ ] Verify: `CI=true pytest tests/unit/test_cli.py -k "coverage_show" --no-header -q` passes (GREEN)

- [ ] Task: Refactor and verify
    - [ ] Run `CI=true pytest tests/unit/test_cli.py --no-header -q` — all tests pass
    - [ ] Run `ruff check src/gd_tools/cli.py` — no errors
    - [ ] Run `black --check src/gd_tools/cli.py` — no errors
    - [ ] Document any deviations in plan.md

- [ ] Task: Conductor - User Manual Verification 'Phase 4: CLI Wiring — coverage report/merge/show' (Protocol in workflow.md)

---

## Phase 5: Integration & E2E Tests

**Goal:** Write integration and E2E tests that verify the full coverage flow with real Godot on the sample project fixture.

- [ ] Task: Read `spec.md` and `conductor/workflow.md` to refresh context before starting this phase
    - [ ] Review spec.md AC-1 through AC-12 (all acceptance criteria)
    - [ ] Review workflow.md TDD lifecycle and Phase Completion Verification protocol

- [ ] Task: Write integration test for `test --coverage` flow
    - [ ] Test: `run_coverage_test()` with real Godot + `tests/fixtures/projects/sample_project/`
    - [ ] Verify: plan.json generated in `.gd-tools/coverage/`
    - [ ] Verify: coverage.json generated in `.gd-tools/coverage/`
    - [ ] Verify: HTML report generated in `.gd-tools/coverage/html/`
    - [ ] Verify: JUnit XML generated at `.gd-tools/results.xml`
    - [ ] Mark with `@pytest.mark.integration`
    - [ ] Verify: `CI=true pytest tests/integration/test_coverage_cli_integration.py -m integration --no-header -q` passes

- [ ] Task: Write E2E test for full CLI flow
    - [ ] Test: `gd-tools test --coverage` via subprocess on sample project
    - [ ] Test: `gd-tools test --coverage --min 80` exits 1 when below threshold
    - [ ] Test: `gd-tools coverage show` prints summary after coverage run
    - [ ] Test: `gd-tools coverage report --format lcov` generates LCOV file
    - [ ] Test: `gd-tools coverage merge` combines two coverage JSON files
    - [ ] Mark with `@pytest.mark.e2e`
    - [ ] Verify: `CI=true pytest tests/e2e/test_coverage_e2e.py -m e2e --no-header -q` passes

- [ ] Task: Verify all acceptance criteria
    - [ ] AC-1: `gd-tools test --coverage` runs tests, collects coverage, generates HTML report
    - [ ] AC-2: `--min 80` exits 1 when below 80%, exits 0 when ≥80%
    - [ ] AC-3: `gd-tools coverage report` regenerates reports without re-running tests
    - [ ] AC-4: `gd-tools coverage merge` correctly combines two coverage data files
    - [ ] AC-5: `gd-tools coverage show` prints readable summary table
    - [ ] AC-6: Coverage data saved to `.gd-tools/coverage/`
    - [ ] AC-7: JUnit XML produced alongside coverage
    - [ ] AC-8: Full end-to-end works on Windows (dev OS)
    - [ ] AC-9: `[coverage]` config section loaded from `gd-tools.toml`
    - [ ] AC-10: Test failures reported first when both test + coverage errors occur
    - [ ] AC-11: Unit tests pass with `CI=true pytest -m unit` (<5s)
    - [ ] AC-12: `ruff check src/ tests/` and `black --check src/ tests/` pass

- [ ] Task: Final quality gates
    - [ ] Run `CI=true pytest --no-header -q` — all tests pass
    - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` — verify ≥80% line / ≥70% branch coverage
    - [ ] Run `ruff check src/ tests/` — no errors
    - [ ] Run `black --check src/ tests/` — no errors
    - [ ] Document any deviations in plan.md

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Integration & E2E Tests' (Protocol in workflow.md)
</protect>
