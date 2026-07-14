<protect>
# Track 24: Version Command

## Overview

Add a `gd-tools version` subcommand that prints all component versions (gd-tools, Godot, GUT, gdtoolkit, Python) in a Rich table. This provides users with a single command for environment diagnostics and bug reports, complementing the existing `--version` flag which only shows the gd-tools package version.

## Functional Requirements

### FR1: Version Subcommand
- Add `gd-tools version` as a Click subcommand (not a flag — a subcommand)
- The command detects and prints versions for 5 components:
  - **gd-tools** — package version (`__version__` from `gd_tools.__init__`)
  - **Godot** — detected Godot version via `find_godot()` with a default `GodotConfig` (binary=None), triggering the full 5-level resolution chain (env vars → PATH → common locations)
  - **GUT** — installed GUT version read from `addons/gut/plugin.cfg` via `get_installed_gut_version()`, using `find_project_root()` to locate the project root
  - **gdtoolkit** — installed gdtoolkit version via `importlib.metadata.version("gdtoolkit")`
  - **Python** — `sys.version` (full version string)

### FR2: Missing Component Handling
- If a component is not found, display an appropriate message:
  - Godot not found → "not detected"
  - GUT not installed → "not installed"
  - gdtoolkit not installed → "not installed"
- Missing components never cause the command to fail (exit code is always 0)

### FR3: Rich Table Output (Default)
- Default output renders a Rich table with columns:
  - Component name
  - Version (or "not detected"/"not installed")
- Uses the existing `console` Rich instance for consistent styling

### FR4: JSON Output (`--json` flag)
- `--json` flag produces machine-readable JSON output
- Structure: flat JSON object keyed by component name:
  ```json
  {
    "gd-tools": "0.3.0",
    "godot": "4.5.1",
    "gut": "9.5.0",
    "gdtoolkit": "6.1.0",
    "python": "3.11.5"
  }
  ```
- Missing components have `null` values:
  ```json
  {
    "gd-tools": "0.3.0",
    "godot": null,
    "gut": null,
    "gdtoolkit": "6.1.0",
    "python": "3.11.5"
  }
  ```

### FR5: Exit Code
- Exit code is always 0 (informational command)
- Even when components are missing, exit code remains 0

### FR6: Performance
- Command completes in <2 seconds
- No network calls (all version detection is local)
- Godot version detection subprocess is the only potentially slow operation

## Non-Functional Requirements

- **Module structure**: Version detection logic lives in a new `src/gd_tools/version.py` module with a `collect_versions()` function. The CLI command in `cli.py` stays thin (calls the module, prints the table).
- **Testing**: Unit tests with mocked version detection (no real Godot binary or GUT installation needed for tests)
- **Consistency**: Follows existing codebase patterns (Click commands, Rich console, type hints, docstrings)

## Acceptance Criteria

1. `gd-tools version` prints a Rich table with all 5 component versions
2. Missing components show "not installed" (GUT, gdtoolkit) or "not detected" (Godot)
3. `--json` flag produces valid JSON output with the flat object structure
4. Missing components in JSON output have `null` values
5. Exit code is always 0, regardless of whether components are found
6. Command completes in <2 seconds with no network calls
7. Version detection logic is in `src/gd_tools/version.py`, not inline in `cli.py`
8. Unit tests cover: all components found, Godot not found, GUT not installed, gdtoolkit not installed, JSON output, table output

## Out of Scope

- Checking coverage addon version (handled by Track 23's `check_addon_version()`)
- Checking for gd-tools updates (handled by existing `check_for_update()` in the CLI group)
- Checking pip/package manager versions
- Network-based version checks
- Checking Godot project configuration validity
</protect>
