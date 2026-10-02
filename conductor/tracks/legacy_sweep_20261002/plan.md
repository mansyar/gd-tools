# Plan: v0.6.0 Legacy Sweep

Methodology per `conductor/workflow.md`: TDD for source-code tasks (Red → Green), full-suite verification, commit + git note per task, phase checkpoints with manual user verification.

## Phase 1 — GUT Remnant Audit (read-only)

- [ ] Task: Build the GUT remnant inventory for `src/gd_tools/`
  - Grep every `gut`/`Gut`/`GUT` reference across `src/`
  - Classify each hit: **remove** (dead) vs **keep** (intentional: doctor advisory, `migrate`, v0.6.0 rejection errors, version report if still justified)
  - Record the classification table with rationale in `plan.md`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Dead Code Removal

- [ ] Task: Write guard tests first (Red)
  - Guard test asserting `GUT_VERSION_MAP` / `get_gut_version_for_godot` no longer exist in `gd_tools.godot`
  - Guard test asserting no `src/gd_tools/` module references removed symbols
  - Confirm tests fail before removal
- [ ] Task: Remove verified-dead code (Green)
  - `godot.py`: `GUT_VERSION_MAP`, `get_gut_version_for_godot`, fix module docstring
  - Audit-listed candidates: `GUTNotInstalledError` (`errors.py`), `is_gut_installed` + legacy-runner display remnants (`test_runner.py`), stale docstrings — only those proven unreferenced
  - Update any existing tests referencing removed code; run full suite
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Config Cleanup

- [ ] Task: Write failing config tests (Red)
  - Test that a TOML with `[test] gutconfig = "..."` fails validation as an unknown key (per existing config error conventions)
- [ ] Task: Remove the `gutconfig` field and regenerate schema (Green)
  - Remove field from `config.py` Pydantic model (keep `runtime`, single-valued `"native"`)
  - Regenerate `docs/gd-tools.schema.json`; keep the schema sync test green
  - Full test suite green
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Docs Truth Pass & Track 32 Retirement

- [ ] Task: Living-docs sweep
  - `README.md`, `docs/USER_GUIDE.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`: remove/fix GUT-era claims contradicting v0.6.0 (config tables, examples, runtime references)
  - Historical docs (`TDD.md`, `ROADMAP_v1.md`, `SPIKE_*.md`) untouched
- [ ] Task: Retire Roadmap Track 32
  - Mark "Configurable Version Mapping" obsolete in `docs/ROADMAP.md` with rationale
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Audit Table (Phase 1 output)

_To be filled during Phase 1: symbol | file | classification (remove/keep) | rationale._

## Implementation Notes

_Appended per task per workflow.md (commit SHAs, deviations)._
