# Track Specification — Parallel Suite Execution

**Track ID:** `native_parallel_suites_20260930` · **Type:** Feature · **Targets:** v0.6.0

## Overview

`gd-tools test` currently runs every suite sequentially — one isolated Godot
process at a time (`ARCHITECTURE.md` §13 lists "No parallel execution" as a
known limitation). Because suites are already process-isolated, this track adds
an **opt-in bounded worker pool**: N suite processes run concurrently, with
deterministic result aggregation. Sequential behavior remains the default and
is code-path-identical to today.

## Functional Requirements

### FR1 — API surface (flag + config)

- `--parallel N` flag on `gd-tools test`; `N` must be an integer 1–32; invalid
  values exit `2` with an actionable fix hint.
- Persistent config key `parallel` in the `[test]` section of `gd-tools.toml`;
  the flag overrides config; absent from both → sequential.
- `N = 1` runs the existing sequential path unchanged (no pool machinery).
- When enabled without an explicit `N`, default is **4**.

### FR2 — Scheduling & execution

- Suites are dispatched in **discovery order** via a queue; each worker takes
  the next suite when it frees up; summary renders in discovery order.
- **All discovered suites are treated uniformly** — native and GUT-bridge
  suites alike.
- Per-suite timeout semantics are **unchanged**, enforced independently per
  worker; a timed-out suite fails its slot, which immediately picks up the next
  queued suite.
- Failure semantics preserved: a failing/crashed suite never cancels others;
  exit-code precedence (infrastructure > coverage gate > test failure) is
  unchanged.

### FR3 — Output & protocol

- Human output: suites run concurrently but the final summary renders in
  discovery order (deterministic CI logs).
- NDJSON progress events gain **suite identifier + worker slot** fields; the
  protocol version bumps per the existing versioned-JSON convention.

### FR4 — Coverage

- `gd-tools test --parallel N --coverage` is fully supported: per-suite
  coverage data writes compose with the existing merge path; correctness
  verified by e2e (merged report matches the sequential run's structure).

### FR5 — Watch mode

- `--watch` inherits `--parallel`/config through the shared run path; no new
  watch-specific behavior.

### FR6 — Interruption & process safety

- On Ctrl+C/SIGTERM: stop dispatching, **kill all in-flight suite process
  trees** (Godot + descendants) on every platform — Windows via `taskkill /T`
  or Job Objects — mark the run's artifact index `incomplete`, exit `130`.

### FR7 — Documentation (in-track)

- `docs/ARCHITECTURE.md`: remove the "No parallel execution" known limitation;
  document the parallel model.
- `docs/USER_GUIDE.md`, `README.md` feature list, and config reference:
  document `--parallel` and `[test] parallel`.

## Non-Functional Requirements

- TDD per `workflow.md`: tests precede implementation for all code changes.
- Coverage targets: ≥80% line / ≥70% branch on new/changed `src/gd_tools/*.py`.
- Non-interactive under `CI=true`; exit-code convention unchanged (0/1/2, plus
  130 for interrupts).
- **Artifact contract unchanged:** `.gd-tools/artifacts/<run_id>/` per-suite
  layout, machine-readable index, latest-run retention, JUnit XML/NDJSON
  formats preserved (only NDJSON gains the tagging fields).
- No behavior change to sequential runs (default path semantics identical).

## Acceptance Criteria

1. A performance e2e in `tests/performance/` proves an M-suite run with N
   workers completes faster than the sequential equivalent (functional e2e
   proves identical results).
2. Parallel and sequential runs of the same project produce identical
   pass/fail outcomes, exit codes, and discovery-ordered JUnit XML.
3. `--parallel 4 --coverage` produces correct merged coverage reports.
4. Interrupted parallel run: no orphan Godot processes, incomplete artifact
   marker, exit 130.
5. Invalid `--parallel` values (0, 33, non-integer) exit `2` with a fix hint;
   `--parallel 1` behaves exactly as today.
6. Watch mode honors parallel config; docs updated and truthful.

## Out of Scope

- Native runtime caching
- Auto-detecting CPU count
- Distributed/remote execution
- Per-test (vs per-suite) parallelism
- Resume of interrupted runs
- Adopting `--parallel` in this repository's own CI
- PyPI publishing
