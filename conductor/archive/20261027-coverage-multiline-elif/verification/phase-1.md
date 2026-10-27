# Phase 1 Verification — Regression harness (red)

- Track: 20261027-coverage-multiline-elif
- Phase: Phase 1 (Regression harness, red — tests only)
- Date: 2026-10-27
- Branch: fix/20261027-coverage-multiline-elif
- Base: main @ 332573836dfcd642f9df80b48037f3339e09ab24
- Head: d7ac455c2f209463c0137d7bad9fbf431cd3cb0e
- Result: verified (red harness: intended new tests fail, all else passes)

## Commits

- 5fd869d69ece87c6ff843185c9d912c1d47ab763 —
  test(coverage): add multiline elif fixture and header-end injection
  red tests (P1.T1, P1.T2)
- d7ac455c2f209463c0137d7bad9fbf431cd3cb0e —
  test(coverage): add boolop anchor, stale-plan, and gate-split
  regression tests (P1.T3, P1.T4)

## Commands

Note: the brief's `CI=true pytest ...` prefix is sh syntax and the
machine shell is PowerShell, so the suite was run as
`$env:CI='true'; pytest ...` — same command, same env, same args.

| Layer | Command | Exit | Summary |
| --- | --- | --- | --- |
| unit | `$env:CI='true'; pytest tests/unit/test_plan_generator_boolops.py tests/unit/test_omissions.py -q` | 1 (expected) | 40 passed, 1 failed: the new FR-3 anchor test is red (`assert 4 == 6` — or-chain anchors to the if line, not the elif line). New stale-version (FR-4) and gate-split (FR-6) tests pass. Trailing coverage-gate error is the repo-global fail-under=80 on a narrow run, not a test failure. |
| integration | `$env:CI='true'; pytest tests/integration/test_coverage_instrumentation_parses.py -q` | 1 (expected) | 45 passed, 2 failed: both new header-end tests are red — the elif tracker lands directly after `elif (` inside the parens, and the fixture's match_case tracker lands inside the `[1,` pattern. The single-line NFR-1 pin, drift guard, and all Godot batch parse tests pass. |

## Red proof (new tests that fail before the fix)

- tests/unit/test_plan_generator_boolops.py::test_or_chain_in_elif_anchors_to_elif_header_line —
  FAIL, `assert 4 == 6` (FR-3 / AC-4).
- tests/integration/test_coverage_instrumentation_parses.py::test_multiline_elif_tracker_lands_after_header_terminator —
  FAIL, tracker `hit(0, 7)` injected between `elif (` and the condition
  (FR-1 / AC-1).
- tests/integration/test_coverage_instrumentation_parses.py::test_multiline_elif_fixture_injects_after_header_terminator —
  FAIL, elif tracker at output line 10 instead of after the `):`
  terminator; match_case tracker inside the multi-line pattern
  (FR-1 / AC-1).

## Green pins (must pass now and after)

- test_single_line_branch_headers_inject_exactly_as_before (NFR-1 / AC-2)
- test_read_plan_json_rejects_stale_plan_version (FR-4 / AC-5 contract)
- test_incomplete_measurement_and_below_threshold_are_distinct
  (FR-6 / AC-7)
- Fixture parses: `generate_plan` returns exactly 1 file for
  multiline_elif.gd (asserted inside the fixture test before injection).

## Acceptance criteria

| ID | Criterion | Evidence | Status |
| --- | --- | --- | --- |
| AC-1 | Multi-line elif instruments to parseable code | Red tests above pin the defect; fixture parses | red (as intended) |
| AC-2 | Single-line output byte-identical | NFR-1 pin test passes | pinned |
| AC-3 | Bracket/string/comment/continuation terminators | Covered by FR-1 red tests for parens; full edge sweep belongs to Phase 2 | partial (Phase 2) |
| AC-4 | or-chain in elif reports against elif line | Red anchor test pins it | red (as intended) |
| AC-5 | Old cached plan rejected | Stale-version test passes on current PLAN_VERSION=8 | pinned |
| AC-6 | Port/collector drift guard green | test_injection_port_tracks_the_collector passes | pinned |
| AC-7 | Gate distinguishes incomplete vs below-threshold | Split test passes | pinned |

## Deviations

None. No file outside Touches was edited. `git status` confirms no
`src/` modification; the pre-existing `plan.md` modification belongs to
the primary agent and was left untouched (commits used explicit
`git add` on task files only). No fixture-list registration was needed:
the gdscript fixtures directory has no central registry — both
consumers (expected-plans tool, plan-generation params) use explicit
name lists, and the integration batch uses inline CASES.

## Notes

- Godot binary is present: the full batched parse session ran green
  (45 passed), so the harness canary is honest.
- Phase 2 must move the port's after-line insertion to the
  header-terminating colon for elif_true/match_case/if_false and mirror
  it in `_inject`; Phase 3 must re-anchor elif/match-guard boolops and
  bump PLAN_VERSION (the stale test keys off the constant, so it stays
  green through the bump).
