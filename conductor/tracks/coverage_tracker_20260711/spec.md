# Track 10: Coverage Tracker Addon (GDScript)

## Overview

Implement the GDScript coverage tracker autoload (`_GDTCoverage`) that records line hit counts during GUT test execution. This is the runtime data collection component of Architecture C (hybrid instrumentation approach validated in Track 0 spike). The tracker is a Godot autoload singleton bundled with gd-tools, deployed to user projects via `gd-tools init`.

This track replaces the 3-line placeholder `coverage.gd` (deployed in Track 7) with the full tracker implementation, and adds autoload registration to the `init.py` flow.

## Functional Requirements

### FR-1: Coverage Tracker Autoload (`coverage.gd`)

The file `src/gd_tools/addons/gd-tools-coverage/coverage.gd` shall implement a Godot autoload singleton with the following:

**Class structure:**
- `extends Node`
- Registered as autoload `_GDTCoverage` in `project.godot`

**Internal state:**
- `_hits: Dictionary` — nested dictionary keyed by `file_id (int)`, value is `Dictionary` of `line_id (int) -> count (int)`
- `_active: bool` — flag controlling whether `hit()` records data

**Methods:**
- `_ready() -> void` — reads `GD_TOOLS_COVERAGE_ACTIVE` environment variable; sets `_active` to `true` only when value is `"1"` or `"true"` (case-insensitive); `false` otherwise (including when unset, `"0"`, `"false"`, or any other value)
- `hit(file_id: int, line_id: int) -> void` — if `_active` is false, returns immediately (no-op, single bool check); if active, increments `_hits[file_id][line_id]` counter, creating nested dict entries as needed
- `get_hits() -> Dictionary` — returns `_hits` (raw dictionary with int keys)
- `reset() -> void` — clears `_hits` to empty `{}`
- `set_active(active: bool) -> void` — sets `_active` flag (for testability)
- `is_active() -> bool` — returns `_active`

### FR-2: Autoload Registration in init.py

Add a new function `register_coverage_autoload(project_root: Path) -> None` to `src/gd_tools/init.py`:

- Registers `_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"` in the `[autoload]` section of `project.godot`
- Creates `[autoload]` section if it doesn't exist
- Idempotent: if `_GDTCoverage=` already exists in `[autoload]`, does not duplicate
- Called in `run_init()` flow after `install_coverage_addon()`

### FR-3: Testing

**Python unit tests (pytest):**
- Test `register_coverage_autoload()`: registers autoload in project.godot, idempotent on repeat calls, handles missing `[autoload]` section
- Test `install_coverage_addon()`: verify deployed `coverage.gd` contains real implementation (not placeholder TODO)

**GUT integration tests (`@pytest.mark.integration`):**
- Test `hit()` records correctly when active
- Test multiple hits to same line increment counter
- Test `reset()` clears all data
- Test `hit()` is no-op when `_active` is false
- Test `set_active()` / `is_active()` toggle
- Test `get_hits()` returns correct nested dictionary structure

## Non-Functional Requirements

- **NFR-1:** When `_active` is false, `hit()` must perform only a single boolean check before returning (minimal overhead for production runs)
- **NFR-2:** Tracker must be thread-safe with GUT coroutines (no issues with `await` in test scripts)
- **NFR-3:** `coverage.gd` must pass `gdlint` and `gdformat` checks
- **NFR-4:** Python code must pass `ruff`, `black`, and maintain >80% line coverage / >70% branch coverage

## Acceptance Criteria

1. Autoload `_GDTCoverage` registers correctly in `project.godot` via `register_coverage_autoload()`
2. `hit(0, 5)` records correctly; `get_hits()` returns `{0: {5: 1}}` (int keys in GDScript Dictionary)
3. Multiple `hit(0, 5)` calls increment correctly: `get_hits()` returns `{0: {5: 3}}` after 3 calls
4. `reset()` clears all hit data; `get_hits()` returns `{}`
5. When `GD_TOOLS_COVERAGE_ACTIVE` is not set (or set to `"0"`/`"false"`), `hit()` is a no-op
6. `set_active(false)` makes `hit()` a no-op; `set_active(true)` re-enables recording
7. `is_active()` returns the current active state
8. GUT integration tests pass with real Godot binary (when available)
9. Python unit tests pass with >80% line coverage for modified init.py code

## Out of Scope

- `pre_run_hook.gd` implementation (Track 11)
- `post_run_hook.gd` implementation (Track 11)
- Coverage metrics computation and report generation (Track 12+)
- Instrumentation plan generation (Track 9 — completed)
- Python-side `--coverage` flag behavior (Track 6 — completed, currently no-op)
