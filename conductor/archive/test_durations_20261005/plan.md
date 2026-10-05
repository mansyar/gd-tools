# Implementation Plan: Test Durations Reporting

**Track ID:** test_durations_20261005
**Branch:** feature/test-durations-20261005
**Methodology:** TDD per `conductor/workflow.md` (Red → Green → Refactor,
coverage gates >80% line / >70% branch, task commits with git notes).

## Phase 1 — Config & CLI Plumbing

- [x] Task: Write failing unit tests for the `[test] durations` config field (red 8583f13)
  - [x] `TestConfig.durations` defaults to `None` (disabled)
  - [x] Accepts `0` and positive ints; rejects negative values (Pydantic `ge=0`)
  - [x] Rejects unknown extra keys (existing `extra="forbid"` behavior unchanged)
- [x] Task: Implement `durations: int | None` in `TestConfig` + update `docs/gd-tools.schema.json` (green ca6b07d)
  - [x] Field with `ge=0` constraint and docstring entry
  - [x] Schema JSON updated so the schema-sync unit test passes
- [x] Task: Write failing unit tests for the `--durations` CLI option (red f84abbf)
  - [x] Bare `--durations` resolves to N=10 (`flag_value="10"`, mirroring `--parallel`)
  - [x] Explicit `--durations 0` and `--durations 5` parse correctly
  - [x] Negative value rejected with exit code 2 and actionable message (`_validate_durations` callback, mirroring `_validate_parallel`; hint tested directly — click 8.2.1 rejects negative flag_value values at parse level in all syntaxes)
  - [x] CLI flag overrides config value; config used when flag absent
- [x] Task: Implement the CLI option and validation callback in `cli.py` (green f257b2e)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Durations Table Renderer

- [x] Task: Write failing unit tests for the durations reporting function in `test_results.py` (red 1b3917a)
  - [x] Sorts tests slowest-first by `TestDetail.duration`
  - [x] `N>0` truncates to slowest N; `N=0` lists all tests
  - [x] Includes pass/fail/skip tests with outcome markers
  - [x] Formats durations as seconds (e.g. `1.23s`)
  - [x] Disabled (None) → prints nothing; default output unchanged
  - [x] No per-test details → nothing printed (e.g. protocol fallback runs)
- [x] Task: Implement `print_durations_table(result, n)` in `test_results.py` using the `output` module (green 3df07be)
  - [x] Called from `format_test_results` after failure details, before summary footer/success line
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Integration & Composition

- [x] Task: Write failing integration tests wiring flag/config through the test command
  - [x] End-to-end (mocked Godot): `--durations 10` produces the table in output (command-level: real `format_test_results` with mocked `run_native_tests`; moved from CLI layer because mocking `run_native_test_command` bypasses real formatting)
  - [x] Config-driven run (`[test] durations = 5`) produces the table; CLI flag wins on conflict (CLI-layer precedence verified via forwarded kwargs; command-layer render verified with real formatting)
  - [x] Composition: table still renders with `--suite`, `--tag`, `--parallel` filters
- [x] Task: Wire `durations` through `cli.py` → reporting path; ensure `watch/session.py` re-runs honor config/flag (landed early in Phase 1 as commit b1e36a2 to keep e2e green; verified by the new forwarding tests in this phase)
- [x] Task: Verify retries-sum timing behavior is preserved by the renderer (regression test with multi-attempt `TestDetail` fixtures)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [checkpoint: eaf18bd]

## Phase 4 — Documentation & Final Verification

- [x] Task: Update `README.md` with the `--durations` flag, config key, and `--durations 0` semantics (pytest-parity note) (docs 7229597)
  - [x] README command summary, example block, and a dedicated paragraph
  - [x] USER_GUIDE.md kept truthful: `[test]` config row + §3.4 flag row
- [x] Task: Final quality gates: `ruff check`, `black --check`, `CI=true pytest` with coverage >80% line / >70% branch on new code (style ee7b3f6)
  - [x] ruff clean on all touched files; black applied to 3 files
  - [x] Full suite: 1782 passed, 7 skipped (15:30); total coverage 95.75% — gates passed
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [checkpoint: eaf18bd]

## Completion Notes

- The `durations` pass-through (command.py, watch/session.py, `format_test_results`
  signature) landed during Phase 1 (commit b1e36a2) because the full e2e suite
  invokes the real CLI; the 17 failing e2e tests served as the Red for that fix.
  Phase 3's wiring tests are therefore born-green verification tests (documented
  in the e6eaa20 git note).
- click 8.2.1 rejects negative values for `flag_value` options at parse level in
  every syntax; the CLI contract is "negatives never reach the tool" and
  `_validate_durations` remains as a guard against click-version drift.

## Phase: Review Fixes

- [x] Task: Apply review suggestions 8a79510
  - Low: `format_test_results` docstring corrected — durations table prints
    after failure details on the failure path but before the success line on
    the success path. `tests/unit/test_test_results.py` 31 passed post-fix.
  - Review verdict: no Critical/High/Medium findings; plan/style/coverage/test
    checks all passed (full suite 1782 passed, 95.75% coverage).
