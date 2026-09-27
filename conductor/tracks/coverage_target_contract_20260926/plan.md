# Implementation Plan — Coverage Target Contract: Warn and Continue

**Track ID:** `coverage_target_contract_20260926`
**Spec:** [`./spec.md`](./spec.md)
**Workflow:** [`../../workflow.md`](../../workflow.md)
**Branch:** `feature/coverage-target-contract-20260927`

## Guiding constraints for this plan

1. **Verify R3's premise before building on it.** Spec R3 chooses *seeding* — writing an
   empty hit entry for every successfully instrumented file — so that `files[]` in the
   coverage data means "the instrumented set" and a plan-vs-data diff becomes a reliable
   statement about omissions. That only works if the reporter already scores an empty
   `hits` dict and an absent data entry the same way. This is **not known** and is the
   subject of Phase 1. Do not begin Phase 2 before the Phase 1 finding is recorded here.
2. **No schema version bumps.** Per spec R5, `NATIVE_PROTOCOL_VERSION` stays `2`
   (`native_test/protocol.py:21`) and the coverage data JSON stays `version: 1`. The
   native omission rides the *existing* `NativeRunResult.diagnostics` (`:187`) and
   `engine_warnings` (`:191`) channels. **If a task below appears to require a new
   field or a version bump, that is a design signal — stop and revisit the spec, do not
   edit.** R1's carve-out exists for the same reason: a missing/malformed plan, an
   unwritable output directory, a missing autoload, and an unsupported plan version all
   stay fatal.
3. **Batch Godot spawns.** Every `.gd` change is verified through a real Godot
   subprocess, costing seconds each and adding flake surface per
   [`known_flakes.md`](./known_flakes.md). Do **not** write one test per case. Group
   assertions so each test spawns Godot **once** and checks many behaviours from one
   result payload.
4. **Follow the existing harnesses; do not build parallel ones.**
   `tests/integration/test_coverage_hooks.py` already drives the real
   `addons/gd-tools-coverage/coverage.gd` and is the home for the new contract. The
   native harness template is `tests/e2e/test_native_runtime.py:378-430` (prepare
   project → `protocol_version: 2` manifest → `GD_TOOLS_NATIVE_MANIFEST` /
   `GD_TOOLS_NATIVE_RESULT` → `godot --headless --script res://addons/gd-tools-test/gd_tools_test_runner.gd`
   → assert on result JSON). Exit codes: `0` pass, `1` test failure, `2` error.
5. **Both runtimes must agree.** Spec §1.1: this is one decision, not two. Native is the
   default runtime, so a change that lands only in the legacy path is incomplete. Every
   behavior in Phase 1 and Phase 2 is pinned in both.
6. **One reconciliation helper, two call sites.** `orchestrator.py:340`
   (`_print_coverage_inline`) and `command.py:284` (`_generate_native_report`) both need
   the plan-vs-data reconciliation, and `command.py:297-298` already reads both inputs.
   A single shared helper in the `coverage` package is justified by those two call
   sites; do not add a third abstraction, a strategy object, or a config flag.
7. **`.gd` files require tests too.** Per `workflow.md`, every source file (`.py` and
   `.gd`) needs a corresponding test. GDScript behavior is pinned from Python through
   the integration/e2e harness above — that is the established pattern for
   `coverage.gd`, and it is how these changes must be tested.

---

## Phase 1 — Establish the reporter baseline (spec R3's premise)

No production code changes in this phase. It exists because spec R3's mechanism is
conditional on reporter behavior the spec explicitly declined to assume, and Phase 2
writes GDScript against that premise. A checkpoint here is the cheapest place to catch a
wrong assumption.

Covers spec R3 (premise verification only).

### Task 1.1: Characterize how the reporter scores uninstrumented and unhit files

- [x] Task: Locate the reporter's scoring path [661e1b7]
  - [x] In `src/gd_tools/coverage/reporter.py` (519 lines), identify where per-file
    line/branch percentages are computed and what happens when a plan file has **no**
    entry in the coverage data `files[]` array
  - [x] Identify the same for a data entry whose `hits` object is **empty**
  - [x] Note whether `read_coverage_json` (`reporter.py`) tolerates an entry with no
    `hits` key at all, or whether that is a parse failure
- [x] Task: Write characterization tests pinning the current behavior
  - [x] These tests are expected to **pass** against current `main`; they document the
    baseline rather than failing. Do not force them red.
  - [x] A plan file with no data entry scores: **0 hits on every line; `line_rate` and
    `branch_rate` 0.0; all its lines in `uncovered_lines`** — already pinned by
    `test_compute_summary_missing_file_in_coverage_data`
  - [x] A data entry with an empty `hits` dict scores: **identically the same** — the
    previously untested case, now covered by
    `test_empty_hits_entry_scores_identically_to_absent_entry`
  - [x] A partially-hit file scores: unchanged from today
  - [x] Place in the existing coverage reporter unit test module; follow current
    fixture style
  - [x] *(Deviation: the plan called for three new tests. Two of the three baseline
    points were already pinned by existing tests in the target module, so one new test
    was written instead. Recorded here rather than edited into agreement, per the
    archived track's precedent.)*
- [x] Task: Record the finding as an implementation note in this `plan.md`
  - [x] State whether an empty `hits` dict and an absent data entry are scored
    identically
  - [x] **Decision gate:** if they are scored *differently*, Phase 2 Task 2.3 needs an
    explicit mapping task so seeding does not silently change reported percentages
  - [x] State explicitly whether `read_coverage_json` accepts an entry with no `hits` key

> **Implementation note — Task 1.1 (2026-09-28). R3's premise is CONFIRMED.**
>
> The scoring path is `compute_file_summary` (`reporter.py:320-374`), which
> iterates `file_plan.lines` and reads `file_data.hits.get(str(line.id), 0)`. An
> empty `hits` dict therefore yields 0 for every line.
>
> **Absent entry and empty `hits` dict score identically.** Seven call sites
> independently substitute an empty `FileCoverage` for a missing `file_id`, so
> the two cases converge before scoring: `reporter.py:398-401` (`compute_summary`,
> whose docstring at `:381` already states "Files in the plan but missing from
> coverage data are treated as 0 hits"), `reporter.py:592-595`
> (`generate_report`), `html_reporter.py:78-81`, `terminal_reporter.py:71-74`,
> `lcov_reporter.py:38-41`, `cobertura_reporter.py:45-48`, and
> `orchestrator.py:419-422`. All four output formats and the terminal report are
> covered, so seeding moves no reported number in any renderer.
>
> `read_coverage_json` **rejects** an entry with no `hits` key at all
> (`reporter.py:220-227` raises `CoveragePlanError`), but **accepts** an empty
> dict — `:229` only checks `isinstance(hits_data, dict)`. The key must be
> present; it need not be populated.
>
> **Decision gate: resolved — scored identically, so no mapping task is
> required.** Task 2.3 proceeds as written.
>
> **Two of the three baseline points were already pinned** by existing tests, so
> Task 1.1 needed one new test rather than three:
> `test_compute_summary_missing_file_in_coverage_data` (`:568`) already covers
> the absent entry, and `test_read_coverage_json_missing_hits` (`:266`) already
> covers the missing key. Note that `test_read_coverage_json_zero` (`:159`) uses
> a dict full of **zero-valued** hits, not an empty dict — no existing test
> covered `{}`. That is the new test:
> `test_empty_hits_entry_scores_identically_to_absent_entry`, which round-trips
> a seeded `{"file_id": 1, "hits": {}}` through `read_coverage_json` and asserts
> the totals equal the absent-entry baseline (`total_lines == 8`,
> `covered_lines == 5`, `line_rate == 5/8`, `total_branches == 3`,
> `covered_branches == 2`, `branch_rate == 2/3`).
>
> **Carry into Task 2.3 — do not "optimize" this away.** `merge_coverage_data`
> creates `merged_files[fid] = {}` *before* iterating hits
> (`reporter.py:274-275`), so a seeded empty entry survives the merge. This is
> load-bearing, not incidental: the native orchestrator shards coverage per suite
> and merges (`orchestrator.py::_merge_coverage_shards`), so without it the
> instrumented set would be destroyed by the merge and the Phase 3
> reconciliation would have nothing to reconcile on any multi-suite run. Its
> test belongs in Task 2.3, where the seeding that produces it exists — not
> here, where a test would pass for a reason unrelated to what it claims to
> cover.

### Task 1.2: Phase Verification & Checkpoint

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Characterization tests pass
  - [ ] The R3 premise is confirmed or refuted **in writing, in this file**
  - [ ] Phase 2's Task 2.3 is adjusted if the premise was refuted

---

## Phase 2 — Runtime contract: warn, continue, and make the instrumented set derivable

Covers spec R1, R2, R3 (seeding), and R4, in both runtimes.

### Task 2.1: Failing tests for the runtime contract (Red)

- [ ] Task: Legacy runtime — write the failing tests
  - [ ] In `tests/integration/test_coverage_hooks.py`, a plan naming a target that
    cannot be loaded produces a **completed run**, not a `GdToolsError` (spec AC 1)
  - [ ] A plan naming a target that loads but fails `reload(true)` also completes (AC 1)
  - [ ] The remaining targets in the same plan still report coverage (spec R2)
  - [ ] Group into as few Godot spawns as constraint 3 allows
- [ ] Task: Native runtime — write the failing tests
  - [ ] Using the `tests/e2e/test_native_runtime.py:378-430` template: a plan whose
    first target fails still instruments and reports the later targets — this is the
    abort defect at `gd_tools_native_coverage.gd:34-37` and it is the sharpest
    regression to pin (spec R2, AC 2)
  - [ ] The run completes with a recorded omission rather than an error status

### Task 2.2: Implement the warn-and-continue contract (Green)

- [ ] Task: Legacy runtime — `addons/gd-tools-coverage/coverage.gd`
  - [ ] R1: the per-target `_log_error` calls at `:96-100` (load failure) and
    `:108-112` (reload failure) become warning-level. `_log_error` itself is defined
    at `:278` — add a warning-level sibling rather than changing `_log_error`, so the
    fatal callers are untouched
  - [ ] R1 carve-out: confirm no other `_log_error` caller changes. Missing/malformed
    plan, unwritable output dir, missing tracker, unsupported version all stay fatal
  - [ ] `:77-83` `_instrument_files` already continues past failures — verify, do not
    change
  - [ ] Accumulate each omitted `{path, reason}` where the legacy collector can expose
    it to Python
- [ ] Task: Native runtime — `addons/gd-tools-test/gd_tools_native_coverage.gd`
  - [ ] R2: the loop at `:34-37` continues past a failed target instead of
    `_active = false; return false`; `activate()` (`:15`) returns `true` when coverage
    was activated regardless of individual omissions
  - [ ] R1: the `push_error` at `:94` and `:107` become warning-level
  - [ ] R1 carve-out: the plan-version check at `:30-32` stays fatal
  - [ ] Accumulate each omitted `{path, reason}` in a static collection readable by the
    runner
- [ ] Task: R4 — distinct messages for a stale plan and a broken script
  - [ ] Load failure: name the path, point at regenerating the plan (`--no-cache`, or a
    run with no warm cache)
  - [ ] Reload failure: name the path as a **broken script to fix**
  - [ ] Correct the misleading text at `coverage.gd:111` — "Check tracker injection
    logic for syntax errors" blames gd-tools' instrumentation for what is usually a
    defect in the user's script. It must not send a user into the wrong place (spec R4)

### Task 2.3: Seed the instrumented set (Green, conditional on Phase 1)

- [ ] Task: Implement seeding in both runtimes
  - [ ] R3: every successfully instrumented file gets an entry in the coverage data
    with an **empty** `hits` object, so `files[]` denotes the instrumented set and
    "instrumented but never executed" is distinguishable from "could not instrument"
  - [ ] Legacy: seed in `coverage.gd` `_instrument_files` (`:77-83`)
  - [ ] Native: seed in `gd_tools_native_coverage.gd` alongside the instrumentation loop
  - [ ] **Skip this task and report back if Phase 1 refuted the premise.** Seeding
    without a confirmed scoring baseline risks silently changing reported percentages
- [ ] Task: Write the test for AC 7
  - [ ] An instrumented-but-never-executed file reports as 0% covered and is **not**
    reported as uninstrumented

### Task 2.4: Phase Verification & Checkpoint

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Both runtimes warn and continue; neither aborts the run
  - [ ] R1's carve-out verified: a malformed plan still fails with exit 2
  - [ ] AC 7 and AC 8 confirmed; the coverage JSON is still `version: 1` and still
    parses in both runtimes

---

## Phase 3 — Reconciliation, reporting, and the `--min` gate

Covers spec R3 (reconciliation), R5 (terminal report), R6, and R7.

### Task 3.1: Failing tests for reconciliation and gating (Red)

- [ ] Task: Reconciliation unit tests
  - [ ] No omissions: plan set equals the instrumented set, omission list empty
  - [ ] Some omitted: the uninstrumented targets are identified
  - [ ] **The critical case (spec R3):** an instrumented-but-never-executed file is
    **not** an omission — this is what a naive diff gets wrong
  - [ ] Every omission carries a reason and a fix hint (spec R4)
- [ ] Task: `--min` gate unit tests
  - [ ] Percentage is computed over the **instrumented** set, not the total plan
  - [ ] One uninstrumented target does not depress the percentage for measured code
  - [ ] With `--min`: an omission is an error, exit 2 (spec R6, R7, AC 5)
  - [ ] Without `--min`: an omission is a warning, exit code unaffected
  - [ ] No omissions: `--min` behavior is unchanged from today
- [ ] Task: Terminal report tests
  - [ ] Each omitted target is named with its reason and fix in the output (AC 3)

### Task 3.2: Implement the shared reconciliation helper

- [ ] Task: One helper in `src/gd_tools/coverage/`, two call sites (constraint 6)
  - [ ] Reads the plan and the coverage data and returns the omitted `{path, reason}`
    list, distinguishing "could not instrument" from "instrumented but never run"
  - [ ] Reuse the reason text the Godot side emits per R4; do not re-derive the reason
    in Python — a diff cannot know it
- [ ] Task: Wire it into the two reporting seams
  - [ ] `coverage/orchestrator.py:340` `_print_coverage_inline` (call sites `:147`,
    `:162`) — the legacy path
  - [ ] `command.py:284` `_generate_native_report`, which already reads the plan at
    `:297` and the coverage data at `:298` — the native path

### Task 3.3: Implement the `--min` gate (R6, R7)

- [ ] Task: Percentage over the instrumented set
  - [ ] Recompute or reweight the reported total so it covers only instrumented targets
  - [ ] Report the instrumented count alongside the total, so the denominator is
    visible rather than implied
- [ ] Task: The omission gate
  - [ ] `--min` requested **and** at least one omission → error, exit **2** (config
    class per R7, not test failure 1)
  - [ ] `--min` not requested → prominent warning, exit code unaffected
  - [ ] Emit the omitted targets in the gate's message so the failure is actionable
- [ ] Task: Terminal report
  - [ ] Name every omitted target, its reason, and its fix (AC 3)

### Task 3.4: Phase Verification & Checkpoint

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] AC 1, 2, 3, 5, 6 confirmed
  - [ ] A malformed plan still fails, still exit 2 (AC 6)
  - [ ] Coverage of new Python source above 80% line / 70% branch

---

## Phase 4 — Native plumbing, artifacts, and documentation truth

Covers spec R5 (run diagnostics and artifact index) and closes out the track's
documentation and flake obligations.

### Task 4.1: Failing tests for the two machine-readable surfaces (Red)

- [ ] Task: Run diagnostics
  - [ ] The native omission reaches `NativeRunResult.diagnostics` / `engine_warnings`
    **without** a protocol version bump — assert `protocol_version == 2` still (AC 9)
  - [ ] The omission rides the existing channels; no new field is introduced (R5)
- [ ] Task: Artifact index
  - [ ] `native_test/artifacts.py:125` `publish_artifact_index` records the omitted
    targets for a machine consumer (AC 4)
  - [ ] The payload at `:168` gains an **additive** key only; it has no version field
    of its own, so nothing is bumped

### Task 4.2: Implement the native plumbing

- [ ] Task: Surface the native collector's omissions to the runner
  - [ ] The `activate()` call site is `gd_tools_test_runner.gd:551`; the collector's
    omissions must reach the run result through the **existing** `diagnostics` and
    `engine_warnings` channels (`:738-739`, `:777-778`), not a new one
  - [ ] Note that `gd_tools_test_runner.gd:729` promotes a non-empty `_engine_errors`
    to an error status. The R1 change removes these particular errors from that
    channel — **verify** that a per-target omission no longer trips `:729`, and that
    genuine engine errors still do
- [ ] Task: Record in the artifact index
  - [ ] Additive key on the `publish_artifact_index` payload (`:168`)
  - [ ] Batched behind the existing `publish_artifact_index` call, not a second write

### Task 4.3: Update the contract test and the known-flakes note

- [ ] Task: Repin the existing contract test
  - [ ] `tests/integration/test_coverage_hooks.py::test_hooks_nonexistent_script_in_plan`
    currently depends on the run **failing**. Update it to the new contract (AC 10)
- [ ] Task: Verify the Vector-A flake is actually gone
  - [ ] `known_flakes.md` attributes this test's ~1-in-5 failure to **Vector A** —
    Godot's `push_error` exit-code escalation being timing-sensitive. R1 removes that
    `push_error` from this path, so the flake should disappear as a side effect
  - [ ] **Verify, do not assume.** Run the full suite and confirm
  - [ ] If the flake persists, Vector A has another source: record that in
    `known_flakes.md` rather than leaving the note's recommendation to quarantine a
    test that should now be deterministic
  - [ ] The other two tests named in `known_flakes.md` are unrelated to coverage
    instrumentation and are **out of scope**
- [ ] Task: Update the documentation
  - [ ] `docs/ARCHITECTURE.md` — the coverage contract and the instrumentation failure
    path
  - [ ] `docs/USER_GUIDE.md` — if it documents the old fail-on-uninstrumentable behavior
  - [ ] `docs/ROADMAP.md` — only if this work is tracked there
  - [ ] This track's own [`known_flakes.md`](./known_flakes.md), per the task above

### Task 4.4: Phase Verification & Checkpoint

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] AC 4, 8, 9, 10 confirmed
  - [ ] `NATIVE_PROTOCOL_VERSION` is still `2`; the coverage JSON is still `version: 1`
  - [ ] Full suite run, with the flake outcome reported
  - [ ] `ruff check src/ tests/` and `black --check src/ tests/` clean

---

## Acceptance criteria traceability

| Spec AC | Phase | Task |
| --- | --- | --- |
| 1 — run completes, remaining targets report | 2 | 2.1, 2.2 |
| 2 — both runtimes agree | 2 | 2.1, 2.2 |
| 3 — terminal names each omission + reason + fix | 3 | 3.1, 3.3 |
| 4 — artifact index records omissions | 4 | 4.1, 4.2 |
| 5 — `--min` on the instrumented set + own gate | 3 | 3.1, 3.3 |
| 6 — bad plan still fails, exit 2 | 3 | 3.4 |
| 7 — unhit ≠ uninstrumented | 2 | 2.3 |
| 8 — coverage JSON still `version: 1` | 2 | 2.4, 4.4 |
| 9 — protocol still `2` | 4 | 4.1, 4.4 |
| 10 — hooks test deterministic | 4 | 4.3 |

## Requirements traceability

| Spec | Phase | Tasks |
| --- | --- | --- |
| R1 — warn, do not escalate | 2 | 2.2 |
| R2 — native instruments the rest | 2 | 2.1, 2.2 |
| R3 — derivable instrumented set | 1, 2, 3 | 1.1, 2.3, 3.2 |
| R4 — distinct messages | 2 | 2.2 |
| R5 — all three surfaces | 3, 4 | 3.3, 4.1, 4.2 |
| R6 — `--min` hybrid + exit rule | 3 | 3.1, 3.3 |
| R7 — exit-code contract unchanged | 3 | 3.3, 3.4 |

## Out of scope

Per spec §6, and not to be pulled into any task above: coverage exclusion annotations
(`# gd-tools: no cover`, roadmap Track 30); repairing the broken script this track
reports on; changing plan generation; the GUT compatibility bridge (migration roadmap
Phase 3); parallel suite execution (Phase 5).
