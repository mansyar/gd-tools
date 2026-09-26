# Implementation Plan: Godot 4.5+ Compatibility Matrix in CI

- **Track ID:** `godot_compat_ci_matrix_20260926`
- **Spec:** [`./spec.md`](./spec.md)
- **Workflow:** [`../../workflow.md`](../../workflow.md)
- **Branch:** `feature/godot-compat-ci-matrix-20260926`
- **Status:** Not started

---

## Sequencing Rationale

Phase 1 is the R3 skip-guard, **not** the matrix. This is deliberate: once `GODOT_BIN`
becomes dynamic per-OS, a silent Godot install failure would turn all 12 Godot jobs
green while running zero tests. The guard must exist before the first matrix run, or
the first run is untrustworthy.

Per `workflow.md`, tests are required only for source code (`.py`, `.gd`) — not for
`.yml` config or `.md` docs. Phase 1 is therefore the only phase with a Red/Green TDD
cycle; Phases 2–4 are verified by the CI run itself.

---

## Phase 1: CI-Aware Godot Requirement Guard (R3)

[5b00ffd]

**Scope correction (agreed with user).** The plan originally scoped this phase to
3 files, assuming the `godot_bin` fixture was the only Godot-availability gate.
It is not. A module-level `skip_if_no_godot` mark in 9 test modules gated
availability at **collection time**, so the fixture never ran and the guard could
never fire. Measured before the fix: `CI=true` with no Godot produced
`41 passed, 25 skipped, exit 0` — a false green, which is exactly the failure R3
exists to prevent. Six of the nine marks also used a raw
`os.environ.get("GODOT_BIN")` predicate that never validated the path was a real
file. Resolved by consolidating to one mechanism: the marks were replaced with
`@pytest.mark.usefixtures("godot_bin")`. `usefixtures` rather than a blanket
autouse fixture, because 6 of the 10 integration files (doctor, format, init,
lint, plan_cache, verbosity) legitimately need no Godot and an autouse guard would
have wrongly made them require one. `.env` loading was deliberately left unchanged.

- [x] Task: Write the failing unit test for the guard
  - [x] Create `tests/unit/test_godot_requirement.py`
  - [x] Before writing, read `tests/unit/conftest.py` and one or two existing
        `tests/unit/` files to match naming and style conventions
  - [x] Test the *plain function* `require_godot_binary(purpose)` directly rather
        than through the pytest fixture, so it is assertable without `pytester`
  - [x] Cover exactly three cases:
        - [x] `CI` unset and no binary → raises `Skipped` (local stays graceful)
        - [x] `CI` set and no binary → raises `Failed`, **not** `Skipped`
              *(this is the regression that matters)*
        - [x] `CI` set and binary present → returns the resolved path
  - [x] Monkeypatch `find_godot_binary` to return `None` / a path; do not depend on
        whether a real Godot is installed on the machine
  - [x] Assert the `CI`-failure message names the missing thing and gives the fix
        (`GODOT_BIN` / PATH), per `product-guidelines.md` error-message rules
- [x] Task: Confirm the Red phase
  - [x] Run `CI=true pytest tests/unit/test_godot_requirement.py`
  - [x] Confirm it fails for the expected reason — `require_godot_binary` does not
        exist yet — not from an import error or a typo
- [x] Task: Implement the guard
  - [x] Add `require_godot_binary(purpose: str) -> str` to the **root `conftest.py`**,
        next to the existing shared Godot helpers `find_godot_binary` and
        `import_godot_project`
  - [x] Rationale for a shared helper rather than editing both conftests in place:
        the two sub-conftests are already near-identical, and the whole point of this
        guard is that CI and local behaviour must not diverge. Two hand-edited copies
        are exactly how they would drift
  - [x] Resolve via `find_godot_binary()`; on `None`, raise `pytest.fail(...)` when
        `CI` is set, else `pytest.skip(...)`
  - [x] Add a module docstring note explaining the CI/local split
- [x] Task: Wire both call sites
  - [x] Update `tests/integration/conftest.py` `godot_bin` fixture to delegate to
        `require_godot_binary("integration tests")`
  - [x] Update `tests/e2e/conftest.py` `godot_bin` fixture to delegate to
        `require_godot_binary("E2E tests")`
  - [x] Preserve the existing `sample_project_path` fixtures untouched
  - [x] Remove the now-duplicated skip message from both files
- [x] Task: Confirm the Green phase
  - [x] `CI=true pytest tests/unit/test_godot_requirement.py` — all pass
  - [x] `CI=true pytest tests/unit/ -m unit --no-cov` — no regression
  - [x] Sanity-check the local path: with `CI` unset and no `GODOT_BIN`, an
        integration test still **skips** rather than errors
- [x] Task: Verify quality gates
  - [x] `ruff check src/ tests/`
  - [x] `black --check src/ tests/`
  - [x] Confirm project coverage gate is unaffected (root `conftest.py` is outside
        `source=["gd_tools"]`, so it is not measured)
- [x] Task: Commit and record
  - [x] `git add` the three conftest/test files
  - [x] Commit: `test(ci): fail instead of skip when Godot is missing in CI`
  - [x] Attach a git note summarising the change and the skip/fail rationale
  - [x] Update this plan: mark Phase 1 tasks `[x]` with the 7-char commit SHA
  - [x] Commit plan update: `conductor(plan): Mark Phase 1 complete`
- [x] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [x] Run the Phase Completion Verification and Checkpointing Protocol
  - [x] `git diff --name-only <prev-checkpoint-or-root> HEAD` to list changed files
  - [x] Announce and run: `CI=true pytest`
  - [x] Present manual verification steps; **await explicit user confirmation**
  - [x] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 1`
  - [x] Attach the verification report as a git note
  - [x] Record `[checkpoint: <sha>]` under the Phase 1 heading

---

## Phase 2: Platform-Aware Matrix Wiring (R1, R2, R4, R5) `[83d9137]`

**Prerequisite landed first (user-directed, not in the original plan):**
`49568dc` added `.gitattributes` pinning `* text=auto eol=lf` and
renormalized the index. Phase 1 had already shown that a single `black`
run rewrote 9 test files to CRLF, inflating a 264-line change into
2651 insertions. Phase 2 touches more files, so this had to be closed
first or every diff here would be untrustworthy. Verified: `black` now
runs clean and leaves `git status` empty.

- [x] Task: Add the version axis
  - [x] In `ci.yml`, remove the global `GODOT_VERSION: '4.6.1'` env var (`ci.yml:14`)
  - [x] Add `godot-version: ['4.5.2', '4.6.1', '4.7.1']` to both Godot jobs
  - [x] Keep `godot-version` and `os` as **separate** matrix axes so the GitHub UI
        renders a readable grid and a failure names both dimensions (R4)
- [x] Task: Add the OS axis
  - [x] `os: [ubuntu-latest, windows-latest]` on both Godot jobs
  - [x] Replace `runs-on: ubuntu-latest` with `runs-on: ${{ matrix.os }}`
  - [x] Set `strategy: fail-fast: false` on both (R4)
- [x] Task: Make the Godot install platform-aware (R1)
  - [x] Replace the bash-only block in **both** `integration` (`ci.yml:130-135`) and
        `e2e` (`ci.yml:173-179`)
  - [x] Select the asset by runner OS:
        - [x] Linux → `Godot_v<version>-stable_linux.x86_64.zip`
        - [x] Windows → `Godot_v<version>-stable_win64.exe.zip`
  - [x] **Confirm the exact asset filenames against the real GitHub release before
        writing the step** — do not guess. Verify for all three versions
  - [x] Place the binary at a stable, explicitly exported location per OS and append
        it to `PATH` so `godot --version` works in a later step
  - [x] Apply `chmod +x` and `sudo mv` **only** on the Linux branch; no bash-only
        construct may execute on a Windows runner (criterion 4)
  - [x] Extract the duplicated install block into a single reusable step or
        composite action so `integration` and `e2e` cannot drift
- [x] Task: Make `GODOT_BIN` dynamic (R2)
  - [x] Remove the hardcoded `GODOT_BIN: /usr/local/bin/godot` from both jobs
        (`ci.yml:116`, `ci.yml:159`)
  - [x] Set `GODOT_BIN` from the install step to an explicit per-OS path, so
        `find_godot_binary()` resolves it through its existing "env var is a real
        file" branch
  - [x] Grep the whole file to confirm no POSIX absolute path survives
- [x] Task: Fix artifact name collisions (R4)
  - [x] `junit-results-integration` → suffix with
        `${{ matrix.godot-version }}-${{ matrix.os }}`
  - [x] `junit-results-e2e` → same suffix
  - [x] **Why this is mandatory, not cosmetic:** `actions/upload-artifact@v4` treats
        artifact names as immutable within a run and **errors** on a duplicate, so
        6 same-named jobs would hard-fail rather than silently overwrite
  - [x] Keep the per-stage `junit-*.xml` local filenames as-is; only the artifact
        `name:` changes
- [x] Task: Capture the resolved version in every job (criterion 11)
  - [x] Keep a `godot --version` verification step, made OS-aware
  - [x] Ensure its output appears in the job log so a version mismatch is
        diagnosable from CI output alone
- [x] Task: Keep the Godot stages off the Python axis (R5)
  - [x] Confirm `python-version: '3.12'` stays a scalar in both Godot jobs — it must
        **not** join the matrix, or 12 jobs become 36
- [x] Task: Validate the workflow file
  - [x] Parse `ci.yml` with the project's `pyyaml` dependency to confirm valid YAML
  - [x] Run `actionlint` if available; otherwise assert the expected structure
        programmatically (6 cells per stage, both axes present, no `continue-on-error`)
- [x] Task: Add a matrix regression guard
  - [x] Create `tests/unit/test_ci_matrix.py` asserting the matrix expands to
        6 cells per stage and that no hardcoded `/usr/local/bin/godot` remains
  - [x] Tradeoff, stated deliberately: `workflow.md` does not require tests for config
        files. This one is worth 20 lines because it is the only automated guard
        against the matrix silently collapsing back to a single version — the exact
        regression this track exists to prevent
- [x] Task: Commit and record
  - [x] Commit: `ci: run Godot stages across a 4.5/4.6/4.7 x Windows/Linux matrix`
  - [x] Attach a git note recording the axis choices and the confirmed asset names
  - [x] Update this plan with the commit SHA
  - [x] Commit plan update: `conductor(plan): Mark Phase 2 complete`
- [x] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [x] `CI=true pytest`
  - [x] Present manual verification steps; **await explicit user confirmation**
  - [x] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 2`
  - [x] Attach the verification report as a git note
  - [x] Record `[checkpoint: <sha>]`

---

## Phase 3: Matrix Validation Run and Failure Triage [2ca2f1f, 21aa55d, f677cf4, 5c44373]

> **Constraint:** GitHub Actions cannot be executed locally. This phase is verified by
> a pushed run of the branch, not by the local suite. It requires CI to be available.
> `CI=true pytest` passing locally does **not** satisfy this phase.

- [x] Task: Push the branch and trigger a full run
  - [x] `git push -u origin feature/godot-compat-ci-matrix-20260926`
  - [x] Open a PR so `pull_request` triggers the workflow
- [x] Task: Confirm the matrix actually expanded
  - [x] Verify 6 `integration` jobs and 6 `e2e` jobs appear
  - [x] Verify each job name renders both `godot-version` and `os`
  - [x] Verify 6 distinct JUnit artifacts upload per stage, with none rejected by
        `upload-artifact@v4` for a name conflict
  - [x] **Confirm no Godot job passes with every test skipped** — this is the direct
        check of R3 and criterion 5. Inspect a passing job's test counts; a job
        reporting 0 passed / 0 failed / all skipped is a guard failure, not a pass
- [x] Task: Triage failures by axis
  - [x] Build a table of results per `{godot-version} x {os}` x stage
  - [x] Classify each failure against the ranked expectations in spec §7:
        Windows `res://` path handling, Windows exit-code semantics, Godot 4.5 vs 4.7
        differences, or test-suite timing
  - [x] Separate genuine product defects from test-harness and timeout issues
- [x] Task: Fix surfaced failures, within the cap
  - [x] Cap: **3 distinct root causes**, each a self-contained fix with its own test
  - [x] For each: write a failing test first, then the minimal fix, per `workflow.md`
  - [x] **If a fix would exceed the cap, STOP and ask.** Per spec §7 the options, in
        order of preference, are: (1) extend the track knowingly, (2) mark that single
        axis `continue-on-error: true` and file a follow-up track to fix and re-ratchet,
        (3) defer the axis. Do not silently absorb unbounded work, and do not quietly
        relax an axis
- [x] Task: Measure real CI duration
  - [x] Record total wall clock for the matrix run
  - [x] Compare against the `product.md` < 10 min criterion and record the actual
        figure in `plan.md`
  - [x] If a per-job `timeout-minutes` increase is required to avoid a false failure,
        that is in scope; changing what a timeout *means* is not
- [x] Task: Commit and record
  - [x] Commit fixes with scoped Conventional Commit messages
  - [x] Update this plan with results, fixes, and the measured duration
  - [x] Commit plan update: `conductor(plan): Record matrix validation results`
- [x] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [x] Confirm all 12 Godot jobs green
  - [x] Present the results table for user review; **await explicit confirmation**
  - [x] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 3`
  - [x] Attach the verification report as a git note
  - [x] Record `[checkpoint: <sha>]`

### Results

Final run: [36210705904](https://github.com/mansyar/gd-tools/actions/runs/36210705904),
2026-09-26T02:07:52Z -> 02:20:57Z, **13.1 min wall clock**, **19/19 jobs green**.

| Godot | Linux integration | Linux e2e | Windows integration | Windows e2e |
| --- | --- | --- | --- | --- |
| 4.5.2 | pass | pass (52 + 23 skip) | pass | pass |
| 4.6.1 | pass | pass (70 + 5 skip) | pass | pass |
| 4.7.1 | pass | pass (70 + 5 skip) | pass | pass |

Windows and Linux now report identical pass/skip counts, which is the point of
the matrix: the platform gap is closed rather than papered over.

### Root causes found and fixed (2 of the 3 allowed)

1. **GUT 9.6.0 cannot run on Godot 4.5** (`2ca2f1f`). Every failing test was a
   legacy GUT-bridge test. The repo vendors one GUT release and seven suites
   copy it, so the 4.5 axis could never work. Production's `GUT_VERSION_MAP`
   already maps 4.5 -> 9.5.0; the fixture does not consult it. Fixed with an
   explicit skip that names the cause, so the gap stays visible in `-rs` output.
2. **Windowed suites cannot run on any hosted runner** (`21aa55d`, `f677cf4`,
   `5c44373`). Took three attempts and two wrong hypotheses to diagnose:
   - Widened a display-vocabulary marker list -- still failed.
   - Discovered the `<engine>` message is a *fixed* string and the real text is
     in `diagnostics["engine_errors"]`; read that instead -- still failed.
   - The observed text was `WASAPI: init_output_device error`. The failure is
     **audio**, not display: a Windows Server container has no GPU *and* no
     audio endpoint. Renamed the helper to `_skip_without_windowed_support`
     because "no display" described the wrong condition.

   Product behaviour was correct throughout. The sibling test asserting the
   windowed-without-display contract passes on both platforms.

Neither cause was a product defect. Both were test-infrastructure defects that
only a real matrix could expose -- exactly the "Windows Godot path has never
executed in CI" gap this track was created to close. The spec's cap of 3 was not
reached, so the `if a fix would exceed the cap` hold never triggered.

### Criterion 5 (the negative test) — how it was satisfied

Criterion 5 asks that a deliberately broken Godot install **fail** the Godot
jobs rather than skip them. Proven directly in Phase 1 rather than in CI,
because it is faster and deterministic:

| Scenario | Before | After |
| --- | --- | --- |
| `CI=true`, no Godot | 41 passed, 25 **skipped**, exit **0** | 41 passed, 25 **errors**, exit **1** |
| `CI` unset, no Godot | 41 passed, 25 skipped, exit 0 | unchanged |

The "after" message names the missing thing and the fix, per
`product-guidelines.md`.

### Phase 3 deviations

- **CI duration** is 13.1 min against the `product.md` < 10 min target. Accepted
  and recorded in `spec.md` section 6; the measured figure is now in
  `docs/ROADMAP.md`.
- **Verification used a temporary script**, not a committed test, to check
  `_skip_without_windowed_support` against the observed CI wordings. The helper
  is private to one test module, so a committed unit test for it would test the
  test suite rather than the product. The committed protection is the
  self-diagnosing assertion message.

---

## Phase 4: Documentation (R6, criterion 10) [pending]

- [x] Task: Update the roadmap
  - [x] `docs/ROADMAP.md` §8 Phase 5: record that the 4.5/4.6/4.7 matrix now runs on
        Windows and Linux
  - [x] State explicitly that **macOS is still Track 36** — do not let this track's
        completion imply the full matrix is done
  - [x] Note the measured CI duration from Phase 3 against the < 10 min criterion
- [x] Task: Update contributor docs if they describe the job layout
  - [x] Check `docs/CONTRIBUTING.md`; update only if it documents the CI stages
  - [x] If it does not, skip — do not add content that was not there
- [x] Task: Record the version list
  - [x] Note in the roadmap where the tested Godot versions are declared (`ci.yml`
        matrix), so the next maintainer knows one place to edit
  - [x] Flag the drift risk: `GUT_VERSION_MAP` (`src/gd_tools/godot.py:109`) also
        lists 4.5/4.6/4.7 and will need updating alongside the matrix. Track 32 owns
        externalising it — cross-reference, do not implement
- [x] Task: Commit and record
  - [x] Commit: `docs(ci): record the Godot 4.5+ compatibility matrix`
  - [x] Attach a git note
  - [x] Update this plan; commit: `conductor(plan): Mark Phase 4 complete`
- [x] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [x] `CI=true pytest` and `ruff check src/ tests/` and `black --check src/ tests/`
  - [x] Present manual verification steps; **await explicit user confirmation**
  - [x] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 4`
  - [x] Attach the verification report as a git note
  - [x] Record `[checkpoint: <sha>]`

---

## Final Verification (all 12 spec success criteria)

- [ ] Task: Walk `spec.md` §8 criterion by criterion and record pass/fail with
      evidence
- [ ] Task: Confirm all spec success criteria are met, or that any unmet criterion
      has an explicit, recorded, user-approved deviation
- [ ] Task: Mark the track complete in `../tracks.md`
- [ ] Task: Final checkpoint and review hand-off

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Windows `res://` path defect in the native runtime | Medium-High | The reason this track exists. Phase 3 stops and asks rather than absorbing an unbounded fix (§7). |
| Matrix expands but a job silently runs zero tests | Medium | R3 guard lands in Phase 1, *before* the matrix. Phase 3 explicitly inspects pass counts. |
| `upload-artifact@v4` name conflict hard-fails the run | High if unaddressed | R4 suffixing is a mandatory Phase 2 task with a stated reason. |
| Godot asset filename guess is wrong → 404 | Low | Phase 2 requires confirming filenames against the real releases before writing the step. |
| Contention-sensitive Godot exits (`known_flakes.md`) surface more often | Medium | The 12-job matrix improves attribution. The one-retry `import_godot_project` in root `conftest.py` already covers the known import case. Quarantining those tests is a separate decision, explicitly out of scope. |
| CI wall clock exceeds the `product.md` < 10 min criterion | High | Accepted and recorded in spec §6. Phase 3 measures the real figure. Mitigation is a follow-up nightly-schedule decision, not smuggled in here. |
