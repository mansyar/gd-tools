# Phase R2 — Verification Evidence

Track: 20261027-coverage-multiline-elif — Review Fixes, round 2 (guarded match branches).

## Tasks

- R2.T1: Handle `guarded_match_branch` in the plan generator (anchor set + `match_case` emission) — `src/gd_tools/coverage/plan_generator.py`.
- R2.T2: Confirm guarded-case plan output through snapshots/batch parse; keep PLAN_VERSION at 9.

## Src change summary

`src/gd_tools/coverage/plan_generator.py` (2 edits, following existing
conventions — frozen set, ALL_CAPS constant, visitor-pattern handler mirroring
`match_branch`):

1. `BRANCH_GUARD_ANCHOR_NODES` (line 652): added `"guarded_match_branch"` —
   `frozenset({"elif_branch", "match_branch"})` →
   `frozenset({"elif_branch", "match_branch", "guarded_match_branch"})`
   (formatted multi-line per black). Guard boolop/ternary anchors now reset
   to the guarded case line instead of the enclosing `match` line.
2. New visitor handler after `match_branch` (line ~905):
   `def guarded_match_branch(self, tree) -> None:` emitting
   `self._add_point(tree, "branch", "match_case")` — guarded cases now emit
   a `match_case` point on the case line, identical to unguarded cases.
   (Previously only the wildcard `match_branch` emitted one.)

No other `match_branch`/`elif_branch` handling sites exist in the file
(verified by grep: only `STATEMENT_HEADER_NODES` `match_stmt`, the anchor
set, and the two visitor methods), so no further handling was needed.

## PLAN_VERSION decision

Kept at 9 — no bump. v9 is unreleased (this track introduces it), so the
guarded-branch fix rides the already-pending v9 invalidation; a second bump
would churn caches for no benefit.

## Commands run (exact) and exit codes

1. `$env:CI='true'; pytest tests/unit/test_plan_generator_boolops.py
   tests/unit/test_plan_generator.py tests/unit/test_omissions.py
   tests/integration/test_coverage_instrumentation_parses.py -q`
   → exit 1. Result line: `169 passed in 10.56s`. Zero test failures —
   including the previously failing
   `test_or_chain_in_match_when_guard_anchors_to_case_line`.
   The exit-1 is solely the repo-global fail-under=80 gate tripping on a
   4-file partial run (`FAIL Required test coverage of 80.0% not reached.
   Total coverage: 31.48%` — a gate artifact, not a test failure), as
   anticipated by the brief.
2. `ruff check src/ tests/` → exit 0 (`All checks passed!`).
3. `black --check src/ tests/` → exit 0
   (`203 files would be left unchanged.`). No hand-formatting needed.

## Fixture-diff outcome (R2.T2)

`git status --porcelain tests/fixtures/plans/` → clean (no output);
`git diff --stat tests/fixtures/plans/` → no diff. Zero snapshot changes,
as expected: per Phase 3 regeneration evidence, no existing fixture source
contains a guarded match case, so the new `match_case` emission and anchor
change alter no existing fixture output. No regeneration via
`tools/generate_expected_plans.py` was needed and no expected JSON was
hand-edited.
