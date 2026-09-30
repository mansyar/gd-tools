# Implementation Plan: macOS CI Matrix

Chore track: add macOS to the CI test matrix at full parity and fix any
macOS-specific issues that surface. Source of truth: `spec.md`.
Workflow rules: `conductor/workflow.md` (tests required for source code
`.py`/`.gd` only; CI YAML and docs do not require tests).

## Phase 1 — Enable macOS in CI

- [x] Task: Add macOS support to the `install-godot` composite action
  (efb79ef)
  - Add a macOS branch to the asset selection in
    `.github/actions/install-godot/action.yml`
    (`Godot_v{v}-stable_macos.universal.zip`).
  - Extract, `chmod +x`, install to `.godot-bin`, export `GODOT_BIN`
    (POSIX path — no `cygpath` on macOS).
  - Keep the existing glob-based extraction diagnostic (`::error` if no
    binary found).
- [x] Task: Add `macos-latest` to all CI stages
  (0e9b679)
  - `matrix-unit`: add `macos-latest` to the `os` axis (runs for all 3
    Python versions).
  - `integration`: add `macos-latest` to the `os` axis (runs for all 3
    Godot versions).
  - `e2e`: add `macos-latest` to the `os` axis (runs for all 3 Godot
    versions).
  - `timeout-minutes` review: no raises needed — unit (5 min) and
    integration/e2e (20 min) budgets already absorb Windows, and macOS
    hosted runners are typically comparable or faster; confirm via CI
    observed runtimes in Task 3.
- [~] Task: Verify macOS runs green (iterative)
  - Push the branch, observe the CI run, diagnose and iterate until all
    macOS jobs pass.
  - Announce each push/watch cycle; max two self-correction attempts per
    failure before escalating to the user.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Fix macOS-specific issues surfaced by CI (conditional)

- [ ] Task: Diagnose macOS-only failures
  - Collect failing test names/logs; classify each as (a) genuine macOS
    platform bug in `src/gd_tools/`, (b) test-fixture assumption (e.g.
    POSIX paths, line endings), or (c) runner-environment limitation.
- [ ] Task: Fix source-code issues (TDD)
  - Only if (a) issues exist: write failing unit tests that reproduce the
    platform-specific behavior via mocks/monkeypatched platform info
    (tests must pass on all 3 OSes), then implement the minimal fix in
    `godot.py` (or the related module). Red → Green → refactor.
- [x] Task: Fix test-fixture assumptions
  (c467b31 — done early: the CI contract tests in
  `tests/unit/test_ci_matrix.py` pinned the old matrix shape and blocked
  Stage 1 before macOS jobs could run)
  - Only if (b) issues exist: adjust fixtures/assertions to be
    platform-neutral; document why.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Documentation truth pass

- [ ] Task: Update `docs/ROADMAP.md`
  - §8 compatibility matrix: add a macOS column with verified
    combinations.
  - Remove/rewrite the "macOS is not covered" limitation notes.
  - Mark Roadmap Track 36 status as `Done` with an outcome summary.
- [ ] Task: Update README platform wording
  - Align any platform-support wording with the verified state (no
    capability-table changes expected unless new facts emerged).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
