# Implementation Plan: Migration Tooling (Roadmap §8 Phase 4)

**Track ID:** `migration_tooling_20260929`
**Spec:** [./spec.md](./spec.md)
**Workflow:** `conductor/workflow.md` (TDD mandatory; phases end with verification checkpoints)

---

## Phase 1: Analysis Engine `[checkpoint: 623d210]`

- [x] Task: Migration scanner and report model *(TDD: Red → Green → Refactor)* — `0524984`
  - [ ] Write failing tests: reusing `native_test/bridge_scan.py`, build a migration report model (per-file: base class, supported constructs, unsupported constructs with file:line + guidance, bridge-only aliases)
  - [ ] Implement `src/gd_tools/migration/` scanner module
  - [ ] Verify coverage (pytest --cov, >80% line / >70% branch)
- [x] Task: `.gutconfig.json` option mapping inventory *(TDD)* — `cd80792`
  - [ ] Write failing tests defining the known-option → `[test]` key mapping table and unmapped-option passthrough
  - [ ] Implement the mapping module (explicit table; unknown options reported, never dropped)
  - [ ] Verify coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Report Rendering & Config Translation

- [x] Task: Rich report rendering *(TDD)* — `3b74579`
  - [ ] Write failing tests: per-file inventory, "works now, rename later" alias section, config mapping results, unified diff display, summary
  - [ ] Implement report renderer following `output.py` conventions
  - [ ] Verify coverage
- [x] Task: Config translation (merge, never clobber) *(TDD)* — `43e3083`
  - [ ] Write failing tests: merge into existing `[test]` section, preserve user-set values, report conflicts and unmapped options, no-op when `.gutconfig.json` absent
  - [ ] Implement translation using existing config save/validate machinery
  - [ ] Verify coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Rewrites (`--apply`)

- [ ] Task: Base-class rename rewriter + diff generation *(TDD)*
  - [ ] Write failing tests: `extends GutTest` → `extends GdToolsTest` rename; files with unsupported constructs are never rewritten; diff generation
  - [ ] Implement rewriter
  - [ ] Verify coverage
- [ ] Task: Atomic apply flow *(TDD)*
  - [ ] Write failing tests: `--apply` writes only proposed changes, per-file atomic writes, failure leaves files untouched, `--config-only` scope limiting
  - [ ] Implement apply orchestration
  - [ ] Verify coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: CLI Integration & Documentation

- [ ] Task: `gd-tools migrate` command wiring *(TDD)*
  - [ ] Write failing tests: command registration, flags (`--apply`, `--config-only`), exit codes (0 nothing to migrate / 1 findings / 2 infrastructure error), discovery reuse from test config
  - [ ] Implement CLI command in `cli.py`
  - [ ] Verify coverage
- [ ] Task: Documentation
  - [ ] Update `docs/gut-migration.md` (replace the "arrives with migration tooling" promise with real usage)
  - [ ] Update README and USER_GUIDE as applicable
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
