# Implementation Plan: E2E Test Speed

Execution follows `conductor/workflow.md` (TDD where code changes; config
and workflow YAML tasks are verified through their own verification steps).

## Phase 1: Measurement & Marker Infrastructure

- [x] Task: Add `--durations=20` to CI pytest steps — `2d2f9e3`
  - Append the flag to the Stage 3 E2E and Stage 2 integration `pytest`
    invocations in `.github/workflows/ci.yml`.
  - Verification: workflow YAML parses; a CI run shows the slowest tests in
    the job log.
- [x] Task: Register the `e2e_smoke` marker — `b2f0619`
  - Add `e2e_smoke: Fast critical-path E2E subset for PR CI.` to the
    `markers` list in `pyproject.toml`.
  - Verification: `pytest --collect-only -m e2e_smoke` collects without
    `PytestUnknownMarkWarning` under `--strict-markers`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Timing-Knob Injection for Real-Time E2E Waits [checkpoint: 5552cb2]

- [x] Task: Audit real-time waits in watch/migration e2e — `bf95fc7`
  - Inventory every sleep/debounce/poll wait in `test_watch_e2e.py` and the
    migration e2e paths with its source: fixture value, production default,
    or hardcoded.
  - Output: inventory recorded in git notes for the task commit.
- [x] Task: Inject fast timing values through e2e fixtures — `bf95fc7`
  - Use existing seams (`Coalescer(debounce_seconds=...)`, session clock
    injection, `GdToolsConfig`) to shrink waits in e2e runs.
  - Any missing seam is added TDD-style: failing test first, minimal
    parameter, green; production defaults unchanged.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Smoke Subset & CI Split

- [ ] Task: Select and mark smoke tests
  - Pick 3-5 critical-path e2e tests (representative native run with
    coverage, lint/format pass, migration dry-run) guided by the Phase 1
    durations data; target <= ~2 minutes per job.
  - Apply `@pytest.mark.e2e_smoke` to the selected tests.
- [ ] Task: Split CI execution
  - PR E2E job runs `pytest tests/e2e/ -m "e2e and e2e_smoke"`.
  - Full E2E (`-m e2e`) runs via a nightly `schedule` trigger plus
    `workflow_dispatch` on the unchanged 6-job matrix.
- [ ] Task: Document the local smoke run
  - CONTRIBUTING (or USER_GUIDE dev section): how to run the smoke subset
    locally.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Final Acceptance Check

- Open the track PR and observe PR CI wall time <= 10 minutes.
- Trigger the full E2E `workflow_dispatch` run and confirm green.
