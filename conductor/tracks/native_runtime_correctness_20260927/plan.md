# Native Runtime Correctness: Signal Wait Bounds, Suite Timeout, and Token Invariants

**Track ID:** native_runtime_correctness_20260927
**Spec:** [./spec.md](./spec.md)
**Workflow:** [../../workflow.md](../../workflow.md)
**Branch:** feature/native-runtime-correctness-20260927

## Guiding constraints for this plan

1. **No Python source changes** (R5). The only Python this track touches is
   under `tests/`. If a task appears to need an edit inside `src/gd_tools/`,
   that is a design signal — stop and revisit the task rather than making the
   edit.
2. **Re-read every line number cited in the spec before editing.** They are
   2026-09-27 orientation pointers, and `gd_tools_test_runner.gd` will have
   moved after every phase.
3. **Extend the existing harness; do not build a parallel one.**
   `tests/e2e/test_native_runtime.py` already provides
   `_prepare_project(tmp_path, godot_bin)`,
   `_run_native_manifest(project, godot_bin, manifest, result_path, *, events_path=None, log_path=None)`,
   `_manifest(project, path, names, suite_name)`, and
   `_single_failure(payload, name)`. Match the existing manifest and assertion
   style in that file.
4. **Batch Godot spawns.** The prior track's ratio was roughly five spawns for
   ten asserted behaviours. One spawn per assertion is the wrong shape; group
   related behaviours into one suite and one run.
5. **Never trust an `all()` over a collected result list without a length
   guard.** A prior track here found a test that passed vacuously because the
   suite it asserted over had never loaded. Every assertion this track writes
   over `payload["tests"]` must first assert the expected count.
6. **A Red that looks like a timeout is not an acceptable Red.** If a new test
   fails because Godot hung rather than because the assertion was violated, the
   test is not yet pinning the behaviour — fix the test before implementing.
7. **R3 and R4 are behaviour-preserving.** They are justified only by the suite
   passing identically before and after. If any existing test's expectation
   changes, stop: the refactor has altered behaviour, which is a finding to
   report, not something to encode into a new expectation.
8. **Do not decompose `_run_test_attempt`.** Out of scope (§5), and it drives
   every test the project runs. A large diff on that file for a refactor task is
   the wrong shape.
9. **Godot's `await` has no race primitive.** Probe any await-based pattern
   against the real 4.5.2 binary before relying on it — a prior track here found
   the obvious approach failed to compile.
10. **Read the flake note before trusting a single full-suite run.**
    [`../coverage_target_contract_20260926/known_flakes.md`](../coverage_target_contract_20260926/known_flakes.md)
    records ~1-in-1100 Godot-under-load failures, a different test each run,
    each passing in isolation. Re-run any single failure isolated before calling
    it a regression.

## Phase 1 — BOUNDED SIGNAL WAIT

*Covers spec R1.*

Touches `src/gd_tools/addons/gd-tools-test/gd_tools_test.gd` only. No runner
change is in scope, and constraint 1 is why.

### Task 1.1: Pin the current behaviour, then implement the bounded wait

- [~] Task: Pin and implement bounded `wait_for_signal`
  - [ ] Re-read `gd_tools_test.gd:480-483` and confirm the file still matches
        what the spec describes
  - [ ] Red: extend
        `tests/fixtures/projects/native_test_project/test/async_helpers_suite.gd`
        with the bounded-wait cases, and add a test to
        `tests/e2e/test_native_runtime.py` asserting all five of:
        - a signal that does arrive returns `true`
        - a signal that never arrives returns `false` instead of blocking
        - the wait resolves when the signal fires **without** waiting out the
          remaining budget
        - the one-argument call form still works
        - the wait records no failure of its own
  - [ ] For the third case, prefer asserting the per-test `duration_seconds` in
        the result payload over wall-clock. The runner already records it, so the
        assertion is on the runner's own measurement of that test rather than on
        machine timing. Note in the task that a wall-clock bound is the fallback
        if the duration field proves unusable.
  - [ ] Run the new test; confirm it fails for the right reason and not by
        timeout (constraint 6)
  - [ ] Green: add a `timeout_seconds` parameter with a finite `5.0` default to
        the base-class method, resolving on whichever of signal or timer
        completes first, returning `bool` and recording nothing
  - [ ] Confirm `test_native_runner_supports_async_helpers` still passes
        unchanged. It is the one-argument compatibility guard: its
        `async_helpers_suite.gd:17` awaits `process_frame`, which resolves on
        the next frame, so the new bound is never reached
  - [ ] Confirm the docstring states the difference from
        `GdToolsTestContext.wait_for_signal` — bounded, but records its own
        failure
  - [ ] Refactor: only if the Phase 1 tests are Green; extract the await-race
        pattern if it turns out to need more than one call site
  - [ ] Verify coverage: `pytest --cov=gd_tools --cov-report=html --cov-branch`
  - [ ] Commit and record
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

### Task 1.2: Record the R6 behaviour change

R6 makes exactly one bounded, deliberate exception, and R1 is where it lands.

- [ ] Task: Document the bounded-wait behaviour change
  - [ ] Add a `CHANGELOG.md` entry under the unreleased heading stating that a
        test waiting on a signal that never arrives now reports `false` at the
        `wait_for_signal` budget instead of running to the per-test timeout
  - [ ] Update `docs/USER_GUIDE.md` where `wait_for_signal` is documented, if it
        is. Verify by search first — if it is not documented, record that and do
        not add a section for it
  - [ ] Confirm `README.md` and `docs/ARCHITECTURE.md` need no change: the five
        Known Limitations are mocking, parameterized tests, parallel execution,
        suite-level skip, and editor integration, and none is this
  - [ ] Commit and record
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — SUITE TIMEOUT

*Covers spec R2.*

Touches `gd_tools_test_runner.gd:_suite_timeout` only.

### Task 2.1: Make the suite budget the maximum across all tests

- [ ] Task: Fix `_suite_timeout` to consider every test
  - [ ] Red: add a test whose suite declares differing `timeout_seconds` in an
        order placing the smallest first, and whose `before_all` needs more time
        than that smallest budget. It must fail by timing out under the current
        implementation and pass once the budget is the maximum
  - [ ] Red: add the order-independence case. The same multiset of timeouts in a
        different order must yield the same budget, and therefore the same
        result. Order-independence is the property that actually distinguishes a
        fix from a re-ordering
  - [ ] Red: assert a suite with no tests still receives `5.0`
  - [ ] Run the new tests; confirm each fails for the right reason
  - [ ] Green: compute the maximum `timeout_seconds` across all tests, floored at
        `0.001`, falling back to `5.0` for an empty suite
  - [ ] Confirm `test_native_runner_bounds_lifecycle_timeout_and_runs_cleanup`
        still passes. It is the closest existing precedent and the regression
        guard for this change
  - [ ] Refactor: not expected; if the maximum computation needs more than a
        straightforward accumulation, say so rather than restructuring
  - [ ] Verify coverage: `pytest --cov=gd_tools --cov-report=html --cov-branch`
  - [ ] Commit and record
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — TOKEN CANCELLATION

*Covers spec R3.*

Touches `gd_tools_test_runner.gd`. The mutation sites are `:277`, `:365`, and
`:559`; the readers at `:570`, `:582`, `:585` are verified, not changed.

### Task 3.1: Introduce `_invalidate_timeout()` and `_cancel_timeout()`

- [ ] Task: Name the token invariant and route every mutation through it
  - [ ] Re-read the three mutation sites and the three readers. Confirm the
        spec's description still matches the source
  - [ ] Establish a test baseline **before** editing, and record the run's
        result. This task changes no behaviour, so any difference afterwards is a
        defect introduced here
  - [ ] Implement `_invalidate_timeout()` as the sole site of
        `_active_test_token += 1`, with a comment stating the invariant it
        upholds
  - [ ] Call it from `_begin_test_timeout` to arm, and from a new
        `_cancel_timeout()` to cancel
  - [ ] Route both early-return paths in `_run_test_attempt` through
        `_cancel_timeout()`
  - [ ] Verify by inspection against the source that no direct
        `_active_test_token += 1` remains outside `_invalidate_timeout()`
  - [ ] Verify by inspection that both early returns and the arming path are
        covered. This cannot be established by a single run's results: a leaked
        timer corrupts a *later* test rather than its own
  - [ ] Confirm the three readers at `:570`, `:582`, `:585` are unchanged
  - [ ] Confirm the baseline result is unchanged. If any test's expectation
        differs, stop — constraint 7 applies
  - [ ] Refactor: not applicable; this task *is* the refactor
  - [ ] Verify coverage: `pytest --cov=gd_tools --cov-report=html --cov-branch`
  - [ ] Commit and record
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — INVOKE COLLAPSE

*Covers spec R4.*

Touches `gd_tools_test_runner.gd`. The spec establishes these as **two distinct
shapes**, not five copies of one:

- **Await an already-armed timer** — three inlined copies: `before_each`,
  the test body, and `after_each` on the non-timeout path. None of these re-arms,
  because the timer is armed once per attempt. A helper that re-arms here would
  silently give each hook a fresh budget and change the meaning of a declared
  `timeout_seconds`. This is the specific way to get R4 wrong.
- **Arm, then await** — `_run_optional_call` and `_run_cleanup`, byte-identical
  apart from the return value.

### Task 4.1: Collapse each shape to one helper

- [ ] Task: Collapse the duplicated invoke-and-await shapes
  - [ ] Re-read all five sites and confirm the spec's two-shape analysis still
        matches the source
  - [ ] Establish and record a test baseline **before** editing
  - [ ] Collapse the arm-then-await shape: have `_run_cleanup` delegate to
        `_run_optional_call`
  - [ ] Collapse the already-armed shape: route the three inlined copies through
        one helper that awaits the existing timer and **does not re-arm**. Write
        the "does not re-arm" requirement into the helper's doc comment, since it
        is the property that is invisible at the call sites
  - [ ] Confirm the baseline result is unchanged. If any test's expectation
        differs, stop — constraint 7 applies
  - [ ] Confirm the diff touches only the five named sites plus the new helper.
        Anything else in `gd_tools_test_runner.gd` is scope creep (constraint 8)
  - [ ] Refactor: not applicable; this task *is* the refactor
  - [ ] Verify coverage: `pytest --cov=gd_tools --cov-report=html --cov-branch`
  - [ ] Commit and record
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Risk register

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| No await-race pattern compiles or behaves correctly on 4.5.2 | Medium | Constraint 9: probe in a scratch fixture before writing the real test. If none works, stop and report — do not ship a `wait_for_signal` that can only wait out the full budget, which would be a worse version of the current defect |
| R1 changes an observable result for an existing suite (timeout → `false`) | Medium | R6 records it as deliberate. The one known call site, `async_helpers_suite.gd:17`, awaits `process_frame`, which resolves on the next frame and is unaffected. CHANGELOG entry is a required task, not optional |
| R3 or R4 silently alters runner behaviour | Low | Constraint 7: a changed test expectation is a finding to report, never a new expectation to encode. Baselines are recorded before each refactor phase |
| A refactor churns `gd_tools_test_runner.gd` and masks a real regression | Medium | Phase checkpoints require the full `CI=true pytest` run. Constraint 10 applies to every checkpoint |
| A Godot-under-load flake is mistaken for a regression | Medium | Constraint 10: re-run any single failure isolated before calling it a regression |
| Churn across four phases on one 799-line file accumulates drift | Medium | Each phase is independently checkpointed, so any phase can be reverted without losing the others |

## Follow-ups found during implementation

Recorded here as they are found, rather than added to the approved spec.
Candidates already known and deliberately excluded are listed in spec §5.
