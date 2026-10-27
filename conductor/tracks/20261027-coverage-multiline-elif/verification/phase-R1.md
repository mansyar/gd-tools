# Phase R1 — Verification Evidence

Track: 20261027-coverage-multiline-elif — Review Fixes (F1–F4).

## Tasks

- R1.T1 (F1 + F3): six direct port-level `_find_header_end` units +
  `_short`-skip parity asserts in the drift guard —
  `tests/integration/test_coverage_instrumentation_parses.py`.
- R1.T2 (F2): match-`when`-guard or-chain test + elif-guard ternary
  test — `tests/unit/test_plan_generator_boolops.py`. **Partially
  blocked** (see below): the ternary half passes; the match half fails
  against a real implementation gap in `src` (outside Touches).
- R1.T3 (F4): coverage-plan-schema parenthetical v7 → v9 —
  `conductor/tech-stack.md` line 132.

## New tests added

R1.T1 in `tests/integration/test_coverage_instrumentation_parses.py`:

- `test_find_header_end_ignores_colon_inside_string`
- `test_find_header_end_ignores_colon_inside_comment`
- `test_find_header_end_allows_trailing_comment_after_terminator`
- `test_find_header_end_follows_backslash_continuation`
- `test_find_header_end_skips_nested_brackets`
- `test_find_header_end_resolves_terminator_on_last_line`
- Drift guard extended: collector side asserts
  `ends_with("_short")` still present; port side asserts
  `endswith("_short")` inside the `_inject` section.

R1.T2 in `tests/unit/test_plan_generator_boolops.py`:

- `test_or_chain_in_match_when_guard_anchors_to_case_line` — FAILS
  (blocked, correct expectation kept per brief).
- `test_ternary_in_elif_guard_anchors_to_elif_line` — passes.

## Commands run (exact) and exit codes

1. `$env:CI='true'; pytest
   tests/unit/test_plan_generator_boolops.py
   tests/integration/test_coverage_instrumentation_parses.py -q`
   → exit 1. Result line: `1 failed, 72 passed`. The single failure
   is `test_or_chain_in_match_when_guard_anchors_to_case_line`
   (`assert 4 == 5`). The same run also reports `FAIL Required test
   coverage of 80.0% not reached. Total coverage: 26.62%` — that is
   the repo-global fail-under=80 gate tripping on a 2-file partial
   run (a gate artifact), not a test failure.
2. `ruff check src/ tests/` → exit 0 (`All checks passed!`).
3. `black --check src/ tests/` → exit 0
   (`203 files would be left unchanged.`). No hand-formatting needed.

A temporary AST probe test (added, run, then removed before
committing) confirmed the root cause; it is not part of the diff.

## R1.T2(a) blocked — root-cause evidence

gdtoolkit parses a guarded match case (`1 when b or c:`) as a
`guarded_match_branch` node, NOT `match_branch`:

```
match_stmt
  expr  a
  guarded_match_branch        <- guard lives here
    pattern  1
    expr
      or_test
        b / or / c
  match_branch                <- only the unguarded `_` case
```

`BRANCH_GUARD_ANCHOR_NODES`
(`src/gd_tools/coverage/plan_generator.py:652`) is
`frozenset({"elif_branch", "match_branch"})` — it does not contain
`guarded_match_branch`, so `_map_expression_anchors` never resets the
enclosing anchor to the case line and the guard's `or_site` /
`or_right` / `or_short` points anchor to line 4 (the `match` line)
instead of line 5 (the case line). Observed plan points for the probe
source:

```
POINTS=[('or_site', 4, (5, 10, 5, 16)),
        ('or_right', 4, (5, 15, 5, 16)),
        ('or_short', 4, None), ...]
```

Spans are correct (line 5); only the anchor line is wrong.
Additionally observed (not pinned, out of scope): no `match_case`
branch point is emitted for the guarded case at all — the visitor has
`match_branch()` but no `guarded_match_branch()` handler, so the only
`match_case` point is the wildcard case on line 7.

Fix requires a `src` change (add `"guarded_match_branch"` to
`BRANCH_GUARD_ANCHOR_NODES`, plus a `guarded_match_branch()` visitor
handler emitting `match_case`), which is outside this phase's
Touches. Per the brief, the test keeps the correct expectation
(anchor == 5) rather than being weakened, and R1.T2 is reported
blocked/partial. No `src` file was modified.
