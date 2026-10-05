# Plan: Fail-Fast and CI Sharding (`fail_fast_ci_sharding_20261005`)

Workflow: strict TDD per task (Red → Green), coverage gate (>80% line, >70% branch on new source), phase checkpoints per `conductor/workflow.md`.

## Phase 1: CLI flag parsing & validation (`cli.py`) `[checkpoint: 9c734ea]`

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

## Phase 2: Suite-level sharding (orchestrator) `[checkpoint: 354a539]`

- [x] **Task 2.1: Write failing tests for shard selection (Red)** `c40ca90`
  - [x] Unit tests: round-robin assignment function — suite *i* → shard ((i mod N)+1) over deterministic plan order
  - [x] Unit tests: selection is a pure filter of the plan (plan cache unaffected)
  - [x] Unit tests: `--shard 1/1` selects the full plan; empty shard yields clean "nothing to run" exit
  - [x] Unit tests: changed → shard ordering (selection applies to the changed-filtered plan)
  - [x] Unit tests: shard banner reports `Running shard k/N (M of T suites)`
- [x] **Task 2.2: Implement shard selection & banner (Green)** `c40ca90`
  - [x] Round-robin selection step in plan assembly after changed-filtering, before parallelism
  - [x] Shard context in run banner `Running shard k/N (M of T suites)` (FR2.7; plan previously over-specified an artifact-index field — spec requires banner only)
- [x] **Task 2.3: Write failing integration tests for shard × parallel × coverage (Red)** `bc8045c`
  - [x] `--shard 2/3` + `--parallel`: parallelism applies within shard only (e2e: `tests/e2e/test_native_shard_e2e.py`; composition behavior already implemented by Task 2.2, so tests passed on first full run — earlier Red runs against the un-instrumented fixture shaped the fixture prep)
  - [x] `--shard k/N` + `--coverage`: per-shard coverage data/report as today, with a shard-agnostic plan (NFR2)
- [x] **Task 2.4: Implement integration behavior (Green)** `bc8045c` — no further code needed: selection (2.2) already applies before preflight/parallelism; coverage behaves per-shard as with `--suite` filtering today
- [x] **Task 2.5: Verify coverage & commit** `bc8045c` — ruff + black clean; unit suite 1528 passed / 3 skipped; coverage 92.88% ≥ 80% gate
- [x] **Task 2.6: Phase Verification & Checkpoint (Refer to workflow.md)** `354a539`

## Phase 3: Fail-fast dispatch gate (orchestrator) `[checkpoint: 12f1b02]`

- [x] **Task 3.1: Write failing tests for the dispatch gate (Red)** (`sha: 18e7052`, `tests/unit/test_native_exitfirst.py`, 8 tests, all Red: TypeError 'exitfirst' / ValidationError 'fail_fast')
  - [x] Unit tests: failure result sets stop-dispatch flag; queued suites not started; in-flight drained and collected (sequential + parallel drain test)
  - [x] Unit tests: trigger on any failure class - test failure, infra error (status "error"), timeout (timeout covered by existing _process_error path → has_error, same gate); skip/pass never triggers
  - [x] Unit tests: retries respected - suite passing after retry (attempts=2) does not trigger
  - [x] Unit tests: exit code 1 with summary line `Stopped early: fail-fast after suite <id> (K of M suites skipped)` (command-level rendering test; exit 1 via existing TestFailureError)
  - [x] Unit tests: unstarted suites recorded as skipped-due-to-fail-fast in results (synthetic skipped entries); artifact index already lists the full plan's suite_names
  - [x] Unit tests: `--exitfirst` + `--coverage`: shards from drained suites still merged (existing omission "partial" labeling applies unchanged)
  - [x] Unit tests: without the flag, dispatch loop behavior byte-identical to v0.7.0 (regression guard)
- [x] **Task 3.2: Implement the gate in the dispatch loop (Green)** `58a6efb` - `run_native_tests(exitfirst=...)`: plain parallel dispatch unchanged (submit-all-upfront); exitfirst dispatches incrementally bounded by --parallel, stops on has_failure/has_error, drains in-flight futures, records unstarted suites as synthetic skipped entries in discovery order; `NativeRunResult.fail_fast = {trigger, skipped, planned}`; command.py renders `Stopped early: fail-fast after suite <id> (K of M suites skipped)` before the failure exit; interrupt-test result stub updated for the additive field
- [x] **Task 3.3: Write failing integration tests for combined interplay (Red)** (`tests/unit/test_watch_session.py` + `tests/unit/test_native_exitfirst.py`)
  - [x] `--exitfirst` + `--parallel N`: drain semantics proven at orchestrator level (Task 3.1 parallel test); command-level guard asserts both flags forwarded in one call (Red: KeyError 'exitfirst' - flag was dropped at the command seam); skip breakdown carried on TestFailureError.result
  - [x] `--exitfirst` + `--shard`: fail-fast applies within the shard's run - shard selection happens upstream of run_native_tests, so the flag composes by construction; composition covered by shard e2e (bc8045c) + forwarding guard
  - [x] `--exitfirst` + `--watch`: per-iteration reset - Red: run_watch_mode accepted exitfirst but never forwarded it; now every iteration's call carries the flag (fresh orchestrator state per run)
- [x] **Task 3.4: Implement combined behavior (Green)** `fe46d96` - exitfirst forwarded in `_run_native_test_command` -> `run_native_tests` and in `run_watch_mode.runner()` -> `run_native_test_command`
- [x] **Task 3.5: Verify coverage & commit** `fe46d96` - ruff + black clean (175 files unchanged); full unit suite 1539 passed / 3 skipped; coverage 92.88% >= 80% gate
- [x] **Task 3.6: Phase Verification & Checkpoint (Refer to workflow.md)** `12f1b02` - manual fail-fast run: early stop, summary line, exit 1, coherent artifacts (found+fixed publish ValueError); regression run unchanged

## Phase 4: Documentation `[checkpoint: cac4819]`

- [x] **Task 4.1: README flag reference** `6b9c71d` - test-command table row, flag examples, and interplay paragraphs for `--exitfirst`/`-x` and `--shard k/N` (watch rejections, retries, coverage, changed/shard/parallel pipeline)
- [x] **Task 4.2: CI recipe** `6b9c71d` - USER_GUIDE 4.2 "Sharding a test run across CI jobs": GitHub Actions matrix over shard indices with a `coverage merge` across-shards job (plus flag-reference rows and examples in 3.4)
- [x] **Task 4.3: ARCHITECTURE.md** `6b9c71d` - 11.2 orchestrator section: dispatch pipeline (changed -> shard -> parallel), round-robin rule, fail-fast gate + artifact-index `fail_fast: "skipped"` markers; 9.7 note that fail-fast introduces no new exit code
- [x] **Task 4.4: Commit docs** `6b9c71d`
- [x] **Task 4.5: Phase Verification & Checkpoint (Refer to workflow.md)** `cac4819` - anchor link resolves, markdown fences balanced, flag references present

## Phase 5: End-to-end validation

- [ ] **Task 5.1: E2E tests (Red → Green)** — full `gd-tools test` on the sample Godot project: fail-fast early stop with artifacts coherent; sharded runs produce expected suite subsets; combined `--changed --shard --exitfirst --parallel --coverage` run
- [ ] **Task 5.2: Full quality gate** — `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest --cov=gd_tools --cov-branch` (>80% line, >70% branch on new code)
- [ ] **Task 5.3: Final Phase Verification & Checkpoint (Refer to workflow.md)**
