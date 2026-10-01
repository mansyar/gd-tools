# Plan: Native Runtime Caching (Preflight Cache)

**Track ID:** `native_runtime_caching_20261001` · **Spec:** [spec.md](./spec.md)

> Every task follows the Standard Task Workflow (workflow.md): mark `[~]` →
> write failing tests (Red) → implement (Green) → refactor → verify coverage
> (`pytest --cov=gd_tools --cov-branch`, >80% line / >70% branch for new source)
> → commit → attach git note with task summary → mark `[x]` with commit SHA.

## Phase 1 — Preflight Cache Core [checkpoint: 8a64130]

- [x] Task: Write failing unit tests for the preflight cache module — cache-key
  computation (suite set, test-file hashes, `project.godot`, Godot version,
  addon file hashes, schema version), hit/miss read, atomic store, corrupt-file
  and OSError fail-open behavior → verify Red (1631d55)
- [x] Task: Implement `src/gd_tools/native_test/preflight_cache.py` —
  `load_cached_preflight()` / `store_cached_preflight()` using
  `write_json_atomic`, schema-versioned payload → verify Green
- [x] Task: Refactor and verify coverage gates for the new module (e5bac86)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Command Flow Integration [checkpoint: 5fbc7c5]

- [x] Task: Write failing unit/integration tests: cache hit skips
  `run_native_preflight()` (no Godot preflight process spawned) and copies the
  cached manifest/result into the run's `preflight_dir`; miss runs the real
  preflight and populates the cache → verify Red (e9329e9)
- [x] Task: Wire cache lookup/store into the native test command flow in
  `src/gd_tools/native_test/command.py` between suite discovery and preflight →
  verify Green (b79beed)
- [x] Task: Refactor and verify coverage gates (bc1744f)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [checkpoint: 5fbc7c5]

## Phase 3 — CLI Flag & Verbose UX [checkpoint: fa628ac]

- [x] Task: Write failing tests for `--no-cache` on `gd-tools test` (bypasses
  read and write) and `--verbose` hit/miss output with reason → verify Red
  (7828ff1)
- [x] Task: Plumb the flag through `cli.py` → `command.py` and add verbose
  logging → verify Green (b673a51)
- [x] Task: Refactor and verify coverage gates (b673a51)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [checkpoint: fa628ac]

## Phase 4 — Benchmark, Clean Regression & Docs [checkpoint: 77fe0fa]

- [x] Task: Write a repeat-run benchmark in `tests/performance/` against the
  dogfood `spike/` project measuring cold vs. cached wall clock; run it and
  confirm the revised gate (warm strictly faster + preflight skipped on hit;
  spec NFR-3/AC-6 revised 2026-10-01) (9980661)
- [x] Task: Add a regression test that `gd-tools clean --cache` removes
  `preflight-cache/` (9e5163b)
- [x] Task: Update documentation — README (test command + cache note),
  ROADMAP.md (close the Phase 5 "native runtime caching" item), CHANGELOG.md
  (Unreleased) (7bcb740)
- [~] Task: Phase Verification & Checkpoint (Refer to workflow.md)
