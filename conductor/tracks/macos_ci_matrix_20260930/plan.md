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
- [x] Task: Verify macOS runs green (iterative)
  (run 36684641137 — success; iteration 2 fixed `Killed: 9` via
  quarantine strip + ad-hoc re-sign, d1e9ff3)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  [checkpoint: 0aba077]

## Phase 2 — Fix macOS-specific issues surfaced by CI (conditional)

- [x] Task: Diagnose macOS-only failures
  (run 36684261317, commit 5a1773b)
  - Findings: (1) macOS integration failed on ALL 3 Godot versions in the
    action's verify step — `godot --version` SIGKILLed ("Killed: 9",
    exit 137) on macos-latest arm64 → macOS code-signing/Gatekeeper kill
    of the extracted binary, category (c) runner-environment limitation.
    (2) Unit tests failed on Python 3.10 across ALL 3 OSes —
    `ModuleNotFoundError: No module named 'tomllib'` in
    `tests/unit/test_version.py` (pre-existing on main, first surfaced
    here because matrix-unit runs 3.10) → category (b) test-fixture
    assumption, not macOS-specific. No category (a) issues found.
- [x] Task: Fix source-code issues (TDD) — not applicable
  (no category (a) issues: no `src/gd_tools/` changes needed)
- [x] Task: Fix test-fixture assumptions
  (c467b31 — done early: the CI contract tests in
  `tests/unit/test_ci_matrix.py` pinned the old matrix shape and blocked
  Stage 1 before macOS jobs could run)
  - Only if (b) issues exist: adjust fixtures/assertions to be
    platform-neutral; document why.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  [checkpoint: 0aba077]

## Phase 3 — Documentation truth pass

- [x] Task: Update `docs/ROADMAP.md`
  (e9b7a64)
  - §8 compatibility matrix: add a macOS column with verified
    combinations.
  - Remove/rewrite the "macOS is not covered" limitation notes.
  - Mark Roadmap Track 36 status as `Done` with an outcome summary.
- [x] Task: Update README platform wording — no change required
  (README makes no per-OS claims; its only requirement statement is
  platform-neutral: "requires Python 3.10+ and a Godot 4.5+ binary". The
  platform support claim lives in `conductor/product.md` and ROADMAP §8,
  which Task 9 updated.)
  - Align any platform-support wording with the verified state (no
    capability-table changes expected unless new facts emerged).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
