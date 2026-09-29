# Spec: Native Mocking & Stubbing

**Type:** Feature · **Area:** Native test runtime (`GdToolsTest`) + GUT bridge · **Track ID:** `native_mocking_stubbing_20260929`

## Overview

Add a test-double facility to the native runtime so GDScript suites can isolate collaborators: `double()`, `partial_double()`, `stub()`, and the call-assertion family, using GUT-compatible names and semantics. This closes the most painful documented gap (ARCHITECTURE.md "No mocking or stubbing") and lets the bridge stop rejecting mocking constructs, un-blocking migration of GUT suites that depend on them.

## Functional Requirements

1. **API surface (GUT-compatible, on `GdToolsTest`):**
   - `double(script)` / `partial_double(script)` — accept GDScript scripts (by path or preloaded `Script`); scripts only (no built-in classes, no inner classes in MVP).
   - `stub(double, "method")` returning a chainable stub spec: `.to_return(value)`, `.to_call_super()`.
   - Call matching: exact argument values, an "any argument" wildcard, and a no-args/default fallback stub.
   - Call assertions: `assert_called`, `assert_not_called`, `assert_call_count`, `assert_call_arguments`.
2. **Semantics:** unstubbed double methods return `null` (GUT semantics); `partial_double()` runs the real implementation unless stubbed; `to_call_super()` invokes the parent implementation.
3. **Validation (fail fast):** stubbing a method the target doesn't have, or doubling a non-script value, fails the test immediately with a diagnostic naming the method and target.
4. **Availability:** works in unit suites and in suites declaring `INTEGRATION` (same process model).
5. **Bridge:** preflight stops rejecting `double()`, `partial_double()`, `stub()`, `assert_called*`; the bridge shim forwards these to the native implementation. `parameterize()`/`use_parameters()` remain rejected (separate track).
6. **Coverage honesty:** dynamically generated double scripts must not appear in coverage plans or reports; stubbed paths must not distort per-file metrics of the real script. Tests must prove coverage output is unaffected; the interaction is documented.

## Non-Functional Requirements

- No new third-party runtime dependency (GDScript-side implementation only, consistent with tech-stack §9).
- Per-test isolation: doubles/stubs do not leak across tests (fresh suite instances per test already provide the model).
- Assertion failure messages actionable: expected vs. actual calls with arguments.
- >80% line / >70% branch coverage for new Python source; GDScript addon changes covered by native test suites.

## Acceptance Criteria

1. A `GdToolsTest` suite can double a script, stub return values (with and without argument matching), and verify calls with the four assertions.
2. `partial_double()` + `to_call_super()` works (real behavior preserved except overridden methods).
3. Bridge suites using `double()`/`stub()`/`assert_called*` run through the bridge with identical semantics; preflight no longer lists them as refused.
4. A coverage run over a project using doubles contains no generated double scripts and unchanged metrics for the real scripts.
5. Invalid usage fails the test with a clear diagnostic at setup time.
6. All four docs updated: USER_GUIDE (API reference), gut-migration.md (refused table), ARCHITECTURE.md (limitations), README (capability table).

## Out of Scope

- `parameterize()`/`use_parameters()` (separate track).
- Doubling built-in engine classes and inner classes.
- `to_call(callable)` custom responses, spy chains, argument matchers beyond exact/wildcard, sequence verification.
- Parallel execution; editor integration.
