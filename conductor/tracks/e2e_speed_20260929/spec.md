# Specification: E2E Test Speed

## Overview

The E2E test stage is the CI wall-time bottleneck: jobs range 5m16s to
10m23s, with Windows jobs dominating, pushing PR CI to ~13 minutes against
the documented 10-minute target (see `docs/ROADMAP.md`). This track adds
duration measurement, eliminates real-time waits in watch/migration e2e via
the existing config-injection seams, and splits PR-time E2E into a
marker-selected smoke subset — without changing any product behavior or test
coverage semantics.

## Functional Requirements

### FR-1: Duration instrumentation

Add `--durations=20` to the E2E pytest invocation (`pytest tests/e2e/ -m
e2e ...`) and the Stage 2 integration invocation in
`.github/workflows/ci.yml` so the slowest tests are visible in job logs. No
new infrastructure beyond the CLI flag.

### FR-2: Timing knobs via injection

E2E fixtures pass small `debounce_seconds`/poll values (and injected clocks
where supported) through the existing `GdToolsConfig` model and watch
session seams (`Coalescer(debounce_seconds=...)`, session clock injection).
No production defaults change and no new environment variables are
introduced. Where a needed knob does not exist, extend the production seam
TDD-style (failing test first, minimal parameter, green) — but only for
seams the e2e actually needs.

### FR-3: Smoke marker

Register an `e2e_smoke` pytest marker in the `markers` list of
`pyproject.toml` (the project uses `--strict-markers`). Mark 3-5
critical-path e2e tests — representative native test run with coverage,
lint/format pass, migration dry-run — selected to run in <= ~2 minutes per
job, guided by the FR-1 durations data.

### FR-4: CI split

PR runs `pytest tests/e2e/ -m "e2e and e2e_smoke"` on the unchanged 6-job
matrix (Godot 4.5.2/4.6.1/4.7.1 x ubuntu/windows). The full E2E suite
(`-m e2e`) runs on a nightly schedule plus `workflow_dispatch` (new
scheduled workflow or added trigger on the existing one).

### FR-5: Documentation

CONTRIBUTING (or the USER_GUIDE dev section) documents how to run the smoke
subset locally.

## Non-Functional Requirements

- Zero production-code behavior change; production defaults untouched.
- No new dependencies (no pytest-xdist in this track).
- Markers registered to avoid `PytestUnknownMarkWarning` under
  `--strict-markers`.
- Workflow YAML changes kept minimal and reviewed.

## Acceptance Criteria

1. PR CI wall time (Stage 1 + Stage 2 + smoke E2E) is <= 10 minutes on
   GitHub, observed on a real PR run.
2. E2E job logs list the 20 slowest tests.
3. The full E2E suite runs and passes via nightly/`workflow_dispatch`.
4. Timing values flow only through existing injection seams (verifiable by
   diff; any new seam parameters are TDD-derived and default-preserving).
5. The full local test suite stays green; coverage gates unchanged.

## Out of Scope

- pytest-xdist parallelism within jobs.
- Godot import/binary caching.
- E2E matrix trimming.
- A persistent Godot worker process (product-level process-model change).
- CI step retry logic (e.g., the transient curl revocation flake observed on
  the "Install Godot" step).
