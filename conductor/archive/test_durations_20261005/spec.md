# Specification: Test Durations Reporting

**Track ID:** test_durations_20261005
**Type:** Feature
**Branch:** feature/test-durations-20261005
**Created:** 2026-10-05

## Overview

Add pytest-parity test durations reporting to `gd-tools test`: an opt-in
**slowest-N table of individual tests**, activated by a CLI flag and
configurable via `gd-tools.toml`, built entirely on per-test timing data that
already flows through protocol v3. Pure Python-side reporting surface — no
GDScript/protocol changes.

## Background

- The native runner records per-test `duration_seconds` (attempt-aware;
  retries sum attempt durations) → protocol v3 → `NativeTestDetail.duration`
  → `TestDetail(name, suite, status, duration)` in `test_results.py` →
  `TestResult.test_details`.
- Today only a **total** duration appears in the summary table; there is no
  per-test duration surface.

## Functional Requirements

1. **FR1 — CLI flag:** `--durations N` on `gd-tools test` (`int`,
   `flag_value="10"` for bare usage, default `None`, mirroring the existing
   `--parallel` option pattern).
2. **FR2 — Config key:** `[test] durations: int | None` (`ge=0`) in
   `TestConfig`; CLI flag **overrides** config; absent in both → reporting
   disabled.
3. **FR3 — Semantics:** `N=0` → show **all** executed tests sorted
   slowest-first; `N>0` → slowest N; disabled → no table, output unchanged.
4. **FR4 — Table contents:** all executed tests (pass/fail/skip), each row
   with outcome marker, suite name, test name, duration (e.g. `1.23s`);
   rich-styled table via the existing `output` module.
5. **FR5 — Retry timing:** durations are sums across attempts (already true
   for `TestDetail.duration`; lock in with tests).
6. **FR6 — Placement:** printed after the results table and failure details,
   before the summary footer/success line.
7. **FR7 — Composition:** works with `--watch` (every re-run), `--parallel`,
   and `--suite`/`--test`/`--tag`/`--changed` filters; no changes to JUnit XML
   or artifacts.
8. **FR8 — Schema:** `docs/gd-tools.schema.json` gains `test.durations`
   (unit-test-synced per repo convention).

## Non-Functional Requirements

- TDD per `conductor/workflow.md`; >80% line / >70% branch coverage on new code.
- Type hints, docstrings, `ruff`/`black` clean; no new dependencies.

## Acceptance Criteria

1. `gd-tools test --durations 10` prints the slowest-10 table.
2. Bare `--durations` defaults to N=10.
3. `--durations 0` lists all tests, slowest-first.
4. `[test] durations = 5` in config works; CLI flag overrides it.
5. Without flag/config, default output is unchanged.
6. Composes with `--watch`, `--parallel`, and all filters.
7. `gd-tools config validate` accepts the new key; schema JSON synced.
8. Full suite green: `CI=true pytest`.

## Out of Scope

- Machine-readable durations JSON export.
- Artifact-index changes / historical duration comparison.
- Per-suite slowest table.
- Any GDScript runtime or protocol v3 changes.
