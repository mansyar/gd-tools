# Implementation Plan: Import-Step Caching

- **Track ID:** import_step_caching_20261001
- **Type:** Feature (performance enhancement)
- **Status:** New
- **Specification:** [`spec.md`](./spec.md)

## Phase 1 — Import cache module

**Purpose:** Establish the content-hash import-freshness cache as a standalone, fully tested module before touching the test pipeline.

- [x] Task: Add failing unit tests for the import cache module [5188e38]
  - [ ] Test the composite cache key: `project.godot` content, project source/resource file hashes, Godot binary identity, and bundled addon hashes (mirroring `preflight_cache.py` keying).
  - [ ] Test cache miss reasons: first run, changed file, changed `project.godot`, changed Godot binary, changed addon file, missing/corrupt cache file.
  - [ ] Test that unchanged projects produce a cache hit after a successful import is recorded.
  - [ ] Test fail-open behavior: hashing errors, unreadable/corrupt cache files, and write failures are reported as a miss and never raise.
  - [ ] Test that cache writes are atomic (no partial/truncated cache state on interruption).
  - [ ] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Implement `src/gd_tools/native_test/import_cache.py` [5188e38]
  - [ ] Reuse hashing/cache helpers from `preflight_cache.py` (extract a shared helper if that avoids duplication).
  - [ ] Implement the cache-status result with hit/miss and a human-readable reason, consistent with the existing cache-status conventions.
  - [ ] Implement reading, validating, and atomically writing the cache state under `.gd-tools/native/import-cache/`.
  - [ ] Implement the file-discovery scope for import-relevant project files with the agreed exclusions (`.godot/`, `.git/`, `.gd-tools/`, VCS/IDE noise).
  - [ ] Run the new unit tests to Green.
- [x] Task: Add import-cache coverage and style gates [5188e38]
  - [ ] Verify `import_cache.py` meets the >80% line / >70% branch coverage gates.
  - [ ] Run `ruff check` and `black --check`.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [checkpoint: 49401c2]

## Phase 2 — Pipeline integration

**Purpose:** Gate the unconditional `godot --headless --import` call with the cache while preserving all existing behavior on miss, failure, and `--no-cache`.

- [x] Task: Add failing tests for pipeline gating [267066b]
  - [ ] Test that a warm second run (no changes) skips the `godot --headless --import` process.
  - [ ] Test that a cold/changed project still runs the import and records the cache only on success.
  - [ ] Test that a failed or timed-out import does not update the cache.
  - [ ] Test that `--no-cache` always runs the import and bypasses cache reads/writes.
  - [ ] Test fail-open integration: cache errors result in a normal import, unchanged exit codes and report output.
  - [ ] Test concurrent-run tolerance: overlapping runs never produce a corrupt cache or a skipped-but-needed import.
  - [ ] Test verbose hit/miss reporting lines follow the existing `cache hit/miss: reason` phrasing.
  - [ ] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Wire the cache into `native_test/command.py` [267066b]
  - [ ] Gate the `_import_project()` call with the cache check (skip on hit).
  - [ ] Record cache freshness only after a successful import.
  - [ ] Honor the global `--no-cache` flag end-to-end.
  - [ ] Emit verbose hit/miss messages.
  - [ ] Run the pipeline tests to Green, then the full unit suite for regressions.
- [x] Task: Add integration-level regression coverage [599d657]
  - [ ] Verify JUnit XML / JSON report outputs and exit-code conventions are unchanged by the gating.
  - [ ] Verify watch-mode sessions observe a cache miss after any file change and a hit on unchanged resume (no watch-specific code paths).
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [checkpoint: e55c70f]

## Phase 3 — Benchmark evidence

**Purpose:** Prove the performance claim with the repo's opt-in benchmark harness, matching the preflight-cache track's evidence standard.

- [x] Task: Extend the benchmark harness for warm/cold import measurement [97c4467]
  - [x] Measure cold runs (cache miss → import executes) on the benchmark fixture.
  - [x] Measure warm runs (cache hit → import skipped) on the benchmark fixture.
  - [x] Record startup and total wall time; document benchmark conditions and known variance.
- [x] Task: Assert strict improvement and record the measured gain in the spec [97c4467]
  - [x] Add a benchmark assertion that warm runs are strictly faster and the import process is eliminated.
  - [x] Record the measured wall-time gain in `spec.md` NFR-1 (revising the figure, not the strict-improvement requirement, if evidence demands, with justification).
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [checkpoint: ad25086]

## Phase 4 — Documentation and quality gates

**Purpose:** Close the track with accurate docs and all quality gates green.

- [x] Task: Update user-facing documentation [c59d053]
  - [x] README: document the import cache behavior and the `--no-cache` bypass alongside the existing cache documentation.
  - [x] CHANGELOG: add an entry for the import-step cache.
  - [x] `docs/ARCHITECTURE.md`: add a "Caching architecture" section describing the import cache, preflight cache, and coverage-plan cache together; correct the known Part I flow-diagram drift as part of that section.
- [x] Task: Final quality gates [c59d053]
  - [x] Run the full unit suite.
  - [x] Run the full integration suite.
  - [x] Run `ruff check` and `black --check`.
  - [x] Verify the full project coverage threshold behavior.
  - [x] Verify no new runtime dependencies were added.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)

## Plan Boundaries

No new `gd-tools.toml` configuration section or CLI flags beyond the existing
global `--no-cache`; no watch-mode-specific cache integration; no caching of
other Godot process invocations; no GUT compatibility bridge changes (planned
as the separate v0.6.0 bridge-removal track); no changes to Godot's own import
behavior or `.godot/` management.
