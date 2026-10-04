# Plan: Doubles & Spy Framework Upgrade

**Track ID:** spy_framework_upgrade_20261004
**Spec:** [spec.md](./spec.md)
**Workflow:** conductor/workflow.md (TDD, coverage gates, git notes, checkpoints)

Primary code targets:
- `src/gd_tools/addons/gd-tools-test/gd_tools_test.gd` (public test API)
- `src/gd_tools/addons/gd-tools-test/gd_tools_mock.gd` (recorder, StubBuilder, Doubler)
- GDScript suites under `tests/` (self-hosting) + pytest e2e where behavior is observable from the CLI

Every phase ends with the Phase Verification & Checkpoint protocol from
workflow.md (tests, manual verification plan, user confirmation, checkpoint
commit + git note, plan update).

---

## Phase 1: Shared matcher + spy wildcard support [checkpoint: 60055f4]

- [x] Task: Write failing GDScript tests for `"any"` wildcards in spy assertions (95415f2)
  - [x] Suite cases: `assert_call_arguments` with `"any"` in first, middle, and last argument positions
  - [x] Suite cases: exact-match assertions unchanged (backward compatibility)
  - [x] Suite cases: wildcard never matches wrong arity (pattern size must equal call size)
  - [x] Verify RED: run the suite via the native runtime and confirm failures
- [x] Task: Extract shared matcher helper and wire spy assertions (2167065)
  - [x] Extract one matching helper used by both `_gd_tools_stub_specificity` matching and spy assertions (single source of truth)
  - [x] Update `assert_call_arguments` to match per-element with `"any"`
  - [x] Verify GREEN: new suites pass; `CI=true pytest` (unit + e2e) passes
- [x] Task: Coverage & style verification for phase changes (workflow Quality Gates) (f7acf91)
  - [x] `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` meets >80% line / >70% branch for touched Python code
  - [x] `ruff check src/ tests/ && black --check src/ tests/`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 2: Rich failure diagnostics

- [x] Task: Write failing GDScript tests for call-list and per-argument diagnostics (50e6de1)
  - [x] Failure output of `assert_call_count` / `assert_not_called` includes the recorded call list (index + args)
  - [x] Failure output of `assert_call_arguments` shows a per-argument expected-vs-actual diff
  - [x] Diagnostics are bounded: a suite with many recorded calls produces capped output
- [x] Task: Implement diagnostics in the spy assertion failure paths (d86c478)
  - [x] Format recorded calls compactly with a cap on listed entries
  - [x] Per-argument diff rendering in `assert_call_arguments` failures
  - [x] Verify GREEN: new suites pass; `CI=true pytest` passes
- [x] Task: Coverage & style verification for phase changes (workflow Quality Gates) (59ac9d4)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 3: Sequenced returns & fail stubs

- [ ] Task: Write failing GDScript tests for `to_return_seq` and `to_fail`
  - [ ] `to_return_seq` returns values in registration order across successive calls
  - [ ] `to_return_seq` repeats the final value on exhaustion (design decision)
  - [ ] `to_fail(msg)` records a test failure at call time via the standard failure path
  - [ ] A `to_fail` call still yields the type-appropriate zero value so execution continues
  - [ ] Both compose with specificity tiers (exact vs wildcard vs default) and per-test isolation
- [ ] Task: Implement StubBuilder extensions and mock response logic
  - [ ] `StubBuilder.to_return_seq(values)` registers a sequence stub
  - [ ] `StubBuilder.to_fail(message)` registers a fail stub; call-time failure recording on the owning suite
  - [ ] Sequence/fail state consumed per call, per-double, per-test
  - [ ] Verify GREEN: new suites pass; `CI=true pytest` passes
- [ ] Task: Coverage & style verification for phase changes (workflow Quality Gates)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 4: Call-order assertions

- [ ] Task: Write failing GDScript tests for `assert_call_order`
  - [ ] Subsequence semantics: unrelated interleaved calls do not break the order check
  - [ ] Out-of-order calls fail with the actual recorded order in the message
  - [ ] Repeated calls of the same method are handled sensibly (first matching consumption)
  - [ ] Non-double target fails with guidance (existing `_gd_tools_assert_target_is_double` behavior)
- [ ] Task: Implement `assert_call_order` with order diagnostics
  - [ ] Subsequence matching over the double's recorded call sequence
  - [ ] Failure message shows the actual method order (bounded)
  - [ ] Verify GREEN: new suites pass; `CI=true pytest` passes
- [ ] Task: Coverage & style verification for phase changes (workflow Quality Gates)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 5: Property get/set spying

- [ ] Task: Spike & decide the interception mechanism (documented in plan notes)
  - [ ] Evaluate generated getter/setter overrides vs `_get`/`_set` interception on the generated double script against Godot 4.5+ semantics
  - [ ] Record the decision and rationale in plan.md notes before implementing
- [ ] Task: Write failing GDScript tests for property recording and assertions
  - [ ] Generated doubles record property reads (name) and writes (name + value)
  - [ ] `assert_property_read` / `assert_property_written` pass and fail as specified (optional expected value and count)
  - [ ] Property records are per-double, per-test like method records
- [ ] Task: Implement property recording in the Doubler generator and property assertions on GdToolsTest
  - [ ] Generator emits property interception for doublable properties
  - [ ] Recorder stores property accesses alongside method calls without breaking existing `calls` consumers
  - [ ] New assertions implemented with rich failure diagnostics consistent with Phase 2
  - [ ] Verify GREEN: new suites pass; `CI=true pytest` passes
- [ ] Task: Coverage & style verification for phase changes (workflow Quality Gates)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 6: Docs & changelog

- [ ] Task: Document the new API
  - [ ] README test-runtime section: new spy capabilities in the feature list
  - [ ] USER_GUIDE: doubles & spy cookbook sections (wildcards, sequences, fail stubs, order, property spying)
  - [ ] CHANGELOG "Unreleased" entries per capability
- [ ] Task: Full-repo verification
  - [ ] `CI=true pytest` (unit, integration, e2e) passes
  - [ ] Full native suite run via `gd-tools test` passes
  - [ ] `ruff check src/ tests/ && black --check src/ tests/`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
