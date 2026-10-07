# Implementation Plan: Flaky Test Reporting

**Track:** `flaky_test_reporting_20261007`
**Spec:** [spec.md](./spec.md)
**Workflow:** [conductor/workflow.md](../../../conductor/workflow.md) — TDD, phase
checkpoints, quality gates.

> Every code task follows the standard workflow: mark `[~]` → write failing
> tests (Red) → implement (Green) → refactor → verify coverage → commit with
> git note → mark `[x]` with the commit SHA.

---

## Phase 1: Protocol v4 — First-Attempt Failure Message

Addendum (pre-existing test-infra repairs, made before checkpoint sign-off at
user request, `4129c5c`): shard e2e `_prepare_project` now writes its own
`gd-tools.toml` (the test previously patched a fixture file that was never
committed to git); the exclude list retains the addon defaults so coverage does
not self-instrument the addons (which crashed Godot 4.7.2's VM); e2e conftest
gained a session-autouse fixture that sweeps gitignored `.gd-tools/` run
residue out of fixture sources; orchestrator diagnostics no longer hardcode
"protocol v3".

- [x] Task: Write failing Python tests for protocol v4 (Red) `[0040f18]`
  - [ ] `NATIVE_PROTOCOL_VERSION` is 4 and `NativeRunResult.protocol_version`
        accepts 4.
  - [ ] `NativeTestResult` parses a result with `first_failure_message` set.
  - [ ] `NativeTestResult` parses a v3-style result **without**
        `first_failure_message` (defaults to empty) — compatibility test.
- [x] Task: Write failing GDScript-runtime tests for first-attempt capture (Red) `[5b70123]`
  - [ ] A test failing on attempt 1 and passing on attempt 2 (retries=1)
        reports `attempts: 2` and carries the attempt-1 failure message in
        `first_failure_message`.
  - [ ] A test passing on attempt 1 carries no `first_failure_message`.
  - [ ] A timeout-then-pass test carries the timeout message.
- [x] Task: Implement protocol v4 in Python (Green) `[0040f18]`
  - [ ] Bump `NATIVE_PROTOCOL_VERSION` to 4; widen `protocol_version`
        literal.
  - [ ] Add optional `first_failure_message: str = ""` to `NativeTestResult`.
- [x] Task: Implement capture + emission in `gd_tools_test_runner.gd` (Green) `[5b70123]`
  - [ ] Track the first retryable attempt's message across the retry loop.
  - [ ] Emit `first_failure_message` in the per-test result and the
        `test_finished` NDJSON event (omit/empty when absent).
  - [ ] Bump the runner's reported protocol version to 4.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Flaky Detection and Aggregation

- [ ] Task: Write failing tests for flaky classification (Red)
  - [ ] `passed` + `attempts > 1` ⇒ flaky (assertion-failure recovery).
  - [ ] `passed` + `attempts > 1` ⇒ flaky (timeout recovery).
  - [ ] `passed` + `attempts == 1` ⇒ not flaky.
  - [ ] `failed`/`timeout`/`skipped` results are never flaky regardless of
        attempts.
- [ ] Task: Implement flaky derivation over `NativeRunResult` (Green)
  - [ ] Pure helper returning the ordered flaky test list (suite, name,
        attempts, first_failure_message) from run results.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Terminal Flaky Panel

- [ ] Task: Write failing tests for panel rendering (Red)
  - [ ] ≥1 flaky test ⇒ panel renders suite, test name, "passed on attempt N",
        and the message collapsed to its first line, truncated to ~120 chars
        with an ellipsis.
  - [ ] Multi-line/long messages collapse and truncate correctly.
  - [ ] Zero flaky tests ⇒ output identical to today (no panel).
  - [ ] QUIET verbosity suppresses the panel.
- [ ] Task: Implement the flaky panel in the native run summary (Green)
  - [ ] Render via the shared output console, following existing summary
        panel conventions.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Parallel, Watch, and Documentation

- [ ] Task: Write failing tests for parallel/watch integration (Red)
  - [ ] Flaky tests from multiple parallel workers all appear in the panel.
  - [ ] Watch re-run summary renders the flaky panel like a normal run.
- [ ] Task: Implement any parallel/watch gaps surfaced by the tests (Green)
- [ ] Task: Update documentation
  - [ ] README: retries/flaky panel mention in the native test section.
  - [ ] USER_GUIDE: flaky panel behavior, protocol v4 note.
  - [ ] CHANGELOG "Unreleased": flaky test reporting entry.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5: Full Quality Gate

- [ ] Task: Run the complete quality gate
  - [ ] `CI=true pytest` (all markers) with >80% line / >70% branch on new
        code.
  - [ ] `ruff check src/ tests/` and `black --check src/ tests/`.
  - [ ] Manual verification of the flaky panel against a sample Godot project
        (retries > 0).
- [ ] Task: Final review readiness (Refer to workflow.md)
