# Implementation Plan: `test --changed` — Affected-Suite Selection

- **Track ID:** test_changed_20261001
- **Type:** Feature
- **Status:** New
- **Specification:** [`spec.md`](./spec.md)

## Phase 1 — Change detection and shared suite-selection core

**Purpose:** Establish the git change-collection boundary and extract the
watch loop's mapping logic into a shared, unit-testable selection function
before touching the CLI.

- [x] Task: Add failing tests for git change collection (Red) [commit: `a1bd066`]
  - [x] Cover working-tree mode: staged, unstaged, untracked, and deleted files via `git status --porcelain`.
  - [x] Cover `--base` mode: `git diff --name-only merge-base(ref, HEAD)` semantics.
  - [x] Cover not-a-git-repo → typed error (maps to exit 2).
  - [x] Cover invalid `--base` ref → typed error (maps to exit 2).
  - [x] Cover empty change set.
  - [x] Mock git subprocess invocations (no real repos in unit tests).
  - [x] Run targeted tests and confirm the expected Red phase.
- [x] Task: Implement `collect_changed_files` module (Green) [commit: `d09a732`]
  - [x] Add the minimal change-collection boundary (new module under `src/gd_tools/`).
  - [x] Parse `git status --porcelain` and `git diff --name-only` output with `pathlib` handling.
  - [x] Resolve merge-base for `--base` mode; validate the ref.
  - [x] Raise actionable, typed errors for repo/ref failures (exit-2 semantics).
  - [x] Run targeted tests to Green.
- [x] Task: Add failing tests for shared suite selection (Red) [commit: `8c8a0f5`]
  - [x] Extract the watch loop's mapping block (changed paths → mapped suites | unmapped list) into a reusable function co-located with `watch/mapping.py`.
  - [x] Cover: mapped-only selection, unmapped fallback partition, deleted paths, respect for already-filtered suite lists.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement selection function and refactor watch loop (Green) [commit: `2b111b9`]
  - [x] Implement the shared selection function.
  - [x] Refactor `watch/loop.py` to use it — no behavior change (surgical refactor).
  - [x] Run the full watch-mode regression tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [x] Run targeted unit tests and static checks (`ruff check`, `black --check`).
  - [x] Verify watch-mode regression tests pass unchanged.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 2 — CLI integration for `--changed` / `--base`

**Purpose:** Wire change collection and shared selection into the `test`
command's discovery→orchestration flow with the specified reporting and
exit semantics.

- [ ] Task: Add failing CLI integration tests (Red)
  - [ ] Cover `--changed` narrowing discovery output to mapped suites before orchestration.
  - [ ] Cover `--base <ref>` switching the change source.
  - [ ] Cover full-suite fallback notice naming unmapped files (e.g. changed `project.godot`).
  - [ ] Cover empty change set → exit 0, "no changes detected", no Godot processes launched.
  - [ ] Cover not-a-repo / invalid ref → exit 2 with actionable message.
  - [ ] Cover the always-on summary line and `--verbose` per-file mapping detail.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement the CLI flags and test-command wiring (Green)
  - [ ] Add `--changed` and `--base` click options to the `test` command.
  - [ ] Narrow discovered suites via the shared selection function before orchestration.
  - [ ] Implement summary line and `--verbose` reporting consistent with preflight-cache hit/miss style.
  - [ ] Map collection errors to exit code 2 with actionable diagnostics.
  - [ ] Run targeted tests to Green.
- [ ] Task: Add composition tests (Red → Green)
  - [ ] `--changed` + `--parallel N` runs narrowed suites concurrently.
  - [ ] `--changed` + `--coverage` produces valid coverage scoped to executed suites.
  - [ ] `--changed` + `--suite/--test/--tag` respects the active selection in both mapped and fallback paths.
  - [ ] Confirm Red, implement the minimal wiring gaps, confirm Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run CLI integration, composition, and full unit suite.
  - [ ] Verify exit-code semantics (0/1/2) are preserved.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 3 — E2E validation, documentation, and track close-out

**Purpose:** Prove the feature end-to-end on a real git-backed Godot
fixture project and land user-facing documentation.

- [ ] Task: Add E2E test on a git-backed fixture project
  - [ ] Initialize a fixture Godot project as a git repo; commit a baseline.
  - [ ] Edit a source `.gd` file and verify only the mapped suite runs.
  - [ ] Modify `project.godot` and verify full-suite fallback with notice.
  - [ ] Commit a change on a branch and verify `--base main` selection.
  - [ ] Run the E2E test to Green.
- [ ] Task: Documentation and changelog
  - [ ] Document `--changed`/`--base` in the test command docs and README.
  - [ ] Add a CHANGELOG `Unreleased` entry.
  - [ ] Note the watch-mode mapping reuse in `docs/` where watch mode is described.
- [ ] Task: Final verification & track completion (Refer to `workflow.md`)
  - [ ] Run the full suite: `CI=true pytest`, with coverage gates (>80% line, >70% branch on new modules).
  - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/`.
  - [ ] Perform the workflow's manual verification and obtain user confirmation.
  - [ ] Create the final checkpoint commit, git note, and recorded SHA.
