# Implementation Plan — Flaky Tests in Machine-Readable Outputs

**Track:** `flaky_machine_outputs_20261016`
**Methodology:** TDD per `conductor/workflow.md` — Red (failing tests) before
Green (implementation) in every phase, followed by the Phase Completion
Verification and Checkpointing Protocol.

## Phase 1 — JUnit flaky properties (FR-1)

- [x] Task: Red — failing tests for `_write_junit_xml` flaky `<properties>`
  in `tests/unit/test_native_command.py`: a flaky case gains
  `flaky=true`/`attempts=N` properties; a non-flaky run's XML is
  byte-identical to today; quiet-mode runs still carry the properties.
- [x] Task: Green — implement in `_write_junit_xml` [7c589ff]
  (`src/gd_tools/native_test/command.py`) via `is_flaky()`; run targeted
  tests plus `ruff check` and `black --check` on touched files.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)

## Phase 2 — artifacts.json flaky fields (FR-2) [checkpoint: 45161b0]

- [ ] Task: Red — failing tests for `publish_artifact_index` flaky fields in
  `tests/unit/test_native_artifacts.py` (per-test `flaky`/`attempts` plus
  top-level summary, additive keys, no version bump), plus orchestrator
  threading coverage including parallel-merge aggregation across workers.
- [ ] Task: Green — implement the additive keys in
  `src/gd_tools/native_test/artifacts.py`, thread through the orchestrator's
  publication call sites; run targeted tests plus `ruff check` and
  `black --check`.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)

## Phase 3 — Docs + full verification (FR-3 – FR-5, acceptance 2–5)

- [ ] Task: Update the `USER_GUIDE.md` flaky section and `ARCHITECTURE.md`
  §9.5 / JUnit docs with the new machine-readable fields.
- [ ] Task: Run full gates — `CI=true pytest` (unit + integration),
  `ruff check src/ tests/`, `black --check src/ tests/`, coverage >80% line
  / >70% branch on changed modules; confirm exit-code behavior unchanged
  (flaky-pass = 0) and non-flaky output byte-identical.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
