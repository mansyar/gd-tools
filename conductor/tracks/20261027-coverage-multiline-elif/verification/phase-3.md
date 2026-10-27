# Phase 3 evidence — Anchor correction + version bump + gate contract

Track: `20261027-coverage-multiline-elif` · Phase 3 (FR-3, FR-4, FR-6; AC-4, AC-5, AC-7)
Branch: `fix/20261027-coverage-multiline-elif`
Date (UTC): 2026-10-27 · `PLAN_VERSION` after phase: **9** (was 8)

## Change (P3.T1 — one file, in Touches)

`src/gd_tools/coverage/plan_generator.py` only:

1. **Re-anchor** (`_map_expression_anchors` + new `BRANCH_GUARD_ANCHOR_NODES`):
   the pre-pass walk now also updates its carried enclosing line on
   `elif_branch` and `match_branch` nodes, so an `and`/`or` chain (or
   ternary) inside an `elif` guard anchors to the `elif` header line and
   one inside a `match` pattern guard anchors to the case header line,
   instead of the enclosing `if`/`match` line. The two node names stay
   out of `ANCHOR_NODES` (their lines are keyword/case labels, not
   statement insertion points); expression points are span-wrapped, so
   the header line is their correct reporting anchor. All other anchor
   behavior is identical (same walk, same statement/header set).
2. **Version bump** `PLAN_VERSION` 8 → 9, with a docstring paragraph
   recording why v8 plans are stale (elif/match-guard arms attributed
   to the wrong line).

No snapshot refresh was needed in `tests/unit/test_plan_generator_boolops.py`:
no assertion in that file encodes an old anchor (all expectations are
line-exact against corrected values or relative to the `PLAN_VERSION`
constant). `tests/unit/test_omissions.py` was left untouched per the brief.

## Verification (exact command from the brief)

Command (PowerShell form — `CI=true` prefix is sh syntax; same env, same args):

```
$env:CI='true'; pytest tests/unit/test_plan_generator_boolops.py tests/unit/test_plan_generator.py tests/unit/test_omissions.py tests/integration/test_coverage_instrumentation_parses.py -q
```

- Exit code: **1** (see §Fallout — every remaining red item is in a file
  outside Touches and is prescribed `blocked` follow-up, not a phase defect).
- Result line: **10 failed, 134 passed, 17 errors** (+ the repo-global
  `fail-under=80` gate tripping on this 4-file partial run: total 29.17% —
  a per-run-totals artifact, not a test failure).

## Turned green (red since Phase 1)

- `tests/unit/test_plan_generator_boolops.py::test_or_chain_in_elif_anchors_to_elif_header_line`
  — **PASSED** through the src fix (or-site/or-right now anchor to the
  `elif` header line 6), not through any test change. Whole boolops file
  is green.

## Confirmed still green (P3.T2, in-scope portion)

- `test_generate_plan_cached_miss_stale_plan_version` and
  `test_read_plan_json_rejects_stale_plan_version` (both key off the
  `PLAN_VERSION` constant relatively) — **PASSED** against the bumped 9.
- Every other test in `test_plan_generator_boolops.py` — **PASSED**.

## Fallout (all outside Touches — primary follow-up, none attempted)

1. **Version-literal test** — `test_plan_generator.py::
   test_plan_version_is_8_after_inference_annotations`: `assert 9 == 8`.
   File is outside Touches; per the brief the literal is not mine to fix.
2. **Expected-plan fixtures** — 7× `test_plan_generation_matches_expected[*]`:
   `tests/fixtures/plans/*.expected.json` still carry `"version": 8` and
   `read_plan_json` rejects them (`Unsupported plan version: 8 (expected 9)`).
   Regenerating them (e.g. via `tools/generate_expected_plans.py`) is outside
   Touches. Note: the `match_stmt`/`branches` fixtures may additionally pick
   up re-anchored guard arms once regenerated — the primary should diff them
   against this phase's anchor intent before accepting.
3. **Omissions fixture (blocks gate-split confirmation)** — all 17
   `test_omissions.py` tests ERROR at the `plan` fixture because
   `tests/fixtures/coverage_plans/test_plan.json` carries `"version": 8`.
   That includes `test_incomplete_measurement_and_below_threshold_are_distinct`
   (FR-6/AC-7): the test logic itself is version-agnostic, but it cannot run
   until the fixture is refreshed — outside Touches, so the gate-split
   re-confirmation is **pending primary fixture refresh**, not failed.
4. **Integration port drift (Phase 2 tests, new failure mode)** —
   `test_multiline_elif_tracker_lands_after_header_terminator` and
   `test_multiline_elif_fixture_injects_after_header_terminator` now fail.
   Root cause, verified by reading both injectors: the re-anchored span-less
   `or_short` point now shares the `elif` header line; the Python port
   `_inject` (integration file, line ~508) line-injects it immediately
   before the `elif (` line, and the subsequent `elif_true` `_find_header_end`
   scan then starts on the injected tracker line and fails open to the
   historical position. The real collector does not have this problem: it
   skips `_short` entries outright
   (`gd_tools_native_coverage.gd:350-354`, "Short-circuit arms are derived
   at write() as site - right"). The port needs the same `_short` skip to
   track the collector — but the port file is explicitly off-limits this
   phase, so this is primary follow-up (one-line mirror fix + re-run).
   The Godot batch-parse session itself is unaffected (failure is in the
   Python port's placement asserts, before any Godot step).

## Statement for the primary

The phase goal is implemented and its red test is green; the remaining red
is version-staleness + port-mirror fallout in forbidden files, exactly the
contingency the brief prescribes `blocked` for. Suggested primary sequence:
(1) port `_short` skip, (2) regenerate `*.expected.json` + omissions
`test_plan.json` at v9, (3) update the `== 8` literal (plus the `== 8`
literals in `test_plan_generator_ternary_spans.py` /
`test_plan_generator_inference_ignores.py`, outside this phase's
verification set but red in full CI), (4) re-run this phase's command.
