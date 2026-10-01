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

- [ ] Task: Write failing e2e tests for the four assertions (Red)
  - [ ] `assert_signal_emitted` / `assert_signal_not_emitted` / `assert_signal_emit_count` pass + failure cases
  - [ ] `assert_signal_emitted_with_args`: any-match, `"any"` wildcard, mismatch diagnostics
- [ ] Task: Implement the four assertions (Green)
  - [ ] Test-class methods integrating `_gd_tools_record_failure` with rich diagnostics (count, expected vs actual, captured-emission list)
- [ ] Task: Awaitable emit-wait helper (Red → Green)
  - [ ] Failing tests for `await assert_signal_emitted_after(signal, timeout)` — emitted path and timeout-failure path
  - [ ] Implement without changing `wait_for_signal`'s `-> bool` contract
- [ ] Task: Refactor pass — shared emission-matching helpers with the stub system's arg-matching logic
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Edge Cases & Robustness

- [ ] Task: Edge-case tests (Red)
  - [ ] Signals on doubles created by `double()`/`partial_double()`
  - [ ] Emissions during `before_all`/`before_test` hooks scoped correctly
  - [ ] Watched object freed mid-test (no dangling-reference error at teardown)
  - [ ] Multiple `watch_signals` calls on different objects in one test
- [ ] Task: Implement fixes/handling for failing edge cases (Green)
- [ ] Task: Run full suite + coverage gates (`CI=true pytest --cov=gd_tools --cov-branch`, `ruff check`, `black --check`)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Documentation & Integration

- [ ] Task: Documentation updates
  - [ ] `docs/USER_GUIDE.md` — test section: signal assertion API with examples
  - [ ] `docs/gut-migration.md` — capability table: signal assertions move from "manual wiring" to "native"
  - [ ] `docs/ARCHITECTURE.md` — assertion surface + Known Limitations refresh
  - [ ] `skills/gd-tools/SKILL.md` — new API entries
  - [ ] `CHANGELOG.md` — Unreleased feature entry
- [ ] Task: Full regression run (unit + integration + e2e) and CI-parity checks (`ruff`, `black`, `CI=true pytest`)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
