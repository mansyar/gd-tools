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

## Phase 2: Rich failure diagnostics [checkpoint: ca19e70]

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

## Phase 3: Runner aborted-test detection (runner correctness) [checkpoint: f6452be]

Discovered during sequenced-returns RED (2026-10-04): a GDScript runtime
error aborts a test body mid-execution, but `_invoke_test` still records
the test as `passed` (script errors are recoverable, so the runner
continues). A suite with a runtime error can report all-green. New-API
RED runs (this track's Phases 4-6) depend on trustworthy status
reporting, so this phase lands first per user approval.

- [x] Task: Spike & decide the aborted-test detection mechanism (documented in plan notes)
  - [x] Probe Godot 4.5-4.7 for script-error interception usable in a headless runner (EngineDebugger, log capture, GDScript APIs)
  - [x] Record the chosen mechanism (or stderr-correlation fallback) and rationale in plan.md notes before implementing
- [x] Task: Write failing e2e test for aborted-test reporting (3568662)
  - [ ] Fixture suite whose test aborts with a deliberate script error mid-body
  - [ ] The e2e run must report the aborted test as failed or errored (not passed)
  - [ ] Verify RED: run and confirm the current runner reports it passed (bug reproduced)
- [x] Task: Implement aborted-test detection in the runner (b117952)
  - [x] Chosen mechanism wired into `_invoke_test` / result recording
  - [x] Result payload (NDJSON + JUnit) statuses reflect the aborted test
  - [x] Verify GREEN: new e2e passes; full `CI=true pytest` passes (full-suite gate deferred to Phase 4 GREEN — the only failure is the intentional Phase 4 RED)
- [x] Task: Coverage & style verification for phase changes (workflow Quality Gates) (385ada5 + 5d07767)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 4: Sequenced returns & fail stubs [checkpoint: 64660df]

- [x] Task: Write failing GDScript tests for `to_return_seq` and `to_fail` (b3c4c81)
  - [x] `to_return_seq` returns values in registration order across successive calls
  - [x] `to_return_seq` repeats the final value on exhaustion (design decision)
  - [x] `to_fail(msg)` records a test failure at call time via the standard failure path
  - [x] A `to_fail` call still yields the type-appropriate zero value so execution continues
  - [x] Both compose with specificity tiers (exact vs wildcard vs default) and per-test isolation
- [x] Task: Implement StubBuilder extensions and mock response logic (27be15f)
  - [x] `StubBuilder.to_return_seq(values)` registers a sequence stub
  - [x] `StubBuilder.to_fail(message)` registers a fail stub; call-time failure recording on the owning suite
  - [x] Sequence/fail state consumed per call, per-double, per-test
  - [x] Verify GREEN: new suites pass; `CI=true pytest` passes (full-suite gate covered at Phase 4 coverage task)
- [x] Task: Coverage & style verification for phase changes (workflow Quality Gates) (5d07767, shared with Phase 3)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 5: Call-order assertions

- [x] Task: Write failing GDScript tests for `assert_call_order` (7b650d0)
  - [x] Subsequence semantics: unrelated interleaved calls do not break the order check
  - [x] Out-of-order calls fail with the actual recorded order in the message
  - [x] Repeated calls of the same method are handled sensibly (first matching consumption)
  - [ ] Non-double target fails with guidance (existing `_gd_tools_assert_target_is_double` behavior)
- [ ] Task: Implement `assert_call_order` with order diagnostics
  - [ ] Subsequence matching over the double's recorded call sequence
  - [ ] Failure message shows the actual method order (bounded)
  - [ ] Verify GREEN: new suites pass; `CI=true pytest` passes
- [ ] Task: Coverage & style verification for phase changes (workflow Quality Gates)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Phase 6: Property get/set spying

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

## Phase 7: Docs & changelog

- [ ] Task: Document the new API
  - [ ] README test-runtime section: new spy capabilities in the feature list
  - [ ] USER_GUIDE: doubles & spy cookbook sections (wildcards, sequences, fail stubs, order, property spying)
  - [ ] CHANGELOG "Unreleased" entries per capability
- [ ] Task: Full-repo verification
  - [ ] `CI=true pytest` (unit, integration, e2e) passes
  - [ ] Full native suite run via `gd-tools test` passes
  - [ ] `ruff check src/ tests/ && black --check src/ tests/`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Plan notes

- 2026-10-04 (Phase 3 spike decision — aborted-test detection): Godot 4.5+
  exposes the `Logger` class: a GDScript object registered via
  `OS.add_logger()` whose `_log_error(function, file, line, code,
  rationale, editor_notify, error_type, script_backtraces)` receives every
  engine error, with `error_type == ERROR_TYPE_SCRIPT` (2) for script
  runtime errors. Verified empirically on the project's Godot 4.7.2 mono
  binary: a `Trap extends Logger` captured
  `"2|Invalid call. Nonexistent function 'nonexistent_method_probe' in
  base 'RefCounted'.|res://probe3.gd:33"` while the caller continued after
  the aborted callee. Chosen mechanism: the runner arms a logger around
  each test-body invocation (`_invoke_test` window) and records the test
  as `error` with the captured message when a script error lands in that
  window. Rejected alternatives: stderr/log-file correlation from the
  Python orchestrator (cannot fix the direct-runner e2e path; duplicate
  source of truth), and EngineDebugger (not for script errors). Scope
  note: hooks (`before_each`/`after_each`/suite hooks) are OUT of scope —
  only the test-body window is armed; hook errors keep their current
  suite-level handling. GUT 9.6 uses the same Godot 4.5 capability for
  its error tracking.

- 2026-10-04 (Phase 4 RED evidence): the five `to_return_seq`/`to_fail`
  suite cases were executed against the unmodified runtime; because of the
  runner bug fixed in Phase 3 they were reported `passed`, but stderr shows
  `SCRIPT ERROR: Nonexistent function 'to_return_seq'/'to_fail'` per case
  (bodies aborted at the builder call). True RED for these cases becomes
  observable once Phase 3 lands; implementation of the builder methods
  follows immediately after (Phase 4 GREEN).
