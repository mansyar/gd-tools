# Native Assertion Parity and `skip_test()`

**Track ID:** `native_assertion_parity_skip_test_20260927`
**Type:** Feature
**Status:** Draft — approved for planning
**Origin:** Surfaced during a Conductor codebase review of `main` @ `f4f578c`, after `native_docs_truth_pass_20260926` completed. Closes two of the six Known Limitations in `docs/ARCHITECTURE.md` §13 and removes the blocker that keeps migration roadmap Phase 3 (`GUT Compatibility Bridge`) from being scoped fairly.

## 1. Problem

The native runtime is the default `gd-tools test` path. Its assertion surface is seven methods, and the documented migration comparison in `ARCHITECTURE.md:1123` is explicit that this is "considerably narrower than the GUT set the migration bridge is being measured against." Two consequences.

### 1.1 The protocol reserves a status no component can produce

`NativeTestResult.status` (`src/gd_tools/native_test/protocol.py:157-165`) admits `skipped` and `pending`. Python already consumes both: `native_test/command.py:334` collapses them to `skip` for the terminal table, `:391` counts them, and `:423-424` writes JUnit `<skipped message=...>`. `docs/ARCHITECTURE.md:806-807` records the consequence — *"the shipped assertion surface has no `skip_test()` call yet, so no GDScript currently emits them."*

The entire Python half of `skip_test()` ships and is tested. Nothing on the Godot side can trigger it. A user who writes `if not connected: skip_test("no socket")` gets a compile error, and a suite cannot opt a test out on an environment condition — so the common workaround is to delete the test or wrap it in a tautology.

### 1.2 A migrating user hits two missing assertion families immediately

`README.md:135` advertises "7 core assertions plus `fail()`" against GUT's "Broad assertion library," and `README.md:144-146` lists parameterized tests, runtime skipping, and parallel execution as "Not yet." Of those, runtime skipping lands with this track.

The ordering comparisons and collection-membership assertions a user reaches for first — `assert_gt`, `assert_between`, `assert_has`, `assert_in` — are absent. Each gap is a line rewritten during migration, and each rewrite is a chance to change a test's meaning silently.

## 2. Requirements

### R1 — `skip_test()` and `pending_test()` emit a skippable test

Both are public methods on `GdToolsTest`. `pending_test()` is an alias: it records the identical reason and the identical `skipped` status. `reason` is optional; when omitted, a default reason string is used so the `message` field is never empty — both the terminal table and JUnit `<skipped message=...>` render it, and an empty reason would render as a blank skip.

State lives on the per-test instance. This is safe across retries because `_new_test_context` (`gd_tools_test_runner.gd:483-495`) constructs a fresh instance per attempt.

### R2 — Mark-and-abort: one guard, not N call sites

After a skip is recorded, every subsequent assertion failure in that test is discarded. The guard lives in `_gd_tools_record_failure`, so it covers the seven existing assertions, `fail()`, and any assertion added later, with no per-assertion change.

Rationale for a single guard point: a per-assertion guard is a rule N authors must remember, and the first forgotten one silently converts a skipped test into a failed one.

### R3 — The runner reports `skipped`, and a failure still outranks a skip

In `_run_test_attempt`, the status computation at `gd_tools_test_runner.gd:317-318` becomes three-way. A test with no recorded failures and a recorded skip reports `status = "skipped"` with the skip reason as `message`.

**A recorded failure outranks a skip.** If an assertion failed before `skip_test()` was reached, the test reports `failed`. A skip must never be able to mask a real failure — that property is what makes the skip trustworthy and is what stops it being used to quiet a red suite.

Three existing behaviors are correct for `skipped` today and must be verified rather than changed:

| Location | Behavior | Requirement |
|---|---|---|
| `gd_tools_test_runner.gd:182` | `retryable := status == "failed" or status == "timeout"` | A skip must not consume a retry. Already correct. |
| `gd_tools_test_runner.gd:338` | Screenshot capture is gated on `["failed", "timeout", "error"]` | A skipped test must not trigger a windowed failure screenshot. Already correct. |
| `gd_tools_test_runner.gd:638` | `_run_status` escalates only on `failed`/`timeout`/`error` | A skip must not fail the run. An all-skipped suite exits 0. Already correct. |

### R4 — Wrong-typed arguments fail the test, never the run

Each new assertion validates its argument types and records an actionable test failure when they are wrong. It must not raise a GDScript runtime error.

This is a hard requirement, not a nicety. An engine error escalates the entire run: `_finish_with_status` sets `_run_status = "error"` on any captured `ERROR:` line (`gd_tools_test_runner.gd:717-724`) and calls `quit(2)`. One assertion called with a non-numeric argument would therefore convert a single bad test into a run-level environment failure and a misleading exit code 2.

The checks that matter: `assert_between` and `assert_almost_eq` against non-numerics, `assert_has` and `assert_in` against a non-container, `assert_has_method` against a non-`Object`, and `assert_is` against arguments that cannot carry reference identity.

### R5 — Nine assertions, with pinned semantics

| Assertion | Contract | Failure message names |
|---|---|---|
| `assert_gt(a, b)` | `a > b` | both operands |
| `assert_gte(a, b)` | `a >= b` | both operands |
| `assert_lt(a, b)` | `a < b` | both operands |
| `assert_lte(a, b)` | `a <= b` | both operands |
| `assert_between(value, lower, upper)` | `lower <= value <= upper`, **both bounds inclusive** | which bound was violated, and its value |
| `assert_almost_eq(a, b, max_delta)` | `abs(a - b) <= max_delta` | the observed delta and the allowance |
| `assert_has(container, element)` | `container.has(element)` | the missing element, and the container's type |
| `assert_in(element, container)` | `container.has(element)` | the missing element, and the container's type |
| `assert_has_method(object, method)` | `object.has_method(method)` | the object's type and the method name |
| `assert_is(a, b)` | reference identity | both types, and that they were distinct instances |

Two semantics are deliberate and must not be "cleaned up":

- **`assert_between` bounds are inclusive.** Exclusive is the more common convention elsewhere; matching GUT matters more here because a migrated test must not change meaning.
- **`assert_has` and `assert_in` take their arguments in opposite order** (`container, element` versus `element, container`). This is a GUT quirk, preserved deliberately so a ported test cannot silently invert its subject and object and still pass.

### R6 — Type-specific detail rides in the existing `message` field

The failure record keeps its current shape — `{assertion, message, actual, expected, source, line}` — and per R5's final column, `message` carries the type-specific detail. No protocol change, no new field, no reporter change: the detail renders wherever a message already renders.

Source attribution is already solved. `_gd_tools_record_failure` walks `get_stack()` and skips frames belonging to `gd_tools_test.gd` and `gd_tools_test_runner.gd`, which is why failures point at user code. New assertions live in `gd_tools_test.gd`, so they inherit this. The plan must verify attribution holds at the new call sites rather than assume it.

### R7 — No protocol change

`skipped` and `pending` are already valid `NativeTestResult.status` values, already mapped for terminal output, and already written to JUnit. `command.py` requires no edit.

Consequently this track's Python surface is **tests only**. If implementation finds itself wanting to change `protocol.py`, `command.py`, or a reporter, that is a signal the GDScript design is wrong — stop and revisit, per `workflow.md`'s surgical-changes principle. Recording this explicitly prevents a later reader from re-deriving the conclusion or adding a redundant `skipped` field.

### R8 — Correct the four documentation claims this track falsifies

| Location | Current claim |
|---|---|
| `docs/ARCHITECTURE.md:1002` | The `GdToolsTest` table row listing the seven assertions |
| `docs/ARCHITECTURE.md:806-807` | "the shipped assertion surface has no `skip_test()` call yet, so no GDScript currently emits them" |
| `docs/ARCHITECTURE.md:1121-1123` | §13 bullets "No `skip_test()`" and "Thin assertion surface" |
| `README.md:135`, `README.md:145`, `README.md:149-151` | The native-vs-GUT matrix rows for assertions and runtime skipping, plus prose naming runtime skipping as a gap |

`README.md:143-147` also lists parameterized tests, parallel execution, and the editor plugin as "Not yet." Those stay "Not yet" — this track does not land them, and the surrounding prose must not imply otherwise.

`docs/USER_GUIDE.md` is corrected only where it documents the assertion surface or the capability matrix. Its existing examples at `:489-501` remain accurate and are not rewritten.

### R9: The terminal summary must not count skipped tests as passed

**Added after Phase 1 verification, approved by the user. This is the one
documented exception to R7.**

R7 holds: the skip mechanism itself required no Python change, and the JUnit XML and
terminal table were already correct. Manual verification in a real Godot project
surfaced a separate pre-existing message that this feature falsifies.

`test_runner.py` printed `All {result.total} test(s) passed.` whenever
`result.failed == 0`. With 1 passing and 3 skipped tests, that reported **"All 4
test(s) passed"** — claiming a fully green suite when most of it never ran. The
message was correct only while no GDScript could emit a skipped status, which is
precisely what R1 changed. It is a latent defect this track makes reachable, not a
defect this track introduced.

The constraint: the message must report passed and skipped separately whenever
`result.skipped` is non-zero, and keep the existing `All {total} test(s) passed.`
wording when nothing was skipped so that existing callers and users are unaffected.
`result.skipped` is already on `TestResult`; the table, the JUnit writer, and the exit
code are all correct and stay untouched.

Why R7's hard stop did not forbid this: R7 exists to catch a design error in the
GDScript skip mechanism — reaching for Python to *produce* a skip would mean the
mechanism was wrong. This change makes an existing message honest about a status the
mechanism now produces. It changes no protocol, no mapping, and no exit code. Shipping
a known-false "All 4 test(s) passed" was judged the worse outcome.

## 3. Non-functional requirements

| Requirement | Statement |
|-------------|-----------|
| Surgical | `protocol.py`, `command.py`, `orchestrator.py`, and the coverage reporters are untouched (R7). The diff is `gd_tools_test.gd`, `gd_tools_test_runner.gd`, fixture suites, tests, and the four documentation sites — plus `test_runner.py`, the single documented R9 exception, which changes one summary message and nothing else. |
| Test-driven | Per `workflow.md`, both `.gd` changes carry a full Red/Green cycle. Asserting the surface from Python means asserting on the `diagnostics.failures` payload in the result JSON, so the plan must budget fixture suites that deliberately trip each of the nine assertions plus the skip path. |
| Honest | `skip_test()` called in `before_all` is **not** supported and is documented as such. `before_all` runs on the suite instance (`gd_tools_test_runner.gd:110-114`), not the per-test instance, so the runner cannot attribute such a call to a test and it silently skips nothing. This is stated as a limitation rather than shipped silently; propagating suite-level skips is deliberately out of scope. |
| No scope absorption | Mocking/stubbing, parameterized tests, and parallel execution remain deferred per `ARCHITECTURE.md` §13. The GUT bridge is Phase 3. |
| Format | ASCII diagrams in documentation stay within 80 columns per `product-guidelines.md` §1. |

## 4. Acceptance criteria

| # | Criterion |
|---|----------|
| 1 | `skip_test(reason)` and `pending_test(reason)` are callable from a `GdToolsTest` suite, and a test that calls either reports `status = "skipped"` in the native result JSON. Confirmed by a test written and confirmed failing before the change. |
| 2 | The skip reason appears as the `message` on the `skipped` result, and renders in the terminal table and in JUnit `<skipped message="...">`. |
| 3 | `skip_test()` with no argument still produces a non-empty reason. |
| 4 | An assertion called after `skip_test()` records no failure, and the test reports `skipped` — not `failed`. |
| 5 | An assertion that fails *before* `skip_test()` is reached leaves the test reporting `failed`. A skip cannot mask a failure. |
| 6 | A skipped test does not consume a configured retry, does not trigger a windowed failure screenshot, and does not escalate the run; a suite in which every test skips exits 0. |
| 7 | Each of the nine new assertions passes on a satisfying input and records a failure on a violating one, with `actual` and `expected` populated per the existing record shape. |
| 8 | `assert_between` accepts both bounds inclusively, and its failure message names the violated bound and its value. |
| 9 | `assert_in` and `assert_has` are distinguished by argument order only, and each failure message names the missing element. |
| 10 | Each of the nine assertions, given a wrong-typed argument, records a test failure naming the type problem — and the run still exits 0, with no `<engine>` error result and no exit code 2. |
| 11 | A failure from each new assertion is attributed to the user's test line, not to `gd_tools_test.gd`. |
| 12 | `protocol.py` and `command.py` are unchanged by this track (`git diff` shows no modification). |
| 13 | The four documentation sites in R8 are corrected, and `README.md:143-147` still shows parameterized tests, parallel execution, and the editor plugin as "Not yet." |
| 14 | `ruff check src/ tests/`, `black --check src/ tests/`, and the full `CI=true pytest` suite pass. The ≥80% line / ≥70% branch self-coverage gate is unchanged or better. |
| 15 | `git diff --check` is clean. |

## 5. Out of scope

- **Mocking/stubbing, parameterized tests, parallel execution.** All three remain §13 limitations, all three remain "Not yet" in `README.md:143-147`.
- **The GUT compatibility bridge.** Migration roadmap Phase 3. This track makes the native surface worth measuring; it does not begin the migration.
- **Engine-diagnostic assertions** — `assert_push_error`, `assert_signal_emitted`, `assert_file_exists`, `assert_deprecated`. They are a distinct design problem that belongs with the bridge, which is where their value is realized.
- **String and regex matching** (`assert_str`). Outside the curated set; not an early migration blocker.
- **Making the GUT path aware of the new assertions.** GUT suites extend `GutTest`; they never see `GdToolsTest`.
- **Propagating a suite-level `skip_test()` from `before_all`.** Recorded as a documented limitation instead (R, Non-functional, "Honest").
- **The coverage target contract.** `coverage_target_contract_20260926` stays open and blocked on its own decision; nothing here touches `coverage.gd` or `gd_tools_native_coverage.gd`.
- **Version bump, changelog, release.** The native runtime is unreleased; `pyproject.toml` and `CHANGELOG.md` are both at `0.4.0`. Separate track.
- **Rewriting `docs/ARCHITECTURE.md`'s coverage half, `docs/PRD.md`, or `docs/ROADMAP_v1.md`.**

## 6. Open questions

None. The four decisions that would otherwise block planning were settled before this spec was drafted:

1. **What `skip_test()` does to the rest of the body.** Resolved: mark-and-abort, with a single guard in `_gd_tools_record_failure`. Makes `if not cond: skip_test("reason")` a safe one-liner, which is the dominant use.
2. **Whether `pending_test()` is a distinct status.** Resolved: an alias emitting `skipped`. The protocol reserves both and `command.py:334` already collapses them, so a distinct status would add a reporting distinction with no defined meaning behind it. `pending` is better designed when the bridge supplies its real semantics.
3. **How much surface to add.** Resolved: the curated GUT-core set. Full GUT parity pulls in the engine-diagnostic group, which is a different problem.
4. **How failures explain themselves.** Resolved: reuse the record, enrich `message`. A structured `detail` field would require a protocol bump and reporter surface for a value only some assertions populate.

## 7. Notes for the implementer

- **The status computation is the single decision point.** `gd_tools_test_runner.gd:317-318` reads `var status := "failed" if not failures.is_empty() else "passed"`. Everything else about `skipped` already works. Read that function before designing anything.
- **`_run_test_attempt` returns the result dictionary at `:363-370`;** the skip reason belongs in that `message`. Do not route it through `diagnostics`, which R6 keeps free of new structure.
- **`_failure_message` at `:655-664` joins failure messages with `"; "`.** A skipped test has no failures, so it returns `""` — the reason must not come from that path.
- **Verify `is_same()` before using it for `assert_is`.** Godot 4.2+ provides it and the project floor is 4.5, but the plan should confirm it against the fixture project rather than assume. The CI matrix already covers 4.5.2 as the floor.
- **The existing seven assertions need no body changes** for R2 — that is the point of the single guard. Confirm this by reading `_gd_tools_record_failure` first; if a guard inside it is not sufficient, stop and revisit rather than adding per-assertion checks.
- **Match existing test style.** `tests/unit/test_native_artifacts.py` and `tests/unit/test_native_command.py` are the reference for module docstring, `pytestmark = pytest.mark.unit`, one-line test docstrings, and arrange/act/assert. Locate the established native GDScript fixture suite layout before adding fixtures.
- **`gd_tools_test.gd` is 140 lines today.** Roughly tripling it is expected and fine. What must not happen is a second failure-recording path appearing alongside `_gd_tools_record_failure`.
