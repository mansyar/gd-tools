# Implementation Plan: GUT Bridge Removal (v0.6.0)

**Track:** `gut_bridge_removal_20261001` · **Branch:** `feature/gut-bridge-removal-20261001`
**Methodology:** TDD per `workflow.md` — every task: Red (failing tests) →
Green (implementation) → commit → git note → plan update.

## Phase 1: Bridge Runtime Removal

- [x] Task: Write failing removal-behavior tests (Red) `4be1f0d`
  - [ ] Test: discovery rejects `extends GutTest` suites (exit 2, file named, migration guidance)
  - [ ] Test: `--runtime gut` exits 2 with the v0.6.0 removal message
  - [ ] Test: test preflight rejects `runtime = "gut"` config with migration guidance
  - [ ] Confirm all new tests fail (Red) before proceeding
- [ ] Task: Remove the `GutTest` shim and bridge routing (Green)
  - [ ] Delete the shim GDScript from `src/gd_tools/addons/gd-tools-test/`
  - [ ] Remove bridge routing/normalization from `native_test/` (discovery, orchestrator, command)
  - [ ] Implement the explicit discovery/preflight error with migration guidance
  - [ ] Keep `native_test/bridge_scan.py` (migrate dependency)
- [ ] Task: Implement `--runtime gut` explicit error in `cli.py`; remove `init --with-gut`
  - [ ] `--runtime gut` → exit 2, v0.6.0 removal message + `gd-tools migrate` pointer
  - [ ] Delete `--with-gut` option and its scaffolding path; remove deprecation notices in `command.py` / `init.py`
- [ ] Task: Remove bridge-only tests and fixtures
  - [ ] Delete bridge unit/integration/e2e tests and `.gutconfig.json` / GUT-project fixtures not used by `migrate` tests
  - [ ] Verify full suite green: `CI=true pytest`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Doctor Advisor, Config Validation & Migrate Updates

- [ ] Task: Write failing tests (Red) for doctor/config/migrate behavior
  - [ ] Test: `doctor` reports legacy GUT artifacts (`addons/gut`, `.gutconfig.json`, `GutTest` suites) as informational migration advice
  - [ ] Test: `config validate` hard-errors on `runtime = "gut"` and GUT-era keys (exit 2, guidance)
  - [ ] Test: `gd-tools migrate` retains report/translate/apply behavior; guidance text is v0.6.0-aware
- [ ] Task: Implement doctor migration advisor (Green) — remove bridge-health/deprecation checks from `doctor.py`, add advisory detection
- [ ] Task: Implement hard config validation (Green) — validator + preflight produce exit-2 errors with migration guidance
- [ ] Task: Update `gd-tools migrate` guidance text for v0.6.0 (bridge no longer exists; migration required)
- [ ] Task: Verify coverage gate (≥80% line / ≥70% branch) and full suite green
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Docs Truth Pass & v0.6.0 Release Prep

- [ ] Task: Documentation truth pass
  - [ ] Update `docs/gut-migration.md` (removal reality, migrate as the path)
  - [ ] Update README, USER_GUIDE, ARCHITECTURE, PRD, `gd-tools.schema.json` (runtime enum), ROADMAP Phase 5 checkbox
- [ ] Task: Release preparation
  - [ ] Bump version to 0.6.0 in `pyproject.toml`
  - [ ] Write CHANGELOG v0.6.0 release section (breaking removal headline)
- [ ] Task: Final verification — `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest --cov=gd_tools --cov-branch`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
