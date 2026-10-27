# Coverage Multiline Elif — Specification

> Requirements are stable. Once an `FR`, `NFR`, or `AC` ID is approved, do not
> renumber it. If a requirement is removed, mark it `Withdrawn` instead of
> deleting it.

## Overview

Fix the native coverage injector so scripts with multi-line branch headers
(parenthesized elif, multi-line match patterns) instrument to parseable
GDScript. After-line trackers insert after the header-terminating colon, and
and/or expression points inside elif/match guards anchor to their true header.

## Problem / Motivation

A passing suite (281/281) fails `gd-tools test --coverage --min 80` with
Godot error 43 on `touch_controls.gd`: measured coverage clears the gate
(94.8% vs 80%) but 1 of 23 targets cannot be instrumented, failing the run.
Any project containing the triggering construct cannot use `--coverage --min`
as a CI gate without excluding the file, silently weakening the metric.

## Goals & Success Metrics

- **Goal:** The repro script instruments to parseable GDScript and the coverage
  run has zero omissions for this construct.
- **Metric:** New regression tests fail before the fix and pass after; the
  batched Godot parse check is green including the new fixture.

## Scope

### In Scope

- Header-end scan for after-line branch types (elif_true, match_case,
  if_false) in the GDScript collector.
- Re-anchor and/or expression points inside elif_branch / match guards to the
  nearest branch header.
- Plan version bump for cache invalidation.
- Python test-port mirror plus drift-guard update.
- Omission-gate message-level split test (incomplete measurement vs below
  threshold).

### Out of Scope

- Omission message wording changes.
- New process exit codes (keep warn-without-`--min` / fail-gate-with-`--min`).
- Inferred-type const handling (no tracking point there).
- Full E2E coverage run.

## Bug Details

- **Reproduction steps:**
  1. Suite passes `gd-tools test` 281/281.
  2. Run `gd-tools test --coverage --min 80` (also with `--no-cache`).
  3. Observe exit 1 with 94.8% lines vs 80% but 1 of 23 targets uninstrumented.
- **Expected behavior:** The injector handles multi-line headers; the file
  instruments and the gate passes when measured coverage clears it.
- **Actual behavior:** `touch_controls.gd` omitted — tracker injection breaks
  the parse (error 43), failing the whole run.
- **Root-cause hypothesis:** elif_true recorded at the header start line
  inserts the tracker on the next line, inside the `( ... )` condition;
  or-chain spans inside the elif anchor to the if line.
- **Regression test:** Python header-scan units + GDScript fixture with
  multi-line elif/match through the batch parse check; must fail before, pass
  after.

## Functional Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-1 | After-line branch trackers (elif_true, match_case, if_false) insert after the header-terminating colon, not the header start line. | must |
| FR-2 | Header-end detection handles parens/brackets/braces, strings, comments, and backslash continuation. | must |
| FR-3 | and/or expression points inside elif_branch / match guards anchor to that header, not the enclosing statement. | must |
| FR-4 | Stale cached plans invalidate via a plan version bump. | must |
| FR-5 | The Python test port mirrors the header-end rule and the drift guard stays green. | must |
| FR-6 | The omission gate keeps the message-level split: incomplete measurement vs below threshold. | must |

## Non-Functional Requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | No behavior change for single-line headers (tracker lands exactly as today). |
| NFR-2 | Instrumentation keeps line counts stable for span wraps (no added/removed newlines inside operands). |
| NFR-3 | Fail open: unresolvable header end never corrupts source; worst case keeps today's omission path. |

## Acceptance Criteria

| ID | Criterion | Verifies |
| --- | --- | --- |
| AC-1 | Multi-line parenthesized elif instruments to code Godot parses (error 43 gone). | FR-1 |
| AC-2 | Single-line elif/else/match instrumentation output is byte-identical to today. | FR-1 |
| AC-3 | Headers with nested brackets, strings/comments containing colons, trailing comments, and backslash continuations resolve to the true terminator. | FR-2 |
| AC-4 | or-chain inside elif reports against the elif line. | FR-3 |
| AC-5 | Old cached plan is rejected after the version bump. | FR-4 |
| AC-6 | Python port and GDScript collector agree (drift guard green). | FR-5 |
| AC-7 | Omission-gate test distinguishes incomplete measurement from below-threshold failure. | FR-6 |

## Edge Cases

- Nested brackets in conditions; colons inside strings/comments/subscripts/
  ternaries; backslash-continued elif; trailing comments after the colon; empty
  body / EOF right after header; CRLF and tab indentation; match `when` guards.

## Dependencies

- **Tracks:** none
- **External:** none (Godot binary needed only for parse/e2e checks per
  workflow manual exceptions)

## Open Questions & Assumptions

- **Assumption:** gdtoolkit reports elif_branch at the header first line;
  header terminator is the first colon at bracket-depth 0.
- **Assumption:** project-gate coverage and watch-CI PR policy from the
  regenerated workflow apply.

## References

- Filed bug report (repro, suspect file, expected behavior)
- `src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd`
  (`_inject_trackers`)
- `src/gd_tools/coverage/plan_generator.py` (anchors, PLAN_VERSION)
- `tests/integration/test_coverage_instrumentation_parses.py` (batch parse
  check)
