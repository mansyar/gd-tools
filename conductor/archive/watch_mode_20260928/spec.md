# Specification: Watch Mode (`gd-tools test --watch`)

- **Track ID:** watch_mode_20260928
- **Type:** Feature
- **Roadmap reference:** Track 28 (Phase 7 — Strategic Features)
- **Status:** Approved (2026-09-28)

## Overview

Add a `--watch` flag to `gd-tools test` that keeps the CLI alive, observes `.gd`
files under the project, and re-runs the affected native-runtime test suites
when files change. This is the flagship Phase 7 feature: it closes the inner
dev loop (save → test → feedback) that today requires manually re-invoking the
CLI after every edit.

## Functional Requirements

1. **CLI flag:** `--watch` on `gd-tools test`. Mutually exclusive with
   `--runtime gut` → hard error, exit 2, message points to the native runtime.
2. **Non-interactive guard:** `--watch` under `CI=true` → exit 2 with a clear
   message (watch mode is interactive; prevents accidental CI hangs, per
   workflow principle #6).
3. **Startup:** run the full filtered suite once (respecting
   `--suite`/`--test`/`--tag`), then enter the watch loop.
4. **Watch scope:** all `.gd` files under the project root, excluding
   `.godot/`, `.gd-tools/`, `addons/gd-tools-*`, and artifact directories
   (reusing existing exclusion logic). Newly created `.gd` files are picked up
   automatically (watchdog handles create/delete/rename events).
5. **File→suite mapping (convention):** changed `foo.gd` → suite `test_foo.gd`
   or `foo_test.gd`, with the `test_` prefix taking precedence; a sibling in
   the same directory is preferred, otherwise any selected suite with a
   matching stem is used (supports the common `src/` + `tests/` layout); a
   changed file that *is* a suite re-runs itself; edits to shared test helpers
   fall back sensibly. No match →
   explicit status line ("No test suite maps to `<path>` — running full suite").
6. **Debounce:** fixed 500 ms, coalescing rapid saves into one run.
7. **Mid-run saves:** set a dirty flag; exactly one fresh re-run of the
   currently-mapped tests executes when the in-flight run completes.
8. **Filters:** `--suite`/`--test`/`--tag` remain respected inside the watch
   loop; mapping selects within the filter.
9. **Coverage:** `--coverage` composes per-run as in a normal invocation.
10. **Terminal UX:** clear screen before each run; print
    `Watching N files. Press Ctrl+C to stop.` on entry; every run (including
    fallback/no-match runs) ends with the existing result reporter output, so
    the last result is always visible.
11. **Exit codes:** Ctrl+C → exit 0 regardless of the last run's result;
    startup failures (bad config, no Godot binary, invalid flags) → exit 2.
12. **Dependency:** `watchdog` added to runtime deps and documented in
    `tech-stack.md` (tech-stack note precedes implementation per workflow).

## Non-Functional Requirements

- Cross-platform: Windows + Linux must work (CI matrix); macOS best-effort
  (not in CI matrix).
- Single-process, no daemon; reuses the existing native-runtime orchestrator
  (one Godot process per suite, sequential).
- New source meets the workflow quality gates: >80% line / >70% branch
  coverage, type hints, docstrings, ruff/black clean.
- Watch-loop logic unit-testable with a mocked/emulated event source (no real
  filesystem events in unit tests).

## Acceptance Criteria

1. `gd-tools test --watch` runs the full suite once, then prints the watching
   banner and blocks.
2. Editing `res://src/foo.gd` re-runs only `test_foo.gd`/`foo_test.gd` (within
   any active filters) after ≤ ~1 s.
3. Saving a file with no suite mapping prints an explicit status line and
   triggers the full-suite fallback run.
4. Rapid multi-saves within 500 ms produce exactly one run; a save during a
   run produces exactly one queued follow-up run.
5. A newly created test suite file is discovered and run without restarting
   watch mode.
6. `--watch --coverage` produces a coverage report per run;
   `--watch --runtime gut` exits 2 with a clear message; `CI=true` + `--watch`
   exits 2.
7. Ctrl+C exits 0 with the last run's result visible; no orphan Godot
   processes remain.
8. Watch mode works on Windows and Linux.

## Out of Scope

- GUT runtime watching (GUT is a migration bridge slated for Phase 5 removal).
- Dependency-aware source→suite mapping (class_name/preload graph analysis) —
  possible follow-up track.
- Watching `.tscn`/`.tres`/other resource types.
- User-defined ignore rules (`.gdignore` / config excludes).
- Editor plugin integration, parallel suite execution, auto-rerun on config
  file change.
