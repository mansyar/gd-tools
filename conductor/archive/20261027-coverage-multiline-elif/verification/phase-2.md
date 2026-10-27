# Phase 2 verification — Header-end injection (collector + port)

- Track: 20261027-coverage-multiline-elif
- Phase: 2 (Header-end injection)
- Date: 2026-10-27
- Branch: fix/20261027-coverage-multiline-elif
- Base: main @ 332573836dfcd642f9df80b48037f3339e09ab24
- Head: 4499361714290a0754ff1ea98a107b89e848e156
- Result: verified (47 passed, 0 failed; Godot batch parse session green)

## Commits

- 30e9289 `fix(coverage): insert after-line trackers after header terminator` (P2.T1)
- 4499361 `test(coverage): mirror header-end rule in injection port and drift guard` (P2.T2)

## Commands

| Command | Exit | Result |
|---|---|---|
| `$env:CI='true'; pytest tests/integration/test_coverage_instrumentation_parses.py -q` (first run, before test-assert correction) | 1 | 46 passed, 1 failed (`test_multiline_elif_tracker_lands_after_header_terminator`, second assert tripped on value-preserving `hit_ret` wrappers inside the guard — see deviations) |
| `$env:CI='true'; pytest tests/integration/test_coverage_instrumentation_parses.py -q` (final run) | 1 | 47 passed, 0 failed; trailing `FAIL Required test coverage of 80.0%` is the repo-global `fail-under=80` gate on a single-file run (total 10%), identical in kind to the Phase 1 baseline — not a test failure |

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 multiline elif tracker lands after header terminator and instrumented output parses | pass | `test_multiline_elif_tracker_lands_after_header_terminator`, `test_multiline_elif_fixture_injects_after_header_terminator`, and the module-scoped Godot batch parse session all green in the final run |
| AC-2 single-line branch headers inject exactly as before | pass | `test_single_line_branch_headers_inject_exactly_as_before` green; single-line headers resolve `header_end == target`, so `insert_index` and indent are byte-identical to the old path |
| AC-3 nested brackets / string-comment colons / trailing comments / backslash continuations resolve to the true terminator | pass (implementation) | `_find_header_end` (both GDScript and port) counts `(`, `[`, `{`, ignores colons inside strings and after `#`, and only continues past EOL on `depth > 0` or a code trailing `\`; unresolved headers fail open to the historical position. Covered by the unit + fixture suite (47 passed); no dedicated new edge-case tests were added in this phase |
| AC-6 port and collector agree | pass | `test_injection_port_tracks_the_collector` green, extended to require `_find_header_end` defined and used in both collector and port |
| Boolop anchor stays red until Phase 3 | confirmed untouched | `plan_generator.py`, `test_omissions.py`, `test_plan_generator_boolops.py` not touched (no such files in this diff) |

## Evidence paths

- Collector fix: `src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd` (`_find_header_end` + header-end `insert_index` + EOF-safe indent fallback)
- Port mirror + drift guard: `tests/integration/test_coverage_instrumentation_parses.py` (`_find_header_end`, `_inject` header-end rule, extended `test_injection_port_tracks_the_collector`)
- This file: `conductor/tracks/20261027-coverage-multiline-elif/verification/phase-2.md`

## Deviations

1. `tests/integration/test_coverage_instrumentation_parses.py` — `test_multiline_elif_tracker_lands_after_header_terminator`, second assert narrowed from `"GdToolsNativeCoverage" not in segment` to `"GdToolsNativeCoverage.hit(" not in segment` (with comment). Reason: the header under test contains an or-chain (`action == "run" or fast`), whose arms are value-preserving `hit_ret()` operand wrappers placed inside the guard by design (unchanged `operand_span` wrapping, parseable — the batch session proves it). The broad substring matches `hit_ret` too, so the assert could never pass while boolop wrapping exists, regardless of the header-end fix. The narrowed assert keeps the test's intent (no line-inserted `hit()` inside the open condition) while allowing the expected wrappers. First assert and all other red-test logic unchanged.
2. `src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd` — indent lookup guarded (`insert_index` in range, else fall back to `target_index` indent). Reason: header-end insertion at EOF (`insert_index == size`) would index out of bounds; the guard prevents a crash and fails open. No behavior change for in-range (single-line) cases.

## Notes

- `conductor/tracks/20261027-coverage-multiline-elif/plan.md` shows as modified in `git status` but was not touched by this phase (primary-agent state); it was left uncommitted.
- Retry budget: 1 fix retry used (test-assert correction); 1 remaining, unused.
- Phase 3 owns boolop re-anchor + PLAN_VERSION bump; nothing in this phase changes plan output.
