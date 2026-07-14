<protect>
# Track: Show Coverage Summary on Success

## Overview

When running `gd-tools test --coverage [--min N]`, the coverage percentage is only displayed when coverage falls **below** the threshold (via the `CoverageThresholdError` message). On **success** — when coverage meets or exceeds the threshold, or when `--min` is not specified — no coverage information is shown at all. This track fixes that gap by displaying a coverage summary table on success as well.

## Problem Statement

The `run_coverage_test()` function in `orchestrator.py` calls `reporter.generate_report()`, which computes a `CoverageSummary` (including `line_rate` and `branch_rate`). On failure, `CoverageThresholdError` is raised with the percentage embedded in the error message. On success, the `ReportResult` is returned but no coverage data is printed to the terminal.

The `show_coverage_summary()` function in `orchestrator.py` already prints a Rich table with Lines and Branches (Found/Hit/Rate columns), but it is only wired to the `gd-tools coverage show` command, not to the `test --coverage` flow.

## Functional Requirements

### FR-1: Display Coverage Summary on Success
When `gd-tools test --coverage` completes successfully (tests pass, coverage data is available), a Rich coverage summary table **must** be printed to **stdout**.

The table must display:
- **Lines**: Found count, Hit count, Rate (percentage)
- **Branches**: Found count, Hit count, Rate (percentage)

This applies whether or not `--min` is specified.

### FR-2: Display Coverage Summary on Failure
When coverage falls below the `--min` threshold, the Rich coverage summary table **must** be printed to **stdout first**, followed by the existing error message (which goes to stderr via the CLI error handler).

The table and error message together give the user full context: the table shows the coverage breakdown, and the error message provides the actionable fix hint.

### FR-3: Reuse Existing Table Implementation
The coverage summary table must reuse the existing table-rendering logic from `show_coverage_summary()` in `orchestrator.py`. No new table layout or styling should be introduced.

### FR-4: No Change to Exit Codes
Exit codes remain unchanged:
- `0` — tests pass, coverage meets or exceeds threshold (or no threshold set)
- `1` — tests fail or coverage below threshold
- `2` — configuration error

## Non-Functional Requirements

### NFR-1: Output Stream
The coverage summary table must go to **stdout** (consistent with test result output and CI capture). Error messages continue to go to **stderr** as before.

### NFR-2: No Performance Impact
The summary computation already happens inside `generate_report()` via `compute_summary()`. The table rendering must reuse this already-computed data — no redundant recomputation.

## Acceptance Criteria

1. Running `gd-tools test --coverage` (without `--min`) prints the coverage summary table to stdout on success.
2. Running `gd-tools test --coverage --min 80` where coverage >= 80% prints the coverage summary table to stdout on success.
3. Running `gd-tools test --coverage --min 80` where coverage < 80% prints the coverage summary table to stdout, then prints the error message to stderr, and exits with code 1.
4. The table format is identical to the one produced by `gd-tools coverage show`.
5. Exit codes are unchanged from current behavior.
6. No coverage table is printed when `--coverage` is not used.

## Out of Scope

- Changes to `gd-tools coverage show` (already works correctly).
- Changes to `gd-tools coverage report` command.
- Adding new coverage metrics or report formats.
- Changes to the HTML/LCOV/Cobertura report generation.
- Changes to the `TestFailureError` handling flow (test failures without coverage threshold).
</protect>
