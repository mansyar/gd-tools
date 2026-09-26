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

## Phase 2: Platform-Aware Matrix Wiring (R1, R2, R4, R5)

- [ ] Task: Add the version axis
  - [ ] In `ci.yml`, remove the global `GODOT_VERSION: '4.6.1'` env var (`ci.yml:14`)
  - [ ] Add `godot-version: ['4.5.2', '4.6.1', '4.7.1']` to both Godot jobs
  - [ ] Keep `godot-version` and `os` as **separate** matrix axes so the GitHub UI
        renders a readable grid and a failure names both dimensions (R4)
- [ ] Task: Add the OS axis
  - [ ] `os: [ubuntu-latest, windows-latest]` on both Godot jobs
  - [ ] Replace `runs-on: ubuntu-latest` with `runs-on: ${{ matrix.os }}`
  - [ ] Set `strategy: fail-fast: false` on both (R4)
- [ ] Task: Make the Godot install platform-aware (R1)
  - [ ] Replace the bash-only block in **both** `integration` (`ci.yml:130-135`) and
        `e2e` (`ci.yml:173-179`)
  - [ ] Select the asset by runner OS:
        - [ ] Linux → `Godot_v<version>-stable_linux.x86_64.zip`
        - [ ] Windows → `Godot_v<version>-stable_win64.exe.zip`
  - [ ] **Confirm the exact asset filenames against the real GitHub release before
        writing the step** — do not guess. Verify for all three versions
  - [ ] Place the binary at a stable, explicitly exported location per OS and append
        it to `PATH` so `godot --version` works in a later step
  - [ ] Apply `chmod +x` and `sudo mv` **only** on the Linux branch; no bash-only
        construct may execute on a Windows runner (criterion 4)
  - [ ] Extract the duplicated install block into a single reusable step or
        composite action so `integration` and `e2e` cannot drift
- [ ] Task: Make `GODOT_BIN` dynamic (R2)
  - [ ] Remove the hardcoded `GODOT_BIN: /usr/local/bin/godot` from both jobs
        (`ci.yml:116`, `ci.yml:159`)
  - [ ] Set `GODOT_BIN` from the install step to an explicit per-OS path, so
        `find_godot_binary()` resolves it through its existing "env var is a real
        file" branch
  - [ ] Grep the whole file to confirm no POSIX absolute path survives
- [ ] Task: Fix artifact name collisions (R4)
  - [ ] `junit-results-integration` → suffix with
        `${{ matrix.godot-version }}-${{ matrix.os }}`
  - [ ] `junit-results-e2e` → same suffix
  - [ ] **Why this is mandatory, not cosmetic:** `actions/upload-artifact@v4` treats
        artifact names as immutable within a run and **errors** on a duplicate, so
        6 same-named jobs would hard-fail rather than silently overwrite
  - [ ] Keep the per-stage `junit-*.xml` local filenames as-is; only the artifact
        `name:` changes
- [ ] Task: Capture the resolved version in every job (criterion 11)
  - [ ] Keep a `godot --version` verification step, made OS-aware
  - [ ] Ensure its output appears in the job log so a version mismatch is
        diagnosable from CI output alone
- [ ] Task: Keep the Godot stages off the Python axis (R5)
  - [ ] Confirm `python-version: '3.12'` stays a scalar in both Godot jobs — it must
        **not** join the matrix, or 12 jobs become 36
- [ ] Task: Validate the workflow file
  - [ ] Parse `ci.yml` with the project's `pyyaml` dependency to confirm valid YAML
  - [ ] Run `actionlint` if available; otherwise assert the expected structure
        programmatically (6 cells per stage, both axes present, no `continue-on-error`)
- [ ] Task: Add a matrix regression guard
  - [ ] Create `tests/unit/test_ci_matrix.py` asserting the matrix expands to
        6 cells per stage and that no hardcoded `/usr/local/bin/godot` remains
  - [ ] Tradeoff, stated deliberately: `workflow.md` does not require tests for config
        files. This one is worth 20 lines because it is the only automated guard
        against the matrix silently collapsing back to a single version — the exact
        regression this track exists to prevent
- [ ] Task: Commit and record
  - [ ] Commit: `ci: run Godot stages across a 4.5/4.6/4.7 x Windows/Linux matrix`
  - [ ] Attach a git note recording the axis choices and the confirmed asset names
  - [ ] Update this plan with the commit SHA
  - [ ] Commit plan update: `conductor(plan): Mark Phase 2 complete`
- [ ] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [ ] `CI=true pytest`
  - [ ] Present manual verification steps; **await explicit user confirmation**
  - [ ] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 2`
  - [ ] Attach the verification report as a git note
  - [ ] Record `[checkpoint: <sha>]`

---

## Phase 3: Matrix Validation Run and Failure Triage

> **Constraint:** GitHub Actions cannot be executed locally. This phase is verified by
> a pushed run of the branch, not by the local suite. It requires CI to be available.
> `CI=true pytest` passing locally does **not** satisfy this phase.

- [ ] Task: Push the branch and trigger a full run
  - [ ] `git push -u origin feature/godot-compat-ci-matrix-20260926`
  - [ ] Open a PR so `pull_request` triggers the workflow
- [ ] Task: Confirm the matrix actually expanded
  - [ ] Verify 6 `integration` jobs and 6 `e2e` jobs appear
  - [ ] Verify each job name renders both `godot-version` and `os`
  - [ ] Verify 6 distinct JUnit artifacts upload per stage, with none rejected by
        `upload-artifact@v4` for a name conflict
  - [ ] **Confirm no Godot job passes with every test skipped** — this is the direct
        check of R3 and criterion 5. Inspect a passing job's test counts; a job
        reporting 0 passed / 0 failed / all skipped is a guard failure, not a pass
- [ ] Task: Triage failures by axis
  - [ ] Build a table of results per `{godot-version} x {os}` x stage
  - [ ] Classify each failure against the ranked expectations in spec §7:
        Windows `res://` path handling, Windows exit-code semantics, Godot 4.5 vs 4.7
        differences, or test-suite timing
  - [ ] Separate genuine product defects from test-harness and timeout issues
- [ ] Task: Fix surfaced failures, within the cap
  - [ ] Cap: **3 distinct root causes**, each a self-contained fix with its own test
  - [ ] For each: write a failing test first, then the minimal fix, per `workflow.md`
  - [ ] **If a fix would exceed the cap, STOP and ask.** Per spec §7 the options, in
        order of preference, are: (1) extend the track knowingly, (2) mark that single
        axis `continue-on-error: true` and file a follow-up track to fix and re-ratchet,
        (3) defer the axis. Do not silently absorb unbounded work, and do not quietly
        relax an axis
- [ ] Task: Measure real CI duration
  - [ ] Record total wall clock for the matrix run
  - [ ] Compare against the `product.md` < 10 min criterion and record the actual
        figure in `plan.md`
  - [ ] If a per-job `timeout-minutes` increase is required to avoid a false failure,
        that is in scope; changing what a timeout *means* is not
- [ ] Task: Commit and record
  - [ ] Commit fixes with scoped Conventional Commit messages
  - [ ] Update this plan with results, fixes, and the measured duration
  - [ ] Commit plan update: `conductor(plan): Record matrix validation results`
- [ ] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [ ] Confirm all 12 Godot jobs green
  - [ ] Present the results table for user review; **await explicit confirmation**
  - [ ] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 3`
  - [ ] Attach the verification report as a git note
  - [ ] Record `[checkpoint: <sha>]`

---

## Phase 4: Documentation (R6, criterion 10)

- [ ] Task: Update the roadmap
  - [ ] `docs/ROADMAP.md` §8 Phase 5: record that the 4.5/4.6/4.7 matrix now runs on
        Windows and Linux
  - [ ] State explicitly that **macOS is still Track 36** — do not let this track's
        completion imply the full matrix is done
  - [ ] Note the measured CI duration from Phase 3 against the < 10 min criterion
- [ ] Task: Update contributor docs if they describe the job layout
  - [ ] Check `docs/CONTRIBUTING.md`; update only if it documents the CI stages
  - [ ] If it does not, skip — do not add content that was not there
- [ ] Task: Record the version list
  - [ ] Note in the roadmap where the tested Godot versions are declared (`ci.yml`
        matrix), so the next maintainer knows one place to edit
  - [ ] Flag the drift risk: `GUT_VERSION_MAP` (`src/gd_tools/godot.py:109`) also
        lists 4.5/4.6/4.7 and will need updating alongside the matrix. Track 32 owns
        externalising it — cross-reference, do not implement
- [ ] Task: Commit and record
  - [ ] Commit: `docs(ci): record the Godot 4.5+ compatibility matrix`
  - [ ] Attach a git note
  - [ ] Update this plan; commit: `conductor(plan): Mark Phase 4 complete`
- [ ] Task: Phase Verification & Checkpoint (Refer to `../../workflow.md`)
  - [ ] `CI=true pytest` and `ruff check src/ tests/` and `black --check src/ tests/`
  - [ ] Present manual verification steps; **await explicit user confirmation**
  - [ ] Checkpoint commit: `conductor(checkpoint): Checkpoint end of Phase 4`
  - [ ] Attach the verification report as a git note
  - [ ] Record `[checkpoint: <sha>]`

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
