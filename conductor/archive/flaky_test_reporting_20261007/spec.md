# Track: Flaky Test Reporting

**Type:** Feature
**Status:** Spec approved (2026-10-07)
**Branch:** `feature/flaky-test-reporting-20261007`

## Overview

Surface tests that pass only after a retry ("flaky") in the native test run
summary. The GDScript runtime already retries failed/timed-out tests when
`[test].retries > 0` and records `attempts` per test in the result protocol —
but a test that ultimately passed after retries is indistinguishable from one
that passed first try. This track makes recovered tests visible without
changing any pass/fail semantics.

## Background / Current State

- `gd_tools_test_runner.gd` retries on `failed`/`timeout` statuses when
  `retries > 0` and emits `"attempts": N` per test (protocol v3).
- The Python protocol model (`native_test/protocol.py`) already parses
  `attempts` (default 1).
- No flaky concept exists anywhere in aggregation or reporting today.

## Functional Requirements

- **FR1 — Definition:** a test is *flaky* iff final status is `passed` and
  `attempts > 1`. Covers both assertion-failure and timeout recoveries.
  Applies to sequential and parallel runs.
- **FR2 — First-attempt message (protocol v4):** the runner captures the first
  failed attempt's error message and emits it as an **optional**
  `first_failure_message` field in the per-test result. Protocol version bumps
  to **v4**. Python accepts payloads without the field (v3 compatibility:
  field absent → empty), so older result files still parse.
- **FR3 — Flaky panel:** when ≥1 flaky test exists, the terminal summary shows
  a *Flaky* panel listing each test with suite, test name, "passed on attempt
  N", and the first-attempt message collapsed to its first line, truncated to
  ~120 characters with an ellipsis. The panel is suppressed when there are no
  flaky tests and in `--quiet` mode; watch-mode re-runs render it like any
  run.
- **FR4 — Exit codes unchanged:** flakiness never fails the run
  (all-pass-with-flaky ⇒ exit 0).
- **FR5 — Parallel & watch:** detection derives purely from per-test results,
  so it works identically under `--parallel N` and watch re-runs.

## Non-Functional Requirements

- No new config keys; behavior derives solely from the existing `retries`
  setting (flaky reporting is inert when `retries = 0`).
- New Python code meets the standard gates (>80% line / >70% branch coverage,
  ruff, black, type hints, docstrings).

## Acceptance Criteria

1. `retries = 0`: output byte-identical to today; no panel ever.
2. `retries = 1`, test fails once then passes: panel lists the test, "passed
   on attempt 2", first-attempt message (first line, ≤120 chars); exit 0.
3. Timeout-recovered test appears as flaky.
4. No flaky tests ⇒ output identical to today.
5. Parallel run aggregates flaky tests across all workers.
6. Payload without `first_failure_message` parses; panel omits the message
   line.
7. `--quiet` suppresses the panel.

## Out of Scope

- JUnit XML flaky attributes/properties.
- Artifact index / `--output json` flaky fields.
- `[test].fail_if_flaky` gating.
- Cross-run flakiness history/trends.
- Editor plugin dock flaky indicator.
- Per-attempt history beyond the first failure message.
