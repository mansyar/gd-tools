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
- **Status:** pending

- [ ] **P2.T1: Implement _find_header_end scan (depth-aware colon, strings/comments/backslash) + use for elif_true/match_case/if_false** — covers: FR-1, FR-2
- [ ] **P2.T2: Mirror header-end rule in Python test port; update drift guard** — covers: FR-5

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
- **Touches:** `src/gd_tools/coverage/plan_generator.py`, `tests/unit/test_plan_generator_boolops.py` snapshots, `tests/unit/test_omissions.py`
- **Verification:** `CI=true pytest tests/unit/test_plan_generator_boolops.py tests/unit/test_plan_generator.py tests/unit/test_omissions.py tests/integration/test_coverage_instrumentation_parses.py -q`
- **Status:** pending

- [ ] **P3.T1: Re-anchor elif/match-guard boolops to nearest branch header; bump PLAN_VERSION** — covers: FR-3, FR-4
- [ ] **P3.T2: Refresh plan snapshots + stale-cache test; confirm gate message split** — covers: FR-4, FR-6

<!--
The primary appends after acceptance:
**Result:** verified
**Checkpoint:** <short-sha>
**Evidence:** conductor/tracks/20261027-coverage-multiline-elif/verification/phase-3.md
-->

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
