# Plan: Fail-Fast and CI Sharding (`fail_fast_ci_sharding_20261005`)

Workflow: strict TDD per task (Red → Green), coverage gate (>80% line, >70% branch on new source), phase checkpoints per `conductor/workflow.md`.

## Phase 1: CLI flag parsing & validation (`cli.py`)

- [x] **Task 1.1: Write failing tests for flag parsing (Red)** `799400f`
  - [ ] Unit tests: `--exitfirst` and `-x` set the fail-fast option (default False)
  - [ ] Unit tests: `--shard k/N` parses to (k, N) tuple; `--shard 1/1` valid
  - [ ] Unit tests: invalid shard forms (`4/3`, `0/3`, `3`, `a/b`) exit 2 with usage error
  - [ ] Unit tests: `--shard` + `--watch` → exit 2; `--exitfirst` + `--watch` accepted
- [x] **Task 1.2: Implement parsing & validation (Green)** `799400f`
  - [x] Add `--exitfirst`/`-x` and `--shard k/N` options to `test` command
  - [x] Validate shard form at parse time; plumb both into orchestrator invocation
- [x] **Task 1.3: Verify coverage & commit** (`ruff check` + `black --check` + `CI=true pytest` + coverage gate) `799400f`
- [ ] **Task 1.4: Phase Verification & Checkpoint (Refer to workflow.md)**

## Phase 2: Suite-level sharding (orchestrator)

- [x] **Task 2.1: Write failing tests for shard selection (Red)** `c40ca90`
  - [x] Unit tests: round-robin assignment function — suite *i* → shard ((i mod N)+1) over deterministic plan order
  - [x] Unit tests: selection is a pure filter of the plan (plan cache unaffected)
  - [x] Unit tests: `--shard 1/1` selects the full plan; empty shard yields clean "nothing to run" exit
  - [x] Unit tests: changed → shard ordering (selection applies to the changed-filtered plan)
  - [x] Unit tests: shard banner reports `Running shard k/N (M of T suites)`
- [x] **Task 2.2: Implement shard selection & banner (Green)** `c40ca90`
  - [x] Round-robin selection step in plan assembly after changed-filtering, before parallelism
  - [x] Shard context in run banner `Running shard k/N (M of T suites)` (FR2.7; plan previously over-specified an artifact-index field — spec requires banner only)
- [ ] **Task 2.3: Write failing integration tests for shard × parallel × coverage (Red)**
  - [ ] `--shard 2/3` + `--parallel`: parallelism applies within shard only
  - [ ] `--shard k/N` + `--coverage`: per-shard coverage data/report as today
- [ ] **Task 2.4: Implement integration behavior (Green)**
- [ ] **Task 2.5: Verify coverage & commit**
- [ ] **Task 2.6: Phase Verification & Checkpoint (Refer to workflow.md)**

## Phase 3: Fail-fast dispatch gate (orchestrator)

- [ ] **Task 3.1: Write failing tests for the dispatch gate (Red)**
  - [ ] Unit tests: failure result sets stop-dispatch flag; queued suites not started; in-flight drained and collected
  - [ ] Unit tests: trigger on any failure class — test failure, infra error, preflight failure, timeout; skip/pass never triggers
  - [ ] Unit tests: retries respected — suite passing after retry does not trigger
  - [ ] Unit tests: exit code 1 with summary line `Stopped early: fail-fast after suite <id> (K of M suites skipped)`
  - [ ] Unit tests: unstarted suites recorded as skipped-due-to-fail-fast in results/artifact index (additive)
  - [ ] Unit tests: `--exitfirst` + `--coverage`: partial report generated and labeled partial
  - [ ] Unit tests: without the flag, dispatch loop behavior byte-identical to v0.7.0 (regression guard)
- [ ] **Task 3.2: Implement the gate in the dispatch loop (Green)**
- [ ] **Task 3.3: Write failing integration tests for combined interplay (Red)**
  - [ ] `--exitfirst` + `--parallel N`: drain semantics, coherent results, no orphaned processes
  - [ ] `--exitfirst` + `--shard`: fail-fast applies within the shard's run
  - [ ] `--exitfirst` + `--watch`: per-iteration reset (fail-fast state does not persist across watch iterations)
- [ ] **Task 3.4: Implement combined behavior (Green)**
- [ ] **Task 3.5: Verify coverage & commit**
- [ ] **Task 3.6: Phase Verification & Checkpoint (Refer to workflow.md)**

## Phase 4: Documentation

- [ ] **Task 4.1: README flag reference** — `--exitfirst`/`-x` and `--shard k/N` entries with interplay rules (watch, retries, coverage, changed→shard→parallel)
- [ ] **Task 4.2: CI recipe** — GitHub Actions matrix over shard indices with `coverage merge` across shards
- [ ] **Task 4.3: ARCHITECTURE.md** — orchestration section: dispatch-loop fail-fast gate, shard selection step, round-robin rule; §9.7 exit-map note that fail-fast exits 1
- [ ] **Task 4.4: Commit docs**
- [ ] **Task 4.5: Phase Verification & Checkpoint (Refer to workflow.md)**

## Phase 5: End-to-end validation

- [ ] **Task 5.1: E2E tests (Red → Green)** — full `gd-tools test` on the sample Godot project: fail-fast early stop with artifacts coherent; sharded runs produce expected suite subsets; combined `--changed --shard --exitfirst --parallel --coverage` run
- [ ] **Task 5.2: Full quality gate** — `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest --cov=gd_tools --cov-branch` (>80% line, >70% branch on new code)
- [ ] **Task 5.3: Final Phase Verification & Checkpoint (Refer to workflow.md)**
