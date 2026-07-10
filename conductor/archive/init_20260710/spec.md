<protect>
# Track 7: Init Command — Specification

## Overview

The `init` command bootstraps a Godot project for use with gd-tools. It detects the project root, identifies the Godot version, installs GUT (Godot Unit Test) if not present, deploys the coverage addon as placeholder stubs, creates all configuration files (`.gutconfig.json`, `gd-tools.toml`, `gdlintrc`, `gdformatrc`), creates the `.gd-tools/` data directory, and prints a summary of actions taken. The command is idempotent — running it multiple times produces the same end state without duplicating entries.

## Functional Requirements

### FR-1: Project Root Detection
- Walk up from CWD to find `project.godot`.
- Reuse `config.find_project_root()` (Track 2).
- Raise `ConfigError` (exit code 2) if not found, with an actionable error message.

### FR-2: Godot Version Detection
- Reuse `godot.find_godot()` and `godot.get_godot_version()` (Track 3).
- Require Godot 4.5+. Raise `GodotNotFoundError` (exit code 2) if Godot is not found.
- Map Godot version to GUT version via `godot.get_gut_version_for_godot()` (Track 3).

### FR-3: GUT Installation Check
- Check if `addons/gut/gut.gd` exists in the project root.
- If GUT is installed: verify version compatibility. Print a warning if the installed GUT version does not match the expected version from `GUT_VERSION_MAP`.
- If GUT is NOT installed:
  - Interactive mode: prompt "GUT not found. Install automatically? [Y/n]".
    - Y: proceed to download and extract.
    - n: print manual install instructions (Asset Library link + GitHub zip URL). Exit 0.
  - `--non-interactive` mode: assume Y (install automatically). Do not prompt.

### FR-4: GUT Download and Extraction
- Download GUT zip from: `https://github.com/bitwes/Gut/archive/refs/tags/v{version}.zip`.
- Extract the zip and copy `addons/gut/` to `project_root/addons/gut/`.
- **Fail fast**: on any network, download, or extraction error, immediately print an actionable error with manual install instructions (Asset Library link + zip URL). No retry logic.
- Clean up temporary files (downloaded zip, extracted temp directory).

### FR-5: GUT Plugin Enabling in project.godot
- Add `[editor_plugins]` section with `enabled=PackedStringArray("res://addons/gut/plugin.gd")` to `project.godot`.
- Idempotent: check if the entry already exists before adding. Do not duplicate.
- Preserve all existing content in `project.godot`.

### FR-6: Coverage Addon Deployment (Placeholder Stubs)
- Copy bundled placeholder GDScript files to `addons/gd-tools-coverage/`.
- Files to deploy (all placeholder stubs with TODO comments, no real instrumentation):
  - `coverage.gd` — `extends Node`, TODO: Phase 3 will implement tracking.
  - `pre_run_hook.gd` — `extends GutHookScript`, TODO: Phase 3 will implement instrumentation.
  - `post_run_hook.gd` — `extends GutHookScript`, TODO: Phase 3 will implement coverage saving.
- Always overwrite if files are stale (different from bundled version).
- Files ship as package data inside the Python distribution.

### FR-7: .gutconfig.json Creation/Update
- Create `.gutconfig.json` if it does not exist, using `GUTCONFIG_TEMPLATE`:
  ```json
  {
    "dirs": ["res://test/", "res://tests/"],
    "include_subdirs": true,
    "prefix": "test_",
    "suffix": ".gd",
    "should_exit": true,
    "junit_xml_file": ".gd-tools/results.xml",
    "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
    "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd"
  }
  ```
- If `.gutconfig.json` already exists: merge with existing config.
  - Preserve user's `dirs`, `prefix`, `suffix`, `include_subdirs`.
  - Always set/overwrite `pre_run_script`, `post_run_script`, `junit_xml_file`, `should_exit`.

### FR-8: gd-tools.toml Creation
- Create `gd-tools.toml` with default values if it does not exist.
- If `gd-tools.toml` already exists: do not overwrite (preserve existing config).
- Reuse `config.save_config()` (Track 2).

### FR-9: gdlintrc and gdformatrc Generation
- Generate `gdlintrc` and `gdformatrc` from `[lint]`/`[format]` exclude lists in `gd-tools.toml`.
- Reuse `config.generate_gdlintrc()` and `config.generate_gdformatrc()` (Track 2).
- **Policy: Generate if missing, warn if differs.**
  - If the file does not exist: generate it.
  - If the file exists but differs from what init would produce: print a warning showing the difference. Do not overwrite.
  - If the file exists and matches: do nothing.

### FR-10: .gd-tools/ Directory and .gitignore
- Create `.gd-tools/` directory in the project root.
- Add `.gd-tools/` to `.gitignore` if not already present.
- Create `.gitignore` if it does not exist.

### FR-11: Summary Output
- Print a summary of all actions taken (what was installed, configured, created).
- Print next steps (e.g., "Run `gd-tools test` to execute tests").
- Use Rich-formatted output with semantic colors (green for success, yellow for warnings, cyan for info).

### FR-12: Non-Interactive Mode
- `--non-interactive` flag: skip all prompts, assume defaults.
  - GUT not installed: proceed with automatic download (assume Y).
  - All other operations: proceed without confirmation.
- Required for CI/CD pipelines.

## Non-Functional Requirements

### NFR-1: Idempotency
- Running `init` multiple times must produce the same end state.
- No duplicate entries in `project.godot`, `.gitignore`, or config files.
- Stale files (coverage addon, GUT version) should be updated, not duplicated.

### NFR-2: Error Handling
- All errors follow the product-guidelines format: `[Error] <What>\n  Cause: <Why>\n  Fix: <Steps>`.
- Exit codes: 0=success, 1=failure, 2=config/environment error.
- Network failures: fail fast with manual install instructions (no retry).

### NFR-3: Code Quality
- Type hints on all function signatures (Python 3.10+).
- Docstrings on all public functions.
- Naming: `snake_case` functions, `UPPER_SNAKE_CASE` constants.
- ASCII-only terminal output (✓/✗, [OK]/[FAIL]). Color is supplementary.

### NFR-4: Test Coverage
- >80% line coverage, >70% branch coverage for `init.py`.
- Mock network calls (`requests.get`), Godot detection (`shutil.which`, `subprocess.run`).
- Use `tmp_path` for filesystem operations.

## Acceptance Criteria

1. Running `gd-tools init` in a Godot project installs GUT correctly (correct version for detected Godot).
2. `project.godot` has GUT plugin enabled under `[editor_plugins]`.
3. Plugin enabling is idempotent — running `init` twice does not duplicate the `[editor_plugins]` entry.
4. Coverage addon placeholder files are copied to `addons/gd-tools-coverage/`.
5. `.gutconfig.json` is created with coverage hook paths (`pre_run_script`, `post_run_script`).
6. Existing `.gutconfig.json` is merged correctly (user config preserved, hooks added/updated).
7. `gd-tools.toml` is created with defaults if absent.
8. Existing `gd-tools.toml` is not overwritten.
9. `gdlintrc` and `gdformatrc` are generated if absent.
10. If `gdlintrc`/`gdformatrc` exist but differ from expected, a warning is printed (no overwrite).
11. `.gd-tools/` directory is created.
12. `.gd-tools/` is added to `.gitignore` (idempotent — no duplicate entries).
13. `--non-interactive` mode works without any prompts.
14. Re-running `init` is fully idempotent (no duplicates, stale files updated).
15. GUT download failure prints actionable error with manual install instructions.
16. GUT already installed with compatible version: no download, no warning.
17. GUT already installed with incompatible version: warning printed.
18. Summary of actions is printed after completion.

## Out of Scope

- **Autoload registration**: `_GDTCoverage` autoload registration in `project.godot` is deferred to Track 11 (Phase 3 — Hooks). The `register_autoload()` function is NOT part of Track 7.
- **Real coverage addon files**: Placeholder stubs only. Real instrumentation (tracker, hooks) will be implemented in Phase 3 (Tracks 9-11).
- **GUT version verification after download**: Not validating the downloaded GUT version matches expectations beyond the version map lookup. Trust the GitHub release tag.
- **Retry logic for network failures**: Fail fast with instructions. No retry/backoff.
- **GUT update/uninstall**: If GUT is installed with an incompatible version, only warn. Do not auto-update or uninstall.
- **Interactive project.godot editing UI**: Direct file manipulation only.
- **Multi-project support**: Init operates on a single project root.
</protect>
