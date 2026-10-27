# Phase 1 Verification — Refusal-Gate Regression Tests (Red)

- Track: 20261027-addon-version-mismatch — Coverage Addon Version Gate
- Phase: 1 — Refusal-gate regression tests (red)
- Date: 2026-10-27
- Branch: feat/20261027-addon-version-mismatch
- Base commit: 6afd82c
- Head commit: c7a4af0
- Result: verified (RED: new gate tests fail before fix, as intended)

## Commands

| Layer | Command | Exit | Summary |
| --- | --- | --- | --- |
| static | `black tests/unit/test_coverage_addon_gate.py` | 0 | Reformatted once; clean |
| static | `ruff check tests/unit/test_coverage_addon_gate.py` | 0 | All checks passed |
| static | `black --check tests/unit/test_coverage_addon_gate.py` | 0 | Unchanged, clean |
| unit | `$env:CI = 'true'; pytest tests/unit/test_addon_check.py tests/unit/test_coverage_addon_gate.py -q` | 1 | 9 passed, 6 failed: all 6 new refusal tests fail with `assert 0 == 2` (no gate in `src/` yet); all 7 existing advisory tests plus the 2 pass-through tests pass |

Note: the brief's verification command is written with a POSIX
`CI=true` prefix, which PowerShell rejects. The run above sets
`$env:CI = 'true'` first, which is semantically identical. The
`fail-under=80` coverage error in the output is an artifact of
running a two-file subset (pyproject addopts enforce total
coverage); the load-bearing signal is the 6 red refusal tests.

## Acceptance criteria

| ID | Criterion | Evidence | Status |
| --- | --- | --- | --- |
| AC-1 | Stale coverage addon + `test --coverage` refuses exit 2, zero suites | `test_stale_coverage_addon_refuses` fails with exit 0, mock called (no gate yet) | red (expected) |
| AC-2 | Missing coverage version file refuses exit 2 | `test_missing_coverage_version_refuses` fails with exit 0 | red (expected) |
| AC-7 | Unparseable coverage version treated as stale, exit 2 | `test_unparseable_coverage_version_refuses` fails with exit 0 | red (expected) |
| AC-3 | Stale/missing native test addon refuses exit 2 | `test_stale_native_addon_refuses`, `test_missing_native_version_refuses` fail with exit 0 | red (expected) |
| AC-4 | `GD_TOOLS_NO_UPDATE_CHECK=1` skips the gate | `test_gate_suppressed_by_env_var` passes (exit 0, dispatch called) | pass |
| AC-5 | Deployed addon newer than CLI proceeds | `test_newer_addon_proceeds` passes (exit 0, dispatch called) | pass |
| AC-6 | Refusal names deployed + CLI versions, `gd-tools init` fix, aborted-before-tests note | `test_refusal_names_versions_fix_and_abort` fails with exit 0 | red (expected) |

FR-1/FR-2 covered by AC-1/AC-2/AC-7 tests; FR-3 by the native
addon tests; FR-4 by the suppression test; FR-5 by the message
test; FR-6 by the newer-addon test.

## Evidence paths

- `tests/unit/test_coverage_addon_gate.py` (new, 8 tests, commit c7a4af0)
- `conductor/tracks/20261027-addon-version-mismatch/verification/phase-1.md` (this file)

## Deviations

- None. Only `tests/unit/test_coverage_addon_gate.py` added;
  `src/` untouched per the RED contract. The helper also patches
  `gd_tools.commands.test.__version__` (create=True) alongside
  `gd_tools.addon_check.__version__` and `gd_tools.__version__`
  so the Phase 2 gate passes regardless of which namespace it
  reads the CLI version from.

## Notes

- Tests follow the repo's CliRunner pattern (`test_cli_changed.py`):
  mocked `load_config`, mocked `run_native_test_command`
  (assert not called on refusal), fake project root via
  `tmp_path` addons with monkeypatched `find_project_root`,
  and silenced group-level update/advisory checks.
- Click 8.2.1 merges stderr into `result.output`, so message
  assertions on `result.output` hold for `err=True` output.
- Existing `tests/unit/test_addon_check.py` (7 tests) all pass;
  no existing behavior changed.

## Primary verification

- `$env:CI='true'; pytest tests/unit/test_addon_check.py tests/unit/test_coverage_addon_gate.py -q -p no:cacheprovider` → exit 1, 6 failed / 9 passed. All 6 failures are `assert 0 == 2` in the new refusal tests (RED as intended); all existing + pass-through tests green.
- `ruff check src/ tests/` → clean. `black --check src/ tests/` → 204 files unchanged.
- `git diff --name-only 6afd82c..HEAD` → only `tests/unit/test_coverage_addon_gate.py`; no `src/` changes. Touches respected.
- Note: the "FR-5 by the message test; FR-6 by the newer-addon test" sentence above has the IDs swapped (FR-5 = newer-addon allowed, FR-6 = message content); the AC table itself is correct.
