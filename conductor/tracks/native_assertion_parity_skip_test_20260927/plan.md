# Implementation Plan — Native Assertion Parity and `skip_test()`

**Track ID:** `native_assertion_parity_skip_test_20260927`
**Spec:** [`./spec.md`](./spec.md)
**Workflow:** [`../../workflow.md`](../../workflow.md)
**Branch:** `feature/native-assertion-parity-skip-test-20260927`

## Guiding constraints for this plan

1. **No Python source changes.** Per spec R7, `protocol.py` and `command.py` are untouched. The Python surface of this track is tests only. If a task below appears to need a Python source edit, that is a design signal — stop and revisit, do not edit.
2. **Batch Godot spawns.** Every assertion test needs a real Godot subprocess (`test_native_runtime.py:405-420`), costing seconds each and adding flake surface per `known_flakes.md`. Do **not** write one e2e test per assertion. Instead, each fixture suite carries many test methods and each e2e test spawns Godot **once** and asserts across all `payload["tests"]` entries. Target: roughly 5 Godot spawns for the whole track, not 25.
3. **Follow the existing harness exactly.** `tests/e2e/test_native_runtime.py:378-430` is the template: `_prepare_project(tmp_path, godot_bin)`, write a `protocol_version: 2` manifest, set `GD_TOOLS_NATIVE_MANIFEST` and `GD_TOOLS_NATIVE_RESULT`, run `godot --headless --path <project> --script res://addons/gd-tools-test/gd_tools_test_runner.gd` with `timeout=30`, then assert on the result JSON. Exit codes: `0` pass, `1` test failure, `2` error.
4. **Two fixtures already exist and are the starting point:** `tests/fixtures/projects/native_test_project/test/assertion_suite.gd` (currently 5 lines, one `assert_eq` failure) and its consumer test `test_native_assertions_report_values_and_source`. Extend both; do not build a parallel harness.

---

## Phase 1 — `skip_test()` / `pending_test()` end to end

Covers spec R1, R2, R3, and the R7 no-protocol-change verification.

**`[checkpoint: d5b4d1b]`** — phase complete. Manual verification confirmed by the
user ("Yes, this meets expectations"). Full automated and manual evidence is recorded
in the git note on `d5b4d1b`. Phase commits: `abbb5de` (the skip surface), `34a3550`
(the R9 summary-message fix found during verification), `d5b4d1b` (the checkpoint).

**Implementation note — committed as `abbb5de`.** Tasks 1.1 and 1.2 were executed
differently from how they are written below, and the difference is deliberate. The
plan listed five separately-spawned e2e tests and a second fixture,
`skip_interactions_suite.gd`, holding `test_ordinary_passing_test`. What shipped is
three batched tests over a single `skip_suite.gd`, and no second fixture.

Guiding constraint 2 of this plan is the reason: each Godot spawn costs seconds and
adds flake surface per `known_flakes.md`, and the five behaviours are all provable
from one manifest's `payload["tests"]`. The retry and no-escalation behaviours the
second fixture was meant to pin are provable from `skip_suite.gd` plus manifest
config — `retries: 2` on a skipping test proves retries are unconsumed, and the
all-skipped manifest proves the run does not escalate. The task text below is left
as written so the divergence stays visible rather than being edited into agreement.

One test-name change worth noting: the plan's
`test_native_skip_reports_skipped_status_with_reason` shipped as
`test_native_skipped_tests_report_status_and_reason`, because it asserts the reason
across three methods rather than one.

Verification for this phase: full suite `1152 passed, 2 skipped, 0 failed` in 7m35s
across two separate runs, with no flakes; coverage `96.15%` total against a `80%`
gate (`Required test coverage of 80.0% reached`), branch coverage included.
`protocol.py` and `command.py` are untouched, per spec R7.

### Task 1.1: Write the failing tests (Red)

- [x] Task: Add fixture suites for the skip surface [abbb5de]
  - [ ] Create `tests/fixtures/projects/native_test_project/test/skip_suite.gd` with a `NativeSkipSuite` (`class_name`) containing these methods:
    - `test_skips_with_reason` — calls `skip_test("no network in sandbox")` and nothing else
    - [ ] `test_skips_without_reason` — calls `skip_test()` with no argument, covering spec R1's default-reason requirement
    - [ ] `test_assertion_after_skip_is_discarded` — calls `skip_test("guard")` then `assert_eq(1, 2, "must not be recorded")`
    - [ ] `test_fail_after_skip_is_discarded` — calls `skip_test("guard")` then `fail("must not be recorded")`
    - [ ] `test_failure_before_skip_still_fails` — calls `assert_eq(1, 2, "real failure")` **then** `skip_test("too late")`, covering spec R3's failure-outranks-skip rule
    - [ ] `test_pending_test_alias` — calls `pending_test("alias path")`
  - [ ] Create `tests/fixtures/projects/native_test_project/test/skip_interactions_suite.gd` with a `NativeSkipInteractionsSuite` covering spec R3's three "already correct, verify not change" behaviors:
    - [ ] `test_ordinary_passing_test` — a normal passing test, so the suite is not all-skips
  - [ ] Keep each fixture method small and single-purpose. No method combines two skip behaviors.

### Task 1.2: Add the e2e tests (Red)

- [x] Task: Add skip tests to `tests/e2e/test_native_runtime.py` [abbb5de]
  - [ ] `test_native_skip_reports_skipped_status_with_reason` — one Godot spawn over `skip_suite.gd`. Assert `returncode == 0`, the entry for `test_skips_with_reason` has `status == "skipped"` and `message == "no network in sandbox"`, and the run carries no `failed`/`error` entry.
  - [ ] `test_native_skip_without_reason_supplies_default` — asserts `message` is non-empty for `test_skips_without_reason`.
  - [ ] `test_native_assertions_after_skip_are_discarded` — one spawn; both post-skip methods report `skipped` with **empty** `diagnostics.failures`, proving the guard.
  - [ ] `test_native_failure_before_skip_still_reports_failed` — asserts `test_failure_before_skip_still_fails` reports `status == "failed"`, proving a skip cannot mask a failure.
  - [ ] `test_native_pending_test_is_alias_for_skip` — asserts `status == "skipped"` and the reason is preserved.
  - [ ] `test_native_all_skipped_suite_exits_zero` — a suite whose every method skips yields `returncode == 0` and no run-level escalation.
  - [ ] Match file style: one-line docstring, arrange/act/assert, no new helper abstractions.
  - [ ] **Run the new tests and confirm they fail** for the right reason — `skip_test` is not yet a method, so Godot reports a parse/compile error. A failure that looks like a flaky timeout is not an acceptable Red.

### Task 1.3: Implement the skip surface (Green)

- [x] Task: Add skip state and emission to `src/gd_tools/addons/gd-tools-test/gd_tools_test.gd` [abbb5de]
  - [ ] Add a per-instance skip flag and a skip reason string. State must live on the **test** instance, not the suite instance — `_new_test_context` (`gd_tools_test_runner.gd:483-495`) builds a fresh instance per attempt, which is what keeps a skip from leaking across retries.
  - [ ] Add public `skip_test(reason := "")`. When `reason` is empty, substitute a default so `message` is never blank (spec R1) — JUnit `<skipped message=...>` and the terminal table both render it.
  - [ ] Add public `pending_test(reason := "")` as a direct alias delegating to `skip_test` (spec R1, decision 2 in spec §6). It must not be a second code path.
  - [ ] Add an accessor the runner can read, and a reset so the flag cannot survive into a later test on a reused instance.
  - [ ] **No assertion bodies change.** The guard goes in `_gd_tools_record_failure` (spec R2): if the skip flag is set, return without recording. Confirm by reading that function first; a per-assertion guard is a rule N authors must forget.

### Task 1.4: Implement the three-way status in the runner (Green)

- [x] Task: Report `skipped` from `gd_tools_test_runner.gd` [abbb5de]
  - [ ] Read `_run_test_attempt` before editing. The single decision point is the status computation at `:317-318` — `var status := "failed" if not failures.is_empty() else "passed"`.
  - [ ] Make it three-way: no failures **and** a recorded skip → `status = "skipped"` with the skip reason as `message`. Failures still take precedence, so the existing `failed` branch is unchanged in behavior.
  - [ ] Put the reason in the returned `message` (`:363-370`). Do **not** route it through `diagnostics` — spec R6 keeps that structure unchanged.
  - [ ] **Verify, do not modify,** the three behaviors spec R3 lists as already correct: not retryable (`:182`), no windowed screenshot (`:338`), no run escalation (`:638`). If any turns out to need an edit, that contradicts the spec — stop and report rather than editing.
  - [ ] Confirm `_failure_message` (`:655-664`) is not the reason's source; a skipped test has no failures and that path returns `""`.
  - [ ] Run the Phase 1 e2e tests and confirm Green.

### Task 1.5: Refactor (optional)

- [x] Task: Clean up only if Phase 1 tests are Green [abbb5de] - no duplication introduced; nothing to refactor
  - [ ] Remove any duplication the implementation introduced.
  - [ ] Do not reorganize the seven existing assertions or touch unrelated runner code, per `workflow.md`'s surgical-changes principle.

### Task 1.6: Verify coverage

- [x] Task: Check the self-coverage gate [abbb5de]
  - [ ] `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
  - [ ] Target: >80% line, >70% branch on new source. The ≥80%/>70% gate must be unchanged or better.

### Task 1.7: Commit and record

- [x] Task: Commit Phase 1 [abbb5de]
  - [ ] Stage the `.gd`, fixture, and test changes.
  - [ ] Commit: `feat(native-test): Add skip_test and pending_test to the native runtime`
  - [ ] Attach a `git notes` summary per `workflow.md` step 9.
  - [ ] Mark tasks `[~]` → `[x]` in this plan with the first 7 chars of the commit SHA, and commit the plan update as `conductor(plan): Mark phase 'SKIP EMISSION' as complete`.

### Task 1.8: Phase Verification & Checkpoint

- [x] Task: Phase Verification & Checkpoint (Refer to [`../../workflow.md`](../../workflow.md))
  - [ ] Run `git diff --name-only <previous_checkpoint_sha> HEAD`; for every changed `.py`/`.gd`, confirm a corresponding test exists.
  - [ ] Announce and run the full `CI=true pytest` suite. If it fails, propose at most two fixes, then stop and ask.
  - [ ] Present manual verification steps for the user and **await explicit confirmation** before checkpointing:
    - `pip install -e .`
    - Create a suite in a Godot project calling `skip_test("reason")` mid-test, then `gd-tools test --runtime native`
    - Confirm the terminal table shows the test as skipped with its reason, and the run exits 0
  - [ ] Create the checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 1 - SKIP EMISSION`
  - [ ] Attach the verification report as a `git notes` entry, record `[checkpoint: <sha>]` under the Phase 1 heading, and commit the plan update.

---

## Phase 2 — The nine assertions with type safety

Covers spec R4, R5, R6.

**Implementation note — probe findings that shaped the design.** Spec §7
required verifying the Godot primitives rather than assuming them. A probe run
against Godot 4.7.1 established four constraints, none of which were
guessable and two of which contradict the obvious implementation:

1. **`is_same()` exists and behaves as R5 needs.** Same reference → `true`;
   two equal-but-distinct Arrays → `false`. Verified locally on 4.7.1; the CI
   matrix covers 4.5.2, which is the floor the project claims.
2. **`expr is T` is a compile-time error when the static type of `expr` is
   provably disjoint from `T`.** The first probe, written with `:=`-typed
   locals, failed to compile with eight such errors. This is why every
   assertion parameter is an untyped Variant — a typed parameter would make
   the type checks themselves uncompilable, and the R4 guarantee would
   invert into a parse error.
3. **`is Object` is `false` for Array, Dictionary, String and every Packed
   array.** They are Variant types, not Objects, so the obvious
   `value is Object and value.has_method("has")` membership check silently
   rejects every builtin container. Membership therefore tests
   `typeof(value)` against an explicit `TYPE_` list.
4. **`String` has no `has()`** — it spells it `contains()`, and calling `.has()`
   on a String is itself a parse error. `assert_has("a", "b")` bridges this
   so the natural call does not read as a type failure.

A fifth decision follows from the same probe: **`assert_is` requires both
arguments to carry reference identity** (Object, Array, or Dictionary). `is_same`
is a total function and would happily value-compare two ints, so
`assert_is(2, 2)` would silently behave like `assert_eq`. Recording a
type failure that names `assert_eq` as the right tool is more honest than
passing. The alternative — accepting primitives — was rejected because a
passing `assert_is(2, 2)` reads as an identity claim that was never made.

**Task 2.5 (refactor) — decided: no refactor.** The four ordering
comparisons share a shape, but each differs in both its operator
(`<=`, `<`, `>=`, `>`) and its recorded `assertion` name, so a shared helper
would need the operator and the name passed in as parameters. That is
indirection with no reduction in behaviour, and it would make each assertion
harder to read rather than easier. The task's own condition was "if it does
not obscure them"; it would. Recorded here so the decision is visible rather
than looking like an oversight.

**One correction to this phase's own test.** The type-safety suite fails by
design, so the run must exit **1**, not 0. Task 2.2's wording implied 0; the
test initially asserted the wrong code. R4's actual guarantee is that these
failures stay at 1 and never escalate to 2, which is what the test now pins.

Verification for this phase: `tests/e2e/test_native_runtime.py` 24 passed
(including the Phase 1 skip tests, which is the load-bearing check — the single
guard in `_gd_tools_record_failure` suppressed all nine new assertions with no
per-assertion change, exactly as R2 intended). Full suite `1157 passed, 2
skipped, 0 failed` in 8m36s. Coverage `96.15%`, unchanged from Phase 1, which
is the correct result: the coverage gate measures Python and this phase added
only GDScript. `ruff` and `black` clean. `protocol.py`, `command.py` and
`orchestrator.py` verified untouched against the branch point.

### Task 2.1: Write the failing tests (Red)

- [x] Task: Add fixture suites for the assertion surface [60e12c0]
  - [ ] Extend `tests/fixtures/projects/native_test_project/test/assertion_suite.gd` (`NativeAssertionSuite`) with **passing** methods, one per new assertion, each with a one-line docstring-style comment naming the contract it pins. These must all pass, proving the satisfying side of R5.
  - [ ] Create `tests/fixtures/projects/native_test_project/test/assertion_failures_suite.gd` (`NativeAssertionFailuresSuite`) with one method per assertion that deliberately violates it. This is where R5's message requirements become assertable.
  - [ ] Pin R5's two deliberate semantics as named methods so neither is "cleaned up" later:
    - [ ] `test_between_inclusive_lower_bound` and `test_between_inclusive_upper_bound`
    - [ ] `test_has_argument_order` and `test_in_argument_order` — the same membership check written in both orders, so the inversion is exercised rather than assumed
  - [ ] Create `tests/fixtures/projects/native_test_project/test/assertion_type_safety_suite.gd` (`NativeAssertionTypeSafetySuite`) with one method per R4 case: `assert_between` and `assert_almost_eq` on a non-numeric, `assert_has` and `assert_in` on a non-container, `assert_has_method` on a non-`Object`, `assert_is` on arguments that cannot carry reference identity.
  - [ ] Add an `assert_has_method` passing case and an `assert_is` passing case using two references to the same object and to two distinct objects.

### Task 2.2: Add the e2e tests (Red)

- [x] Task: Add assertion tests to `tests/e2e/test_native_runtime.py` [60e12c0]
  - [ ] `test_native_new_assertions_pass_on_satisfying_input` — one spawn over the extended `assertion_suite.gd`; every entry is `passed` and `returncode == 0`.
  - [ ] `test_native_new_assertions_report_values_and_message_detail` — one spawn over `assertion_failures_suite.gd`; `returncode == 1`, and per assertion assert `failure["assertion"]` is the right method name, `actual` and `expected` are populated, and `message` satisfies **R5's final column**:
    - [ ] `assert_between` message names the violated bound and its value
    - [ ] `assert_in` / `assert_has` message names the missing element
    - [ ] `assert_almost_eq` message names the observed delta and the allowance
    - [ ] `assert_has_method` message names the object's type and the method
    - [ ] `assert_is` message names both types and that they were distinct instances
  - [ ] `test_native_assertions_are_attributed_to_user_code` — asserts every new failure's `source` contains the fixture filename and not `gd_tools_test.gd`, and `line > 0` (spec R6, acceptance criterion 11).
  - [ ] `test_native_assertion_type_mismatch_fails_the_test_not_the_run` — one spawn over the type-safety suite. Assert `returncode == 0`, every entry is `failed` with a message naming the type problem, `payload["engine_errors"]` is empty, and **no entry has `status == "error"`**. This is the R4 guarantee expressed as a test.
  - [ ] `test_native_protocol_and_command_sources_unchanged` — assert no `skipped`-field change reached the protocol. Prefer a source-level check over a runtime one; see Task 2.6.
  - [ ] **Run and confirm Red** for the right reason: `assert_gt` and friends are not yet methods.

### Task 2.3: Implement the assertions (Green)

- [x] Task: Add nine assertions to `gd_tools_test.gd` [60e12c0]
  - [ ] Add a private type-mismatch helper that records a failure naming the expectation, the received type, and the argument position. Nine call sites justify it; it is not speculative.
  - [ ] Implement the four ordering comparisons — `assert_gt`, `assert_gte`, `assert_lt`, `assert_lte` — per R5. Type-check before comparing so a bad argument records a failure instead of raising (R4).
  - [ ] Implement `assert_between(value, lower, upper)` with **both bounds inclusive** (R5). The failure message must name which bound was violated and its value.
  - [ ] Implement `assert_almost_eq(a, b, max_delta)` using absolute difference. The message names the observed delta and the allowance.
  - [ ] Implement `assert_has(container, element)` and `assert_in(element, container)`. **The argument order is deliberately inverted between the two** (R5) — do not normalize it. Each message names the missing element and the container's type.
  - [ ] Implement `assert_has_method(object, method)`. Message names the object's type and the method.
  - [ ] Implement `assert_is(a, b)` for reference identity. **Verify the primitive before relying on it:** Godot 4.2+ provides `is_same()` and the project floor is 4.5, but confirm it against the fixture project rather than assuming (spec §7). Message names both types and that they were distinct instances.
  - [ ] Every new assertion routes failures through the existing `_gd_tools_record_failure`. **Do not introduce a second failure-recording path.**
  - [ ] Do not modify the seven existing assertion bodies — the Phase 1 guard in `_gd_tools_record_failure` already covers them.

### Task 2.4: Run and confirm Green

- [x] Task: Verify the assertion surface [60e12c0]
  - [ ] Run the Phase 2 e2e tests; all pass.
  - [ ] Re-run the Phase 1 skip tests; still Green. The Phase 1 guard must still suppress post-skip failures now that the assertion count has grown — a new assertion is exactly the case R2 was designed to cover for free.
  - [ ] Re-run `test_native_assertions_report_values_and_source`; still Green. The pre-existing `assert_eq` fixture method must be unaffected.

### Task 2.5: Refactor (optional)

- [x] Task: Clean up only if Phase 2 tests are Green [60e12c0]
  - [ ] Collapse genuine duplication among the four ordering comparisons if it does not obscure them.
  - [ ] Leave `gd_tools_test.gd`'s existing structure and naming alone otherwise.

### Task 2.6: Verify the R7 no-protocol-change constraint

- [x] Task: Prove `protocol.py` and `command.py` were not touched [60e12c0]
  - [ ] `git diff --name-only` against the branch point; confirm `src/gd_tools/native_test/protocol.py` and `src/gd_tools/native_test/command.py` are absent.
  - [ ] If either appears, the implementation reached outside the GDScript surface. Revert it and revisit the design — spec R7 makes this a stop condition, not a review note.

### Task 2.7: Verify coverage

- [x] Task: Check the self-coverage gate [60e12c0]
  - [ ] `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
  - [ ] Target: >80% line, >70% branch on new source; gate unchanged or better.

### Task 2.8: Commit and record

- [x] Task: Commit Phase 2 [60e12c0]
  - [ ] Commit: `feat(native-test): Add GUT-core comparison, membership, and introspection assertions`
  - [ ] Attach a `git notes` summary per `workflow.md` step 9.
  - [ ] Mark tasks `[x]` with the commit SHA and commit the plan update as `conductor(plan): Mark phase 'ASSERTION SURFACE' as complete`.

### Task 2.9: Phase Verification & Checkpoint

- [~] Task: Phase Verification & Checkpoint (Refer to [`../../workflow.md`](../../workflow.md))
  - [ ] Run `git diff --name-only <phase_1_checkpoint_sha> HEAD`; confirm a test exists for every changed `.py`/`.gd`.
  - [ ] Announce and run the full `CI=true pytest` suite. On failure, propose at most two fixes, then stop and ask.
  - [ ] Present manual verification steps and **await explicit confirmation**:
    - `pip install -e .`
    - In a Godot project, write a suite using `assert_between`, `assert_in`, `assert_has_method`, and `skip_test`
    - `gd-tools test --runtime native`; confirm the passing methods report as passed, a deliberately violated one names the missing element or violated bound, and a skipped method reports as skipped
  - [ ] Create the checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 2 - ASSERTION SURFACE`
  - [ ] Attach the verification report as a `git notes` entry, record `[checkpoint: <sha>]` under the Phase 2 heading, and commit the plan update.

---

## Phase 3 — Documentation truth and the final gate

Covers spec R8 and the track's Definition of Done.

### Task 3.1: Correct `docs/ARCHITECTURE.md`

- [ ] Task: Update the three affected sites
  - [ ] `:1002` — the `GdToolsTest` table row listing the assertions. Replace the seven-method list with the full surface, including `skip_test` and `pending_test`.
  - [ ] `:804-807` — remove "the shipped assertion surface has no `skip_test()` call yet, so no GDScript currently emits them." That sentence is now false. The surrounding explanation of which statuses exist stays.
  - [ ] `:1121-1123` — delete the §13 bullets "No `skip_test()`" and "Thin assertion surface." **Leave the other four §13 limitations in place** — no mocking, no parameterized tests, no parallel execution, no editor integration are all still true and all still say so in `README.md:143-147`.
  - [ ] Keep every ASCII diagram within 80 columns per `product-guidelines.md` §1.
  - [ ] No test obligation — per `workflow.md`, documentation changes carry none.

### Task 3.2: Correct `README.md`

- [ ] Task: Update the capability matrix and the surrounding prose
  - [ ] `:135` — the Assertions row. Reflect the widened surface.
  - [ ] `:145` — "Skipping a test at runtime | Not yet | Yes" becomes supported.
  - [ ] `:143-144` and `:146-147` — parameterized tests, parallel execution, and the editor plugin **stay "Not yet."**
  - [ ] `:149-151` — the prose naming "runtime skipping" as a gap a migrating project must avoid. Rewrite so it names only the limitations that remain, and point at the legacy GUT path for those specifically.
  - [ ] If the new surface makes the "Broad assertion library" comparison row stale in the GUT column, leave the GUT column alone — it describes GUT, not this project.

### Task 3.3: Review `docs/USER_GUIDE.md`

- [ ] Task: Correct only what this track falsified
  - [ ] Update wherever USER_GUIDE documents the assertion surface or repeats the capability matrix.
  - [ ] Its integration examples at `:489-501` remain accurate. Do not rewrite them.
  - [ ] If USER_GUIDE documents no assertion surface, make no change and say so in the commit note.

### Task 3.4: Final quality gate

- [ ] Task: Run the complete Definition of Done
  - [ ] `ruff check src/ tests/`
  - [ ] `black --check src/ tests/`
  - [ ] `CI=true pytest` — the full suite
  - [ ] `git diff --check` clean
  - [ ] Coverage gate unchanged or better (>80% line, >70% branch)

### Task 3.5: Commit and record

- [ ] Task: Commit Phase 3
  - [ ] Commit: `docs(native-test): Document the widened assertion surface and runtime skipping`
  - [ ] Attach a `git notes` summary per `workflow.md` step 9.
  - [ ] Mark tasks `[x]` with the commit SHA and commit the plan update as `conductor(plan): Mark phase 'DOCUMENTATION TRUTH' as complete`.

### Task 3.6: Phase Verification & Checkpoint

- [ ] Task: Phase Verification & Checkpoint (Refer to [`../../workflow.md`](../../workflow.md))
  - [ ] Announce and run the full `CI=true pytest` suite one final time.
  - [ ] Present manual verification steps and **await explicit confirmation**:
    - `pip install -e .`
    - `gd-tools test --runtime native` on a project using the new surface
    - Read `README.md`'s capability matrix and `ARCHITECTURE.md` §13; confirm the claims match what the commands just did
  - [ ] Create the checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 3 - DOCUMENTATION TRUTH`
  - [ ] Attach the verification report as a `git notes` entry, record `[checkpoint: <sha>]` under the Phase 3 heading, and commit the plan update.

### Task 3.7: Close the track

- [ ] Task: Finalize
  - [ ] Confirm every acceptance criterion in `spec.md` §4 is satisfied, or record which are not and why.
  - [ ] Confirm the branch contains no changes to `protocol.py`, `command.py`, or `orchestrator.py`.
  - [ ] Propose the track to the user for `conductor-review` and to `main` for merge.

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Type-mismatch handling escalates a run to exit 2 | Medium | Spec R4 exists because of it. `test_native_assertion_type_mismatch_fails_the_test_not_the_run` asserts `returncode == 0`, empty `engine_errors`, and no `error` status. |
| Reaching for a Python source change and breaking R7 | Medium | Task 2.6 makes it a hard stop with an explicit revert instruction, not a review comment. |
| Godot spawn count inflates CI time and flake exposure | High if unbatched | Guiding constraint 2. ~5 spawns, not ~25. |
| Normalizing `assert_has`/`assert_in` argument order for tidiness | Medium | R5 names it a deliberate inversion; Task 2.1 pins both orders as separate methods. |
| A post-skip assertion slips through as a failure | Low | The guard sits in `_gd_tools_record_failure`, so new assertions are covered for free. Task 2.4 re-runs the Phase 1 tests specifically to prove this. |
| Retrying a skipped test wastes a retry | Low | Already correct at `:182`; Task 1.4 verifies rather than edits. |
| Scope creep into mocking / parameterized / parallel | Medium | All three are in `spec.md` §5 Out of Scope and stay "Not yet" in `README.md:143-147`. |
| Docs overclaim | Medium | Task 3.1 forbids touching the four §13 limitations that remain true. |

---

## Follow-ups found during implementation

Recorded here rather than in `spec.md`, which is approved. Neither is in scope for
this track; both are candidates for their own track.

### A suite that fails to load is silently dropped and the run passes

Found during Task 1.2 while confirming the Red phase. Not a flake and not caused by
this track's changes.

`gd_tools_test_runner.gd` `_run_suite` loads a suite script and calls `script.new()`
on it. When the script has a parse error, `load()` returns a null `GDScript`, and the
`new()` call at `:101` raises `Invalid call. Nonexistent function 'new' in base
'GDScript'`. That error is swallowed rather than escalated, the suite is dropped, and
the run finishes with:

```
status: "passed"
tests:  []
returncode: 0
```

**Severity is narrower than it first looks, and Phase 1 verification established
this.** Driving the runner through the normal CLI, a suite with a parse error is
caught by the preflight instead:

```
$ gd-tools test --runtime native
Error: Suite 'res://test/verify_suite.gd' references unknown test 'test_plain_passes'
=== EXIT CODE: 2 ===
```

So `gd-tools test` is safe today. The false pass is reachable only when the runner is
invoked **directly** — which is exactly what the e2e tests in
`tests/e2e/test_native_runtime.py` do, bypassing preflight. The user-facing risk is
therefore low, but the testing risk is real: an e2e test can silently assert nothing.

Observed with a `Function "pending_test()" not found in base self` parse error, which
is precisely the error this track's Red phase was supposed to produce. The test meant
to catch it passed vacuously, because `all(test["status"] == "skipped" for ...)` over
an empty list is `True`. `test_native_all_skipped_suite_exits_zero` now asserts
`len(payload["tests"]) == 5` first, so it cannot pass that way again.

Two things a future track should weigh:

- The runner already has the vocabulary. A load failure is `error`, and `error` is not
  retryable, does not escalate silently, and exits 2. A suite that cannot load is an
  environment problem, exactly the class `spec.md`'s exit code 2 reserves.
- The engine error *was* captured — it reached stderr and the run's engine diagnostics —
  yet the escalation at `:717-724` that turns any captured `ERROR:` into exit 2 did not
  fire. Read that capture-or-escalate path before choosing a fix; patching `:101` alone
  would address the symptom and leave the gap that makes the failure silent.

### Blanket test-count assertion

Independent of the bug above, e2e tests that assert over `payload["tests"]` should
assert the expected count before the content. A dropped suite turns content
assertions vacuously true, and the same class of false pass could reach any of the
existing tests in this file.
