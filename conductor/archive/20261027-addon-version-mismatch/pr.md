# PR: Coverage Addon Version Gate

## Summary

`gd-tools test --coverage` used to run against a stale deployed coverage
addon with only a buried line-1 warning, then report the resulting parse
failures as if they were problems in the user's source file. The coverage
run now refuses **before dispatching any suite** when the deployed coverage
addon or the native test addon is stale, missing, or unparseable.

## Changes

- `src/gd_tools/addon_check.py`: new `check_coverage_addon_gate()` comparing
  both deployed `_version.txt` files against the CLI version. Missing /
  unparseable / older → refusal; matching or newer → pass; unexpected errors
  fail safe to `None`. Honors `GD_TOOLS_NO_UPDATE_CHECK=1`. Existing
  `check_addon_version()` advisory untouched.
- `src/gd_tools/commands/test.py`: the `--coverage` path calls the gate after
  config load and flag validation but before any dispatch; refusal echoes to
  stderr and exits 2. Plain `test` never reaches the gate.
- `tests/unit/test_coverage_addon_gate.py`: 8 pinned CliRunner tests (6 red in
  Phase 1, green in Phase 2).
- `docs/USER_GUIDE.md`: documents the hard gate, exit-2 row, and Requires line.

## Refusal message

```text
Error: Coverage addon is outdated (v0.8.0 deployed, v0.9.0 installed). Run `gd-tools init` to update. Aborted before running tests.
```

(The addon label varies: Coverage addon / Native test addon; missing or
unparseable version files are reported the same way.)

## Test report

- New: `tests/unit/test_coverage_addon_gate.py` — 8/8 pass (stale/missing/
  unparseable for both addons → exit 2 + zero dispatch; env suppression;
  newer-addon pass-through; message content).
- Existing: `tests/unit/test_addon_check.py` — 7/7 pass, advisory unchanged.
- Full `tests/unit`: 1850 passed, 3 skipped; 2 failures are pre-existing
  post-release drift unrelated to this change (checked-in schema snapshot;
  version test pins 0.8.0 vs repo 0.9.0).
- Coverage TOTAL 95% (gate 80%). `ruff` / `black --check` clean.
  `python -m build` succeeds.

## Follow-ups

- none
