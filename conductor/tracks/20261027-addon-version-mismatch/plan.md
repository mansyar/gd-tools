# Coverage Addon Version Gate — Implementation Plan

> **Branch:** `feat/20261027-addon-version-mismatch`
> **Base:** `main` @ `3d70aa37e2e8a02f998a006bbdaf8cd7d823f7f3`
>
> Phase states are `pending`, `in_progress`, `verified`, `failed`, or `blocked`.
> Only the primary agent writes this file. Phase subagents report results and the
> primary records them.

## Phase 1: Refusal-gate regression tests (red)

- **Goal:** Failing CLI-level tests pin the exit-2 refusal contract.
- **Depends on:** none
- **Covers:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- **Touches:** `tests/unit/test_addon_check.py`, `tests/unit/test_coverage_addon_gate.py` (new)
- **Verification:** `CI=true pytest tests/unit/test_addon_check.py tests/unit/test_coverage_addon_gate.py -q` (new gate tests FAIL before fix)
- **Status:** in_progress

- [ ] **P1.T1: Add gate tests for stale/missing coverage addon (exit 2, zero suites dispatched)** — covers: FR-1, FR-2, AC-1, AC-2, AC-7
- [ ] **P1.T2: Add gate tests for native test addon + suppression/newer/message-content cases** — covers: FR-3, FR-4, FR-5, FR-6, AC-3, AC-4, AC-5, AC-6

<!--
The primary appends after acceptance:
**Result:** verified
**Checkpoint:** <short-sha>
**Evidence:** conductor/tracks/<track-id>/verification/phase-1.md
-->

## Phase 2: Strict gate in the coverage dispatch path

- **Goal:** `test --coverage` refuses pre-dispatch on stale/missing addons with a promoted message.
- **Depends on:** Phase 1
- **Covers:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- **Touches:** `src/gd_tools/addon_check.py`, `src/gd_tools/commands/test.py`, `tests/unit/test_addon_check.py`, `tests/unit/test_coverage_addon_gate.py`
- **Verification:** `CI=true pytest tests/unit/test_addon_check.py tests/unit/test_coverage_addon_gate.py -q` (green) plus full `tests/unit` for regressions
- **Status:** pending

- [ ] **P2.T1: Add strict gate helper (stale/missing → exit 2, both addons, env-suppressible)** — covers: FR-1, FR-2, FR-3, FR-4, FR-5
- [ ] **P2.T2: Wire gate into `test --coverage` pre-dispatch with promoted refusal message** — covers: FR-6, FR-7, AC-6
- [ ] **P2.T3: Confirm no behavior change for matching versions and non-coverage commands** — covers: NFR-1, NFR-2, NFR-3

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