# Spec: Native Runtime Caching (Preflight Cache)

**Track ID:** `native_runtime_caching_20261001` · **Type:** Chore (Performance) · **Date:** 2026-10-01

## Overview

Close the final deferred migration Phase 5 item — *"Integrate native runtime caching (deferred)"*. Every `gd-tools test` run currently pays for a headless preflight Godot process (after `--import`) that resolves `INTEGRATION` constants and enriches the discovery manifest, even when nothing has changed. This track adds a content-hash cache for the preflight result so repeat runs on unchanged projects skip that process entirely — the same optimization Track 37 delivered for the coverage plan.

## Background

The native test command flow is: discovery (pure Python) → `_import_project` (headless `godot --import`) → `run_native_preflight` (second headless Godot process producing the enriched `NativePreflightResult`) → per-suite Godot processes. The preflight output is deterministic given: the discovered suite set, test-file contents, `project.godot`, the Godot binary version, and the bundled addon files. All are content-hashable.

## Functional Requirements

- **FR-1** — Cache valid preflight results under `.gd-tools/native/preflight-cache/` (inside the existing worker scratch directory already removed by `gd-tools clean --cache`).
- **FR-2** — Cache key = SHA-256 over: the discovered suite set (names, paths, runtime markers), content hashes of discovered test files, `project.godot`, the Godot binary version, and the bundled addon `.gd` files (including `gd_tools_test_preflight.gd`), plus a cache schema-version constant.
- **FR-3** — On hit: reuse the cached `NativePreflightResult` and copy the cached preflight manifest/result into the run's `preflight_dir`, so `publish_artifact_index()` keeps its existing contract unchanged.
- **FR-4** — `--no-cache` flag on `gd-tools test` bypasses both cache read and write (mirroring the coverage plan-cache flag).
- **FR-5** — **Fail-open:** any cache read/write error (OSError, corrupt JSON, schema mismatch) logs under `--verbose` and falls back to a real preflight. The cache must never fail a run.
- **FR-6** — Cache hit/miss (with reason) is printed only under `--verbose`; the artifact index requires no schema change.
- **FR-7** — Cache writes are atomic (reuse `write_json_atomic`).
- **FR-8** — Cache applies to native and bridge suites alike; the runtime marker participates in the key.

## Non-Functional Requirements

- **NFR-1** — A cache-hit run produces results, exit codes, coverage output, and artifacts identical to a cold run.
- **NFR-2** — No new runtime dependencies.
- **NFR-3** — Repeat-run wall clock on the unchanged dogfood `spike/` project improves by **≥30%** (measured via the existing `tests/performance/` harness).

## Acceptance Criteria

- **AC-1** — A cold run populates the cache; a second identical run reports a hit under `--verbose` and spawns no preflight Godot process.
- **AC-2** — Modifying a test file, `project.godot`, the Godot binary, or an addon file invalidates the cache (a real preflight runs).
- **AC-3** — `--no-cache` bypasses cache read and write.
- **AC-4** — A corrupt cache file fails open: the run succeeds with a real preflight.
- **AC-5** — The artifact index of a cache-hit run still contains `preflight.manifest.json` and `preflight.result.json`.
- **AC-6** — The benchmark evidences the ≥30% repeat-run speedup on the dogfood fixture.
- **AC-7** — Unit and e2e coverage for hit, miss, invalidation, `--no-cache`, and fail-open paths.

## Out of Scope

- Godot boot/import reuse across suite processes (possible follow-up track).
- Changes to the Track 37 coverage plan cache.
- TTL-based invalidation.
- Cross-machine or global cache sharing.
