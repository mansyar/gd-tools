<protect>
# Implementation Plan: Show Coverage Summary on Success

## Phase 1: Coverage Summary Display

- [ ] Task: Read spec.md and workflow.md to load context for this phase
    - [ ] Read `conductor/tracks/coverage_success_display_20260714/spec.md`
    - [ ] Read `conductor/workflow.md`

- [ ] Task: Write failing tests for coverage summary display (Red Phase)
    - [ ] Test: `run_coverage_test()` prints coverage summary table to stdout on success (without `--min`)
    - [ ] Test: `run_coverage_test()` prints coverage summary table to stdout on success when `--min` threshold is met
    - [ ] Test: `run_coverage_test()` prints coverage summary table to stdout before raising `CoverageThresholdError` when coverage is below threshold
    - [ ] Test: `run_coverage_test()` does NOT print coverage table when coverage data is unavailable (plan/coverage JSON missing — `CoveragePlanError` path)
    - [ ] Test: Coverage summary table format matches the output of `show_coverage_summary()` (same columns: Metric, Found, Hit, Rate)
    - [ ] Verify: Run `CI=true pytest tests/unit/test_orchestrator.py -k coverage_summary` and confirm all new tests fail as expected

- [ ] Task: Extract reusable table-printing helper from `show_coverage_summary()`
    - [ ] Create a private `_print_coverage_table(summary: CoverageSummary) -> None` function in `orchestrator.py` that encapsulates the Rich table rendering (lines 267-288 of current `show_coverage_summary`)
    - [ ] Refactor `show_coverage_summary()` to call `_print_coverage_table()` instead of inline table construction
    - [ ] Verify: Existing `show_coverage_summary` tests still pass (`CI=true pytest tests/unit/test_orchestrator.py -k show_coverage_summary`)

- [ ] Task: Implement coverage summary display in `run_coverage_test()` (Green Phase)
    - [ ] Modify `generate_report()` in `reporter.py` to attach the `ReportResult` (containing `summary`) as an attribute on `CoverageThresholdError` before raising, so the caller can access the already-computed summary without recomputation (NFR-2)
    - [ ] Modify `run_coverage_test()` in `orchestrator.py` to call `_print_coverage_table()` with the `ReportResult.summary` on the success path (after `generate_report()` returns)
    - [ ] Modify `run_coverage_test()` to catch `CoverageThresholdError`, extract the attached summary, call `_print_coverage_table()`, then re-raise (preserving existing error precedence: `TestFailureError` still takes priority)
    - [ ] Verify: Run `CI=true pytest tests/unit/test_orchestrator.py` and confirm all tests pass

- [ ] Task: Verify coverage and run full test suite
    - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` and confirm >80% line, >70% branch coverage for modified files
    - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/` to verify no lint/format issues
    - [ ] Run full test suite `CI=true pytest` to confirm no regressions

- [ ] Task: Conductor - User Manual Verification 'Coverage Summary Display' (Protocol in workflow.md)
</protect>
