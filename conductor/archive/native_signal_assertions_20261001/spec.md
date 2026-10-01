# Track: Native Signal Assertion Helpers

## Overview

`GdToolsTest` currently offers no first-class signal assertions. Users must hand-wire `wait_for_signal` + boolean flags to verify emission, losing GUT-parity and producing noisy test code. This track adds an explicit-watch capture model with four signal assertions plus an awaitable emit-wait helper, keeping all assertions as test-class methods and causing zero protocol changes.

## Functional Requirements

1. **`watch_signals(target: Object) -> void`** — starts recording every signal emission of `target` (any `Object`: Node, RefCounted, custom, doubles included). Recording is scoped to the current test; watchers disconnect automatically at test end (per-test auto-reset; no cross-test bleed). No `unwatch_signals` API.
2. **`assert_signal_emitted(target: Object, signal_name: String, message := "")`** — passes if at least one emission was captured since the test started.
3. **`assert_signal_not_emitted(target: Object, signal_name: String, message := "")`** — passes only if zero emissions were captured.
4. **`assert_signal_emit_count(target: Object, signal_name: String, count: int, message := "")`** — passes if exactly `count` emissions were captured.
5. **`assert_signal_emitted_with_args(target: Object, signal_name: String, expected_args: Array, message := "")`** — any-match semantics: passes if at least ONE captured emission's payload matches element-wise; the string `"any"` is a per-element wildcard, reusing the stub system's argument convention.
6. **`await assert_signal_emitted_after(signal: Signal, timeout_seconds := 5.0)`** — awaitable helper: awaits emission up to the timeout, then asserts it fired; fails with timeout detail if it did not. `wait_for_signal`'s existing `-> bool` contract is untouched.
7. **Unwatched targets:** any assertion targeting an object never passed to `watch_signals` fails immediately with actionable guidance ("object not watched — call watch_signals(node) first"), mirroring the stub assertions' rejection of non-doubles.
8. **Diagnostics:** failures report the captured emission count, expected-vs-actual for `with_args` mismatches, and a compact list of all captured emissions (signal + args).
9. **Protocol:** no change — signal failures are ordinary failed-test entries; protocol v3, result JSON, JUnit XML, and parallel aggregation are untouched.

## Non-Functional Requirements

- No new third-party dependency; pure GDScript in the `gd-tools-test` addon.
- Assertions integrate with the existing `_gd_tools_record_failure` surface (structured diagnostics, lifecycle failure records).
- Watchers on freed objects must not produce dangling-reference errors at test teardown.

## Acceptance Criteria

- All 6 new public methods exist on `GdToolsTest` and are exercised by native-runtime tests.
- A test asserting against an unwatched object fails with the guidance message, not a runtime script error.
- Watchers survive parameterized-case expansion and retries without cross-case leakage.
- Signals on doubles created by `double()`/`partial_double()` are watchable.
- Emissions captured in `before_all`/`before_test` hooks are visible to test-body assertions only within the same test's scope.
- Docs updated: USER_GUIDE test section, gut-migration.md capability table (signals move from "manual wiring" to "native"), ARCHITECTURE assertion surface, `skills/gd-tools/SKILL.md`.

## Out of Scope

- Structured emission data in the result protocol/JUnit XML.
- `unwatch_signals` / mid-test re-watching controls.
- Signal assertions for non-native (bridge) suites beyond what the existing surface provides.
- Callable/custom matcher arguments (a future track if needed).
- Python-side changes beyond docs.
