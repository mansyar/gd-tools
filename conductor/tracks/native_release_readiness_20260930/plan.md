# Implementation Plan — Native Release Readiness (v0.5.0)

**Track:** `native_release_readiness_20260930` · **Type:** Chore/Release
**Spec:** [spec.md](./spec.md)

Execution follows `conductor/workflow.md`: TDD (tests before code), task markers,
git notes per task commit, and a Phase Verification & Checkpoint at the end of
every phase (pause for user sign-off before checkpointing).

---

## Phase 1 — Crash-Recovery & Diagnostics Hardening

- [ ] Task 1: Orphan process cleanup on interruption
  - [ ] Write failing tests (Red): interrupted `gd-tools test` run terminates spawned Godot child processes (SIGINT/SIGTERM propagation; no orphans after run)
  - [ ] Implement minimal cleanup in the native orchestrator (Green)
  - [ ] Confirm decided exit code for interrupted runs (130 vs 2) and encode it in tests
- [ ] Task 2: Crash-safe incomplete-run artifact marking
  - [ ] Write failing tests (Red): a run terminated before completion writes a machine-readable incomplete marker under `.gd-tools/artifacts/<run_id>/` and prints a human notice
  - [ ] Implement marker + terminal notice (Green)
  - [ ] Verify complete runs are never marked incomplete (regression test)
- [ ] Task 3: Actionable exit-2 diagnostics
  - [ ] Write failing tests (Red): environment/config/protocol/engine failures emit structured diagnostics (what failed, expected vs. found, suggested fix)
  - [ ] Implement diagnostics on existing exit-2 paths (Green; no exit-code redesign)
- [ ] Task 4: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Verify tests exist for every changed `.py`/`.gd` file in this phase
  - [ ] Announce and run full verification command (`ruff`, `black --check`, `CI=true pytest` with coverage)
  - [ ] Produce manual verification plan (CLI feature variant) and pause for user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

## Phase 2 — GUT Bridge Deprecation

- [ ] Task 1: One-time deprecation notice for GUT-style suites
  - [ ] Write failing tests (Red): running a GUT-style suite prints a deprecation notice exactly once per run stating removal is planned for v0.6.0; native suites print nothing new
  - [ ] Implement notice in the bridge path (Green)
- [ ] Task 2: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Verify tests exist for every changed file in this phase
  - [ ] Announce and run full verification command
  - [ ] Produce manual verification plan and pause for user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

## Phase 3 — Documentation Truth Pass

- [ ] Task 1: `docs/ROADMAP.md`
  - [ ] Fix stale "Phases 3–5 outstanding" header
  - [ ] Check off delivered Phase 4 checkboxes
  - [ ] Rewrite Phase 5 status: hardening + deprecation delivered by this track; parallel execution and runtime caching remain deferred
- [ ] Task 2: `README.md`
  - [ ] Update known-limitations table (parameterized tests supported; bridge = Deprecated)
  - [ ] Verify CLI examples against actual current output
- [ ] Task 3: `docs/ARCHITECTURE.md` + `docs/USER_GUIDE.md`
  - [ ] Remove/reword bridge-era statements (GUT-as-default, bridge-as-new)
  - [ ] State the deprecation timeline consistently (deprecated 0.5, removed 0.6)
- [ ] Task 4: `doctor` / `init` wording alignment
  - [ ] Update bridge status wording in doctor output and init messaging
  - [ ] Update any tests asserting doctor/init output wording
- [ ] Task 5: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Verify tests exist for every changed `.py`/`.gd` file in this phase
  - [ ] Announce and run full verification command
  - [ ] Produce manual verification plan and pause for user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

## Phase 4 — Release Preparation (v0.5.0)

- [ ] Task 1: Version bump
  - [ ] Bump to `0.5.0` in `pyproject.toml` and version-displayed surfaces
  - [ ] Update version tests
- [ ] Task 2: CHANGELOG finalization
  - [ ] Convert Unreleased section to v0.5.0 (date placeholder until publish) with accurate Known Limitations
- [ ] Task 3: Pre-release gate
  - [ ] `ruff check src/ tests/` and `black --check src/ tests/` clean
  - [ ] `CI=true pytest` with coverage targets met (≥80% line / ≥70% branch)
  - [ ] `python -m build` produces 0.5.0 wheel + tarball; `twine check` passes
- [ ] Task 4: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Full verification command run and green
  - [ ] Produce manual verification plan (release-readiness checklist) and pause for user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

---

## Definition of Done
- All spec functional requirements implemented and tested
- Coverage targets met on `src/gd_tools/*.py`
- `ruff` + `black` clean; docs complete and truthful
- All plan tasks marked `[x]` with commit hashes; git notes attached
- All phase checkpoints signed off
