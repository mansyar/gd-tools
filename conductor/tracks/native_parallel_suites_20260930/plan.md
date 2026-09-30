# Implementation Plan — Parallel Suite Execution

**Track:** `native_parallel_suites_20260930` · **Type:** Feature
**Spec:** [spec.md](./spec.md)

Execution follows `conductor/workflow.md`: TDD (tests before code), task
markers, git notes per task commit, and a Phase Verification & Checkpoint at
the end of every phase (pause for user sign-off before checkpointing).

---

## Phase 1 — Configuration & API Surface [checkpoint: ec8d653]

- [x] Task 1: Config key `[test] parallel` in `config.py` (505a0ab)
  (Pydantic validation, 1–32 bounds, absent = sequential)
  - [x] Write failing tests (Red): valid/invalid/boundary values
    (0, 1, 32, 33, non-int), absent-key default
  - [x] Implement (Green); config renderers expose the key
- [x] Task 2: `--parallel N` CLI flag in `cli.py`/`command.py` (6533c26)
  (flag overrides config; invalid values exit 2 with fix hint; default 4 when
  enabled without N)
  - [x] Write failing tests (Red)
  - [x] Implement (Green)
- [x] Task 3: `N = 1` routes to the existing sequential path — regression
  tests prove zero behavior change (no pool machinery engaged) (ab8c73f;
  CLI-level pin; orchestrator-level sequential-path regression lands with
  the parallel branch in Phase 2 Task 1)
- [x] Task 4: Phase Verification & Checkpoint (Refer to workflow.md) (ec8d653)
  - [ ] Verify tests exist for every changed `.py`/`.gd` file in this phase
  - [ ] Announce and run full verification command
    (`ruff`, `black --check`, `CI=true pytest` with coverage)
  - [ ] Produce manual verification plan (CLI feature variant) and pause for
    user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

## Phase 2 — Parallel Execution Engine [checkpoint: 0fd0504]

- [x] Task 1: Worker-pool scheduler in `native_test/orchestrator.py`
  (discovery-order queue, per-worker dispatch, mocked subprocesses in unit
  tests) (62bf0a4)
  - [x] Write failing tests (Red): concurrency bound respected, dispatch
    order, all suites executed
  - [x] Implement (Green)
- [x] Task 2: Per-worker timeout enforcement + continue-after-failure
  semantics (timed-out/crashed suite fails its slot; next suite dispatched; no
  cross-suite cancellation) (e623db1)
  - [x] Write failing tests (Red)
  - [x] Implement (Green)
- [x] Task 3: Result aggregation — ordered summary + discovery-ordered JUnit
  XML + unchanged exit-code precedence in `command.py` (36fd158)
  - [x] Write failing tests (Red) — caught the adapter dropping `parallel`
  - [x] Implement (Green)
- [x] Task 4: Interrupt handling — stop dispatch, kill all in-flight process
  trees (POSIX + Windows `taskkill /T`/Job Object strategy behind a testable
  seam), incomplete artifact index, exit 130 (5f850d1)
  - [x] Write failing tests (Red)
  - [x] Implement (Green)
  - [x] Regression: complete runs never marked incomplete
- [x] Task 5: Phase Verification & Checkpoint (Refer to workflow.md) (0fd0504)
  - [x] Verify tests exist for every changed `.py`/`.gd` file in this phase
  - [x] Announce and run full verification command
  - [x] Produce manual verification plan and pause for user sign-off
  - [x] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

## Phase 3 — Protocol, Coverage & Watch Integration

- [x] Task 1: NDJSON progress events carry suite identifier + worker slot;
  protocol minor version bump per versioned-JSON convention (392a6be)
  - [x] Write failing tests (Red)
  - [x] Implement (Green)
- [x] Task 2: Coverage under parallel — per-suite data files compose with the
  existing merge path; merged report structurally identical to sequential (237856f)
  - [x] Write failing tests (Red)
  - [x] Implement (Green)
- [ ] Task 3: Watch mode inherits `--parallel`/config through the shared run
  path
  - [ ] Write failing tests (Red)
  - [ ] Implement (Green)
- [ ] Task 4: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Verify tests exist for every changed `.py`/`.gd` file in this phase
  - [ ] Announce and run full verification command
  - [ ] Produce manual verification plan and pause for user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

## Phase 4 — E2E, Performance & Documentation

- [ ] Task 1: Functional e2e — parallel vs sequential: identical outcomes,
  exit codes, discovery-ordered JUnit, coverage parity (marked for the e2e
  suite; smoke-compatible selection)
- [ ] Task 2: Performance e2e in `tests/performance/` — M-suite run with N
  workers completes faster than sequential
- [ ] Task 3: Documentation — `ARCHITECTURE.md` limitation removal + parallel
  model, `USER_GUIDE.md`, `README.md`, config reference
- [ ] Task 4: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Verify tests exist for every changed `.py`/`.gd` file in this phase
  - [ ] Announce and run full verification command
  - [ ] Produce manual verification plan and pause for user sign-off
  - [ ] Checkpoint commit + git note + `[checkpoint: <sha>]` in plan.md

---

## Definition of Done

- All spec functional requirements implemented and tested; sequential default
  behavior unchanged
- Coverage targets met on `src/gd_tools/*.py` (≥80% line / ≥70% branch)
- `ruff` + `black` clean; docs complete and truthful
- All plan tasks marked `[x]` with commit hashes; git notes attached
- All phase checkpoints signed off
