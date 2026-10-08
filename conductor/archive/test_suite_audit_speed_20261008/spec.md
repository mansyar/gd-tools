# Specification: Test Suite Audit & Speed-Up

- **Track ID:** `test_suite_audit_speed_20261008`
- **Type:** Chore
- **Branch:** `feature/test-suite-audit-speed-20261008`
- **Created:** 2026-10-08

## Overview

A measured audit of the pytest suites (2026-10-08, local, Godot 4.7.2, two consistent unit runs) identified hotspots with concrete root causes. This track implements the approved improvements: (A) unit quick wins, (B) pytest-xdist adoption for CI, (C) integration parse-check batching, (D) integration tuning, (E) E2E smoke speed-up. The goal is faster feedback locally and in CI **without weakening test semantics or reducing coverage**.

## Measured Baseline (evidence)

| Suite | Tests | Wall time | Dominant costs |
|---|---|---|---|
| Unit | 1,582 | 40.7s | `test_exitfirst_parallel_stops_dispatch_and_drains_inflight` 5.0s (release `Event` never set; `wait(timeout=5)` always expires); real subprocess tests in `test_main` (3 × ~1.1s) and `test_generate_expected_plans` (2 × ~1s); `test_run_lint_default_paths` 1.8s (real ruff over repo cwd); `test_watch_observer` watcher threads (3 × ~1s, sleeps); `test_format_test_results_truncates_long_output` 0.8s (unexplained for string work); ~1,540 remaining tests avg 13ms (overhead-dominated). Collection ≈ 3s. |
| Integration | 90 (56 defs, parametrized) | 310.9s | `test_instrumented_source_parses[*]` ≈ 170s (≈27 cases × 5.6–12.6s; each launches Godot to parse one instrumented script); `test_coverage_run_timeout_closes_game_and_reports` 20.9s (real timeout wait); playtest CLI tests 7–11s each (real game runs). |
| E2E smoke (PR CI subset) | 5 | 119s | `test_changed_selection_end_to_end` 40.5s + `test_watch_session_end_to_end` 34.1s (63% of suite). |

## Functional Requirements

- **FR-A (Unit quick wins):**
  - Fix the exitfirst fake-runner so the release `Event` is signaled at the correct point of the parallel dispatch/drain scenario; the test must still assert the same dispatch-stop and in-flight-drain semantics.
  - De-subprocess `test_main::TestSubprocess` (3 tests), `test_generate_expected_plans` (2 tests), and `test_lint_runner::test_run_lint_default_paths` via mocking or tmp_path scoping, preserving each test's assertions.
  - Reduce `test_watch_observer` real-thread/sleep waits with event-driven synchronization.
  - Diagnose and fix the 0.8s cost of `test_format_test_results_truncates_long_output`.
- **FR-B (pytest-xdist, CI-only):** Add `pytest-xdist` to dev dependencies. CI Stage 1 (cov job) and matrix-unit jobs run with `-n auto`. Local default remains serial.
- **FR-C (Integration parse batching):** All `test_instrumented_source_parses[*]` fixtures are parsed in a single Godot session driven by a fixture manifest. Per-fixture pass/fail outcomes are preserved and a failure must identify the offending fixture.
- **FR-D (Integration tuning):** `test_coverage_run_timeout_closes_game_and_reports` uses a configured short timeout instead of a real multi-second wait. Playtest scenario tests (7–11s each) are batched or trimmed where semantics allow.
- **FR-E (E2E smoke):** Root-cause the internal waits of `test_changed_selection_end_to_end` and `test_watch_session_end_to_end`; fix with configured short timeouts or event-based waits, preserving semantics.

## Non-Functional Requirements

- **Coverage is sacred:** line/branch coverage must be ≥ the recorded baseline after every consolidation or test removal; before/after values recorded in plan.md.
- **No weakened tests:** every modified test asserts the same behavior as before. If a wait is proven semantically necessary, document the evidence in plan.md instead of forcing a change.
- Tests may only be removed by merge/parametrize with coverage verification; the passing-test counts (1,582 unit / 90 integration / 5 smoke) may only drop via such merges.
- ruff/black clean, type hints, docstrings per workflow quality gates.

## Acceptance Criteria (numeric, local measurement)

- Unit suite ≤ **15s** (baseline 40.7s)
- Integration suite ≤ **2:30** (baseline 5:10)
- E2E smoke subset ≤ **1:15** (baseline 1:59)
- Coverage ≥ baseline in every phase
- All tests pass; CI Stage 1 + matrix jobs measurably faster with `-n auto`

## Out of Scope

- CI workflow matrix rationalization (deferred to a future track)
- `test_cli.py` consolidation/parametrization (deferred)
- Changes to product source-code behavior (test infrastructure only)
- The opt-in performance benchmark suite (`tests/performance`)
