<protect>
# Track 37: Plan Generator Caching

## Overview

The coverage plan is regenerated on every `gd-tools test --coverage` run, even when no source files have changed. For large projects (100+ GDScript files), the Lark AST parsing and visitor traversal adds noticeable latency to every test run.

This track adds hash-based plan caching: the existing `source_hash` field (already computed per-file in `FilePlan`) is used to detect whether any source file has changed since the last plan generation. When all hashes match and no files have been added or removed, the cached `plan.json` is reused without regeneration.

## Context

- **Phase:** 9 — Robustness & Quality
- **Dependencies:** Track 9 (plan generator)
- **Modules:** `src/gd_tools/coverage/plan_generator.py`, `src/gd_tools/coverage/orchestrator.py`, `src/gd_tools/cli.py`
- **Effort:** 1 day
- **Risk:** LOW-MEDIUM — cache invalidation, staleness detection

## Current Behavior

`orchestrator.run_coverage_test()` (lines 87-92) calls:
1. `plan_generator.generate_plan(project_root, exclude_dirs, test_dirs)` — parses every `.gd` file with Lark, runs `CoverageVisitor`
2. `plan_generator.write_plan_json(plan, output_dir / "plan.json")` — writes the result

This happens unconditionally on every `test --coverage` invocation.

## Functional Requirements

### FR-1: Cache Check Function in plan_generator.py

Add a new function (e.g., `generate_plan_cached()`) or an optional `use_cache` parameter to `generate_plan()` in `plan_generator.py` that:

1. Checks if a cached `plan.json` exists at the target output path
2. If it exists, reads it via `read_plan_json()`
3. Discovers all current `.gd` files (using the same `discover_gd_files` + test-dir filtering logic as `generate_plan`)
4. Computes current source hashes for all discovered files
5. Compares the cached plan's file set + hashes against the current file set + hashes:
   - **Cache hit:** Same set of file paths AND all `source_hash` values match → reuse cached plan (skip AST parsing)
   - **Cache miss:** Any file added, deleted, changed, or the cached plan is missing/corrupt → fall back to full `generate_plan()`
6. Returns the plan (cached or freshly generated) plus a status indicator (hit/miss) for logging

### FR-2: Cache Invalidation Triggers

The cache is invalidated (full regeneration occurs) when ANY of the following are true:
- `plan.json` does not exist at the output path
- `plan.json` exists but is corrupt or fails schema validation (raises `CoveragePlanError`)
- A source file has been **added** (exists on disk, not in cached plan)
- A source file has been **deleted** (in cached plan, not on disk)
- A source file has been **modified** (source hash differs from cached plan)
- `--no-cache` flag is passed (forces regeneration regardless of hash state)

### FR-3: `--no-cache` CLI Flag

Add a `--no-cache` flag to the `test` command in `cli.py` (applicable when `--coverage` is used):
- Forces full plan regeneration, bypassing the cache check
- Default behavior (without flag): use cache
- The flag is threaded through `run_coverage_test()` → `generate_plan_cached()`

### FR-4: Cache Status Logging

Log whether the plan was loaded from cache or freshly regenerated:
- Use the existing verbosity system (Track 27): `output.print_verbose()`
- Only visible when `--verbose` flag is active
- Example messages:
  - Cache hit: `"Coverage plan loaded from cache (N files unchanged)"`
  - Cache miss: `"Coverage plan regenerated (reason: N files changed/added/deleted)"`
- In default/quiet verbosity: no output

### FR-5: Orchestrator Integration

Update `orchestrator.run_coverage_test()` to:
- Call the new cached generation function instead of `generate_plan()` directly
- Pass the `use_cache` / `no_cache` parameter through
- Always call `write_plan_json()` after generation (even on cache hit, to ensure the file is up to date — or skip write on cache hit since it's already there)
- Thread the `no_cache` parameter from `run_coverage_test()` signature through to the plan generator

## Non-Functional Requirements

### NFR-1: Performance
- Cache check (file discovery + hash computation) must be significantly faster than full AST parsing for large projects
- Target: 50%+ faster `test --coverage` on 50+ file projects when cache is valid (per ROADMAP success metrics)
- Hash computation (SHA-256 of file content) is cheap relative to Lark parsing

### NFR-2: Correctness
- A cached plan must produce identical coverage results to a freshly generated plan
- Cache must never serve a stale plan (any source change invalidates)
- File ordering in the cached plan must be deterministic (same as fresh generation)

### NFR-3: Backward Compatibility
- Existing `generate_plan()` signature and behavior remain unchanged (no breaking changes to callers)
- The `tools/generate_expected_plans.py` utility continues to work
- Existing tests for `generate_plan()` and `read_plan_json()` remain valid

## Acceptance Criteria

1. When no source files changed, plan is loaded from cache (no AST parsing occurs)
2. When a source file is modified, plan is regenerated
3. When a new source file is added, plan is regenerated
4. When a source file is deleted, plan is regenerated
5. `--no-cache` flag forces full plan regeneration
6. Cached plan produces identical coverage results to a fresh plan
7. Cache hit/miss status is logged when `--verbose` is active
8. Cache hit/miss status is NOT printed in default or quiet verbosity
9. Corrupt or invalid `plan.json` triggers safe fallback to regeneration (no crash)
10. All existing tests continue to pass
11. New code achieves >80% line coverage and >70% branch coverage

## Out of Scope

- **Partial/incremental caching** (only re-parsing changed files): The cache is all-or-nothing — either the full cached plan is reused or the full plan is regenerated. Incremental caching adds complexity for marginal gain.
- **Cache for `coverage show` / `coverage report` commands**: These commands read existing `plan.json` and don't generate plans. The `--no-cache` flag is only on `test --coverage`.
- **Configurable cache directory or TTL**: The cache lives at the existing `plan.json` output path (`.gd-tools/coverage/plan.json`). No separate cache directory or time-based expiration.
- **Cache for non-coverage test runs**: Only `test --coverage` generates plans. Plain `test` without `--coverage` is unaffected.
- **`gd-tools clean --cache`**: The existing Track 39 (Clean Command) already plans a `--cache` flag. This track does not add clean functionality.
</protect>
