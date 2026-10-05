# Track Plan: Snapshot Testing in the Native Runtime

- **Track ID:** `snapshot_testing_20261005`
- **Branch:** `feature/snapshot-testing-20261005`
- **Workflow:** TDD mandatory (Red → Green → optional Refactor). Coverage
  targets for new source: >80% line, >70% branch. Conventional commits with
  git-note summaries; phase checkpoints per `conductor/workflow.md`.

## Phase 1 — Snapshot Serialization Core (GDScript runtime) [checkpoint: f3c3d7d]

- [x] Task: Write failing tests for value serialization (Red) (bb19cfc)
  - Primitives, Arrays, Dictionaries with sorted keys, nested structures
  - Byte-identical output across repeated runs
- [x] Task: Implement deterministic value serializer (Green) (bb19cfc)
- [x] Task: Write failing tests for Object property dump & Node scene-tree dump (Red) (f2556cb)
  - Recursive property serialization; indented tree rendering (path, class, properties)
- [x] Task: Implement object & node-tree serialization (Green) (f2556cb)
- [x] Task: Write failing tests for cycle-safety & reference rendering (Red) (7522e7c)
- [x] Task: Implement cycle-safe reference rendering (Green) (7522e7c)
- [x] Task: Refactor pass — extract shared serialization helpers, style-guide conformance (7522e7c)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Snapshot Store & assert_snapshot API (GDScript runtime)

- [x] Task: Write failing tests for snapshot store (Red) (4b77a2e)
  - Versioned header, `.gd-tools/snapshots/<suite>/<test>/<name>.snap` layout,
    LF enforcement, malformed-file diagnostics
- [x] Task: Implement snapshot store read/write (Green) (4b77a2e)
- [x] Task: Write failing tests for `assert_snapshot` (Red) (26c72fa)
  - Auto-naming (`<test>_<call_index>`), explicit names, first-run auto-write
    + pass, mismatch fail with unified diff, I/O error fail-closed
- [x] Task: Implement `assert_snapshot` in `GdToolsTest` with failure diagnostics (Green) (26c72fa)
- [x] Task: Write failing tests for parallel/watch/changed-mode compatibility (Red) (26c72fa)
- [x] Task: Fix parallel/watch/changed-mode compatibility (Green) (26c72fa)
- [x] Task: Refactor pass — failure message consistency with existing `assert_*` diagnostics (e3a56e3)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Python CLI & Reporting

- [x] Task: Write failing tests for `gd-tools test --snapshot-update` (Red) (dfe2824)
- [x] Task: Implement flag pass-through to native runtime & update semantics (Green) (dfe2824)
- [x] Task: Write failing tests for summary counts & obsolete detection (Red) (c93d875)
  - written / passed / failed / obsolete counts; obsolete = stored snapshots
    with no owning suite/test in the run
- [x] Task: Implement summary reporting & obsolete detection (Green) (c93d875)
- [x] Task: Write failing tests for `gd-tools clean --snapshots` (Red) (1a52026)
- [x] Task: Implement `gd-tools clean --snapshots` (Green) (1a52026)
- [ ] Task: Refactor pass — reporting alignment with existing summary/artifact patterns
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Docs & Final Verification

- [ ] Task: README — snapshot testing usage section + example suite
- [ ] Task: ARCHITECTURE — snapshot subsystem description (storage,
  serialization tiers, protocol touchpoints)
- [ ] Task: Update JSON schema / config docs if any config surface was added
- [ ] Task: Full verification — `CI=true pytest`, `ruff check`, `black --check`,
  coverage targets, Definition-of-Done sweep
- [~] Task: Phase Verification & Checkpoint (Refer to workflow.md)
