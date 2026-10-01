# Implementation Plan: Godot Editor Plugin (Roadmap Track 35)

Follows `conductor/workflow.md`: TDD (tests before implementation), >80% line /
>70% branch coverage on Python source, phase checkpoints with manual
verification, conventional commits with git notes.

---

## Phase 1 — Python Deployment Infrastructure (TDD) [checkpoint: 9b6ea8c]

- [x] Task: Write failing unit tests for editor-plugin deployment
  - [x] `tests/unit/test_init.py`: init deploys `addons/gd-tools-editor/` files (plugin.cfg, plugin.gd, dock.gd, coverage_overlay.gd); idempotent re-init; smart backup on modified files; wheel packaging includes the new addon dir
  - [x] `tests/unit/test_doctor.py`: doctor reports editor-plugin presence/staleness status
- [x] Task: Implement deployment — `src/gd_tools/init.py` (editor addon install + smart backup), `src/gd_tools/addon_check.py` / `src/gd_tools/doctor.py` (verification), `pyproject.toml` package data
- [x] Task: Refactor + coverage check (≥80% line / ≥70% branch on touched modules); `ruff` + `black` clean
- [x] Task: Commit `feat(init): deploy gd-tools editor plugin addon` + git note (59ebd27)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md — manual verify: `pip install -e .` → `gd-tools init` in fixture project → confirm addon files deployed; `gd-tools doctor` reports status)

## Phase 2 — Dock Panel (GDScript, manual-checklist verified) [checkpoint: 857255d]

- [x] Task: `plugin.cfg` + `plugin.gd` — EditorPlugin registration, dock instantiation, enable/disable cleanliness
- [x] Task: `dock.gd` — UI layout (Run Tests / Run Coverage buttons, progress state, results area)
- [x] Task: Async process runner — non-blocking invocation of `gd-tools test` / `gd-tools test --coverage` (argument-list form), in-progress state, re-click guard, friendly "gd-tools not found" fallback with install hint (anchored via the new global `--project` CLI option — user-approved scope addition)
- [x] Task: Results parsing — read `.gd-tools/artifacts/<run_id>/` machine-readable index (JSON via Godot's native parser) → pass/fail/skip counts, duration, failed-test assertion messages, artifact path; coverage summary after coverage runs
- [ ] Task: Manual testing checklist for dock behavior (in track docs; executed at checkpoint)
- [x] Task: Manual checklist — document editor UI verification steps (`manual_checklist.md`, Phase 2 section)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md - manual verify on Godot 4.5: enable plugin, run tests + coverage from dock, confirm async UX, missing-CLI fallback)

## Phase 3 — Coverage Heatmap Overlay (GDScript, manual-checklist verified)

- [x] Task: `coverage_overlay.gd` — hook script editor `CodeEdit`, read per-file line/branch status from `.gd-tools/coverage/` artifacts, apply line background colors (green/red/yellow)
- [x] Task: Sync logic — auto-refresh when dock coverage run completes; load on editor open if artifacts exist; stale flag when source files are newer than coverage data (never show stale as fresh)
- [x] Task: Responsiveness guard — bounded per-file work on script open (no editor lag)
- [x] Task: Extend manual testing checklist (overlay colors, stale flag, toggle off/on)
- [~] Task: Phase Verification & Checkpoint (Refer to workflow.md — manual verify: coverage run → open scripts → confirm green/red/yellow; touch a source file → confirm stale flag)

## Phase 4 — Documentation & Integration

- [ ] Task: USER_GUIDE — editor plugin section (deployment, enabling, dock usage, heatmap legend, troubleshooting)
- [ ] Task: README capability table — Editor Plugin "Not yet" → shipped; update `docs/ROADMAP.md` Track 35 status
- [ ] Task: Compat-matrix note — editor-API caveats for Godot 4.5/4.6/4.7 in the checklist
- [ ] Task: Final verification — full `CI=true pytest`, coverage gates, `ruff`/`black`, manual checklist executed
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Testing Approach Note

Phase 2/3 GDScript files are shipped plugin UI code that cannot run in headless
CI — per the workflow's phase-verification protocol they are verified via the
manual checklist at each checkpoint; all Python-side code follows strict
red-green TDD.
