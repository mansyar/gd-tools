<protect>
# Track 27: Verbose/Quiet Global Flags

## Overview

Add `--verbose`/`-v` and `--quiet`/`-q` global flags to the `gd-tools` CLI to control output verbosity. These flags allow users to increase output detail (for debugging) or decrease it (for CI/minimal output), addressing the current inability to control output verbosity.

A `Verbosity` enum and context object will propagate the selected verbosity level to all runner modules. The existing shared `output.py` module (created in Track 25b) will be extended to respect the verbosity level.

## Functional Requirements

### FR-1: Verbosity Enum and Context
- Define a `Verbosity` enum with three levels: `QUIET`, `DEFAULT`, `VERBOSE`
- Create a verbosity context object that stores the active `Verbosity` level
- The context is initialized from the global flags and passed to runner modules

### FR-2: Global Flags
- Add `--verbose` / `-v` flag to the main CLI group (before subcommand)
- Add `--quiet` / `-q` flag to the main CLI group (before subcommand)
- Flags are placed at the group level only: `gd-tools --verbose test`, `gd-tools --quiet lint`
- `--verbose` and `--quiet` are mutually exclusive; using both produces a usage error (exit code 2)
- When neither flag is provided, verbosity defaults to `DEFAULT` (current behavior)

### FR-3: Verbose Mode (`--verbose` / `-v`)
When verbose mode is active, the CLI displays:
- **Underlying commands:** The full external commands being executed (e.g., the complete `godot --headless -s addons/gut/gut_cmdln.gd ...` invocation, the `gdlint` command, the `gdformat` command)
- **Timing information:** Elapsed time for each major operation (test run, lint scan, format pass, coverage generation)

### FR-4: Quiet Mode (`--quiet` / `-q`)
When quiet mode is active, the CLI suppresses non-essential output:
- **Update check notification:** Suppress the stale addon version warning and PyPI update check notification
- **Init/doctor details:** Suppress init summary output and doctor detailed diagnostics (only show pass/fail status)
- **Progress/info messages:** Suppress informational messages like "Running tests...", "Generating coverage plan...", "Formatting N files..."

The following outputs are **always shown** regardless of quiet mode:
- Test pass/fail summary
- Lint violations
- Coverage reports and threshold results
- Error messages
- Exit codes remain unchanged

### FR-5: Output Module Integration
- Extend the shared `output.py` module (from Track 25b) to check the active verbosity level before printing
- Add helper functions or modify existing ones (`print_info`, `print_warning`, etc.) to respect verbosity
- Runner modules (`test_runner.py`, `lint_runner.py`, `format_runner.py`, coverage modules) check the verbosity context before printing non-essential output

## Non-Functional Requirements

### NFR-1: Backward Compatibility
- Default verbosity (no flag) must match current behavior exactly — no visible change to existing output
- All existing tests must pass without modification (unless they directly test verbosity behavior)

### NFR-2: Code Quality
- >80% line coverage and >70% branch coverage for new/modified source code
- Code follows project style guidelines (`ruff check`, `black --check`)
- Type hints on all new public functions

### NFR-3: Performance
- Verbosity check must be a simple enum comparison (O(1)), no performance impact
- No additional subprocess calls or I/O introduced by the flags themselves

## Acceptance Criteria

1. `gd-tools --verbose test` shows the underlying Godot/GUT command being executed
2. `gd-tools --verbose test` shows timing information for the test run
3. `gd-tools --verbose lint` shows the underlying gdlint command and timing
4. `gd-tools --quiet test` shows only test results summary (no progress messages)
5. `gd-tools --quiet lint` shows only lint violations (no progress messages)
6. `gd-tools --quiet doctor` shows only pass/fail status (no detailed diagnostics)
7. `--verbose` and `--quiet` used together produce a usage error with exit code 2
8. Default verbosity (no flag) matches current behavior — no output changes
9. All existing tests pass without modification
10. New code achieves >80% line coverage and >70% branch coverage

## Out of Scope

- Per-subcommand verbosity flags (e.g., `gd-tools test --verbose`) — group-level only
- Internal state path display (config file path, plan path, coverage output path) — not selected for verbose mode
- Debug diagnostics (Godot version detected, GUT version used, file counts) — not selected for verbose mode
- Config file support for default verbosity (e.g., `verbosity = "quiet"` in `gd-tools.toml`)
- Logging to file — verbosity controls terminal output only
- Changes to JSON output format — machine-readable output is unaffected by verbosity flags
</protect>
