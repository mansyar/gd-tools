# Coverage Multiline Elif — Implementation Plan

> **Branch:** `fix/20261027-coverage-multiline-elif`
> **Base:** `main` @ `332573836dfcd642f9df80b48037f3339e09ab24`
>
> Phase states are `pending`, `in_progress`, `verified`, `failed`, or `blocked`.
> Only the primary agent writes this file. Phase subagents report results and the
> primary records them.

## Phase 1: Regression harness (red)

- **Goal:** Failing regression tests pin the multi-line header defect and the mis-anchored boolop.
- **Depends on:** none
- **Covers:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- **Touches:** `tests/unit/test_plan_generator_boolops.py`, `tests/unit/test_omissions.py`, `tests/integration/test_coverage_instrumentation_parses.py`, `tests/fixtures/gdscript/multiline_elif.gd`
- **Verification:** `CI=true pytest tests/unit/test_plan_generator_boolops.py tests/unit/test_omissions.py -q` (new tests FAIL before fix)
- **Status:** verified

- [x] **P1.T1: Add multiline_elif.gd fixture (repro elif + multi-line match pattern)** — covers: FR-1
- [x] **P1.T2: Add header-end injection units via Python port (tracker after `):`, single-line unchanged)** — covers: FR-1, FR-2
- [x] **P1.T3: Add boolop anchor expectation (or-chain in elif anchors to elif line) + PLAN_VERSION stale rejection** — covers: FR-3, FR-4
- [x] **P1.T4: Add omission-gate message-level split test (incomplete vs threshold)** — covers: FR-6

**Result:** verified
**Checkpoint:** b91c3f0
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-1.md
**Note:** Primary applied black formatting to the 3 touched test files (pre-existing style baseline; base versions were clean) and re-verified red state unchanged.

<!--
The primary appends after acceptance:
**Result:** verified
**Checkpoint:** <short-sha>
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-1.md
-->

## Phase 2: Header-end injection (collector + port)

- **Goal:** After-line trackers land after the header terminator and instrumented output parses.
- **Depends on:** Phase 1
- **Covers:** FR-1, FR-2, FR-5, AC-1, AC-2, AC-3, AC-6
- **Touches:** `src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd`, `tests/integration/test_coverage_instrumentation_parses.py` (port mirror only)
- **Verification:** `CI=true pytest tests/integration/test_coverage_instrumentation_parses.py -q` (batch parse green incl. new fixture)
- **Status:** verified

- [x] **P2.T1: Implement _find_header_end scan (depth-aware colon, strings/comments/backslash) + use for elif_true/match_case/if_false** — covers: FR-1, FR-2
- [x] **P2.T2: Mirror header-end rule in Python test port; update drift guard** — covers: FR-5

**Result:** verified
**Checkpoint:** ee6b024
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-2.md
**Deviations accepted:** (1) narrowed second assert in header-end red test to `GdToolsNativeCoverage.hit(` — hit_ret operand wrappers are by-design inside guards and parseable; first assert still pins FR-1. (2) EOF-safe indent fallback in collector (fail-open, no single-line behavior change).
**Note:** Primary applied black formatting to the port mirror file and re-verified 47 passed.

<!--
The primary appends after acceptance:
**Result:** verified
**Checkpoint:** <short-sha>
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-2.md
-->

## Phase 3: Anchor correction + version bump + gate contract

- **Goal:** Boolop anchors point at the true header; stale plans invalidate; gate split is pinned.
- **Depends on:** Phase 2
- **Covers:** FR-3, FR-4, FR-6, AC-4, AC-5, AC-7
- **Touches:** `src/gd_tools/coverage/plan_generator.py`, `tests/unit/test_plan_generator_boolops.py` snapshots, `tests/unit/test_omissions.py`, plus rework expansion (round 1): `tests/integration/test_coverage_instrumentation_parses.py` (port `_short` skip only), `tests/fixtures/plans/*.expected.json` (regenerate), `tests/fixtures/coverage_plans/test_plan.json` (version bump), version literals in `tests/unit/test_plan_generator.py`, `tests/unit/test_plan_generator_inference_ignores.py`, `tests/unit/test_plan_generator_ternary_spans.py`, `tests/integration/test_coverage_playtest_cli.py`
- **Verification:** `CI=true pytest tests/unit/test_plan_generator_boolops.py tests/unit/test_plan_generator.py tests/unit/test_omissions.py tests/integration/test_coverage_instrumentation_parses.py -q`
- **Status:** verified

- [x] **P3.T1: Re-anchor elif/match-guard boolops to nearest branch header; bump PLAN_VERSION** — covers: FR-3, FR-4
- [x] **P3.T2: Refresh plan snapshots + stale-cache test; confirm gate message split** — covers: FR-4, FR-6
- [x] **R3.T1-T4 (rework round 1): port `_short` skip mirror, regenerate 8 expected fixtures at v9, bump coverage_plans fixture, update version literals** — covers: FR-4, FR-5, FR-6

**Result:** verified
**Checkpoint:** a1c0f45
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-3.md
**Note:** Rework round 1 used (1 of 2). Regenerated fixture diffs are version-only; full phase command: 161 passed, 0 failed (exit 1 solely from partial-run fail-under=80 totals artifact).

<!--
The primary appends after acceptance:
**Result:** verified
**Checkpoint:** <short-sha>
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-3.md
-->

## Phase R1: Review Fixes

- **Goal:** Resolve review findings F1–F4 (edge-unit pins, anchor pins, drift-guard parity, version doc).
- **Depends on:** Phase 3
- **Covers:** F1, F2, F3, F4
- **Touches:** `tests/integration/test_coverage_instrumentation_parses.py`, `tests/unit/test_plan_generator_boolops.py`, `conductor/tech-stack.md`
- **Verification:** `CI=true pytest tests/unit/test_plan_generator_boolops.py tests/integration/test_coverage_instrumentation_parses.py -q` plus `ruff check` / `black --check`
- **Status:** verified

- [x] **R1.T1: Resolve F1 + F3 (port edge units + `_short` parity in drift guard)** — covers: F1, F3
- [ ] **R1.T2: Resolve F2 (match-when-guard + ternary-in-guard anchor tests)** — covers: F2 (ternary half green; match half carried to R2 — real src gap)
- [x] **R1.T3: Resolve F4 (tech-stack.md schema version v7 → v9)** — covers: F4

**Result:** partial — R1.T1/R1.T3 done; R1.T2 match-when half blocked by src gap (guarded_match_branch). Carried to Phase R2 (round 2 of 2).
**Checkpoint:** d07c2e0
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-R1.md

## Phase R2: Review Fixes, round 2 — guarded match branches

- **Goal:** Resolve the R1.T2 blocker: guarded match cases (`guarded_match_branch`) anchor and emit like unguarded ones.
- **Depends on:** Phase R1
- **Covers:** F2, FR-3, AC-4
- **Touches:** `src/gd_tools/coverage/plan_generator.py`, `tests/fixtures/plans/*.expected.json` (only if the generator changes guarded-case output — accept intended diffs only)
- **Verification:** `CI=true pytest tests/unit/test_plan_generator_boolops.py tests/unit/test_plan_generator.py tests/unit/test_omissions.py tests/integration/test_coverage_instrumentation_parses.py -q` plus `ruff check` / `black --check`
- **Status:** verified

- [x] **R2.T1: Handle guarded_match_branch in plan generator (anchor set + match_case emission)** — covers: F2
- [x] **R2.T2: Confirm guarded-case plan output through snapshots/batch parse; keep PLAN_VERSION at 9 (unreleased)** — covers: F2

**Result:** verified
**Checkpoint:** 207870d
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-R2.md
**Note:** 169 passed, 0 failed (exit 1 solely from partial-run fail-under=80 totals artifact); zero fixture diffs; ruff/black clean.

<!--
Review fixes are appended by `conductor-review` as:

## Phase R1: Review Fixes

- **Goal:** Resolve review findings ...
- **Depends on:** Phase 2
- **Covers:** review findings
- **Touches:** ...
- **Verification:** ...
- **Status:** pending

- [ ] **R1.T1: Resolve <finding ID>** — covers: <finding ID>
-->
