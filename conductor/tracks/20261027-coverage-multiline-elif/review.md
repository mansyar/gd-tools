# Review: Coverage Multiline Elif

- **Track:** `20261027-coverage-multiline-elif`
- **Type:** `bug`
- **Branch:** `fix/20261027-coverage-multiline-elif`
- **Range:** `332573836dfcd642f9df80b48037f3339e09ab24..9a1f5f8544fe4c4731e57ba814c030b6ab3dfd8f`
- **Date:** `2026-10-27`
- **Verdict:** `PASS`

## Summary

The header-end injection fix, guard re-anchor, and v9 invalidation are correct and all scoped checks are green, but the reviewer's edge analysis shows the new code paths are only partially pinned: FR-2/AC-3 edge branches and FR-3 match-guard/ternary anchors lack direct tests, and the drift guard still does not cover the `_short` skip parity that actually diverged in Phase 2. All four findings are mechanical and go to a fix phase; one also corrects stale version docs.

## Verification

| Layer | Command | Result | Evidence |
| --- | --- | --- | --- |
| test | `CI=true pytest tests/unit` | pass (1842 passed, 3 skipped) | primary run |
| test | `CI=true pytest tests/integration/test_coverage_instrumentation_parses.py tests/integration/test_coverage_playtest_cli.py` | pass (50 passed) | primary run |
| test | `CI=true pytest tests/integration/test_coverage_playtest.py` | pass (4 passed) | primary run |
| coverage | pytest-cov via unit run | pass (94.85% line, gate 80) | primary run |
| lint | `ruff check src/ tests/` | pass | primary run |
| format | `black --check src/ tests/` | pass (203 unchanged) | primary run |
| typecheck | none configured | not-run | workflow config |
| build | `python -m build` | pass (sdist + wheel) | primary run |
| test (full) | `CI=true pytest` | not-run (timed out at 10 min, Godot-heavy) | gap, not a pass |

## Requirements

| ID | Implemented by | Verified by | Status |
| --- | --- | --- | --- |
| FR-1 | P2.T1 | header-end units + batch Godot parse | covered |
| FR-2 | P2.T1 + Phase R1 (6 port-level edge units) | paren-elif + multiline-match paths + string/comment/backslash/nested/EOF units | covered |
| FR-3 | P3.T1 + Phase R2 (guarded_match_branch src fix) | elif or-chain + match-when-guard + elif-ternary anchor tests | covered |
| FR-4 | P3.T1, P3.T2 | stale-rejection test + regenerated fixtures | covered |
| FR-5 | P2.T2, R3.T1 | drift guard green | covered |
| FR-6 | P1.T4 | gate-split test | covered |
| NFR-1 | P2.T1 | byte-identical single-line test | covered |
| NFR-2 | P2.T1 | line-count test + batch parse | covered |
| NFR-3 | P2.T1 + Phase R1 (terminator-on-last-line unit) | EOF-safe fallback + last-line unit | covered |
| AC-1 | P2.T1 | batch parse incl. new fixture | covered |
| AC-2 | P2.T1 | byte-identical test | covered |
| AC-3 | P2.T1 + Phase R1 edge units | nested-bracket depth + string/comment/backslash/trailing-comment/EOF units | covered |
| AC-4 | P3.T1 | elif or-chain anchor test | covered |
| AC-5 | P3.T1, P3.T2 | stale-version test | covered |
| AC-6 | P2.T2, R3.T1 | drift guard | covered |
| AC-7 | P1.T4 | gate-split test | covered |

## Findings

### Critical

- none

### High

- none

### Medium

- **F1 — Header-scan edge paths lack direct units**
  - **File:** `tests/integration/test_coverage_instrumentation_parses.py:897-984`
  - **What:** FR-2/AC-3 edges (colons in strings/comments, trailing comments, backslash continuations, EOF-right-after-header) are implemented in `_find_header_end` but only the paren-elif path is exercised.
  - **Why:** The scan's string/comment/depth/backslash branches can regress silently.
  - **Fix:** Add port-level `_find_header_end` units for colon-in-string/comment, trailing comment, backslash-continued elif, nested brackets, terminator-on-last-line.
  - **Requirement:** FR-2
  - **Test gap:** port-level edge units listed above

- **F2 — Match-guard and ternary-in-guard anchors untested**
  - **File:** `src/gd_tools/coverage/plan_generator.py:687-697`
  - **What:** Re-anchor covers elif/match guards for boolops and ternaries, but only the single-line elif or-chain is pinned.
  - **Why:** Match `when`-guard boolops and ternary-in-elif-guard can regress with no test failing.
  - **Fix:** Add plan-generator units: or/and-chain in match `when` guard anchors to the case line; ternary in elif guard anchors to the elif line.
  - **Requirement:** FR-3
  - **Test gap:** match-when-guard + ternary-in-guard anchor tests in `tests/unit/test_plan_generator_boolops.py`

### Low

- **F3 — Drift guard does not pin `_short` skip parity**
  - **File:** `tests/integration/test_coverage_instrumentation_parses.py:749-770`
  - **What:** The guard pins `_find_header_end` presence and the after-line list but not the `_short` skip parity that actually diverged in Phase 2 (fixed only in R3.T1).
  - **Why:** The exact divergence class the guard exists to prevent is still uncovered.
  - **Fix:** Extend `test_injection_port_tracks_the_collector` with asserts that the collector source contains `ends_with("_short")` and the port `_inject` contains `endswith("_short")`.
  - **Requirement:** FR-5
  - **Test gap:** none (extends existing test)

- **F4 — Stale plan-schema version in tech-stack.md**
  - **File:** `conductor/tech-stack.md:132`
  - **What:** Migration note says the coverage plan schema is "currently v7"; the track bumps PLAN_VERSION to 9 (already stale at v8).
  - **Why:** Stale version docs mislead contributors about the FR-4 invalidation contract.
  - **Fix:** Update the parenthetical to v9 with the elif/match-guard re-anchor note, matching the PLAN_VERSION docstring at `src/gd_tools/coverage/plan_generator.py:68-72`.
  - **Requirement:** FR-4
  - **Test gap:** none

## Overrides

- none

## Plan compliance

All 3 phases verified with Result/Checkpoint/Evidence; every checked task implemented; deviations (Phase 2 assert narrowing, EOF fallback; Phase 3 rework expansion) recorded in plan.md; final diff stays within the union of phase Touches. Full unit suite (1842) green, so no cross-test regressions from the v9 fixture regeneration.

## Out of scope

- none

## Debt

- none (all findings fixed across rounds 1–2)

## Doc sync

`updated` — `conductor/tech-stack.md` schema note v7 → v9 (F4, Phase R1); no user-facing docs affected (CHANGELOG is release-generated; historical PLAN_VERSION narratives remain accurate).

## History

| Round | Verdict | Critical | High | Medium | Low | Fixed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BLOCK | 0 | 0 | 2 | 2 | 0 |
| 2 | PASS | 0 | 0 | 0 | 0 | 4 |
