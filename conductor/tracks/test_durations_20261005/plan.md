# Implementation Plan: Test Durations Reporting

**Track ID:** test_durations_20261005
**Branch:** feature/test-durations-20261005
**Methodology:** TDD per `conductor/workflow.md` (Red → Green → Refactor,
coverage gates >80% line / >70% branch, task commits with git notes).

## Phase 1 — Config & CLI Plumbing

- [ ] Task: Write failing unit tests for the `[test] durations` config field
  - [ ] `TestConfig.durations` defaults to `None` (disabled)
  - [ ] Accepts `0` and positive ints; rejects negative values (Pydantic `ge=0`)
  - [ ] Rejects unknown extra keys (existing `extra="forbid"` behavior unchanged)
- [ ] Task: Implement `durations: int | None` in `TestConfig` + update `docs/gd-tools.schema.json`
  - [ ] Field with `ge=0` constraint and docstring entry
  - [ ] Schema JSON updated so the schema-sync unit test passes
- [ ] Task: Write failing unit tests for the `--durations` CLI option
  - [ ] Bare `--durations` resolves to N=10 (`flag_value="10"`, mirroring `--parallel`)
  - [ ] Explicit `--durations 0` and `--durations 5` parse correctly
  - [ ] Negative value rejected with exit code 2 and actionable message (new `_validate_durations` callback, mirroring `_validate_parallel`)
  - [ ] CLI flag overrides config value; config used when flag absent
- [ ] Task: Implement the CLI option and validation callback in `cli.py`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Durations Table Renderer

- [ ] Task: Write failing unit tests for the durations reporting function in `test_results.py`
  - [ ] Sorts tests slowest-first by `TestDetail.duration`
  - [ ] `N>0` truncates to slowest N; `N=0` lists all tests
  - [ ] Includes pass/fail/skip tests with outcome markers
  - [ ] Formats durations as seconds (e.g. `1.23s`)
  - [ ] Disabled (None) → prints nothing; default output unchanged
- [ ] Task: Implement `print_durations_table(result, n)` in `test_results.py` using the `output` module
  - [ ] Called from `format_test_results` after failure details, before summary footer/success line
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Integration & Composition

- [ ] Task: Write failing integration tests wiring flag/config through the test command
  - [ ] End-to-end (mocked Godot): `--durations 10` produces the table in output
  - [ ] Config-driven run (`[test] durations = 5`) produces the table; CLI flag wins on conflict
  - [ ] Composition: table still renders with `--suite`, `--tag`, `--parallel` filters
- [ ] Task: Wire `durations` through `cli.py` → reporting path; ensure `watch/session.py` re-runs honor config/flag
- [ ] Task: Verify retries-sum timing behavior is preserved by the renderer (regression test with multi-attempt `TestDetail` fixtures)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Documentation & Final Verification

- [ ] Task: Update `README.md` with the `--durations` flag, config key, and `--durations 0` semantics (pytest-parity note)
- [ ] Task: Final quality gates: `ruff check`, `black --check`, `CI=true pytest` with coverage >80% line / >70% branch on new code
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
