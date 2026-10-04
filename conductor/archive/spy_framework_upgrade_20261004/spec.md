# Spec: Doubles & Spy Framework Upgrade

**Track ID:** spy_framework_upgrade_20261004
**Type:** Feature
**Branch:** feature/doubles-spy-framework-20261004

## Overview

The native test runtime already provides `double()` / `partial_double()` /
`stub()` and the spy assertions `assert_called` / `assert_not_called` /
`assert_call_count` / `assert_call_arguments`, backed by the `GdToolsMock`
recorder. This track completes the framework: wildcard argument matching in
spy assertions, failure diagnostics that show what actually happened,
sequenced returns and fail-stubs, call-order verification, and property
access spying. All work targets the `GdToolsTest` public API and the
generated-double machinery (`gd_tools_test.gd`, `gd_tools_mock.gd`) in the
`gd-tools-test` addon.

## Functional Requirements

### FR1 — Arg matchers in spy assertions
- `assert_call_arguments` accepts arrays containing the string `"any"` as a
  per-element wildcard, matching the existing `stub()` semantics (exact >
  wildcard > default tiering is stub-only; assertions simply match-or-not
  per element).
- Exact-match assertions are unchanged — fully backward compatible.
- Matching logic is extracted into one shared helper used by both stubs and
  spy assertions (single source of truth).

### FR2 — Rich failure diagnostics
- Failed spy assertions print the recorded call list for the relevant
  method (per-call index + arguments), so "expected 2 calls, got 1" shows
  what actually happened.
- `assert_call_arguments` failures show a per-argument diff (expected vs
  actual per position), not just two flat arrays.
- Diagnostics are bounded (cap the printed call list length) to keep
  failure output readable.

### FR3 — Sequenced returns & fail stubs (StubBuilder)
- `to_return_seq(values: Array)`: successive matching calls return the
  values in order; the final value repeats on exhaustion.
- `to_fail(message: String)`: a matching call records a test failure via
  the standard failure path at call time; the doubled method still returns
  its type-appropriate zero value so the engine keeps running.
- Both compose with the existing specificity tiers and are per-double,
  per-test like all stub state.

### FR4 — Call-order assertions
- `assert_call_order(target, methods: Array, message = "")`: verifies the
  listed methods were called in the given relative order (subsequence
  semantics: unrelated calls between them are allowed).
- Failure output shows the actual recorded order.

### FR5 — Property-value assertions (amended 2026-10-04 after the Phase 6 spike)
- Original intent (intercepting property get/set on generated doubles) is
  impossible in GDScript: redeclaring a base var in a subclass is a parse
  error, and `_get`/`_set` never fire for declared (inherited) properties —
  verified empirically on Godot 4.7.2 (see plan notes).
- Replaced with `assert_property_is(target, property, expected, message)`:
  a property-value assertion that reads the current value via `get()` and
  works on doubles AND real Objects.
- Failure diagnostics consistent with FR2: missing property vs value
  mismatch with expected/actual rendering.

## Non-Functional Requirements
- TDD per workflow.md (failing GDScript suites first, then implement).
- No breaking changes to the existing double/stub/assert API.
- NDJSON protocol and Python orchestrator unchanged unless a defect forces
  a change; any such change is documented.
- Docs: README + USER_GUIDE sections for the new API; CHANGELOG
  "Unreleased" entries per capability.
- Coverage targets per workflow: >80% line, >70% branch.

## Acceptance Criteria
1. All FR1–FR5 behaviors covered by suites run through the native runtime
   (self-hosting: the repo tests its own addon).
2. Existing suites (incl. e2e) pass unchanged.
3. `ruff`/`black` clean; Python coverage thresholds hold.
4. Docs and CHANGELOG updated.

## Out of Scope
- A full matcher library (type matchers, predicate callables) — deferred;
  only the string `"any"` wildcard.
- Spying on real (non-double) objects.
- Await/async stubbing (callables returning coroutines).
- GdUnit4 runtime compatibility (separate future track).

## Phasing (summary — detail in plan.md)
- P1: Shared matcher + spy wildcard support
- P2: Rich failure diagnostics
- P3: Sequenced returns & fail stubs
- P4: Call-order assertions
- P5: Property-value assertions (amended after the Phase 6 spike)
- P6: Docs & changelog

## Design Decisions (confirmed with user)
- `to_return_seq` repeats its final value on exhaustion (avoids surprise
  failures).
- `to_fail` records a failure but the call still returns a zero value so
  the script under test keeps executing.
- Spy assertions reuse the string `"any"` wildcard already used by
  `stub()` — one mental model, zero new API surface.
- All five capabilities in one track, phased so each lands independently;
  property work last as the riskiest (spike ran first and redirected FR5
  to property-value assertions).
