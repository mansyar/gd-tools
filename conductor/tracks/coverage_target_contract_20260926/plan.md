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

> **`[checkpoint: 40903b6]`** - phase complete. User approved the checkpoint after
> reviewing the full-suite result ("Yes - checkpoint and start Phase 2"). Full
> automated and manual evidence is recorded in the git note on `40903b6`. Phase
> commits: `661e1b7` (characterization test + implementation note), `6d8697d`
> (plan SHA record).

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

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [x] Characterization tests pass
  - [x] The R3 premise is confirmed or refuted **in writing, in this file**
  - [x] Phase 2's Task 2.3 is adjusted if the premise was refuted — *not refuted;
    Task 2.3 proceeds as written*

---

## Phase 2 — Runtime contract: warn, continue, and make the instrumented set derivable

Covers spec R1, R2, R3 (seeding), and R4, in both runtimes.

> **`[checkpoint: e4770c7]`** - phase complete. Manual verification plan proposed and
> approved by the user. Full automated and manual evidence is recorded in the git
> note on `e4770c7`. Phase commits: `02724e8` (Red tests), `727877a` (the fix in both
> runtimes), `fe06562` (seeded-merge test, AC 7), `9fb0c2c` (black formatting).

### Task 2.1: Failing tests for the runtime contract (Red)

- [x] Task: Legacy runtime — write the failing tests [02724e8]
  - [x] In `tests/integration/test_coverage_hooks.py`, a plan naming a target that
    cannot be loaded produces a **completed run**, not a `GdToolsError` (spec AC 1)
  - [x] A plan naming a target that loads but fails `reload(true)` also completes (AC 1)
  - [x] The remaining targets in the same plan still report coverage (spec R2)
  - [x] Group into as few Godot spawns as constraint 3 allows — **zero new spawns.**
    The two existing tests already spawned Godot with exactly the scenarios needed, so
    they were repinned rather than duplicated
- [x] Task: Native runtime — write the failing tests [02724e8]
  - [x] Using the `tests/e2e/test_native_runtime.py:378-430` template: a plan whose
    first target fails still instruments and reports the later targets — this is the
    abort defect at `gd_tools_native_coverage.gd:34-37` and it is the sharpest
    regression to pin (spec R2, AC 2)
  - [x] The run completes with a recorded omission rather than an error status
  - [x] One spawn carries all three cases: an absent target, an instrumented-but-
    never-executed target, and a normally executed one

### Task 2.2: Implement the warn-and-continue contract (Green)

- [x] Task: Legacy runtime — `addons/gd-tools-coverage/coverage.gd` [727877a]
  - [x] R1: the per-target `_log_error` calls at `:96-100` (load failure) and
    `:108-112` (reload failure) become warning-level. `_log_error` itself is defined
    at `:278` — add a warning-level sibling rather than changing `_log_error`, so the
    fatal callers are untouched
  - [x] R1 carve-out: confirm no other `_log_error` caller changes. Missing/malformed
    plan, unwritable output dir, missing tracker, unsupported version all stay fatal —
    **proven, not assumed:** seven pre-existing GDScript tests still expect
    `push_error` for exactly these cases and all seven still pass
  - [x] `:77-83` `_instrument_files` already continues past failures — verified, not
    changed. Confirmed empirically: the legacy test passed `result.passed == 4` and
    `0 not in by_id` before failing on R3
  - [ ] Accumulate each omitted `{path, reason}` where the legacy collector can expose
    it to Python — **deferred to Phase 3 Task 3.2, deliberately.** Adding an untested
    accumulator here would be uncovered code shipped without a test, which is the same
    mistake Phase 1 was built to prevent. The reason channel and the omission list
    land together in Phase 3, where Task 3.1 pins them
- [x] Task: Native runtime — `addons/gd-tools-test/gd_tools_native_coverage.gd` [727877a]
  - [x] R2: the loop at `:34-37` continues past a failed target instead of
    `_active = false; return false`; `activate()` (`:15`) returns `true` when coverage
    was activated regardless of individual omissions
  - [x] R1: the `push_error` at `:94` and `:107` become warning-level
  - [x] R1 carve-out: the plan-version check at `:30-32` stays fatal
  - [ ] Accumulate each omitted `{path, reason}` in a static collection readable by the
    runner — **deferred to Phase 3 Task 3.2**, for the same reason as the legacy
    accumulator above. The runner's seam is already identified (it reads the
    collector at `gd_tools_test_runner.gd:551` and emits `engine_errors`/
    `engine_warnings` at `:738-739`/`:777-778`)
- [x] Task: R4 — distinct messages for a stale plan and a broken script [727877a]
  - [x] Load failure: name the path, point at regenerating the plan (`--no-cache`, or a
    run with no warm cache)
  - [x] Reload failure: name the path as a **broken script to fix**
  - [x] Correct the misleading text at `coverage.gd:111` — "Check tracker injection
    logic for syntax errors" blames gd-tools' instrumentation for what is usually a
    defect in the user's script. It must not send a user into the wrong place (spec R4)
  - [x] The two cases needed a real discriminator, not just two strings: `load()`
    returns null for both a missing file and a broken one, so `FileAccess.file_exists`
    is what separates them. Same control flow, distinct cause and fix

### Task 2.3: Seed the instrumented set (Green, conditional on Phase 1)

- [x] Task: Implement seeding in both runtimes [727877a]
  - [x] R3: every successfully instrumented file gets an entry in the coverage data
    with an **empty** `hits` object, so `files[]` denotes the instrumented set and
    "instrumented but never executed" is distinguishable from "could not instrument"
  - [x] Legacy: seed in `coverage.gd` `_instrument_files` (`:77-83`)
  - [x] Native: seed in `gd_tools_native_coverage.gd` alongside the instrumentation loop
  - [x] **Skip this task and report back if Phase 1 refuted the premise** — premise
    confirmed, so the task proceeded as written
- [x] Task: Write the test for AC 7 [02724e8, fe06562]
  - [x] An instrumented-but-never-executed file reports as 0% covered and is **not**
    reported as uninstrumented
  - [x] `test_merge_preserves_seeded_empty_hits_entries` additionally guards the
    `merge_coverage_data` ordering the Phase 1 note flagged. This is a regression
    guard on existing behavior, not a new contract

> **Implementation note — Tasks 2.2 and 2.3 (2026-09-28).**
>
> **Why R1's carve-out is proven.** Seven pre-existing tests in
> `test_coverage_instrumentation.gd` still assert `push_error` for the plan-level
> failures — `load_plan_nonexistent_file`, `load_plan_malformed_json`, and five
> `_validate_plan` cases. All seven pass unchanged, which is direct evidence that
> weakening the two per-target call sites did not weaken anything else.
>
> **R2 was the worst defect in the track.** The native abort left `_active` false, so
> `write()` bailed out and **no coverage file was written at all** — one broken script
> cost the project its entire coverage, not one file's worth. The legacy collector
> never had this defect.
>
> **A GUT finding worth recording.** GUT matches **one tracked warning per
> assertion**. An initial attempt used two `assert_push_warning` calls against the
> single `push_warning` that `_log_warning` emits; the first consumed it and the
> second failed. One assertion per call site now, with full message text asserted
> from Python in `test_hooks_nonexistent_script_in_plan`, where it already passes.
> Relatedly, `test_instrument_file_invalid_path` asserted `engine_error_count(2)`
> from `load()` opening a missing file; the existence check now runs *before*
> `load()`, so the engine is never asked and the count is 0 — the test's own message
> was describing behavior this change correctly removed.
>
> **Two deviations, both recorded rather than smoothed over.**
> 1. The omitted-target accumulators are deferred to Phase 3 (above), because an
>    untested accumulator shipped in Phase 2 would be exactly the risk Phase 1 exists
>    to prevent. Phase 3 Task 3.1 pins the omission list, so the channel lands with
>    its test.
> 2. The two `test_hooks_*` tests were repinned in Task 2.1 rather than in Phase 4
>    Task 4.3 as originally planned. Phase 2 *changes the behavior these tests
>    observe*, so they could not keep asserting the old contract until Phase 4.
>
> **A gap found and deliberately not fixed.** A plan entry with an empty `lines`
> array returns `false` with **no message** in both collectors, so it remains a
> silent skip. It is pre-existing, not a regression, and no test covers it — fixing
> it would mean adding an untested branch. Flagged for a follow-up rather than
> smuggled into this phase.


### Task 2.4: Phase Verification & Checkpoint

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [x] Both runtimes warn and continue; neither aborts the run — pinned by
    `test_native_coverage_warns_and_continues_past_uninstrumentable_target` (native
    `returncode == 0`, was `2` before) and by `test_hooks_nonexistent_script_in_plan` /
    `test_hooks_unloadable_script` (legacy, both completed)
  - [x] R1's carve-out verified: the fatal path is unchanged. End-to-end, the existing
    `test_hooks_malformed_plan_json` (`test_coverage_hooks.py:240`) still asserts
    `"Failed to parse coverage plan JSON" in combined` and passes. Seven GDScript
    tests in `test_coverage_instrumentation.gd` still expect `push_error` for
    plan-level failures and pass unchanged. *Honest limit:* none of these assert the
    literal exit code `2` on this path (every test in `test_coverage_hooks.py` passes
    `no_exit_code=True`); the `returncode > 1` mapping in `test_runner.py:492-496` is
    unchanged code exercised by other failure paths. The error is proven to fire; the
    exit code on this specific path is not separately asserted
  - [x] AC 7 and AC 8 confirmed; the coverage JSON is still `version: 1` and still
    parses in both runtimes — `read_coverage_json` accepted the seeded `{}` entries
    unchanged, `merge_coverage_data` preserved them across a two-shard merge, and no
    schema version was touched (`NATIVE_PROTOCOL_VERSION` stays 2)

> **Phase 2 verification evidence.**
>
> **Automated.** `CI=true pytest` → **1162 passed, 2 skipped in 546.74s**, 0 failed,
> 0 errors. Total coverage 96.18% (Phase 1: 96.15%); the +2 tests are exactly the two
> added here. The 80% threshold was reached.
>
> **Both skips identified and both environmental, neither related to this track:**
> `tests/performance/test_native_vs_gut_benchmark.py:121` is an opt-in benchmark
> gated on `GD_TOOLS_RUN_BENCHMARK=1`, and
> `tests/unit/test_native_artifacts.py:272` skips with
> `WinError 1314 (A required privilege is not held by the client)` because Windows
> needs Developer Mode or elevation to create a symlink. Confirmed by re-running the
> latter alone with `-rs`. No hit from the ~1-in-1100 Godot-under-load flake.
>
> **Targeted.** 154 passed across the five affected files. `gdlint` reports no
> problems on either changed `.gd` file; `ruff check src/ tests/` and
> `black --check src/ tests/` are clean.
>
> **Effect on the known-flake note.** `test_hooks_nonexistent_script_in_plan` passed
> in both the Phase 1 and Phase 2 full runs. `known_flakes.md` records it failing
> roughly 1 run in 20 with `Godot exited with code 4294967295`. The mechanism is now
> understood: the old assertions only checked that the good target was instrumented
> and the bad path appeared in output, both of which held *except* when `push_error`
> escalated the exit code — which Godot does only under load. R1 removes that
> `push_error` entirely, so the load-dependence is gone. **Consistent with, not proof
> of, elimination:** one non-failing run cannot prove a 1-in-20 flake dead. Task 4.3
> re-checks this.
>
> **Recorded deviations from the plan** (all carried in the Task 2.2 / 2.3
> implementation notes above): the two accumulators deferred to Phase 3, and the two
> `test_hooks_*` repins moved from Task 4.3 to Task 2.1.
>
> **Still open, by design:** R5 (run diagnostics, terminal report, artifact index) and
> R6 (the `--min` gate) are Phase 3. A user currently sees the omission in the
> terminal only; a CI job consuming the artifact index has no structured record of it
> yet. This phase delivers the runtime half of the contract, not the reporting half.

---

## Phase 3 — Reconciliation, reporting, and the `--min` gate

Covers spec R3 (reconciliation), R5 (terminal report), R6, and R7.

### Task 3.1: Failing tests for reconciliation and gating (Red)

- [x] Task: Reconciliation unit tests [5ca2171] — **zero Godot spawns**; pure
      unit tests over the fixture plan
  - [x] No omissions: plan set equals the instrumented set, omission list empty
  - [x] Some omitted: the uninstrumented targets are identified
  - [x] **The critical case (spec R3):** an instrumented-but-never-executed file is
    **not** an omission — this is what a naive diff gets wrong
  - [x] Every omission carries a reason and a fix hint (spec R4)
- [x] Task: `--min` gate unit tests [f19f03c]
  - [x] Percentage is computed over the **instrumented** set, not the total plan
  - [x] One uninstrumented target does not depress the percentage for measured code
  - [x] With `--min`: an omission is an error, exit 2 (spec R6, R7, AC 5)
  - [x] Without `--min`: an omission is a warning, exit code unaffected
  - [x] No omissions: `--min` behavior is unchanged from today
- [x] Task: Terminal report tests [f19f03c]
  - [x] Each omitted target is named with its reason and fix in the output (AC 3)
  - [x] Both figures are shown when they differ, and the report stays silent when
    there are no omissions

### Task 3.2: Implement the shared reconciliation helper

- [x] Task: One helper in `src/gd_tools/coverage/`, two call sites (constraint 6) [007c5f6]
  - [x] Reads the plan and the coverage data and returns the omitted `{path, reason}`
    list, distinguishing "could not instrument" from "instrumented but never run"
  - [x] Reuse the reason text the Godot side emits per R4; do not re-derive the reason
    in Python — a diff cannot know it
- [x] Task: Wire it into the two reporting seams [007c5f6]
  - [x] `coverage/orchestrator.py` — the legacy path
  - [x] `command.py` `_generate_native_report`, which already reads the plan and the
    coverage data — the native path

### Task 3.3: Implement the `--min` gate (R6, R7)

- [x] Task: Percentage over the instrumented set [007c5f6]
  - [x] Recompute or reweight the reported total so it covers only instrumented targets
  - [x] Report the instrumented count alongside the total, so the denominator is
    visible rather than implied
- [x] Task: The omission gate [007c5f6]
  - [x] `--min` requested **and** at least one omission → error, exit **2** (config
    class per R7, not test failure 1)
  - [x] `--min` not requested → prominent warning, exit code unaffected
  - [x] Emit the omitted targets in the gate's message so the failure is actionable
- [x] Task: Terminal report [007c5f6]
  - [x] Name every omitted target, its reason, and its fix (AC 3)

> **Phase 3 implementation note (Tasks 3.2 and 3.3 landed in one commit).**
>
> **Why one commit.** The gate reads the `OmissionReport` the reconciler returns, so
> splitting them would have meant either an unused intermediate import or a second
> pass over the same seam. Constraint 6 is still honoured: one helper, one report
> seam, two callers.
>
> **Both figures, per the resolved (b) decision.** The terminal prints the
> instrumented-set percentage as the headline with the plan-wide figure beside it,
> and the gate names both counts. Reporting only the instrumented-set number would
> let a project keep passing `--min 80` while its worst-covered files progressively
> fail to instrument and drop out of the denominator — the gate would report success
> over a set that shrinks precisely because the code most worth measuring stopped
> being measured.
>
> **Split authority, and why.** *Which* targets were omitted is **derived** as
> `plan.files - data.files`, because that is the definition R3 made reliable. The
> **reason** comes from the additive `omitted` key. If the two ever disagreed the
> derivation wins and a generic reason is supplied, so a broken file can never be
> reported as clean.
>
> **No new error type.** The gate reuses `CoverageThresholdError` with
> `exit_code=2`, verified to be honoured on the `test` path: `cli.py:418-439` catches
> `CoverageThresholdError` under `except GdToolsError` and exits `e.exit_code`. A
> threshold miss still exits 1, so R7 is unchanged and **no `cli.py` change was
> needed**. Deliberately *not* changed: `coverage show --min` (`cli.py:599-609`)
> catches `CoverageThresholdError` first and hard-codes exit 1. That command reads
> pre-existing coverage data and has no notion of omissions from a run, so it is out
> of scope — recorded here so a later reader does not mistake it for an oversight.
>
> **No schema bump**, per guiding constraint 2. The coverage JSON stays `version: 1`
> with an additive optional key. Verified read-compatible both directions:
> `read_coverage_json` reads only the keys it knows and silently ignores unknown
> top-level keys, so old readers parse new data, and a missing key defaults to an
> empty list.
>
> **One real bug, recorded because it is a trap.** The first wiring attempt anchored
> its `omissions` import on a line that already sat *below* the module's
> `if TYPE_CHECKING:` block, so the import landed inside it. **ruff and black both
> passed** — the names were defined, just not at runtime. It surfaced only as a
> `NameError` in 27 CLI-subprocess integration tests. For any later phase adding a
> runtime import to a module that uses `TYPE_CHECKING`: a lint-clean import is not
> necessarily a runtime import. Confirm with `hasattr(module, name)`, not just ruff.

### Task 3.4: Phase Verification & Checkpoint

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [6eab15f]
  - [x] AC 1, 2, 3, 5, 6 confirmed
  - [x] A malformed plan still fails, still exit 2 (AC 6)
  - [x] Coverage of new Python source above 80% line / 70% branch

> **`[checkpoint: 6eab15f]`** - phase complete. Full suite 1183 passed / 2 known
> skips, exit 0, total coverage 96.08%; new source all above the 80% line / 70%
> branch gates (omissions.py 98/90, orchestrator.py 95/88, reporter.py 98/97,
> command.py 93/89); ruff and black clean. Manual verification plan proposed and
> approved by the user (six steps: healthy baseline both runtimes, a
> `load()`-failing target exercising warn-and-continue + the partial block, the
> `--min` gate at exit 2, the AC 7 sanity check, and restore). First suite
> attempt failed on an environment gap only: `gd-tools.exe` was not on PATH in
> this shell (WinError 2) — fixed by adding the Python Scripts dir; no code
> defect. Verification report attached as a git note on the checkpoint commit.

---

## Phase 4 — Native plumbing, artifacts, and documentation truth

Covers spec R5 (run diagnostics and artifact index) and closes out the track's
documentation and flake obligations.

### Task 4.1: Failing tests for the two machine-readable surfaces (Red)

- [x] Task: Run diagnostics
  - [x] The native omission reaches `NativeRunResult.diagnostics` / `engine_warnings`
    **without** a protocol version bump — assert `protocol_version == 2` still (AC 9)
  - [x] The omission rides the existing channels; no new field is introduced (R5)
- [x] Task: Artifact index
  - [x] `native_test/artifacts.py:125` `publish_artifact_index` records the omitted
    targets for a machine consumer (AC 4)
  - [x] The payload at `:168` gains an **additive** key only; it has no version field
    of its own, so nothing is bumped

### Task 4.2: Implement the native plumbing

- [x] Task: Surface the native collector's omissions to the runner
  - [x] The `activate()` call site is `gd_tools_test_runner.gd:551`; the collector's
    omissions must reach the run result through the **existing** `diagnostics` and
    `engine_warnings` channels (`:738-739`, `:777-778`), not a new one
  - [x] Note that `gd_tools_test_runner.gd:729` promotes a non-empty `_engine_errors`
    to an error status. The R1 change removes these particular errors from that
    channel — **verify** that a per-target omission no longer trips `:729`, and that
    genuine engine errors still do
- [x] Task: Record in the artifact index
  - [x] Additive key on the `publish_artifact_index` payload (`:168`)
  - [x] Batched behind the existing `publish_artifact_index` call, not a second write

> **[5480625]** Implemented across both collectors and both merge paths. The
> native collector (`gd_tools_native_coverage.gd`) records each omission as a
> structured `{file_id, path, reason, fix}` entry (`_record_omission`), keeps
> the console warning, and writes the additive `omitted` key in `write()`;
> the legacy tracker does the same and `post_run_hook._build_coverage_json`
> carries the key into the legacy coverage JSON. The runner appends one
> single-line warning per omission to `_engine_warnings` (never
> `_engine_errors`, so `:729` cannot escalate a per-target omission — the
> existing `engine_errors`-escalation e2e test still passes) and writes
> `diagnostics.coverage_omissions` only when omissions exist, so clean runs
> keep the old result shape. Shard merge (`_merge_coverage_shards`) and
> `merge_coverage_data` union omissions with dedupe, so the terminal report
> keeps real reasons instead of generic fallbacks. The native orchestrator
> aggregates per-suite warnings/omissions once and passes them to
> `publish_artifact_index(omitted=...)` (both the primary and republish
> calls). **Deviation recorded:** spec R5 (corrected 2026-09-28) requires the
> `omitted` key to be written by **both** collectors, but no plan task
> assigned that writing — folded into this task rather than left to the
> generic fallback, which would have made every real run's terminal report
> show generic reasons and defeated R4/AC 3. gdlint (4.5.0) reports three
> pre-existing failures in `gd_tools_test.gd`, a file this track never
> touched; the four files this track edited are clean.

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
