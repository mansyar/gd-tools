# Specification: Import-Step Caching

**Track ID:** `import_step_caching_20261001`
**Type:** Feature (performance enhancement)
**Status:** Draft
**Created:** 2026-10-01

## Overview

Every `gd-tools test` invocation currently runs `godot --headless --import`
unconditionally (`src/gd_tools/native_test/command.py::_import_project`),
regardless of whether the project has changed since the last import. After the
preflight-cache track (archived `native_runtime_caching_20261001`) eliminated
the redundant bridge scan, this import step is the last uncached fixed cost —
a full Godot process spawn (typically 2–5+ seconds) that short repeat runs pay
on every invocation.

This track introduces an **import-freshness cache**: a content-hash keyed
record of the last successful import. When nothing that could affect Godot's
import result has changed, the import process is skipped entirely; otherwise
it runs as today and the cache is refreshed. The design mirrors the proven
preflight-cache pattern: SHA-256 content hashing, fail-open on cache errors,
`--no-cache` bypass, and verbose hit/miss reporting.

### Goals

- Eliminate the redundant `godot --headless --import` process on unchanged
  projects, making warm repeat runs of `gd-tools test` strictly faster.
- Preserve correctness: any change that could affect Godot's import result
  must invalidate the cache.
- Reuse the established caching conventions so behavior is predictable and
  consistent with the preflight and coverage-plan caches.

### Non-Goals

- No change to what the import does or to Godot's own `.godot/` cache.
- No new user-facing configuration surface (no `gd-tools.toml` section, no new
  CLI flags beyond the existing global `--no-cache`).
- No watch-mode-specific cache integration (watch sessions reuse the check
  as-is; any observed file change naturally causes a cache miss).
- No changes to GUT-bridge or runtime-mode behavior.

## Functional Requirements

### FR-1: Import-freshness cache module

- **FR-1.1:** A new module `src/gd_tools/native_test/import_cache.py` provides
  the cache: a function that, given the Godot binary path/version, project
  root, and cache path, returns a hit/miss status with a human-readable
  reason, and a function that records a successful import.
- **FR-1.2:** The cache state is stored under
  `<project_root>/.gd-tools/native/import-cache/` (JSON, same style as the
  preflight cache), containing the composite content hash and the Godot
  binary identity it was produced with.
- **FR-1.3:** Hashing and cache-file helpers are reused from
  `preflight_cache.py` (or refactored into a shared helper) rather than
  duplicated.

### FR-2: Cache key — full content hash

The cache key is a composite SHA-256 over:

- **FR-2.1:** `project.godot` content.
- **FR-2.2:** All project source/resource files relevant to Godot's import
  step (at minimum: `.gd`, `.tscn`, `.scn`, `.tres`, `.res`, `.import`,
  `.gdextension`, `.cfg`, `.toml` under the project, excluding `.godot/`,
  `.git/`, `.gd-tools/`, and standard VCS/IDE noise), using the same
  hashing approach as the preflight cache (relative path + content).
- **FR-2.3:** The Godot binary identity (resolved path/version), so switching
  Godot versions invalidates the cache.
- **FR-2.4:** Bundled addon file hashes (consistent with the preflight cache
  keying).

### FR-3: Pipeline integration

- **FR-3.1:** In `native_test/command.py`, the unconditional
  `_import_project()` call is gated by the cache check: on cache hit, the
  import process is skipped; on miss, `_import_project()` runs and, on
  success, the cache is written.
- **FR-3.2:** The existing `--no-cache` global flag bypasses the import cache
  entirely (always run the import, never read the cache).
- **FR-3.3:** Cache hit/miss is reported under `--verbose` using the existing
  phrasing convention (e.g., `Import cache hit: unchanged since last import`
  / `Import cache miss: <reason>`).

### FR-4: Failure behavior

- **FR-4.1:** Fail-open: any error while reading, hashing for, or writing the
  cache results in running the import normally (cache treated as a miss); no
  cache error may ever prevent a test run or corrupt its result.
- **FR-4.2:** Concurrent runs are tolerated: cache writes use atomic
  replace-style writes; a lost race between concurrent processes results at
  worst in a redundant import on a later run, never in a skipped-but-needed
  import.
- **FR-4.3:** A failed or timed-out import must NOT update the cache (only
  successful imports record freshness).

## Non-Functional Requirements

### NFR-1: Performance (benchmark evidence)

- **NFR-1.1:** Warm repeat runs (no project changes since the previous
  `gd-tools test` invocation) must skip the `godot --headless --import`
  process entirely.
- **NFR-1.2:** Benchmark evidence using the repo's existing benchmark fixture
  (the same opt-in benchmark harness the preflight-cache track used) must
  demonstrate that warm runs are strictly faster than cold runs, with the
  import process eliminated, and the measured wall-time gain is recorded in
  this spec before completion. Precedent: the preflight-cache track's
  measured-gain figure was recorded in its spec; if evidence shows the gain
  differs from expectations, the figure (not the requirement of strict
  improvement) may be revised with justification.
- **NFR-1.3 (measured evidence, 2026-10-01):** On the benchmark fixture
  (6 passing native suites, Godot via `GODOT_BIN`, `GD_TOOLS_RUN_BENCHMARK=1`,
  3 warm iterations), the cold run took **7.12s** and the warm median was
  **3.14s** (warm/cold ratio **0.44**; per-iteration warm times 3.14s /
  3.27s / 2.81s) — warm runs were **~56% faster** wall-clock with the import
  process eliminated and all warm runs served the cache (`Import cache hit`
  on every iteration). Benchmark: `tests/performance/`
  `test_native_import_cache_benchmark.py`.

### NFR-2: Consistency with existing cache conventions

- **NFR-2.1:** Behavior on cache errors, `--no-cache` semantics, verbose
  reporting, and storage location follow the conventions established by the
  preflight and coverage-plan caches.
- **NFR-2.2:** No changes to exit-code conventions (0/1/2) or JSON/report
  output formats.

### NFR-3: Code quality

- **NFR-3.1:** New/changed source in `src/gd_tools/` maintains >80% line and
  >70% branch coverage, per `workflow.md`.
- **NFR-3.2:** `ruff check` and `black --check` clean; type hints and
  docstrings per product guidelines.

## Acceptance Criteria

1. Running `gd-tools test` twice with no project changes: the second run
   skips the `godot --headless --import` process (verified by test/fixture
   observation), while the first (or a `--no-cache` run) still performs it.
2. Modifying any file covered by the cache key (e.g., a `.gd` file,
   `project.godot`, an addon file) causes the next run to perform the import
   again (cache miss with a meaningful reason under `--verbose`).
3. Switching the resolved Godot binary version causes a cache miss.
4. `--no-cache` always runs the import and never reads/writes cache hits.
5. Cache read/write/hash errors fail open: the import runs, tests execute,
   exit codes and report formats are unchanged.
6. A failed import (non-zero exit or timeout) does not update the cache.
7. Benchmark evidence recorded: warm runs strictly faster than cold runs on
   the benchmark fixture; measured gain documented in this spec.
8. Documentation updated: README (caching behavior + `--no-cache`), CHANGELOG
   entry, and a "Caching architecture" section in `docs/ARCHITECTURE.md`
   describing the import cache alongside the preflight and coverage-plan
   caches (the known Part I flow-diagram drift may be corrected as part of
   that section).
9. Unit + integration tests cover hit, miss (per invalidation cause), fail-open,
   `--no-cache`, concurrent-write tolerance, and pipeline gating; coverage
   gates per NFR-3.1 met.

## Out of Scope

- Any new `gd-tools.toml` configuration section or CLI flags for the import
  cache.
- Watch-mode-specific cache APIs or integrations.
- Caching other Godot process invocations (e.g., coverage preflight beyond
  its existing cache).
- GUT compatibility bridge changes (separate planned track).
- Changes to Godot's own import behavior or `.godot/` management.
