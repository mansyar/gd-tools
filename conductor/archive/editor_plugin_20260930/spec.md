# Track: Godot Editor Plugin (Roadmap Track 35)

## Overview

Eliminate the context switch between the Godot editor and the terminal. A Godot editor plugin, deployed by `gd-tools init`, provides a **"gd-tools" dock panel** for running tests and coverage, and a **coverage heatmap overlay** in the script editor that colors lines green (covered), red (uncovered), and yellow (partial branches). The plugin shells out to the `gd-tools` CLI and consumes existing machine-readable artifacts — no changes to the native test protocol, no new config keys.

**Type:** Feature
**Roadmap reference:** `docs/ROADMAP.md` Track 35 (Phase 8 — Differentiators)
**Branch:** `feature/editor-plugin-20260930`

## Functional Requirements

### Deployment (Python side, TDD-covered)

1. `gd-tools init` deploys `addons/gd-tools-editor/` (`plugin.cfg`, `plugin.gd`, `dock.gd`, `coverage_overlay.gd`) alongside the existing addons; re-init follows the smart-backup behavior; the addon is package data in the wheel.
2. Activation stays manual: the user enables "gd-tools" in Godot's Plugin settings (writes the `editor_plugins` entry to `project.godot`). `init` does not auto-enable it.
3. `gd-tools doctor` verifies the deployed editor plugin files (presence/staleness), consistent with existing addon checks.

### Dock panel (GDScript, manual-checklist verified)

4. "Run Tests" button → executes `gd-tools test` via non-blocking `OS.execute()`/process API; "Run Coverage" → `gd-tools test --coverage`.
5. Runs are async with a visible in-progress state; a second click while running is ignored. Manual refresh only (no auto-run on save).
6. Results display: pass/fail/skip counts + duration, failed tests with their assertion messages, and the path to the artifact index under `.gd-tools/artifacts/<run_id>/`. Parsed from the CLI's existing machine-readable outputs (artifact index / JUnit XML) — no protocol changes.
7. Coverage summary (line/branch percentages) shown in the dock after a coverage run.
8. If the `gd-tools` executable is not found on PATH, the dock shows a friendly message with the install command (`pip install gd-tools-cli`) instead of a cryptic error.

### Coverage heatmap overlay (GDScript, manual-checklist verified)

9. Uses Godot's `CodeEdit` line background color API: green = covered, red = uncovered, yellow = partial branch.
10. Data source: the machine-readable coverage artifacts under `.gd-tools/coverage/` — no new file format, no CLI invocation for the overlay.
11. Auto-refresh when a dock "Run Coverage" completes; loads on editor open if artifacts exist; stale data (source files newer than coverage data) is flagged visually, never silently shown as fresh.

### Configuration

12. Zero config — no new `gd-tools.toml` keys; hardcoded sensible colors and behavior (convention over configuration).

## Non-Functional Requirements

- **Godot 4.5+** — must work on 4.5, 4.6, 4.7 (the CI-compat-matrix versions); editor-API version caveats documented in the manual checklist.
- **Safety:** subprocess invocation uses argument-list form (no shell string), consistent with the workflow's security rules.
- **No new Python dependencies.**
- **Responsiveness:** the overlay must not introduce noticeable lag when opening scripts (bounded per-file work).

## Verification Model

- **Python side:** strict TDD per workflow (init deployment, doctor checks, packaging) — unit tests first, >80% line / >70% branch.
- **GDScript plugin UI:** documented manual testing checklist, executed and confirmed at phase checkpoints (headless CI cannot exercise editor UI).

## Acceptance Criteria

1. Plugin files deploy via `gd-tools init`; re-init is idempotent with smart backup (unit-tested).
2. Doctor reports editor-plugin status correctly (unit-tested).
3. After enabling in Plugin settings, the "gd-tools" dock appears with Run Tests / Run Coverage buttons.
4. Run Tests executes async and shows summary + failures in the dock.
5. Run Coverage produces reports and the heatmap overlay appears in the script editor.
6. Covered / uncovered / partial lines are visually distinct.
7. Plugin is toggleable on/off in Plugin settings without errors.
8. Missing `gd-tools` shows the friendly fallback message.
9. Works on Godot 4.5/4.6/4.7 per the manual checklist.

## Out of Scope

- Lint warnings in the editor margin (roadmap "if feasible" item — deferred).
- Auto-run on save / watch-mode integration.
- Configurable heatmap colors or an `[editor]` config section.
- Direct native-runtime invocation from the plugin (no protocol coupling).
- Distribution via the Godot Asset Library (init-deployed only).
