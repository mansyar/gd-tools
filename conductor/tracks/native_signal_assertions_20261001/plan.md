# Implementation Plan: Native Signal Assertion Helpers

## Phase 1 — Signal Capture Foundation (`watch_signals`)

- [x] Task: Add e2e tests for signal capture (Red)
  - [x] Add native suites to `tests/fixtures/projects/native_test_project` exercising `watch_signals()` on a Node, a RefCounted, and a double
  - [x] Add e2e cases in `tests/e2e/test_native_runtime.py` asserting captures work and unwatched targets fail with guidance
  - [x] Run and confirm tests fail (command: `CI=true pytest tests/e2e/test_native_runtime.py -k signal`)
- [x] Task: Implement capture mechanism in `gd_tools_test.gd` (Green)
  - [x] `watch_signals(target: Object) -> void`: connect all declared signals, record `(signal, args)` per emission
  - [x] Fail-with-guidance state for assertions on unwatched objects
  - [x] Watcher registry with safe disconnect for freed objects
- [x] Task: Per-test lifecycle isolation
  - [x] Auto-reset recordings and disconnect watchers at test end (hooks, parameterized cases, retries)
  - [x] E2E tests proving no cross-test/cross-case leakage
  *Commit: 219eedb*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  *[checkpoint: 9dc39d3]*

## Phase 2 — Assertion Surface

- [x] Task: Write failing e2e tests for the four assertions (Red)
  - [x] `assert_signal_emitted` / `assert_signal_not_emitted` / `assert_signal_emit_count` pass + failure cases
  - [x] `assert_signal_emitted_with_args`: any-match, `"any"` wildcard, mismatch diagnostics
  *Commit: 219eedb (emitted/not_emitted), a467663 (emit_count/with_args)*
- [x] Task: Implement the four assertions (Green)
  - [x] Test-class methods integrating `_gd_tools_record_failure` with rich diagnostics (count, expected vs actual, captured-emission list)
  *Commit: a467663*
- [x] Task: Awaitable emit-wait helper (Red → Green)
  - [x] Failing tests for `await assert_signal_emitted_after(signal, timeout)` — emitted path and timeout-failure path
  - [x] Implement without changing `wait_for_signal`'s `-> bool` contract
  *Commit: a467663*
- [x] Task: Refactor pass — shared emission-matching helpers with the stub system's arg-matching logic
  *(Satisfied by design: `assert_signal_emitted_with_args` reuses `_gd_tools_stub_specificity` directly; `_gd_tools_format_emissions` centralizes captured-emission diagnostics.)*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  *[checkpoint: f68c3c4]*

## Phase 3 — Edge Cases & Robustness

- [x] Task: Edge-case tests (Red)
  - [x] Signals on doubles created by `double()`/`partial_double()` — doubles inherit declared signals; watchable as ordinary Objects
  - [x] Emissions during `before_all`/`before_each` hooks scoped correctly — separate `signal_hook_scope_suite.gd` proves `before_each` watches/emissions are captured in the test body
  - [x] Watched object freed mid-test (no dangling-reference error at teardown) — reset walks the registry with validity guards
  - [x] Multiple `watch_signals` calls on different objects in one test — per-object registry isolation
  *Outcome: all four cases already green under the Phase 1/2 design; tests pin the contracts rather than drive fixes (no Green changes required). New fixture: `scripts/signal_subject.gd` (doubles inherit `ping`).*
  *Commit: 6027cd2*
- [x] Task: Implement fixes/handling for failing edge cases (Green) — *none required; see Red outcome above*
- [x] Task: Run full suite + coverage gates (`CI=true pytest --cov=gd_tools --cov-branch`, `ruff check`, `black --check`) — *ruff/black clean; 1522 passed, 7 skipped; coverage 94.41%*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  *[checkpoint: 5a49df6]*

## Phase 4 — Documentation & Integration

- [x] Task: Documentation updates
  - [x] `docs/USER_GUIDE.md` — test section: signal assertion API with examples
  - [x] `docs/gut-migration.md` — "Where the bridge is heading": native signal assertion surface + GUT name mapping (`with_parameters` → `with_args`; `assert_has_signal`/`assert_connected`/`assert_not_connected` have no native equivalent yet)
  - [x] `docs/ARCHITECTURE.md` — GdToolsTest API table gains a Signals row (Known Limitations needed no change: the only remaining limitation, no editor integration, is unaffected)
  - [x] `skills/gd-tools/SKILL.md` — native test API highlights + corrected stale "runs using GUT" description
  - [x] `CHANGELOG.md` — Unreleased feature entry
  *Commit: 1a304eb*
- [x] Task: Full regression run (unit + integration + e2e) and CI-parity checks (`ruff`, `black`, `CI=true pytest`) — *ruff/black clean; 1522 passed, 7 skipped; coverage 90.34%*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  *[checkpoint: 69baa58]*
