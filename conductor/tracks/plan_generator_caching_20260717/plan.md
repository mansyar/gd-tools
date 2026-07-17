<protect>
# Implementation Plan: Track 37 — Plan Generator Caching

## Overview

This plan implements hash-based coverage plan caching in `plan_generator.py`, threads it through `orchestrator.py`, and adds a `--no-cache` CLI flag. Each phase follows TDD: failing tests first (Red), then implementation (Green), then coverage verification.

---

## Phase 1: Cache Check Function (plan_generator.py) [checkpoint: 4475dff]

- [x] Task: Read `spec.md` and `workflow.md` to re-establish context before starting this phase
- [x] Task: Write failing tests for `generate_plan_cached()` cache check logic
    - [x] Create `tests/unit/test_plan_generator.py` additions (or new test section) for cache tests
    - [x] Test cache hit: all file hashes match cached plan → returns cached plan, `hit=True`
    - [x] Test cache miss — file modified: one source hash differs → regenerates, `hit=False`
    - [x] Test cache miss — file added: new `.gd` file on disk not in cached plan → regenerates
    - [x] Test cache miss — file deleted: file in cached plan not on disk → regenerates
    - [x] Test cache miss — `plan.json` missing: no cached plan → regenerates
    - [x] Test cache miss — `plan.json` corrupt/invalid: bad JSON or schema → safe fallback, regenerates
    - [x] Test `use_cache=False`: forces regeneration even when cache is valid
    - [x] Test returned `CacheStatus` dataclass has correct `hit` boolean and `reason` string
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement `generate_plan_cached()` function in `plan_generator.py` [12f510d]
    - [x] Add `CacheStatus` dataclass with `hit: bool` and `reason: str` fields
    - [x] Implement `generate_plan_cached(project_root, exclude_dirs, test_dirs, cache_path, use_cache=True) -> tuple[CoveragePlan, CacheStatus]`
    - [x] Cache check logic: if `use_cache` and `cache_path` exists, read plan via `read_plan_json()`
    - [x] Discover current `.gd` files (reuse `discover_gd_files` + test-dir filtering)
    - [x] Compute current source hashes for all discovered files
    - [x] Compare cached plan file paths + hashes vs current file paths + hashes
    - [x] Cache hit: same path set AND all hashes match → return cached plan + `CacheStatus(hit=True, reason="N files unchanged")`
    - [x] Cache miss: paths differ or hashes differ → call `generate_plan()` + `CacheStatus(hit=False, reason="...")`
    - [x] Wrap `read_plan_json()` in try/except `CoveragePlanError` for corrupt plan fallback
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `pytest --cov=gd_tools.coverage.plan_generator --cov-branch` and verify >80% line, >70% branch

- [x] Task: Conductor - User Manual Verification 'Cache Check Function' (Protocol in workflow.md)

---

## Phase 2: Orchestrator Integration & Verbose Logging

- [x] Task: Read `spec.md` and `workflow.md` to re-establish context before starting this phase
- [x] Task: Write failing tests for orchestrator cache integration (b958136)
    - [x] Add tests to `tests/unit/test_orchestrator.py` for cache-aware `run_coverage_test()`
    - [x] Test `run_coverage_test()` with cache hit: `generate_plan_cached()` is called, not `generate_plan()`
    - [x] Test `run_coverage_test()` with `no_cache=True`: forces regeneration
    - [x] Test `run_coverage_test()` writes `plan.json` after generation (even on cache hit)
    - [x] Test verbose logging: `output.print_verbose()` called with cache hit message when `--verbose`
    - [x] Test verbose logging: `output.print_verbose()` called with cache miss message when `--verbose`
    - [x] Test default verbosity: no cache status output printed
    - [x] Test quiet verbosity: no cache status output printed
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement orchestrator changes and verbose logging (b958136)
    - [x] Add `no_cache: bool = False` parameter to `run_coverage_test()` signature
    - [x] Replace `plan_generator.generate_plan()` call (line 87) with `plan_generator.generate_plan_cached()`
    - [x] Pass `cache_path=str(output_dir / "plan.json")` and `use_cache=not no_cache`
    - [x] Handle the returned `CacheStatus` to construct verbose log messages
    - [x] Call `output.print_verbose()` with cache hit/miss message based on `CacheStatus`
    - [x] Always call `write_plan_json()` after generation (skip on cache hit since file already exists, OR write anyway for safety)
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `pytest --cov=gd_tools.coverage.orchestrator --cov-branch` and verify >80% line, >70% branch

- [x] Task: Conductor - User Manual Verification 'Orchestrator Integration & Verbose Logging' (Protocol in workflow.md) [checkpoint: 0a1dfe3]

---

## Phase 3: CLI --no-cache Flag

- [x] Task: Read `spec.md` and `workflow.md` to re-establish context before starting this phase
- [x] Task: Write failing tests for `--no-cache` CLI flag (858e4dd)
    - [x] Add tests to `tests/unit/test_cli.py` for `test --coverage --no-cache`
    - [x] Test `--no-cache` flag exists on `test` command and is passed through to `run_coverage_test()`
    - [x] Test `--no-cache` without `--coverage`: flag is accepted but has no effect (no plan generated)
    - [x] Test default (no `--no-cache`): cache is used
    - [x] Run tests and confirm they fail (Red phase)

- [x] Task: Implement `--no-cache` flag in `cli.py` (858e4dd)
    - [x] Add `--no-cache` Click option to the `test` command decorator
    - [x] Thread `no_cache` parameter through to `run_coverage_test()` call
    - [x] Ensure flag only affects coverage plan generation (not test execution itself)
    - [x] Run tests and confirm they pass (Green phase)
    - [x] Run `ruff check src/ tests/` and `black --check src/ tests/`
    - [x] Run `pytest --cov=gd_tools.cli --cov-branch` and verify >80% line, >70% branch (95% line, 91% branch)

- [ ] Task: Conductor - User Manual Verification 'CLI --no-cache Flag' (Protocol in workflow.md)

---

## Phase 4: Full Integration & Documentation

- [ ] Task: Read `spec.md` and `workflow.md` to re-establish context before starting this phase
- [ ] Task: Write integration test for end-to-end cache behavior
    - [ ] Add test to `tests/integration/` for full `test --coverage` with cache
    - [ ] Test: first run generates plan, second run with no changes uses cache
    - [ ] Test: modifying a file between runs triggers regeneration
    - [ ] Test: `--no-cache` flag on second run forces regeneration
    - [ ] Run tests and confirm they pass

- [ ] Task: Update documentation
    - [ ] Add `--no-cache` flag to `test` command help text and README
    - [ ] Add cache behavior section to USER_GUIDE (brief: plan is cached by default, `--no-cache` to force regeneration)
    - [ ] Run `ruff check` and `black --check` on all changed files

- [ ] Task: Conductor - User Manual Verification 'Full Integration & Documentation' (Protocol in workflow.md)
</protect>
