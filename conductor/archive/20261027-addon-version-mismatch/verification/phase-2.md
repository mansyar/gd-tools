# Phase 2 Evidence — Strict version gate in coverage dispatch

- Track: 20261027-addon-version-mismatch — Coverage Addon Version Gate
- Phase: 2 (P2.T1, P2.T2)
- Date: 2026-10-27
- Branch: feat/20261027-addon-version-mismatch
- Base: 9bef49b
- Head: 925f78a
- Result: verified

## What changed

- `src/gd_tools/addon_check.py`: added `check_coverage_addon_gate()`
  plus `COVERAGE_ADDON_DIR` / `NATIVE_ADDON_DIR` constants and two
  message builders. The gate compares both deployed `_version.txt`
  files against the CLI version, honors `GD_TOOLS_NO_UPDATE_CHECK=1`,
  treats missing / unparseable / older as refusal, lets newer or
  matching versions pass, and never raises (unexpected errors return
  `None` so callers keep existing behavior). The existing advisory
  `check_addon_version()` is untouched.
- `src/gd_tools/commands/test.py`: the `test --coverage` path calls
  the gate after `load_config` and `PRE_DISPATCH` validation but before
  any watch/native dispatch. On refusal it echoes the message to stderr
  and exits 2. Plain `test` (no `--coverage`) never reaches the gate.

## Commands

| Layer | Command | Exit | Summary |
|---|---|---|---|
| unit | `CI=true pytest tests/unit/test_addon_check.py tests/unit/test_coverage_addon_gate.py -q` (via `$env:CI` pwsh equivalent) | 1 | 15/15 tests passed; exit 1 is only the pytest-cov `fail-under=80` threshold tripping on a 2-file subset (23% total). No test failed. |
| unit | Same two files with `--no-cov` | 0 | 15 passed (7 advisory + 8 gate). All 6 previously-red gate tests now green. |
| unit | Full `tests/unit --no-cov` | 1 | 1850 passed, 3 skipped, 2 failed — both pre-existing and unrelated (see notes). |
| static | `ruff check` on both touched files + both test files | 0 | All checks passed. |
| static | `black --check` on the same four files | 0 | Clean (one cosmetic rewrap of `addon_check.py` applied first). |
| manual | Quiet/stale probe via `CliRunner` (repo `src` on path) | n/a | `--quiet test --coverage` with stale addons: exit 2, zero dispatch calls, message contains `gd-tools init` and abort note. Plain `test`: exit 0, dispatches normally. |

## Acceptance criteria

| ID | Criterion | Evidence | Status |
|---|---|---|---|
| AC-1 | Stale coverage addon + `--coverage` → exit 2, zero suites run | `test_stale_coverage_addon_refuses` passes; gate returns refusal before dispatch | pass |
| AC-2 | Missing coverage version file + `--coverage` → exit 2 | `test_missing_coverage_version_refuses` passes | pass |
| AC-3 | Stale/missing native test addon + `--coverage` → exit 2 | `test_stale_native_addon_refuses`, `test_missing_native_version_refuses` pass | pass |
| AC-4 | `GD_TOOLS_NO_UPDATE_CHECK=1` skips the gate, run proceeds | `test_gate_suppressed_by_env_var` passes | pass |
| AC-5 | Newer deployed addon → run proceeds, no refusal | `test_newer_addon_proceeds` passes | pass |
| AC-6 | Refusal names deployed + CLI versions, `gd-tools init` fix, aborted-before-tests note | `test_refusal_names_versions_fix_and_abort` passes; message: `Error: <label> addon is outdated (v<deployed> deployed, v<cli> installed). Run \`gd-tools init\` to update. Aborted before running tests.` | pass |
| AC-7 | Unparseable version file treated as stale (exit 2) | `test_unparseable_coverage_version_refuses` passes (`except (TypeError, ValueError)` → refusal) | pass |
| FR-7 | Advisory group warning unchanged for non-coverage runs | All 7 `test_addon_check.py` tests pass; `check_addon_version()` unmodified; manual probe shows plain `test` dispatches | pass |

## Evidence paths

- `src/gd_tools/addon_check.py` (gate + message builders)
- `src/gd_tools/commands/test.py` (pre-dispatch wiring)
- `tests/unit/test_coverage_addon_gate.py` (pinned contract, unmodified)
- `tests/unit/test_addon_check.py` (advisory regression net)
- `conductor/tracks/20261027-addon-version-mismatch/verification/phase-1.md` (red baseline this phase turns green)

## Deviations

- Ran the POSIX `CI=true ...` verification via the `$env:CI='true'; ...`
  PowerShell equivalent (same approach as phase-1); semantics identical.
- Added a `--no-cov` rerun of the targeted files: the repo enforces
  `fail-under=80`, which any 2-file subset run trips regardless of test
  outcome. The rerun isolates the real signal (15 passed, exit 0).
- `black` rewrapped one long line in `addon_check.py`; no logic change.
- Manual `--quiet`/plain-`test` probes ran from the approved temp dir with
  repo `src` on `sys.path` (the installed dist shadows repo sources when
  running ad-hoc scripts; pytest resolves repo sources). Probe scripts were
  deleted after use.
- Full `tests/unit` shows 2 failures outside this phase's scope:
  `test_schema.py::test_checked_in_schema_snapshot_is_current` and
  `test_version.py::test_package_version_is_0_8_0` — both assert a `0.8.0`
  world while the repo is at `0.9.0`. Neither file is in Touches and neither
  was modified here (`git diff --name-only` shows only the two Touches
  files). No retry loop was needed: the phase's own tests pass first time.
- No test files modified; no files outside Touches changed.

## Notes

- Gate placement is deliberate: after `load_config` (so a broken config
  still reports its existing exit-2 error first) and after `PRE_DISPATCH`
  flag validation, but before runtime selection and both dispatch branches
  (watch and native), satisfying "before any suite dispatch / no Godot
  process on refusal".
- The gate reads `__version__` and `find_project_root` as module globals at
  call time, so the pinned tests' monkeypatching works without new seams.
- Refusal goes through `click.echo(..., err=True)` with no quiet-suppression,
  so `--quiet` stays honest (exit 2 + message, verified by probe).

## Primary verification

- Targeted files with `--no-cov`: 15 passed, exit 0. All 6 RED tests green; pinned gate tests unmodified.
- `ruff check src/ tests/` clean; `black --check src/ tests/` 204 files unchanged.
- `git diff --name-only 9bef49b..HEAD`: only `src/gd_tools/addon_check.py`, `src/gd_tools/commands/test.py` (+ evidence). Touches respected.
- The 2 full-unit failures (`test_schema` snapshot, `test_version` pins `0.8.0` vs repo `0.9.0`) are pre-existing release drift, fail independent of this track, and are recorded here — not caused by, and not in scope for, this phase.
