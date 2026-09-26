# Implementation Plan: Native Documentation Truth Pass

**Track ID:** `native_docs_truth_pass_20260926`
**Specification:** [./spec.md](./spec.md)
**Workflow:** [../../workflow.md](../../workflow.md)
**Branch:** `feature/native-docs-truth-pass-20260926`
**Status:** Not started

## Sequencing rationale

Phase 1 is the only phase carrying a Red/Green TDD cycle, because it is the only phase that modifies `.py` source. It goes first for a specific reason beyond convention: R2 documents the retention guarantee, and documentation written before the code change would either be wrong or have to be written twice. The guarantee is fixed, then described.

Phases 2 through 4 are documentation. Per `workflow.md`, tests are required only for `.py` and `.gd` source files — configuration, Markdown, and other non-code assets carry no test obligation. Those phases are verified by review against the acceptance criteria rather than by a test run.

`README.md` and `docs/ARCHITECTURE.md` are separated into distinct phases because they are read by different audiences at different depths: the README is the landing page scanned in under a minute, ARCHITECTURE.md is the reference read once by someone modifying the runtime. Merging them would produce one document trying to do both jobs.

## Phase 1 — Retention Marker Fix (R1)

Covers spec §2 R1 and acceptance criteria 1–4. The only phase that modifies production code.

- [x] Task: Establish test conventions
  - [x] Read `tests/unit/test_native_artifacts.py` in full (181 lines) to confirm naming, docstring, and arrange/act/assert style before adding tests
  - [x] Read `_write_run` (line 49) and `test_prune_keeps_directories_that_are_not_runs` (line 139) and note precisely what the existing retention coverage does and does not assert
  - [x] Confirm the current Red cause is the retention predicate and not an unrelated import or fixture error

- [x] Task: Red — write failing tests
  - [x] Add a test proving a user directory containing a `native/` subdirectory and no run marker survives retention
  - [x] Add a test proving a user directory containing a `preflight/` subdirectory and no run marker survives retention
  - [x] Add a test proving a run directory carrying the start-of-run sentinel but no published `artifacts.json` is pruned — this is the constraint that rules out an index-only fix
  - [x] Add a test proving a pre-marker run directory carrying only `artifacts.json` is still pruned — this is the constraint that rules out a sentinel-only fix
  - [x] Add a test proving the current run, a symlink, and a plain file under the artifact root all remain unpruned, pinning existing behavior so the fix cannot regress it
  - [x] Update the `_write_run` helper so a run-shaped directory reflects a real run's on-disk shape once the sentinel exists — **superseded**: the `artifacts.json`-only shape is the more valuable fixture, because it is what a pre-marker run looks like on disk. `_write_run` was left unchanged and a dedicated test covers the sentinel-only shape
  - [x] Run `CI=true pytest tests/unit/test_native_artifacts.py` and confirm the new tests fail for the intended reason — the prune predicate, not a typo or import error

- [x] Task: Green — minimum implementation
  - [x] Add a module-level sentinel filename constant to `src/gd_tools/native_test/artifacts.py`
  - [x] Write the sentinel at run start in `src/gd_tools/native_test/command.py`, after `NativeArtifactLayout.create` at line 118 and before `run_native_preflight` at line 120
  - [x] Do not write the sentinel inside `NativeArtifactLayout.create` — it is a pure constructor exercised by `test_layout_uses_safe_run_scoped_stable_names` at line 18 with no filesystem setup, and adding a side effect would make that test depend on disk state
  - [x] Narrow `_is_run_directory` (line 231) to accept only the sentinel or `artifacts.json`, dropping the `native/` and `preflight/` checks
  - [x] Preserve the existing guards in `_prune_old_runs` (line 224) for the current run, non-directories, and symlinks
  - [x] Run `CI=true pytest tests/unit/test_native_artifacts.py` and confirm Green

- [x] Task: Refactor
  - [x] Re-read the changed functions and confirm naming, docstring presence, and type hints match the surrounding module
  - [x] Confirm no orphan imports or names were created by the change
  - [x] Re-run `CI=true pytest tests/unit/test_native_artifacts.py`

- [x] Task: Verify quality gates
  - [x] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` and confirm `artifacts.py` has not dropped below the 83% line / 75% branch recorded at the Phase 7 checkpoint of `native_scene_integration_20260925` — **88% line / 93% branch**, improved on both
  - [x] Run `ruff check src/ tests/`
  - [x] Run `black --check src/ tests/`
  - [x] Run `gdlint` and `gdformat --check` if either file was touched — neither is expected to be
  - [x] Run `git diff --check`

- [x] Task: Commit and record
  - [x] Commit as `fix(native): prune only directories carrying a gd-tools run marker` — `a36cb0b`
  - [x] Attach a git note recording why the sentinel is written at run start and why `artifacts.json` remains accepted, since both constraints are non-obvious and a future reader would otherwise "simplify" the predicate back into a defect
  - [x] Record the 7-character SHA against each Phase 1 task and flip `[ ]` to `[x]`
  - [x] Commit the plan update as `conductor(plan): Mark Phase 1 complete`

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [checkpoint: b3501a7]

### Phase 1 deviation

Two deviations from the plan as written, recorded rather than absorbed:

1. **`_write_run` was not updated.** The plan had it write the sentinel, but the `artifacts.json`-only shape is the more valuable fixture because it is exactly what a run published by v0.4.x looks like on disk. A dedicated test now covers the sentinel-only shape, and `_write_run` keeps representing the legacy shape.
2. **`PYTHONPATH` is required to run the suite in this worktree.** The editable install at `__editable__.gd_tools_cli-0.4.0.pth` points at `C:\Users\Ansyar\Documents\Upskilling\cli\gd-tools\src` — a different checkout. Without `PYTHONPATH=<repo>\src`, `pytest` silently tests that other tree and source changes appear to have no effect. This invalidated the first Red and Green runs, which were redone against the correct source. The cause is environmental, not a defect in this track.

Additionally, 18 tests in `tests/e2e/` fail on Windows with `FileNotFoundError` because `_run_cli()` puts `Path(sys.executable).parent` on `PATH` while Windows console scripts live in `Scripts\`. Confirmed identical on unmodified `main`, so it is pre-existing and out of scope here.

## Phase 2 — Guarantee Documentation (R2, R5, R6)

Covers spec §2 R2, R5, R6 and acceptance criteria 5 and 10. Documentation only.

- [x] Task: Correct the retention guarantee in the user guide
  - [x] Update `docs/USER_GUIDE.md:578-580` so the pruning statement matches the Phase 1 behavior
  - [x] State positively what retention touches and what it never touches, per `product-guidelines.md` §4's requirement that messages be actionable and specific
  - [x] Leave the rest of `docs/USER_GUIDE.md` untouched — R6. It is accurate and is the model Phase 3 copies from
  - [x] Re-read the full artifact section at lines 554-595 to confirm no other sentence repeats the old claim

- [x] Task: Correct the two `artifacts.py` docstrings
  - [x] Update `publish_artifact_index`'s docstring at lines 111-112 to describe the actual marker set
  - [x] Update `_prune_old_runs`'s docstring at lines 218-219 to match
  - [x] Confirm both now describe the sentinel and `artifacts.json`, and neither implies the `native/`/`preflight/` heuristic remains

- [x] Task: Refresh stale status headers
  - [x] Update `docs/ROADMAP.md:3-5` — version and date to current, status to reflect that the native runtime foundation and scene/resource integration are both delivered
  - [x] Update `docs/ROADMAP.md:1553` — §8's "Status: Planning" contradicts its own checked-off, Delivered Phases 1 and 2
  - [x] Update `docs/TESTING_STRATEGY.md:3-5` — the "Phase 4 In Progress (Track 14)" line predates ~1,033 tests and the native runtime entirely
  - [x] Confirm no correction advances a roadmap item's completion status. Phases 3–5 remain unstarted and must read that way

- [x] Task: Commit and record
  - [x] Commit as `docs: correct the artifact retention guarantee and stale status headers` — `444b7ce`
  - [x] Attach a git note recording that the docstring edits are in a `.py` file, so this phase is covered by the Python quality gates even though its content is prose
  - [x] Record the 7-character SHA against each Phase 2 task and flip `[ ]` to `[x]`
  - [x] Commit the plan update as `conductor(plan): Mark Phase 2 complete`

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [checkpoint: 8d9964b]

## Phase 3 — README Rewrite (R3)

Covers spec §2 R3 and acceptance criteria 6, 7, 8. Documentation only.

- [x] Task: Correct the incorrect test command
  - [x] Fix `README.md:230` — `pytest --cov=src/gd_tools` conflicts with `workflow.md` and with `pyproject.toml`'s `addopts`, which already pass `--cov=gd_tools`. Running it as written measures two different source roots
  - [x] Add the `CI=true` prefix the project workflow documents, which is what makes Godot-absent fail rather than skip

- [x] Task: Rewrite the overview and features
  - [x] Update `README.md:16-20` so the native runtime is named as the default and GUT as a selectable legacy path
  - [x] Update the features table at `README.md:26-32` — the "Zero-friction bootstrap" row claims `gd-tools init` installs GUT, and "Standalone compatibility" frames GUT as a peer of gdlint and gdformat rather than a migration bridge
  - [x] Keep the phased-reveal ordering from `product.md` §4: familiar capabilities lead, coverage differentiates

- [x] Task: Correct the quick start and command summary
  - [x] Update `README.md:44-71` so the quick start reflects native-first bootstrap and mentions what `gd-tools init` actually deploys
  - [x] Update the command table at `README.md:75-85` — the `init`, `doctor`, `test`, and `version` rows all describe GUT as the default
  - [x] Mention `GdToolsTest`, `--runtime`, `--tag`, `--test-timeout`, `--with-gut`, and the artifact system, per acceptance criterion 6

- [x] Task: Add the native vs. GUT capability matrix
  - [x] Build a Markdown table comparing the two runtimes across discovery, lifecycle hooks, assertions, async waits, tags, selectors, scene/resource integration, coverage, and JUnit XML
  - [x] Source every cell from `docs/USER_GUIDE.md` §3.4 and the native runtime source — not from memory. A capability claimed here that the code lacks is a new inaccuracy
  - [x] Mark the GUT path as a migration bridge with a bounded support window, per `product.md` §9
  - [x] State the real limitations — no mocking, no parameterized tests, no parallel execution, no editor plugin — following the precedent `USER_GUIDE.md:554-580` already sets

- [x] Task: Correct the configuration sample and acknowledgements
  - [x] Add `runtime`, `timeout_seconds`, `retries`, and `tags` to the `[test]` sample at `README.md:172-195`, matching `config.py:48-73`
  - [x] Update `README.md:247` — GUT is currently credited as "the GDScript test framework that `gd-tools test` drives"
  - [x] Update the documentation table at `README.md:206`, which describes ARCHITECTURE.md as coverage-system-only. Phase 4 changes that — **done in advance**, so this row now depends on Phase 4 landing

- [x] Task: Commit and record
  - [x] Commit as `docs: rewrite the README around the native test runtime` — `9129d53`
  - [x] Attach a git note recording that the capability matrix was sourced from `USER_GUIDE.md` and the runtime source, so a later reader knows it is verified rather than aspirational
  - [x] Record the 7-character SHA against each Phase 3 task and flip `[ ]` to `[x]`
  - [x] Commit the plan update as `conductor(plan): Mark Phase 3 complete`

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

### Phase 3 correction log

Three inaccuracies were introduced and caught during the phase, recorded because
each is the failure mode this track exists to prevent:

1. `--suite test_player.gd` was wrong. `--suite` takes a class name, not a
   file path; file selection is by positional path argument. Corrected to
   `--suite PlayerTests`.
2. Removing GUT from the `gd-tools version` row made it *less* accurate.
   `version.py` still collects a `gut` key. Restored, phrased as "and GUT when
   installed".
3. `Retries | Per-suite configurable` contradicted `config.py`, which documents
   `retries` as per test. Changed to "Configurable per test".

One dependency was created in advance: the documentation table's Architecture
row now claims ARCHITECTURE.md covers the native runtime, which is true only
once Phase 4 lands. Noted in the commit.


## Phase 4 — ARCHITECTURE.md Native Section (R4)

Covers spec §2 R4 and acceptance criterion 9. Documentation only.

- [ ] Task: Survey the components to be documented
  - [ ] Read all five GDScript addon scripts: `gd_tools_test.gd`, `gd_tools_test_runner.gd`, `gd_tools_test_context.gd`, `gd_tools_test_preflight.gd`, `gd_tools_native_coverage.gd`
  - [ ] Read all six Python modules: `command.py`, `orchestrator.py`, `preflight.py`, `discovery.py`, `protocol.py`, `artifacts.py`
  - [ ] Note the existing coverage section's structure to mirror — overview, three phases, data formats, per-component detail, design decisions, cross-references

- [ ] Task: Write the overview and responsibility boundary
  - [ ] State the Python/Godot split as `tech-stack.md` §9 defines it: Python owns config, discovery, process orchestration, reporting, and exit codes; Godot owns test loading, lifecycle, assertions, async waits, scene-tree interaction, and coverage activation
  - [ ] Include an ASCII diagram of the native run flow, within 80 columns per `product-guidelines.md` §1

- [ ] Task: Document protocol v2 data formats
  - [ ] Document the suite manifest, the preflight result, the per-suite result, and the artifact index
  - [ ] Document the NDJSON progress event stream
  - [ ] State the exit code contract — 0 pass, 1 test or coverage failure, 2 environment, config, protocol, engine, or process failure

- [ ] Task: Write per-component detail
  - [ ] One subsection per GDScript script and per Python module, each covering responsibility, key interfaces, and where it sits in the flow
  - [ ] Cross-reference the existing coverage section where the two systems meet, rather than duplicating it

- [ ] Task: Write design decisions
  - [ ] Record the decisions already durable in `product.md` §9 and `ROADMAP.md` §8: the GDScript-metadata preflight so Python never parses GDScript; project autoloads running exactly as in production with no test-only autoload installed; windowed suites failing with exit 2 rather than falling back to headless; per-attempt rebuild for retry isolation; run-scoped artifacts retaining only the latest run
  - [ ] Update the cross-references section to link the new section from the coverage material and vice versa

- [ ] Task: Verify and commit
  - [ ] Confirm the section contains per-component detail for all eleven modules, per acceptance criterion 9
  - [ ] Confirm no ASCII diagram exceeds 80 columns
  - [ ] Confirm the existing coverage content is unaltered — the section is additive
  - [ ] Commit as `docs(architecture): document the native test runtime`
  - [ ] Attach a git note recording the section structure and which components remain undocumented, if any
  - [ ] Record the 7-character SHA against each Phase 4 task and flip `[ ]` to `[x]`
  - [ ] Commit the plan update as `conductor(plan): Mark Phase 4 complete`

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Final Verification

- [ ] Task: Walk all 12 acceptance criteria
  - [ ] Record pass or fail with file:line evidence for each of the 12 criteria in `spec.md` §4
  - [ ] For any unmet criterion, record an explicit user-approved deviation rather than silently closing it
- [ ] Task: Run the full quality gate
  - [ ] `CI=true pytest` — full suite green
  - [ ] `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` — ≥80% line, ≥70% branch
  - [ ] `ruff check src/ tests/`
  - [ ] `black --check src/ tests/`
  - [ ] `git diff --check`
- [ ] Task: Confirm scope was not exceeded
  - [ ] `git diff --name-only` against the track base and confirm only the intended files changed
  - [ ] Confirm no roadmap item was marked complete, no version was bumped, and `CHANGELOG.md` is untouched
- [ ] Task: Mark the track complete
  - [ ] Mark `native_docs_truth_pass_20260926` complete in `../tracks.md`
  - [ ] Synchronize `metadata.json` status and `updated_at`
  - [ ] Final checkpoint commit and review hand-off

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| The sentinel fix strands pre-existing run directories | Medium | Mitigated by design: `_is_run_directory` accepts `artifacts.json` as well as the sentinel, and acceptance criterion 3 tests exactly this |
| The capability matrix introduces new inaccuracies | Medium | Every cell is sourced from `USER_GUIDE.md` and the runtime source. A claim here that the code lacks is as much a defect as the GUT-first README |
| Scope expands from documentation into the wider review findings | Medium | Spec §5 enumerates the excluded findings explicitly. Anything newly discovered is a decision point, not absorbed work |
| Phase 2's docstring edits put Markdown-phase changes in a `.py` file | Low | Disclosed in the Phase 2 commit note; the final gate covers Python regardless |
| README growth | Low | The quick start must stay scannable in under a minute. Depth belongs in `USER_GUIDE.md`, which already has it |
