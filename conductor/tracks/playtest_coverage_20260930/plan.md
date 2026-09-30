# Implementation Plan: Coverage During Playtesting

**Track ID:** `playtest_coverage_20260930`
**Branch:** `feature/playtest-coverage-20260930`
**Spec:** [./spec.md](./spec.md)
**Workflow:** [conductor/workflow.md](../../workflow.md) — TDD mandatory, plan is source of truth.

**Commands:**
- Install: `pip install -e ".[dev]"`
- Tests: `CI=true pytest` (announce before each run)
- Lint: `ruff check src/ tests/` and `black --check src/ tests/`
- Commits: `feat(coverage): <description>` per task; plan updates via `conductor(plan): ...`

---

## Phase 1 — Addon Playtest Mode (`coverage.gd`)

- [x] Task 1.1: Write failing integration tests for playtest mode in
  `tests/integration/test_coverage_playtest.py` — Python-driven real-Godot runs
  mirroring `tests/e2e/test_native_runtime.py` conventions (this is the live way
  to exercise addon GDScript since the GUT-era e2e drivers were removed in
  `99e7779`; amends the originally planned `tests/unit/test_coverage_tracker.gd`
  location, which has no live driver):
  - [ ] `GD_TOOLS_COVERAGE_PLAYTEST=1` activates playtest mode
  - [ ] Periodic flush writes the output file at the configured interval
  - [ ] Exit flush on `NOTIFICATION_WM_CLOSE_REQUEST` finalizes and writes data
  - [ ] Playtest mode is inactive when the env var is unset (no behavior change
        for test runs)

  **Expected fail:** playtest mode does not exist yet (Red).

- [x] Task 1.2: Implement playtest mode in
  `src/gd_tools/addons/gd-tools-coverage/coverage.gd` (`1fec960`):
  - [ ] Env-activated mode (`GD_TOOLS_COVERAGE_PLAYTEST=1`)
  - [ ] SceneTree timer driving periodic flush (default 5s, interval via env)
  - [ ] `NOTIFICATION_WM_CLOSE_REQUEST` handling for exit flush
  - [ ] Non-blocking, small writes (NFR-1)

  **Expected pass:** Task 1.1 tests go green (Green).

- [x] Task 1.3: Refactor + regression:
  - [ ] Existing tracker/instrumentation tests stay green (hook path unaffected)
  - [ ] Coverage gates on affected Python code still met

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  [checkpoint: 99fe07f]

---

## Phase 2 — Python Playtest Orchestrator (`coverage/playtest.py`)

- [x] Task 2.1: Write failing unit tests (mocked Godot process) for
  `run_playtest_coverage(config, scene, timeout) -> ReportResult`:
  - [ ] Coverage plan generated with full-project scope (FR-3)
  - [ ] Env setup: `GD_TOOLS_COVERAGE_PLAN`, `GD_TOOLS_COVERAGE_OUTPUT`,
        `GD_TOOLS_COVERAGE_PLAYTEST=1`
  - [ ] Windowed (non-headless) launch, no `--headless` flag (FR-2)
  - [ ] Scene resolution: explicit `--scene` used as-is; omitted → main scene
        read from `project.godot` (FR-1)
  - [ ] Process wait for game exit

  **Expected fail:** `playtest.py` does not exist yet (Red).

- [x] Task 2.2: Implement `src/gd_tools/coverage/playtest.py` reusing existing
  godot-runner and plan-generator seams (Green) (`5cc7fb1`).

- [x] Task 2.3: Refactor + coverage-gate check for the new module
  (>80% line / >70% branch) — 85% line at Phase 2; the remaining 4
  uncovered lines/branches are exactly the Phase 3 error paths, gate
  re-checked at the Phase 3 checkpoint.

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  [checkpoint: 0c83394]

---

## Phase 3 — Result Collection & Exit Semantics

- [x] Task 3.1: Write failing unit tests for:
  - [ ] Clean exit → output file collected, report generated (FR-5)
  - [ ] Crash/kill with periodic data on disk → report from last snapshot
        **with warning** (FR-6)
  - [ ] `--timeout N` → game auto-closed after N seconds (FR-1)
  - [ ] `--min N` → exit 1 when session coverage below threshold (FR-7)
  - [ ] Exit 2 structured diagnostics: invalid scene, missing project, launch
        failure (FR-7)

  **Expected fail:** result-handling logic does not exist yet (Red).

- [x] Task 3.2: Implement result handling in `playtest.py` (`3f06138`):
  - [ ] Partial-data recovery from periodic flush output
  - [ ] Timeout kill of the game process
  - [ ] Threshold gate and exit-code contract 0/1/2

  **Expected pass:** Task 3.1 tests go green (Green).

- [x] Task 3.3: Refactor + route collected data through
  `generate_coverage_report` so all existing `--report-format` outputs work
  unchanged (FR-5), with regression tests — collection already flows through
  the same `read_plan_json`/`read_coverage_json`/`generate_report` seam used
  by `generate_coverage_report`; regression: 202 unit+integration tests green,
  text/html/lcov formats exercised.

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  [checkpoint: 5a02475]

---

## Phase 4 — CLI Wiring (`coverage run`)

- [x] Task 4.1: Write failing CLI unit tests:
  - [ ] `coverage run` accepts `--scene`, `--timeout`, `--min`,
        `--report-format` (FR-1)
  - [ ] Help text documents the subcommand and flags
  - [ ] Argument validation errors → exit 2 (FR-7)

  **Expected fail:** subcommand does not exist yet (Red).

- [x] Task 4.2: Wire `coverage run` into the coverage command group in
  `src/gd_tools/cli.py`, calling the playtest orchestrator (Green)
  (`6012692`).

- [x] Task 4.3: Refactor + full unit suite green (106/106 CLI tests).

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  [checkpoint: f1f015a]

---

## Phase 5 — Integration Test, Docs & Release Polish

- [x] Task 5.1: Integration test for the CLI path (windowed launch, `--timeout`
  auto-close) using a prepared fixture project (real Godot; runs in CI like the
  other integration tests — Godot is present via the `install-godot` action).
  Implemented as `tests/integration/test_coverage_playtest_cli.py` (clean-exit
  scene + lingering scene closed by `--timeout 15`); the ubuntu CI leg now
  runs under `xvfb-run` since the windowed launch needs a display server;
  the Phase 1 integration file also gained its missing `pytestmark`
  (CI would have silently deselected it) (`e486f2c`).

- [x] Task 5.2: Documentation (NFR-4):
  - [ ] USER_GUIDE playtest-coverage section
  - [ ] README feature mention
  - [ ] CHANGELOG entry

- [x] Task 5.3: Full verification:
  - [ ] `CI=true pytest` green
  - [ ] `ruff check src/ tests/` clean
  - [ ] `black --check src/ tests/` clean
  - [ ] Coverage gates met on `src/gd_tools/`
  - [ ] Manual playtest smoke-test checklist presented to the user

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
