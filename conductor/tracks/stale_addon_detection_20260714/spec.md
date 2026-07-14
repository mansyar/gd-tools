<protect>
# Track 23: Stale Addon Detection

## Overview

When a user upgrades `gd-tools-cli` via pip, the deployed GDScript coverage addon files (`coverage.gd`, `pre_run_hook.gd`, `post_run_hook.gd`) in their Godot project are **not** automatically updated. The user must remember to re-run `gd-tools init`. This creates a silent version-skew bug — the Python package and the deployed GDScript addons can drift apart, causing subtle coverage instrumentation failures.

This track adds a version-stamping mechanism and a stale-detection check that warns the user when their deployed addon is outdated relative to the installed `gd-tools-cli` package.

## Background & Context

- **Product Definition Reference**: The product emphasizes "zero-friction bootstrap" and "convention over configuration." Silent version drift violates the zero-friction promise — users shouldn't have to manually track addon freshness.
- **Tech Stack**: Python CLI (Click), `packaging` library (already a dependency, used by `update_check.py` for version comparison), `__version__` from `importlib.metadata`.
- **Existing Patterns**: `update_check.py` already implements a PyPI update check with `GD_TOOLS_NO_UPDATE_CHECK=1` env var suppression. This track reuses the same env var and follows the same module-separation pattern.
- **ROADMAP Reference**: Track 23, Phase 6 — Quick Wins. Effort: 0.5 day. Risk: LOW. Dependencies: Track 7 (init), Track 18 (versioning).

## Functional Requirements

### FR1: Version File Creation During Init

- **FR1.1**: `gd-tools init` shall write a `_version.txt` file to `addons/gd-tools-coverage/_version.txt` in the project root.
- **FR1.2**: The file shall contain a single line with the installed `gd-tools-cli` package version string (e.g., `0.3.0`), as resolved by `gd_tools.__version__`.
- **FR1.3**: The version file shall be (re)written on every `gd-tools init` invocation, overwriting any existing version file.
- **FR1.4**: The `install_coverage_addon()` function in `init.py` shall be extended (or a companion call added in `run_init`) to write the version file after copying the addon `.gd` files.
- **FR1.5**: The init action summary shall include an entry noting the version file was written (e.g., `"Wrote addon version file (v0.3.0)"`).

### FR2: Stale Addon Check on CLI Invocation

- **FR2.1**: On every CLI command invocation (via `GdToolsGroup.invoke()`), the tool shall check whether the deployed addon version file exists and compare its version against the installed package version.
- **FR2.2**: The check logic shall reside in a new `src/gd_tools/addon_check.py` module, called from `GdToolsGroup.invoke()` in `cli.py` — mirroring how `check_for_update()` from `update_check.py` is already called there.
- **FR2.3**: If the addon version file is **missing**, a warning shall be printed to stderr:
  ```
  WARNING: Coverage addon version file not found. Run `gd-tools init` to deploy the addon.
  ```
- **FR2.4**: If the addon version is **older than** the installed package version, a warning shall be printed to stderr:
  ```
  WARNING: Coverage addon is outdated (v0.2.0 deployed, v0.3.0 available). Run `gd-tools init` to update.
  ```
- **FR2.5**: If the addon version **equals** the installed package version, no warning shall be printed.
- **FR2.6**: If the addon version is **newer than** the installed package version (e.g., user downgraded the pip package), no warning shall be printed (this is not a stale-addon scenario).
- **FR2.7**: The warning shall be **non-blocking** — the command shall still execute normally and the exit code shall be unchanged.
- **FR2.8**: The check shall fail silently (no crash, no warning) if any unexpected error occurs during file reading or version parsing.

### FR3: Environment Variable Suppression

- **FR3.1**: The `GD_TOOLS_NO_UPDATE_CHECK=1` environment variable shall suppress the stale addon check entirely (no file read, no warning), reusing the existing env var pattern from `update_check.py`.

### FR4: Version Comparison

- **FR4.1**: Version comparison shall use `packaging.version.parse()` (already a project dependency), consistent with the comparison logic in `update_check.py`.
- **FR4.2**: If the version string in `_version.txt` cannot be parsed, it shall be treated as stale (warning printed with the raw string shown).

### FR5: Doctor Integration

- **FR5.1**: The existing `check_coverage_addon()` function in `doctor.py` shall be enhanced to also check the addon version file.
- **FR5.2**: If the addon files are present and the version file exists, the doctor check message shall include the deployed version (e.g., `"Coverage addon installed (v0.3.0)"`).
- **FR5.3**: If the addon files are present but the version file is missing, the doctor check shall report a warning: `"Coverage addon installed but version file missing - run \`gd-tools init\` to update"`.
- **FR5.4**: If the addon version is stale (addon < package), the doctor check shall report a warning with both versions.

## Non-Functional Requirements

- **NFR1 (Performance)**: The stale addon check shall complete in <5ms (single file read + version parse). No network calls.
- **NFR2 (Robustness)**: The check shall never raise an exception or cause the CLI to crash, regardless of file system state or version string format.
- **NFR3 (Compatibility)**: The `_version.txt` file shall be UTF-8 encoded plain text with a trailing newline.
- **NFR4 (Testability)**: All check logic shall be unit-testable with mocked file system paths and version strings.

## Acceptance Criteria

1. `gd-tools init` writes a `_version.txt` file to `addons/gd-tools-coverage/` containing the installed package version.
2. The init summary includes an entry noting the version file was written.
3. When addon version < package version, a warning is printed to stderr.
4. When versions match, no warning is printed.
5. When the version file is missing, a warning is printed to stderr.
6. The warning does not block command execution (exit code unchanged).
7. `GD_TOOLS_NO_UPDATE_CHECK=1` suppresses the check entirely.
8. When addon version > package version (downgrade), no warning is printed.
9. When the version string is unparseable, a stale warning is printed with the raw string.
10. `gd-tools doctor` reports the addon version when present, and warns when the version file is missing or stale.
11. All unit tests pass with >80% line coverage on new/modified source code.

## Out of Scope

- Automatic addon file updating (the user must still run `gd-tools init` manually).
- Checking individual `.gd` file checksums or content hashes (version-level comparison only).
- Warning when addon version > package version (downgrade scenario — not a stale-addon problem).
- Network-based version checks (this is a local file comparison only; PyPI checks are handled by `update_check.py`).
- Any changes to the GDScript addon files themselves.
- Shell completion, verbose/quiet flags, or other Phase 6 tracks.
</protect>
