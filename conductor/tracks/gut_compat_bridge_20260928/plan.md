# Implementation Plan — GUT Compatibility Bridge

- **Track ID:** `gut_compat_bridge_20260928`
- **Branch:** `feature/gut-compat-bridge-20260928`
- **Method:** TDD per `conductor/workflow.md` — failing tests first (Red),
  minimum implementation to pass (Green), coverage verification, commit with
  git note per task, checkpoint at every phase boundary.

---

## Phase 1 — Discovery Routing & Bridge Classification (Python) [checkpoint: 38faa28]

- [x] Task: Write failing tests for suite classification (RED)
  - `extends GdToolsTest` → native suite; `extends GutTest` → bridge suite;
    neither → explicit per-file error; mixed manifest ordering is stable
  - Orchestrator builds a plan containing both suite kinds in one invocation
- [x] Task: Implement routing in `native_test/discovery.py` + orchestrator (GREEN)
- [x] Task: Verify coverage ≥80/70 for new code; commit + git note
  (commit `00afbe1`)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  (checkpoint `38faa28`)

## Phase 2 — Preflight Static Scan & GUT-Free Rule (Python) [checkpoint: 6e2be56]

- [x] Task: Write failing tests for the unsupported-construct scanner (RED)
  - Per-category detection (mocking, parameterization, mock-assertions,
    property/orphan/interactive, engine-error asserts), per-file reporting,
    exit code 2 with actionable guidance
- [x] Task: Implement scanner and wire into bridge preflight path (GREEN)
  (commit `6c84c41`)
- [x] Task: Write failing tests for the `addons/gut` present → error rule
      (FR-5), then implement (GREEN) (commit `17a56bd`)
- [x] Task: Verify coverage; commit + git note (commit `17a56bd`)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  (checkpoint `6e2be56`)

## Phase 3 — GutTest Shim Base Class (GDScript) [checkpoint: 1fd5937]

- [x] Task: Add fixture GUT-style suites to `tests/fixtures/projects` +
      failing e2e tests asserting bridge behaviour (RED)
- [x] Task: Implement `gd_tools_gut_bridge.gd` shim (`class_name GutTest`),
      six lifecycle hooks incl. `prerun_setup`/`postrun_teardown` (GREEN)
- [x] Task: Implement core assertion aliases reusing native assertions (GREEN)
- [x] Task: Implement signal family (`watch_signals` + signal assertion set) (GREEN)
- [x] Task: Implement async helpers (bounded `wait_*`, `yield_*` aliases) (GREEN)
- [x] Task: Verify e2e green; commit + git note
  (commit `3a9fd2e`)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  (checkpoint `1fd5937`)

## Phase 4 — Result Normalization, Orchestration & Coverage [checkpoint: e40cbf8]

- [x] Task: Write failing tests for bridge→native result normalization
      (statuses, JUnit XML, artifacts index, exit codes, mixed runs) (RED)
- [x] Task: Implement normalization in `native_test/command.py` /
      `orchestrator.py` + runner side (GREEN)
- [x] Task: Write failing tests for coverage on bridge suites, then implement
      (tracker, plan schema v1, no GUT autoload) (RED→GREEN)
- [x] Task: Verify coverage; commit + git note (commit `5be845a`)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
      (checkpoint `e40cbf8`)

## Phase 5 — Legacy Path Removal & Deprecation Diagnostics (Python/CLI)

- [ ] Task: Write failing tests: `--runtime gut` CLI value and
      `test.runtime = "gut"` config rejected with migration guidance; legacy
      subprocess path gone from `test_runner.py` (RED)
- [ ] Task: Implement removal + bridge-run migration notice in output (GREEN)
- [ ] Task: Write failing doctor tests, then update `doctor.py` (GUT checks
      relaxed to optional/bridge-aware) (RED→GREEN)
- [ ] Task: Verify coverage; commit + git note
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 6 — Documentation & Truth Pass

- [ ] Task: Write `docs/gut-migration.md` (supported subset, failing
      constructs, migration steps; linked from diagnostics)
- [ ] Task: Update `docs/ROADMAP.md` Phase 3 checkboxes to delivered; update
      `ARCHITECTURE.md` Known Limitations
- [ ] Task: Update README/CLI help touchpoints referencing the legacy runtime
- [ ] Task: Final verification: full suite (`CI=true pytest`), `ruff check`,
      `black --check`, e2e green; commit
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
