# Review: Coverage Addon Version Gate

- **Track:** `20261027-addon-version-mismatch`
- **Type:** `feature`
- **Branch:** `feat/20261027-addon-version-mismatch`
- **Range:** `3d70aa3..424752f`
- **Date:** `2026-10-27`
- **Verdict:** `PASS`

## Summary

The track is ready. `test --coverage` now refuses pre-dispatch with exit 2
and an actionable message when either deployed addon is stale, missing, or
unparseable, while the group-level advisory for all other runs is untouched.
All 7 FRs, 3 NFRs, and 7 ACs are covered by the 8 pinned CliRunner tests; the
read-only reviewer returned zero findings.

## Verification

| Layer | Command | Result | Evidence |
| --- | --- | --- | --- |
| unit (targeted) | `CI=true pytest tests/unit/test_addon_check.py tests/unit/test_coverage_addon_gate.py -q --no-cov` | pass (15/15) | verification/phase-2.md |
| unit (full) | `CI=true pytest tests/unit -q` | fail* (1850 passed, 3 skipped, 2 failed) | primary run 2026-10-27 |
| coverage | same full run with repo addopts | pass (TOTAL 95% line, gate 80%) | primary run 2026-10-27 |
| lint | `ruff check src/ tests/` | pass | primary run 2026-10-27 |
| format | `black --check src/ tests/` | pass (204 unchanged) | primary run 2026-10-27 |
| typecheck | none configured | n/a | workflow config |
| build | `python -m build` | pass | primary run 2026-10-27 |
| integration/e2e | not run | n/a | CLI-dispatch-only diff, no .gd touched; CliRunner covers gate |

\* The 2 full-unit failures are pre-existing release drift outside this diff:
`test_schema::test_checked_in_schema_snapshot_is_current` (checked-in schema
snapshot stale) and `test_version::test_package_version_is_0_8_0` (pins 0.8.0
while the repo is 0.9.0). Neither file is in the track's Touches and neither
was modified (`git diff base..HEAD -- tests/` shows only the new gate test
file). Recorded here, not caused here.

## Requirements

| ID | Implemented by | Verified by | Status |
| --- | --- | --- | --- |
| FR-1 | P2.T1 | `test_stale_coverage_addon_refuses`, `test_unparseable_coverage_version_refuses` | covered |
| FR-2 | P2.T1 | `test_missing_coverage_version_refuses` | covered |
| FR-3 | P2.T1 | `test_stale_native_addon_refuses`, `test_missing_native_version_refuses` | covered |
| FR-4 | P2.T1 | `test_gate_suppressed_by_env_var` | covered |
| FR-5 | P2.T1 | `test_newer_addon_proceeds` | covered |
| FR-6 | P2.T2 | `test_refusal_names_versions_fix_and_abort` | covered |
| FR-7 | P2.T2 | `test_addon_check.py` (7 advisory tests, unchanged) | covered |
| NFR-1 | P2.T3 | refusal tests assert zero dispatch; gate only reads version files | covered |
| NFR-2 | P2.T3 | `test_newer_addon_proceeds` pass-through branch | covered |
| NFR-3 | P2.T3 | gate fail-safe (`except` → `None`) | covered |
| AC-1 | P2.T1 | `test_stale_coverage_addon_refuses` | covered |
| AC-2 | P2.T1 | `test_missing_coverage_version_refuses` | covered |
| AC-3 | P2.T1 | `test_stale_native_addon_refuses`, `test_missing_native_version_refuses` | covered |
| AC-4 | P2.T1 | `test_gate_suppressed_by_env_var` | covered |
| AC-5 | P2.T1 | `test_newer_addon_proceeds` | covered |
| AC-6 | P2.T2 | `test_refusal_names_versions_fix_and_abort` | covered |
| AC-7 | P2.T1 | `test_unparseable_coverage_version_refuses` | covered |

## Findings

### Critical

- none

### High

- none

### Medium

- none

### Low

- none

## Overrides

- none

## Plan compliance

- Phase 1 (P1.T1, P1.T2): verified, checkpoint `b87245b`, evidence `verification/phase-1.md`. RED contract held — no `src/` changes.
- Phase 2 (P2.T1, P2.T2, P2.T3): verified, checkpoint `cab8048`, evidence `verification/phase-2.md`. Pinned tests unmodified.
- Final diff stays within the union of Touches (`src/gd_tools/addon_check.py`, `src/gd_tools/commands/test.py`, both test files) plus reported deviations (evidence files, USER_GUIDE doc sync). No task dropped.

## Out of scope

- The 2 pre-existing full-unit failures (schema snapshot, 0.8.0 version pin) belong to post-release maintenance, not this track.

## Debt

- none

## Doc sync

`updated` — `docs/USER_GUIDE.md` documents the hard gate (commit `424752f`).

## History

| Round | Verdict | Critical | High | Medium | Low | Fixed |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PASS | 0 | 0 | 0 | 0 | 0 |
