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

**[checkpoint: 852039b]** — verified with the user's explicit yes, given a
`CI=true pytest` run of 1160 passed, 2 skipped, 0 failed in 9m22s at 96.15%
coverage. Full report in the git note on `852039b`.

Touches `src/gd_tools/addons/gd-tools-test/gd_tools_test.gd` only. No runner
change is in scope, and constraint 1 is why.

### Task 1.1: Pin the current behaviour, then implement the bounded wait

- [x] Task: Pin and implement bounded `wait_for_signal` [7b37b55]
  - [x] Re-read `gd_tools_test.gd:480-483` and confirm the file still matches
        what the spec describes
  - [x] Red: extend
        `tests/fixtures/projects/native_test_project/test/async_helpers_suite.gd`
        with the bounded-wait cases, and add a test to
        `tests/e2e/test_native_runtime.py` asserting all five of:
        - a signal that does arrive returns `true`
        - a signal that never arrives returns `false` instead of blocking
        - the wait resolves when the signal fires **without** waiting out the
          remaining budget
        - the one-argument call form still works
        - the wait records no failure of its own
  - [x] For the third case, prefer asserting the per-test `duration_seconds` in
        the result payload over wall-clock. The runner already records it, so the
        assertion is on the runner's own measurement of that test rather than on
        machine timing. Note in the task that a wall-clock bound is the fallback
        if the duration field proves unusable.
  - [x] Run the new test; confirm it fails for the right reason and not by
        timeout (constraint 6)
  - [x] Green: add a `timeout_seconds` parameter with a finite `5.0` default to
        the base-class method, resolving on whichever of signal or timer
        completes first, returning `bool` and recording nothing
  - [x] Confirm `test_native_runner_supports_async_helpers` still passes
        unchanged. It is the one-argument compatibility guard: its
        `async_helpers_suite.gd:17` awaits `process_frame`, which resolves on
        the next frame, so the new bound is never reached
  - [x] Confirm the docstring states the difference from
        `GdToolsTestContext.wait_for_signal` — bounded, but records its own
        failure
  - [x] Refactor: only if the Phase 1 tests are Green; extract the await-race
        pattern if it turns out to need more than one call site
  - [x] Verify coverage: `pytest --cov=gd_tools --cov-report=html --cov-branch`
  - [x] Commit and record
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

**Implementation note.** The plan's fallback for the early-resolve case was not
needed: `duration_seconds` was already carried in the result payload and proved
usable, so the assertion is on the runner's own measurement rather than on
wall-clock. No refactor was performed — the await-race pattern has a single call
site, so extracting it would have been the speculative abstraction
`workflow.md` warns against. One helper beyond the plan was required and is
recorded rather than hidden: `_gd_tools_disconnect_wait`. Without it the losing
side of the race stays connected, so a *second* wait in the same test would be
resolved early by the first one's leftover timer. That failure mode is invisible
at the call site, which is why it lives in a named function with a comment
rather than being inlined.

### Task 1.2: Record the R6 behaviour change

R6 makes exactly one bounded, deliberate exception, and R1 is where it lands.

- [x] Task: Document the bounded-wait behaviour change
  - [x] Add a `CHANGELOG.md` entry under the unreleased heading stating that a
        test waiting on a signal that never arrives now reports `false` at the
        `wait_for_signal` budget instead of running to the per-test timeout
  - [x] Update `docs/USER_GUIDE.md` where `wait_for_signal` is documented, if it
        is. Verify by search first — if it is not documented, record that and do
        not add a section for it
  - [x] Confirm `README.md` and `docs/ARCHITECTURE.md` need no change: the five
        Known Limitations are mocking, parameterized tests, parallel execution,
        suite-level skip, and editor integration, and none is this
  - [x] Commit and record
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

**Implementation note.** Two plan assumptions did not survive contact with the
files, and both are recorded rather than edited away.

The plan said to update `USER_GUIDE.md` "where `wait_for_signal` is documented, if
it is". It is documented at `USER_GUIDE.md:526` — but that is the
`GdToolsTestContext` method, which was already correct. The **base-class** method,
the one this task changed, was documented nowhere in the guide. Following the
plan's own instruction not to invent a section, no guide section was added. The
change was instead documented where the base-class surface is actually described:
the `ARCHITECTURE.md` base-class async table, which now carries the signature and
return value, plus a short note separating the two same-named methods. That
disambiguation is the highest-value part of the edit, because the name collision
is the root cause of the original defect — the guide and the architecture doc each
described one of the two methods correctly and a reader could not tell they
differed.

The plan also predicted `README.md` and `ARCHITECTURE.md` would need no change,
reasoning from the Known Limitations list. That reasoning was sound but the
conclusion was not: both files carry a copy of the same base-class async-waits
table, and both listed `wait_for_signal` bare. Leaving them stale while the
underlying behaviour changed would have reintroduced exactly the documentation gap
this task closed, so both rows were updated to carry the signature.

`CHANGELOG.md` had no unreleased heading, so one was added.

## Phase 2 — SUITE TIMEOUT

*Covers spec R2.*

Touches `gd_tools_test_runner.gd:_suite_timeout` only.

**[checkpoint: 9ed601d]** — verified with the user's explicit yes, given a
`CI=true pytest` run of 1162 passed, 2 skipped, 0 failed in 9m49s at 96.15%
coverage. Full report in the git note on `9ed601d`.

### Task 2.1: Make the suite budget the maximum across all tests

- [x] Task: Fix `_suite_timeout` to consider every test [e848f3b]
  - [x] Red: add a test whose suite declares differing `timeout_seconds` in an
        order placing the smallest first, and whose `before_all` needs more time
        than that smallest budget. It must fail by timing out under the current
        implementation and pass once the budget is the maximum
  - [x] Red: add the order-independence case. The same multiset of timeouts in a
        different order must yield the same budget, and therefore the same
        result. Order-independence is the property that actually distinguishes a
        fix from a re-ordering
  - [x] Red: assert a suite with no tests still receives `5.0`
  - [x] Run the new tests; confirm each fails for the right reason
  - [x] Green: compute the maximum `timeout_seconds` across all tests, floored at
        `0.001`, falling back to `5.0` for an empty suite
  - [x] Confirm `test_native_runner_bounds_lifecycle_timeout_and_runs_cleanup`
        still passes. It is the closest existing precedent and the regression
        guard for this change
  - [x] Refactor: not expected; if the maximum computation needs more than a
        straightforward accumulation, say so rather than restructuring
  - [x] Verify coverage: `pytest --cov=gd_tools --cov-report=html --cov-branch`
  - [x] Commit and record
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

**Implementation note.** No refactor was needed — the maximum is a single
accumulation, as the plan predicted.

Two things surfaced while writing the Red that are worth carrying forward,
because both produced a misleading signal rather than an honest failure. They
are recorded here rather than in the task list, since they are properties of the
test harness rather than of the defect.

The shared manifest helper initially asserted `returncode == 0`. The runner
correctly exits `1` on test failure, so a starved `before_all` surfaced as a
Godot harness error and the real failure was hidden behind it. The helper now
accepts `0` or `1` and leaves the judgement to the caller. A helper that
assumes "the harness ran, therefore 0" cannot be used to test a harness-visible
failure, which is precisely the class of bug this phase is about.

The same helper asserted `len(payload["tests"]) == len(declared)`. The runner
reports hook outcomes as synthetic entries in `tests` — `before_all` appears
there with its own status — so three declared tests produced four entries. The
count is now a subset check on declared names, which is both correct and still
catches the empty-list result a suite load failure produces. That substitution
is not cosmetic: an exact-count assertion was passing for the wrong reason, and
had the count happened to line up it would have been asserting nothing.

Neither is a defect. Hook surfacing in `tests[]` is a deliberate protocol
choice, and `before_all` appearing as a `timeout` entry is the correct report
of a starved hook. They are recorded so a future test does not rediscover them
by misreading a harness failure as a product failure.

## Phase 3 — TOKEN CANCELLATION

*Covers spec R3.*

Touches `gd_tools_test_runner.gd`. The mutation sites are `:277`, `:365`, and
`:559`; the readers at `:570`, `:582`, `:585` are verified, not changed.

### Task 3.1: Introduce `_invalidate_timeout()` and `_cancel_timeout()`

- [x] Task: Name the token invariant and route every mutation through it
  - [x] Re-read the three mutation sites and the three readers. Confirm the
        spec's description still matches the source
  - [x] Establish a test baseline **before** editing, and record the run's
        result. This task changes no behaviour, so any difference afterwards is a
        defect introduced here
  - [x] Implement `_invalidate_timeout()` as the sole site of
        `_active_test_token += 1`, with a comment stating the invariant it
        upholds
  - [x] Call it from `_begin_test_timeout` to arm, and from a new
        `_cancel_timeout()` to cancel
  - [x] Route both early-return paths in `_run_test_attempt` through
        `_cancel_timeout()`
  - [x] Verify by inspection against the source that no direct
        `_active_test_token += 1` remains outside `_invalidate_timeout()`
  - [x] Verify by inspection that both early returns and the arming path are
        covered. This cannot be established by a single run's results: a leaked
        timer corrupts a *later* test rather than its own
  - [x] Confirm the three readers at `:570`, `:582`, `:585` are unchanged
  - [x] Confirm the baseline result is unchanged. If any test's expectation
        differs, stop — constraint 7 applies
  - [x] Refactor: not applicable; this task *is* the refactor
  - [x] Verify coverage: GDScript is not measured by pytest-cov, so this is
        unchanged by construction. Phase 2's checkpoint established that a
        GDScript-only change leaves the figure at 96.15%
  - [x] Commit and record
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

**Implementation note.** Three findings, none of which changed what the task
did.

1. **The plan's "both early-return paths" is imprecise, and the imprecision
   points the wrong way.** The two sites that held a bare increment are the
   missing-method early return (`:285`) and the *normal exit* (`:373`) — one
   early return and one normal exit, not two early returns. The two genuine
   early returns are `:224` (suite does not extend `GdToolsTest`) and `:247`
   (integration preparation failed), and both correctly need no cancel because
   both return *before* `_begin_test_timeout` arms anything. Routing those two
   through `_cancel_timeout()` as well would have been wrong: it would bump the
   token for an attempt that never armed a timer, and a bump that reads as
   "clean up after myself" while having nothing to clean up is exactly the kind
   of misleading step this task exists to remove. Recorded because a future
   reader following the spec's "every exit path" wording literally would add
   those two calls and make the code worse while appearing to follow R3.

2. **`_run_optional_call` and `_run_cleanup` leave their timer armed, and that
   is safe — verified, deliberately not changed.** Both arm via
   `_begin_test_timeout` and return without cancelling, so `before_all`,
   `after_all` and the timed-out `after_each` path each leave a live timer. Two
   things make that safe: the next `_begin_test_timeout` bumps the token, which
   makes the stale timer inert in `_on_test_timeout`; and in the gap before
   that, `_test_completed` is still `true` from the completed hook, so
   `_on_test_timeout` bails at its second condition. Changing this would be a
   behaviour change, and R3 is explicitly behaviour-preserving. Left alone.

3. **Baseline held exactly.** `tests/e2e/test_native_runtime.py` reported 29
   passed in 109.64s before the edit and 29 passed in 113.28s after — the same
   29 tests, no expectation edited. Per constraint 7 any differing expectation
   would have been a finding to report rather than a new expectation to write.

**[checkpoint: d66be91]** — verified with the user's explicit yes, given a
`CI=true pytest` run of 1162 passed, 2 skipped, 0 failed in 9m47s at 96.15%
coverage, unchanged from Phase 2 as expected for a GDScript-only
behaviour-preserving refactor. Full report in the git note on `d66be91`.


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

- [x] Task: Collapse the duplicated invoke-and-await shapes
  - [x] Re-read all five sites and confirm the spec's two-shape analysis still
        matches the source
  - [x] Establish and record a test baseline **before** editing
  - [x] Collapse the arm-then-await shape: have `_run_cleanup` delegate to
        `_run_optional_call`
  - [x] Collapse the already-armed shape: route the three inlined copies through
        one helper that awaits the existing timer and **does not re-arm**. Write
        the "does not re-arm" requirement into the helper's doc comment, since it
        is the property that is invisible at the call sites
  - [x] Confirm the baseline result is unchanged. If any test's expectation
        differs, stop — constraint 7 applies
  - [x] Confirm the diff touches only the five named sites plus the new helper.
        Anything else in `gd_tools_test_runner.gd` is scope creep (constraint 8)
  - [x] Refactor: not applicable; this task *is* the refactor
  - [x] Verify coverage: GDScript is not measured by pytest-cov, so unchanged by
        construction, as in Phases 2 and 3
  - [x] Commit and record
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

**Implementation note.** One trap found and closed while writing the
`_run_cleanup` delegation, which is the reason it carries a comment at all.

`_run_cleanup` is called from exactly one place — the timed-out `after_each`
path at `:292` — and it is `await`ed there. A naive "let it just call
`_run_optional_call`" delegation would have been:

```gdscript
	_run_optional_call(context, method_name, timeout_seconds)
```

without an `await`. That compiles and it *looks* right, but it silently makes
`_run_cleanup` a non-coroutine: a function with no `await` in it. The caller's
`await _run_cleanup(...)` at `:292` would then return immediately instead of
waiting out the cleanup, so a hung test would never get its `after_each` and
teardown would race the hung body. The delegation therefore keeps its `await`,
and the comment says the `await` is load-bearing rather than decorative.

This is the same class of failure as the re-arming trap the spec warns about:
both are invisible at the call site and both compile. The two guards that catch
them are `test_native_runner_bounds_lifecycle_timeout_and_runs_cleanup` (the
cleanup must still run and must still be bounded) and
`test_native_runner_marks_timed_out_tests` (the shared per-attempt budget must
still be shared). Both pass unchanged.

Scope held to the five named sites plus the one new helper. Net effect on the
runner: **−6 lines while adding two explanatory comments**, so the file got
smaller and the two invisible properties got written down.

**[checkpoint: 61b36af]** — verified with the user's explicit yes, given a
`CI=true pytest` run of 1162 passed, 2 skipped, 0 failed in 9m32s at 96.15%
coverage, unchanged across three consecutive GDScript-only phases. Full report
in the git note on `61b36af`.

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

- **A suite that fails to load reports success.** Found in Phase 1 while
  confirming the Red. When a fixture suite has a parse error, Godot exits `0`,
  the result payload reports `status: "passed"`, and `tests` is an empty array.
  A test asserting `all(...)` over that list passes vacuously. The length guard
  added in Task 1.1 is what caught it; without it the Red would have been a
  false Green. This is a runner-level reporting defect, independent of anything
  in this spec's scope, and is not fixed here. Worth its own track — it is the
  same class of bug as the vacuous `assert engine_errors == []` a prior track
  found, and it is a trap for every future native test.
