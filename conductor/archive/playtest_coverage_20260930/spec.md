# Specification: Coverage During Playtesting

**Track ID:** `playtest_coverage_20260930`
**Type:** Feature
**Status:** New
**Source:** `docs/ROADMAP.md` — Track 34
**Risk:** High | **Effort:** 3–4 days

## Overview

Extend the coverage system so coverage can be collected while a human plays the
game — not only during automated test runs. `gd-tools coverage run` launches the
game (windowed, instrumented), collects coverage during live gameplay, and
produces a report on game exit. This closes the biggest gap between gd-tools
coverage and traditional language coverage tools and is a key differentiator no
other GDScript tool offers.

The v0.5.0 coverage architecture makes this the right moment: the coverage addon
already ships an autoload-based tracker (`coverage.gd`) activated via
environment variables, and the reporter suite (terminal, HTML, LCOV, Cobertura,
JSON) is fully reusable. The missing pieces are (1) a playtest-mode flush inside
the tracker — data writing currently happens only through the test-runtime-invoked
`post_run_hook` — and (2) a Python-side orchestrator that launches the windowed
game, waits for it to end, and runs the reporters.

## Functional Requirements

### FR-1 — CLI command: `gd-tools coverage run`

Launch the project's game under coverage instrumentation.

- `--scene <path>`: optional; when omitted, launch the project's main scene from
  `project.godot`.
- `--timeout <N>`: auto-close the game after N seconds (also enables automated
  playtest sessions, e.g. in CI).
- `--min <N>`: exit 1 if session coverage is below the threshold — consistent
  with all other coverage paths.
- `--report-format`: passthrough to the existing reporter machinery.

### FR-2 — Launch behavior

The game runs **windowed** (non-headless) so a human can play. The Godot binary
is resolved via the existing runner machinery. Activation reuses the
environment-variable contract: `GD_TOOLS_COVERAGE_PLAN`,
`GD_TOOLS_COVERAGE_OUTPUT`, plus a new `GD_TOOLS_COVERAGE_PLAYTEST=1`.

### FR-3 — Coverage scope

Full-project coverage plan generation, identical to test coverage — respecting
`# gd-tools: no cover` annotations and configured includes/excludes.

### FR-4 — Playtest mode in the coverage tracker (addon)

`coverage.gd` gains an env-activated playtest mode (`GD_TOOLS_COVERAGE_PLAYTEST=1`):

- **Periodic flush:** coverage data is written every N seconds (configurable
  interval, default 5s) to the output path.
- **Exit flush:** coverage data is finalized and written when the game exits
  (window close / `NOTIFICATION_WM_CLOSE_REQUEST` / quit).
- **Isolation:** playtest mode must not activate during normal test runs; the
  existing test-runtime hook path is unaffected.

### FR-5 — Exit handling (Python side)

The CLI waits for the game process to end, then collects the output file and
runs the **existing reporter suite** — terminal summary (default), HTML, LCOV,
Cobertura, JSON — via the existing `--report-format` machinery. No new reporter
code.

### FR-6 — Crash policy

If the game exits uncleanly (crash or force-kill) but periodic data exists on
disk, the CLI still produces a report from the last written snapshot and emits a
warning noting the session was incomplete.

### FR-7 — Exit codes

Consistent with the project-wide exit-code contract:

- `0` — success.
- `1` — user-facing failure, including `--min` threshold failure.
- `2` — structured diagnostics error (invalid scene, missing project,
  instrumented-game launch failure).

### FR-8 — Addon compatibility

The existing test-runtime coverage path (pre/post-run hooks) is unaffected;
playtest mode activates only via its env var.

## Non-Functional Requirements

- **NFR-1:** Flush writes are small and non-blocking — the player must not feel
  stutter from periodic writes.
- **NFR-2:** Works cross-platform (Ubuntu/Windows/macOS), matching the 6-job CI
  matrix; process-launch code reuses existing Windows-safe runner patterns.
- **NFR-3:** All new/changed Python code meets the >80% line / >70% branch
  coverage gates; GDScript addon code is unit-tested where testable
  (`tests/unit/test_coverage_tracker.gd`).
- **NFR-4:** Docs updated: USER_GUIDE playtest-coverage section, README feature
  mention, CHANGELOG entry.

## Acceptance Criteria

1. `gd-tools coverage run` launches an instrumented game windowed and collects
   coverage during play.
2. On clean game exit, a full report is produced via existing reporters.
3. On crash/kill, the last periodic snapshot still yields a report with a warning.
4. `--timeout N` auto-closes the game after N seconds; `--min N` gates the exit
   code to 1 when unmet.
5. `--scene` omitted → main scene launches; `--scene <path>` launches that scene.
6. Normal test runs (`gd-tools test --coverage`) behave exactly as in v0.5.0
   (no regression).
7. `ruff`/`black` clean; exit codes 0/1/2 tested; git notes attached per
   workflow.

## Out of Scope

- Baseline save/diff integration for playtest sessions (`--save-baseline` /
  `--diff`) — deferred to a later track.
- Any new report formats (existing reporters only).
- Parallel/automated multi-instance playtesting.
- Editor plugin integration (separate roadmap Track 35).
- Changes to the GUT bridge (deprecated path).
