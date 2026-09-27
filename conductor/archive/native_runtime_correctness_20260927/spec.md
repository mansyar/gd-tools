# Native Runtime Correctness: Signal Wait Bounds, Suite Timeout, and Token Invariants

- **Track ID:** `native_runtime_correctness_20260927`
- **Type:** Bug
- **Status:** Draft
- **Branch:** `feature/native-runtime-correctness-20260927`
- **Origin:** Found during the codebase analysis on 2026-09-27, immediately after
  `native_assertion_parity_skip_test_20260927` was archived. Two of the findings
  below are defects on the **default** execution path — `gd-tools test` defaults
  to `--runtime native`, so no GUT opt-in is required to reach them.

---

## 1. Problem

The native runtime has three defects and one structural fragility. All are
contained in two GDScript files shipped to users as package data:

- `src/gd_tools/addons/gd-tools-test/gd_tools_test.gd` (the user-facing base class)
- `src/gd_tools/addons/gd-tools-test/gd_tools_test_runner.gd` (the runner)

### 1.1 `wait_for_signal` cannot return what its signature promises

`gd_tools_test.gd:480-483`:

```gdscript
func wait_for_signal(target_signal: Signal) -> bool:
	## Wait until a signal is emitted and return true.
	await target_signal
	return true
```

It is typed `-> bool` and has exactly two outcomes: block until the signal
arrives, then return `true`. **It can never return `false`.**

A same-named method with the opposite semantics exists on the test context,
`gd_tools_test_context.gd:153`:

```gdscript
func wait_for_signal(target_signal: Signal, timeout_seconds: float) -> bool:
```

which is bounded, returns `false` on timeout, **and records a test failure**
(`:176-179`). So the project's two signal-wait helpers share a name and differ
in both arity and behaviour, and the one a user reaches for first is the one
that cannot time out.

The user-visible failure mode: writing the natural guard

```gdscript
if not wait_for_signal(door_opened):
	fail("door never opened")
```

never reaches the `fail`. Instead the `await` blocks until the runner's
per-test timeout fires, the test is reported as `timeout` rather than `failed`,
and the message explaining *why* is lost. The call site reads as a conditional;
the behaviour is an unconditional hang. That mismatch is only visible to a user
who goes looking for it.

### 1.2 `_suite_timeout` reads one test and ignores the rest

`gd_tools_test_runner.gd:153-156`:

```gdscript
func _suite_timeout(suite_data: Dictionary) -> float:
	for test_data in suite_data.get("tests", []):
		return max(float(test_data.get("timeout_seconds", 5.0)), 0.001)
	return 5.0
```

The `for` loop returns on its first iteration, so it is a `return` wearing a
loop's syntax. The result is the **first** test's `timeout_seconds`, and nothing
else in the suite influences it.

It is consumed at `gd_tools_test_runner.gd:106` and spent on `before_all`
(`:110`) and `after_all` (`:132`). A suite whose first test is declared with a
short `timeout_seconds` therefore gives its own setup and teardown a short
budget — regardless of how much work either actually does, and regardless of
how long every other test in the suite is declared to be allowed.

Ordering dependence in a suite's setup budget is a defect regardless of
direction: reordering test methods, or adding one with a smaller timeout, changes
how long `before_all` is given.

### 1.3 Test-timeout cancellation is maintained by hand at three sites

`_active_test_token` (`:19`) is a monotonically increasing integer. The invariant
is: **when a test attempt ends for any reason, the token is incremented exactly
once, so the timer armed for that attempt can no longer fire.**

The runner relies on this to stop a late `test_call_completed` from bleeding
into the *next* test. It is checked in three places and mutated in three:

| Site | Role |
| --- | --- |
| `:277` | manual increment on the missing-test-method early return |
| `:365` | manual increment on another early return |
| `:559` | increment inside `_begin_test_timeout` when arming |
| `:570`, `:582`, `:585` | reads — the checks that the invariant is intact |

The token is incremented by hand on early-return paths inside `_run_test_attempt`,
a single method spanning `:208-376` with **11 return statements**, 6 `await`s, and
a five-case status-precedence ladder. Nothing enforces that a new early return
increments it. A path that forgets leaves the previous attempt's `create_timer`
armed, and when it fires it calls `test_call_completed.emit()` into whichever test
is now running — producing a spurious `passed` or a spurious `timeout` with no
error raised.

This is latent rather than active: no current path is known to be missing the
increment. The cost of the current design is that the next person who adds an
early return has to know about an invariant that is invisible from the return
statement itself.

### 1.4 The invoke-and-await body is written out four times

Two distinct shapes are repeated:

**"Await the already-armed timer"** — three inlined copies, all inside
`_run_test_attempt`, none of which re-arm the timer because it was armed once at
`:251` for the whole attempt:

- `before_each` — `:254-262`
- the test body — `:265-272`
- `after_each` (non-timeout branch) — `:301-308`

Each sets `_test_completed = false`, calls `_invoke_test(..., _active_test_token)`,
awaits `test_call_completed`, then reads `_test_timeout_reached`.

**"Arm, then await"** — two helpers that are byte-identical except for the return
value:

```gdscript
func _run_optional_call(context, method_name, timeout_seconds) -> Dictionary:
	_begin_test_timeout(timeout_seconds)
	_test_completed = false
	_invoke_test(context, method_name, _active_test_token)
	await test_call_completed
	return {"timed_out": _test_timeout_reached}

func _run_cleanup(context, method_name, timeout_seconds) -> void:
	_begin_test_timeout(timeout_seconds)
	_test_completed = false
	_invoke_test(context, method_name, _active_test_token)
	await test_call_completed
```

The two shapes are genuinely different and must not be merged into one. Only the
duplication *within* each shape is redundant.

---

## 2. Scope

`gd_tools_test.gd` and `gd_tools_test_runner.gd` only. This track writes GDScript
and the tests that exercise it.

---

## 3. Requirements

### R1 — `wait_for_signal` on the base class becomes bounded and honest

Add a `timeout_seconds` parameter with a **finite** default and return `false`
when it elapses without the signal arriving.

- The default is `5.0`, matching the runner's own per-test default at
  `gd_tools_test_runner.gd:248` and `_suite_timeout`'s fallback at `:156`. A
  default that silently waits longer than the test is allowed would reintroduce
  the hang through a different door.
- The wait must resolve on **whichever comes first** — the signal or the timer.
  Awaiting the timer unconditionally and then inspecting a flag is not acceptable:
  it would make every wait cost the full timeout, turning a fast signal into a
  slow test.
- The method **returns `false` and does not record a failure.** Deciding whether a
  timeout is a test failure is the caller's job. This is the one intentional
  semantic difference from `GdToolsTestContext.wait_for_signal`, which owns its
  own context and records its own failure; the docstring must say so, because
  that difference is precisely what made the pair confusing.
- The existing one-argument call form **keeps working.** A suite that already
  calls `wait_for_signal(sig)` gets a bounded wait instead of an unbounded one;
  it does not fail to parse or fail to run.

### R2 — `_suite_timeout` derives from the whole suite

The suite budget is derived from every test in the suite, not the first.

- Take the **maximum** `timeout_seconds` across all tests, floored at `0.001`,
  falling back to `5.0` for a suite with no tests. A suite's setup and teardown
  should not be penalised by, or depend on, declaration order.
- The output must be **order-independent**: two suites whose tests are the same
  multiset, presented in a different order, receive the same budget. This is the
  property that makes the fix verifiable and is what R2's test pins.

### R3 — Token invalidation becomes a named operation

The token is mutated in three places today (`:277`, `:365`, `:559`) and nothing
ties them together. The invariant is: **the token is incremented exactly once per
arm-or-cancel, so that no already-armed timer can fire into a later attempt.**

That invariant has two operations, not one, and the spec must not conflate them:

- **Arming** happens in `_begin_test_timeout` (`:558-566`), which increments the
  token to invalidate any previously armed timer and then binds the new timer to
  the new token value. This is not a cancel and must not be described as one.
- **Cancelling** is the exit-path operation: the early returns at `:277`
  (missing test method) and `:365`.

- A single private `_invalidate_timeout()` owns the mutation
  (`_active_test_token += 1`) and carries a comment stating the invariant. It is
  the **only** place in the file that touches the token. A direct
  `_active_test_token += 1` anywhere else is a defect this track is fixing; if
  one appears, that is a signal the helper is wrong, not that the site is
  exempt.
- `_begin_test_timeout` calls `_invalidate_timeout()` to arm, and a new
  `_cancel_timeout()` calls the same helper to cancel. Both operations are named
  for what they do; neither re-implements the increment.
- Every exit path from a test attempt calls `_cancel_timeout()`.
- The three existing checks at `:570`, `:582`, `:585` are **verified, not
  changed.** They are the readers of the invariant and are correct as written.
- R3 makes the requirement visible at each exit path. It does **not** restructure
  `_run_test_attempt` — see §5.

### R4 — The two duplicated invoke-and-await shapes each collapse to one helper

- The three "await the already-armed timer" sites route through one helper. It
  must **not** re-arm the timeout: the attempt's timer is armed once at `:251` and
  spans `before_each`, the test body, and `after_each`. Re-arming per hook would
  silently give each phase a fresh budget and change the meaning of a declared
  `timeout_seconds`.
- `_run_cleanup` delegates to `_run_optional_call` rather than repeating its
  body, or is removed in favour of it.
- Behaviour is unchanged. The collapse is only justified by tests that already
  pass before and after.

### R5 — No Python source changes

`src/gd_tools/native_test/protocol.py`, `command.py`, and `orchestrator.py` are
untouched. The Python surface of this track is tests only.

If a task below appears to need a Python source edit, that is a design signal —
stop and report rather than editing. R5 makes this a stop condition, not a
review comment.

### R6 — No change to the observable contract

Exit codes (`0` pass, `1` test failure, `2` environment/protocol/engine), the
per-test `status` vocabulary, the result JSON schema, and the native protocol
version are all unchanged.

**R1 is the one deliberate exception and it is bounded.** A test that waits on a
signal which never arrives changes from `timeout` (after the per-test budget) to
`false` returned to the caller at the `wait_for_signal` budget. That is the point
of R1 — the old behaviour discarded the caller's intent. The change is
acceptable because the native runtime is the default and new, the GUT bridge
(migration roadmap Phase 3) has not landed, and the new behaviour reports
*earlier and more informatively* rather than later. It must be recorded in the
release notes, because it is the one place a suite written against the current
behaviour can observe a difference.

---

## 4. Acceptance criteria

Each criterion is pinned by a test confirmed failing first, unless noted.

1. `wait_for_signal` returns `true` when the signal arrives within the budget.
2. `wait_for_signal` returns `false` when the signal never arrives, and does so
   within the budget rather than at the per-test timeout.
3. A signal arriving partway through the budget returns `true` **without** waiting
   out the remainder of the budget. (This is the R1 clause that rules out the
   flag-inspection implementation; a test that only checks the return value would
   pass against a method that always waits the full budget.)
4. A timed-out `wait_for_signal` records **no** failure of its own; the caller
   decides.
5. `wait_for_signal` called with one argument still works and is bounded.
6. `GdToolsTestContext.wait_for_signal` is unchanged: still bounded, still
   records its own failure, still returns `false` on timeout.
7. A suite whose first test declares a short `timeout_seconds` and whose later
   tests declare a long one gives `before_all` the larger budget.
8. Two suites with the same tests in different declaration order receive the same
   suite budget.
9. A suite with no tests still receives `5.0`.
10. No direct `_active_test_token += 1` exists outside `_invalidate_timeout()`.
    Verified by inspection against the source; also asserted as a property of the
    final file, not of runtime behaviour.
11. Both early-return paths in `_run_test_attempt` (`:277`, `:365`) call
    `_cancel_timeout()`, and `_begin_test_timeout` calls `_invalidate_timeout()`
    to arm. Verified by inspection against the source — a leaked timer corrupts a
    *later* test rather than its own, so no single-run test result can establish
    this.
    Established by inspection against the source, since a path that leaks a
    timer produces a wrong result in a *later* test rather than in its own.
12. The full suite still passes; exit codes, statuses, and the result schema are
    unchanged.
13. `protocol.py`, `command.py`, and `orchestrator.py` are verified untouched
    against the branch point.
14. The R6 exit-code and status vocabulary is unchanged for every existing
    fixture suite.

---

## 5. Out of Scope

- **Decomposing `_run_test_attempt`.** It is 169 lines with 11 returns, and it is
  the method that drives every test the project runs. R3 makes its exit paths
  legible; that is the whole of the benefit this track claims. A restructure is a
  separate track with its own evidence.
- **A lint rule against quantified assertions over a possibly-empty list.** A
  previous track recorded that only a length-guarded or index-based assertion
  can fail vacuously, and that the pattern deserves a lint rule. Real, and
  unrelated to signal waits.
- **Mocking, parameterized tests, parallel execution, editor integration.** The
  four remaining `ARCHITECTURE.md` §13 Known Limitations. Untouched here, and
  they stay "Not yet" in `README.md`'s capability matrix.
- **The GUT compatibility bridge** (migration roadmap Phase 3). This track is
  independent of it; §6.2 is the only point of contact.
- **Surfacing `engine_warnings` through the Python side.** The runner collects
  them (`:696-699`) and serializes them (`:778`) but `command.py` discards the
  field. A real gap, a Python-side fix, and therefore outside R5.
- **CI, type checking, macOS.** Separate tracks.

---

## 6. Decisions

### 6.1 `wait_for_signal`: add a bounded timeout to the base method

Four options were considered. The chosen one is to add a finite-default
`timeout_seconds` to the base-class method.

**Chosen.** One name, and `if not wait_for_signal(sig):` becomes code that works.
The context method stays for the already-bounded, context-owned, failure-recording
case, and the docstring states the difference.

**Rejected — rename the unbounded method** (`await_signal`). Honest, but two
similar names coexist and the bounded path still requires knowing that the
context version is the one that times out. It relocates the trap rather than
closing it.

**Rejected — delete the base-class method.** Cleanest naming; a breaking change
for any suite already using the base version, for a runtime that is days old and
whose bridge has not landed. The cost is real and buys tidiness rather than
correctness.

**Rejected — keep it unbounded, change the return type to `void`.** Removes the
lie in the signature at zero risk, but leaves the user with no way to express
"wait, but not forever" from a test method. It documents the problem rather than
solving it.

### 6.2 Interaction with the GUT bridge (Phase 3)

GUT's `wait_for_signal`-equivalent is bounded and returns `false` on timeout.
R1 moves the native base class toward GUT's semantics rather than away from them,
so a compatibility alias for this method is a rename away when Phase 3 lands.
Recorded here so Phase 3 does not have to rediscover it.

---

## 7. Notes for the implementer

- **Re-read every line number in this document before editing.** They are
  orientation pointers recorded on 2026-09-27, not anchors. `gd_tools_test_runner.gd`
  will have moved once Phase 1 lands.
- **The existing e2e harness is the template.** `tests/e2e/test_native_runtime.py`
  (`_prepare_project`, the `protocol_version: 2` manifest, `GD_TOOLS_NATIVE_MANIFEST`
  / `GD_TOOLS_NATIVE_RESULT`, `godot --headless --path <project> --script
  res://addons/gd-tools-test/gd_tools_test_runner.gd`) is the established shape.
  Extend it; do not build a parallel one.
- **Batch Godot spawns.** Each spawn costs seconds and carries flake surface.
  Fixture suites should carry many test methods and each e2e test should spawn
  Godot once and assert across all `payload["tests"]` entries. A previous track
  targeted ~5 spawns for ten behaviours; hold to that ratio.
- **Do not trust a `all()` over `payload["tests"]` without a length guard.** A
  previous track found a test passing vacuously because a suite that failed to
  load produced an empty list. Assert the expected count first. This applies
  directly to R1, R2, and R4, all of which assert over collected results.
- **Godot's await has no race primitive.** Whatever R1's implementation awaits,
  it must resolve on whichever of signal and timer fires first. Probe the pattern
  against the real engine on 4.5.2, the project's floor, before relying on it —
  a previous track found that the obvious approach failed to compile.
- **A Red that looks like a timeout is not an acceptable Red.** Distinguish "the
  behaviour is wrong" from "the engine hung" before implementing.
- **Read [`../coverage_target_contract_20260926/known_flakes.md`](../coverage_target_contract_20260926/known_flakes.md)
  before trusting any single full-suite run as a gate.** Full-suite runs fail
  roughly one test in ~1100, a *different* one each run, each passing in
  isolation. Three Godot-dependent tests are named there. This track spawns
  Godot heavily, so it inherits that exposure and must not read a single
  failure as a regression without re-running it isolated.
