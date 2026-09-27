# Coverage Target Contract: Warn and Continue

**Track ID:** `coverage_target_contract_20260926`
**Type:** Feature
**Status:** Draft — approved for planning
**Origin:** Found during the Conductor review of `native_scene_integration_20260925` (see the review remediation commit `c00d048` git note). Decision taken 2026-09-27 after the four open questions in the previous draft were resolved by the project owner.

## 1. Problem

A coverage target that cannot be instrumented produces two contradictory
signals, and neither is documented: the code returns a skip, and then
escalates a process-fatal error.

### 1.1 The contradiction

`src/gd_tools/addons/gd-tools-coverage/coverage.gd:94-101`:

```gdscript
var script = load(path) as GDScript
if script == null:
    _log_error(                      # coverage.gd:278 -> push_error()
        "Failed to instrument script.",
        "Cannot load script: " + path,
        "Verify the path in the plan exists and compiles."
    )
    return false                     # the function skips
```

`push_error` escalates, so Godot exits non-zero, and
`src/gd_tools/test_runner.py:492-496` turns any `returncode > 1` into a hard
failure. The net behavior is that **the whole test run fails with exit 2**,
while the `return false` and the "Verify the path..." text both imply a
graceful skip. The reload failure at `coverage.gd:106-115` has the same shape.

The native runtime is identical in structure:
`src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd:92-95` loads,
`push_error`s, and returns `false`; `:103-108` does the same when
`script.reload(true)` fails. The native runner captures the resulting engine
error (`gd_tools_test_runner.gd:673-697`) into `_engine_errors`, and
`:729` promotes a non-empty `_engine_errors` to an error status — also exit 2.

**This is one decision, not two.** Fixing only the legacy path would leave the
runtimes inconsistent, and native is now the default.

### 1.2 The native path is worse than "one file is skipped"

`gd_tools_native_coverage.gd:34-37`:

```gdscript
for file_data in parsed.get("files", []):
    if not _instrument_file(file_data):
        _active = false
        return false
```

The native collector **aborts on the first failure**, discarding the targets it
has already instrumented. One uncompilable script therefore costs the project
*all* coverage, not one file's worth. The legacy collector does not have this
defect: `coverage.gd:77-83` counts successes and continues past failures — the
only thing making either path fatal is the `push_error`.

This asymmetry is itself a bug and is in scope. Skipping one target must not
cost the coverage of every other target.

### 1.3 The trigger is narrow, and the important case is a real defect

Verified while reviewing, so the trigger is narrower than it first appears:

- `src/gd_tools/coverage/plan_generator.py:498-501` computes
  `added`/`deleted` from the cached and current file sets and forces plan
  regeneration, so **deleting a file does invalidate the plan cache**.
- `generate_plan` enumerates its targets with `discover_gd_files`
  (`plan_generator.py:363`), a filesystem walk, so **a plan cannot name a
  file that does not exist** — by construction of the enumeration, not by any
  validation step. (The previous draft of this spec cited
  `plan_generator.py:138` for this; that line is the `read_plan_json`
  docstring describing a missing *plan* file, and the claim needed correcting.)

The realistic triggers are therefore:

1. A file deleted in the window between plan generation and the run.
2. `load()` failing for a reason other than "not found" — a real parse error, a
   cyclic dependency, or an engine-version-specific script feature.

Case 2 is the important one: a file that exists but does not compile is a real
defect. Skipping it *silently* would make coverage under-report while looking
complete, which is the more dangerous failure mode because it survives review.
That is why the decision is warn-and-continue-with-evidence rather than a plain
skip.

## 2. Resolved decisions

The previous draft posed four questions. All are now resolved, and the
resolution is binding on the plan.

| # | Question | Decision |
| --- | --- | --- |
| 1 | Fail, skip, or warn? | **Warn and continue.** Matches what pytest-cov effectively does. |
| 2 | `--min` against total plan or instrumented set? | **Hybrid** — percentage against the instrumented set, plus a separate gate so an omission cannot be silently ignored. |
| 3 | Nonexistent vs uncompilable? | **Same control flow, distinct messages.** |
| 4 | Which recording surfaces? | **All three** — run diagnostics, terminal report, artifact index. |

### 2.1 Why "all three" and not fewer

The terminal report is read by a human watching a run. The artifact index is
read by a CI job, a later `doctor` invocation, or any machine consumer — and it
is the only surface that outlives the process. Recording only in the terminal
means the evidence disappears the moment the command exits, which is precisely
the "keeps looking complete" failure mode R1 exists to prevent.

### 2.2 Why distinct messages under one control flow

A nonexistent path indicates a **stale plan**; an uncompilable file indicates a
**broken script**. They call for different user actions — regenerate the plan
versus fix the code. Two exit paths would also mean two things to test and keep
failing; one exit path with two message shapes is honest and cheap. The reason
string is the part that cannot be derived mechanically, so it is the part the
Godot side must supply (see R3).

## 3. Requirements

### R1 — An uninstrumentable target warns; it does not escalate

`_log_error` (`coverage.gd:278-281`) and the `push_error` calls at
`gd_tools_native_coverage.gd:94` and `:107` become warning-level for the
*per-target* failures only. The run continues and exits as it would have if the
target had compiled.

This makes the existing `return false` honest. No other `_log_error` call
changes: a missing or malformed **plan**, an unreadable **output directory**, a
missing **tracker autoload**, and an unsupported plan **version** remain errors.
Widening those would be a behavior change this track does not authorize, and
each indicates a broken installation rather than one bad file.

### R2 — The native collector instruments the remaining targets

`gd_tools_native_coverage.gd:34-37` continues past a failed target instead of
returning early, and `activate()` returns `true` when coverage was activated
regardless of individual omissions. A run in which one target is skipped must
report coverage for every other target — this is the defect in §1.2.

### R3 — The instrumented set must be derivable, and omissions must be reasoned

This is the load-bearing design constraint, and it is subtler than it looks.

**A plan-vs-coverage-data diff is not sufficient on its own.** `coverage.gd:47`
records a file into `_hits` only once something in it is *hit*, so a file that
was successfully instrumented but never executed is **absent from the `files[]`
array** in the coverage JSON — exactly like a file that failed to instrument. A
naive diff would conflate *"could not instrument"* with *"instrumented but never
run"*, which are the two cases this track exists to tell apart.

The fix is to **seed an empty hit entry for every successfully instrumented
file**. `files[]` then denotes the instrumented set — entries with an empty
`hits` object mean "instrumented, never executed" — and a plan-vs-data diff
becomes a reliable statement about omissions. The reason (nonexistent vs
uncompilable) is still supplied by the Godot side, because a diff cannot derive
it.

**Consequence to verify, not assume:** the reporter's treatment of an empty
`hits` dictionary, and of a plan file that has no data entry at all, must be
checked before this is implemented. If the reporter already scores both as
0%-covered, the change is additive. If it scores them differently, that is a
reporting change in its own right and belongs in the plan as its own task.

### R4 — A stale plan and a broken script get different messages

The two per-target failures emit distinguishable text:

- **Target not loadable at all** — a stale plan or a deleted file. Names the
  path and points at regenerating the plan (`--no-cache`, or re-running without
  a warm cache).
- **Target loads but will not reload after instrumentation** — a broken script.
  Names the path as a real defect to fix.

Rationale: `coverage.gd:109-111` currently reports a reload failure as
"Check tracker injection logic for syntax errors," which blames gd-tools'
instrumentation for what is usually a defect in the user's script. The message
must not send a user into the wrong place.

### R5 — The omission is recorded in all three surfaces

- **Run diagnostics.** For native, the runner already carries
  `NativeRunResult.diagnostics` (`native_test/protocol.py:187`) and
  `engine_warnings` (`:191`), and `gd_tools_test_runner.gd:738-739` populates
  them. The omission rides those existing channels, so **no protocol version
  bump is required** — `NATIVE_PROTOCOL_VERSION` stays `2`.
- **Terminal report.** `coverage/orchestrator.py::_print_coverage_inline`
  prints the omission alongside the summary, with the reason and the fix hint.
- **Artifact index.** `native_test/artifacts.py:168-176` writes a plain payload
  dict with no version field of its own, so an additive `coverage` key is safe.

**The coverage data JSON stays at `version: 1`.** Its job is `{file_id, hits}`
— hit counts — and R3 makes the instrumented set derivable without adding a
field. Bumping it would be a breaking change to a documented contract for no
reporting benefit.

**One correction to the above, resolved 2026-09-28 during Phase 3
planning.** R3 makes the *identity* of an omission derivable, but not its
**reason** — and the reason is the whole point. A stale plan and a broken
script are different bugs with different fixes, and a plan-vs-data diff
cannot distinguish them. The reason exists only in the collector, where the
`FileAccess.file_exists` discriminator ran. So the coverage data JSON gains
an **additive, optional `omitted` key**: a list of
`{file_id, path, reason, fix}` entries, written by both collectors.

This is additive evolution, not a format change, and the version stays `1`
honestly because nothing that was valid before became invalid:

- `read_coverage_json` reads only the keys it knows (`version`, `files`, and
  per-entry `file_id`/`hits`) and **silently ignores unknown top-level
  keys** (verified `reporter.py:167-200`). So a reader that predates this
  change parses new data unchanged, and a newer reader parses old data that
  lacks the key by defaulting to an empty list.
- No collector's `write()` signature changes, no new artifact is created, and
  nothing new needs discovering, pruning or cleaning up — which is what a
  sidecar file would have cost.
- A format gaining a *required* field would need a bump. A format gaining an
  *optional* field that old readers ignore is the standard additive path.

The key is authoritative for **reasons only**. Which targets were omitted
is still derived from `plan.files - data.files`, because that is the
definition that R3 made reliable; `omitted` supplies the explanation, and
the reconciler falls back to a generic reason if a target is missing from
the data yet absent from `omitted`, so the two can never silently disagree
about *what* happened.

`docs/ARCHITECTURE.md` §4.2 documents the coverage format and must be
updated in Phase 4.

### R6 — `--min` measures the instrumented set, and omissions get their own gate

Two separate conditions, deliberately not collapsed into one number:

1. **The percentage** is computed over the instrumented set. One broken
   unrelated script must not depress the figure for code that was measured
   perfectly well.
2. **The omission itself** is surfaced as a distinct, named condition so that
   lowering `--min` cannot silently stop protecting the project once targets
   start going uninstrumented.

**The omission's effect on the exit code:**

- **`--min` was requested** → the omission is an **error** (exit 2, per R7). The
  user opted into a coverage gate, and a gate that reports success over a
  knowingly incomplete measurement is not a gate.
- **`--min` was not requested** → the omission is a **prominent warning**, and
  the run's exit code is unaffected. A plain `gd-tools test --coverage` must not
  fail because of an unrelated broken script.

This keeps the two surfaces from fighting: the number stays trustworthy, and
the incompleteness is never silent. Resolved 2026-09-27; the plan should treat
it as binding, not reopen it.

**Both figures are reported, not just the instrumented-set one.** Resolved
2026-09-28, during Phase 3 planning. Reporting only the instrumented-set
percentage has a specific failure mode: the denominator is chosen by which
files happened to load, so a project can keep passing `--min 80` while its
worst-covered files progressively fail to instrument and drop out of the
measurement. The gate would report success over a set that is shrinking
because the code most worth measuring is exactly the code that stopped
being measured. So the terminal report shows the instrumented-set figure as
the headline **and** the plan-wide figure beside it, and the gate states both.
The headline answers "how well is the code we measured covered"; the
plan-wide figure answers "how much of the project did we actually manage to
look at". Resolved 2026-09-28; binding.

### R7 — The exit-code contract is unchanged

`product.md` fixes the contract: 0 pass, 1 test failure, 2 config or
environment error. An omission under R6 is a config-class condition (exit 2),
not a test failure. Runs without `--min` that would otherwise pass continue to
exit 0, with the warning visible.

## 4. Acceptance criteria

1. A plan naming a target that cannot be loaded produces a **completed run**,
   not a `GdToolsError`, and the remaining targets still report coverage.
2. The same holds for the legacy GUT path — the two runtimes agree.
3. The terminal report names each omitted target, its reason, and the fix.
4. The artifact index records the omitted targets for a machine consumer.
5. `--min N` evaluates against the instrumented set, and an omission is
   reported as its own condition rather than folded into the percentage.
6. A plan that is missing, malformed, or an unsupported version still fails,
   and still exits 2.
7. An instrumented-but-never-executed file is reported as 0% covered and is
   **not** reported as uninstrumented.
8. The coverage data JSON is still `version: 1` and still parses in both
   runtimes.
9. `NATIVE_PROTOCOL_VERSION` remains `2`.
10. `tests/integration/test_coverage_hooks.py::test_hooks_nonexistent_script_in_plan`
    is updated to the new contract and becomes deterministic — see §5.

## 5. Expected effect on the known-flake note

`known_flakes.md` records that
`test_hooks_nonexistent_script_in_plan` fails roughly one run in five under CPU
load, and attributes it to **Vector A** — Godot's process-level `push_error`
escalation being timing-sensitive. The run-3 transcript in that note is
verbatim this track's code path:

```
Godot exited with code 4294967295: ERROR: Attempt to open script
'res://scripts/nonexistent.gd' resulted in error 'File not found'.
  at: push_error (core/variant/variant_utility.cpp:1023)
  [0] _log_error (res://addons/gd-tools-coverage/coverage.gd:279)
```

R1 removes the `push_error` from this path, so **the escalation — and with it
Vector A for this test — should disappear as a side effect of the fix**. The
test's expectation changes from "the run fails" to "the run completes with a
recorded omission," which is no longer sensitive to how Godot escalates.

The plan should verify this rather than assume it, and should report the flake
outcome when the track is reviewed. If the flake persists, Vector A has another
source and `known_flakes.md` should say so. Note that the other two tests named
in that note are unrelated to coverage instrumentation and are out of scope.

## 6. Out of scope

- **Coverage exclusion annotations** (`# gd-tools: no cover`). Roadmap Track 30.
  A user who wants to exclude a deliberately-uninstrumentable file needs that
  feature, not this one; this track only makes the omission visible and
  non-fatal.
- **Repairing the broken script.** This track reports the defect; it does not
  fix or suppress it.
- **Changing plan generation.** A nonexistent path is still possible in the
  generation-to-run window described in §1.3.
- **The GUT compatibility bridge.** Migration roadmap Phase 3. Changing the
  legacy path's error behavior is a behavior change to the deprecated runtime,
  which is why this track is separate from the native work.
- **Parallel suite execution.** Migration roadmap Phase 5.

## 7. Notes for the implementer

- `coverage/orchestrator.py:340` (`_print_coverage_inline`) and
  `native_test/command.py:284` (`_generate_native_report`) are the two Python
  reporting seams. `_generate_native_report` already reads both the plan
  (`:297`) and the coverage data (`:298`), which is where the R3 reconciliation
  belongs.
- `gd_tools_test_runner.gd:551` is the native `activate()` call site; the
  collector's omissions must reach the run result through the existing
  `diagnostics` / `engine_warnings` channels, not a new one.
- `tests/integration/test_coverage_hooks.py` is the natural home for the new
  contract, and the fixtures it already builds are sufficient. Add
  unit-level coverage for the reconciliation in Python and the seeding in
  GDScript.
- Per `workflow.md`, write failing tests before implementing, and keep new
  source above 80% line / 70% branch coverage.
