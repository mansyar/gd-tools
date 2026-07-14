# Track: coverage_autoload_fix — Fix Coverage Autoload Corruption & Multi-Path CLI

## Overview

Two related issues are addressed in this track:

**A. Coverage instrumentation corrupts autoload scripts (Bug).** When `gd-tools test --coverage` runs, the coverage system generates a plan of all `.gd` files, then a GUT pre-run hook (`pre_run_hook.gd`) injects `_GDTCoverage.hit()` calls into each script's `source_code` and calls `script.reload()`. Two defects cause a cascading test failure:

1. **Exclude matching is path-vs-basename broken.** `discover_gd_files` matches exclude entries against bare directory *names* (`d not in excludes`), so a config value like `exclude = ["scripts/autoload"]` is silently ignored — autoload scripts end up in the plan.
2. **The hook corrupts autoloads on reload failure.** `_instrument_file` sets `script.source_code = instrumented` *before* calling `reload()`. Autoloads always have active instances, and `Script.reload()` defaults to `keep_state=false`, so Godot returns `ERR_ALREADY_IN_USE` ("Cannot reload script while instances exist"). The canonical hook does not restore the original source on failure, leaving autoloads — and transitively the script-loading system — in a broken state. All subsequent `new()` calls fail.

**B. CLI commands accept only a single path (Feature gap).** `lint` and `format` accept one positional path; `test` has no path argument at all (test dirs come from config). Users cannot scope a run to multiple directories/files in one invocation (e.g. `gd-tools lint src/ tests/`).

## Background / Root Cause

(Confirmed against source during investigation:)
- `src/gd_tools/file_discovery.py:37` — `dirs[:] = [d for d in dirs if d not in excludes]` matches by basename only.
- `src/gd_tools/coverage/plan_generator.py:339` — forwards `exclude_dirs` to `discover_gd_files`.
- `src/gd_tools/coverage/orchestrator.py:77-81` — passes `config.coverage.exclude` into `generate_plan`.
- `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd:62-72` — sets `source_code` then `reload()`; no restore on `err != OK`.
- Godot `Script.reload(keep_state: bool = false)` — default `keep_state=false`; `GDScript::reload` guard `ERR_FAIL_COND_V(!p_keep_state && has_instances, ERR_ALREADY_IN_USE)` fails for scripts with active instances (autoloads).

## Functional Requirements

### Workstream A — Coverage Autoload Fix

**FR-1: Path-aware exclude matching (hybrid).**
`discover_gd_files` must interpret exclude entries as follows:
- Entries with no path separator (e.g. `addons`, `.godot`) match any directory *basename* at any depth (backward compatible with current behavior and `DEFAULT_EXCLUDES`).
- Entries containing a path separator `/` (e.g. `scripts/autoload`) match as a *path prefix* relative to the search root; any file whose path relative to root starts with the prefix is excluded.

**FR-2: Autoload auto-exclusion from `project.godot`.**
`generate_plan` must read the project's `project.godot` `[autoload]` section, resolve the autoload script paths, and exclude those scripts from the coverage plan automatically — regardless of the manual `exclude` list. This eliminates the reload-failure class of bug at the source.

**FR-3: Harden `_instrument_file` in the canonical `pre_run_hook.gd`.**
`_instrument_file` must:
- Capture the original `source_code` before any mutation.
- Before mutating, check whether the script has active instances; if so, skip instrumentation for that file and log a warning (do not call `reload()`).
- On any `reload()` failure, restore `script.source_code` to the original before returning, so a script is never left in a corrupted state.

### Workstream B — Multi-Path CLI

**FR-4: `lint` accepts multiple paths.**
`gd-tools lint` accepts zero or more positional path arguments. When multiple paths are given (e.g. `gd-tools lint src/ tests/`), `.gd` files are discovered across all paths into a single deduplicated set and linted together. With no path given, defaults to `.` (current behavior).

**FR-5: `format` accepts multiple paths.**
`gd-tools format` accepts zero or more positional path arguments with the same combined-discovery behavior as `lint`. Defaults to `.` when none given.

**FR-6: `test` accepts a `paths` filter argument.**
`gd-tools test` gains an optional positional `paths` argument that, when provided, restricts which test files/dirs GUT runs for that invocation, overriding `config.test.test_dirs`. When omitted, behavior is unchanged (config-driven discovery).

## Non-Functional Requirements

- **NFR-1 (Backward compatibility).** Existing `gd-tools.toml` exclude lists using bare names continue to work identically. The default excludes (`addons`, `.godot`, `.gd-tools`, `.git`) remain effective.
- **NFR-2 (Coverage).** New/changed Python source code maintains >80% line and >70% branch coverage. GDScript hook changes are covered by integration/fixture tests where feasible.
- **NFR-3 (Cross-platform paths).** Path-prefix matching and multi-path discovery work on Windows, macOS, and Linux (handle `\` vs `/`).
- **NFR-4 (No regressions).** All existing tests continue to pass; the spike project still instruments/coverage-runs non-autoload scripts correctly.

## Acceptance Criteria

1. `exclude = ["scripts/autoload"]` in `[coverage]` (and `[lint]`/`[format]`) excludes files under `scripts/autoload/` from discovery; `exclude = ["autoload"]` still excludes any dir named `autoload` at any depth.
2. With a `project.godot` containing `[autoload]` entries, those autoload scripts do NOT appear in the generated `plan.json`.
3. In `pre_run_hook.gd`, a script with active instances is skipped with a warning and its `source_code` is never mutated; on any `reload()` failure the original `source_code` is restored.
4. `gd-tools lint src/ tests/` lints all `.gd` files in both directories in one run; `gd-tools lint` (no args) lints `.`.
5. `gd-tools format src/ tests/` formats files across both dirs; `gd-tools format` (no args) formats `.`.
6. `gd-tools test test/foo.gd test/bar/` runs only the specified test paths for that invocation; `gd-tools test` (no args) uses config test_dirs.
7. All existing unit/integration tests pass; new code meets coverage thresholds.

## Out of Scope

- Rewriting `pre_run_hook.gd` to support `keep_state=true` reload of autoloads (skipping is safer and sufficient).
- Coverage *reporting* changes (HTML/LCOV/Cobertura) — unaffected.
- Glob/wildcard syntax in excludes (e.g. `**/autoload`) — hybrid basename+path-prefix only.
- Auto-detecting autoloads for the `lint`/`format` exclude (autoload auto-exclusion applies to coverage plan only).
- Splitting this into separate tracks — bundled per user request.
