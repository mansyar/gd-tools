# Plan: v0.6.0 Legacy Sweep

Methodology per `conductor/workflow.md`: TDD for source-code tasks (Red → Green), full-suite verification, commit + git note per task, phase checkpoints with manual user verification.

## Phase 1 — GUT Remnant Audit (read-only) [checkpoint: f322f2b]

- [x] Task: Build the GUT remnant inventory for `src/gd_tools/`
  - Grep every `gut`/`Gut`/`GUT` reference across `src/`
  - Classify each hit: **remove** (dead) vs **keep** (intentional: doctor advisory, `migrate`, v0.6.0 rejection errors, version report if still justified)
  - Record the classification table with rationale in `plan.md`
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — checkpoint f322f2b

## Phase 2 — Dead Code Removal [checkpoint: 3125b85]

- [x] Task: Write guard tests first (Red) — commit 0c0ff67
  - Guard test asserting `GUT_VERSION_MAP` / `get_gut_version_for_godot` no longer exist in `gd_tools.godot`
  - Guard test asserting no `src/gd_tools/` module references removed symbols
  - Confirm tests fail before removal
- [x] Task: Remove verified-dead code (Green) — commit 7a43e3e
  - `godot.py`: `GUT_VERSION_MAP`, `get_gut_version_for_godot`, fix module docstring
  - Audit-listed candidates: `GUTNotInstalledError` (`errors.py`), `is_gut_installed` + legacy-runner display remnants (`test_runner.py`), stale docstrings — only those proven unreferenced
  - Update any existing tests referencing removed code; run full suite
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — checkpoint 3125b85

## Phase 3 — Config Cleanup [checkpoint: 9285f1e]

- [x] Task: Write failing config tests (Red) — commit 472b2e3
  - Test that a TOML with `[test] gutconfig = "..."` fails validation as an unknown key (per existing config error conventions)
- [x] Task: Remove the `gutconfig` field and regenerate schema (Green) — commit 5f5595c
  - Remove field from `config.py` Pydantic model (keep `runtime`, single-valued `"native"`)
  - Regenerate `docs/gd-tools.schema.json`; keep the schema sync test green
  - Full test suite green
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — checkpoint 9285f1e

- [ ] Task: Living-docs sweep
  - `README.md`, `docs/USER_GUIDE.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`: remove/fix GUT-era claims contradicting v0.6.0 (config tables, examples, runtime references)
  - Historical docs (`TDD.md`, `ROADMAP_v1.md`, `SPIKE_*.md`) untouched
- [ ] Task: Retire Roadmap Track 32
  - Mark "Configurable Version Mapping" obsolete in `docs/ROADMAP.md` with rationale
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Audit Table (Phase 1 output)

| # | Symbol / Surface | File | Class | Rationale |
|---|------------------|------|-------|-----------|
| 1 | `GUT_VERSION_MAP`, `get_gut_version_for_godot` | `godot.py:109-142` | REMOVE | Zero references outside own module; module docstring also still advertises GUT mapping |
| 2 | `GUTNotInstalledError` | `errors.py:56` | REMOVE | Zero usages in `src/`; only `tests/unit/test_errors.py` references it |
| 3 | `is_gut_installed` | `test_runner.py:75-87` | REMOVE | Zero usages |
| 4 | `versions["gut"]` + `get_installed_gut_version` | `version.py:15,38-43`, `init.py:97-110` | REMOVE (user-confirmed 2026-10-02) | GUT is no longer a component; doctor advisory covers legacy detection with better guidance; `version --json` shape change accepted |
| 5 | `"--- GUT stdout/stderr ---"` labels + docstring wording | `test_runner.py:96-97,156-168` | FIX (user-confirmed 2026-10-02) | Rename to `"--- Godot stdout/stderr ---"` — output comes from the native headless Godot process |
| 6 | `RuntimeMode.GUT` | `native_test/protocol.py:53` | KEEP | Live migration taxonomy: `discovery.py` tags `extends GutTest` suites, `migration/scan.py:113` selects them |
| 7 | `check_legacy_gut` advisory | `doctor.py:192-258` | KEEP | Intentional migration advisor (informational, never fails) |
| 8 | `gd-tools migrate` + `migration/*` gutconfig translation | `cli.py`, `migration/` | KEEP | Permanent migration path (v0.6.0 design) |
| 9 | `"gut"` CLI choice + rejection errors, `_reject_gut_runtime`, discovery guidance | `cli.py:493,583-629,1283-1289`, `config.py:83-106`, `native_test/discovery.py:130` | KEEP | Intentional v0.6.0 removal UX |
| 10 | `init.py` module docstring ("Optionally installing and enabling the legacy GUT runtime") | `init.py:7` | FIX | Stale self-description; reword to reflect native-only init |
| 11 | `TestResult` docstring ("from a GUT run", "GUT stdout/stderr" attrs) | `test_runner.py:42-58` | FIX | Stale wording; model now serves the native runtime |

**Test impact inventory:** `tests/unit/test_godot.py:493-531` (GUT map tests → delete), `tests/unit/test_errors.py` (GUTNotInstalledError import/test → remove), `tests/unit/test_version.py` (5 `get_installed_gut_version` mocks → rewrite), `tests/unit/test_init.py:71-98` (gut version tests → delete), `tests/unit/test_test_runner.py:208-209` + failure-path label assertions (→ update to "Godot stdout"), `tests/unit/test_config.py:78,232` (gutconfig field assertions → update in Phase 3).

## Implementation Notes

_Appended per task per workflow.md (commit SHAs, deviations)._

- **Phase 1** (audit): classifications recorded above; user confirmed remove `versions["gut"]` and rename output labels to `--- Godot stdout/stderr ---`. Baseline suite (not e2e): 1418 passed / 7 skipped, one **pre-existing** failure (`test_checked_in_schema_snapshot_is_current`, schema snapshot drifted from config model in v0.6.0) — assigned to Phase 3. Checkpoint f322f2b.
- **Phase 2** (removal): guards in `tests/unit/test_gut_removal_guards.py` (Red 0c0ff67; initial label guard false-passed due to `\n` prefix in source literals, tightened to unanchored substrings). Green 7a43e3e removed the five dead symbols + stale docstrings/labels across `godot.py`, `errors.py`, `test_runner.py`, `version.py`, `init.py` (incl. orphaned `configparser` import); updated `test_godot.py`, `test_errors.py`, `test_version.py`, `test_init.py`, `test_test_runner.py`. ruff (3 orphaned imports fixed), black, 1412 passed, coverage gate held. Checkpoint 3125b85.
- **Phase 3** (config): Red 472b2e3 — two guard tests (`TestConfig(gutconfig=...)` → ValidationError; TOML via `load_config` → ConfigError, the tool's exit-code-2 wrapper). Green 5f5595c — field + docstring removed, `runtime: Literal["native"]` retained; `docs/gd-tools.schema.json` regenerated via `gd-tools config schema --output`, which also resolved the pre-existing snapshot-drift failure. Full suite 1415 passed / 7 skipped, coverage 94.84%, ruff/black clean.
