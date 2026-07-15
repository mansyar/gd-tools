# Track 25: Config Show/Validate

## Overview

Add `gd-tools config show` and `gd-tools config validate` subcommands to give users visibility into their resolved configuration and upfront validation feedback before running commands. Currently, users must manually open `gd-tools.toml` to see what's configured, and there's no way to validate config without running a command that uses it.

**Phase:** 6 — Quick Wins  
**Type:** Feature  
**Effort:** 0.5 day  
**Risk:** LOW  
**Dependencies:** Track 2 (config system)  
**Modules:** `src/gd_tools/cli.py`, `src/gd_tools/config.py`  

## Functional Requirements

### FR-1: `config` Command Group

- A new `config` command group is added to `cli.py` under the root `gd-tools` CLI.
- Contains two subcommands: `show` and `validate`.

### FR-2: `gd-tools config show`

- Prints the **resolved** configuration (defaults applied, not just what's in the file) to stdout.
- **Default output format:** Rich table — section/key/value rows, consistent with `gd-tools doctor` and `gd-tools version` styling.
- **`--format toml` flag:** Prints the resolved config as valid TOML text (using `tomli_w`). Useful for copy-pasting into `gd-tools.toml`.
- **`--json` flag:** Prints the resolved config as valid JSON (using `model_dump()` + `json.dumps()`). Machine-readable for scripts and CI.
- **`--format` and `--json` are mutually exclusive:** If both are provided, print an error to stderr and exit 2.
- Works with no config file present (shows all defaults).
- Exit code 0 on success, 2 on config load error (invalid TOML or Pydantic validation failure).

### FR-3: `gd-tools config validate`

- Validates the configuration and reports all findings.

#### FR-3.1: Schema Validation
- Attempts to load the config via `load_config()`. If loading fails (TOML parse error or Pydantic `ValidationError`):
  - Catches `ConfigError` and prints a clear, user-friendly error message identifying the problem.
  - Reports unknown keys with a friendlier message than Pydantic's raw `extra='forbid'` output (e.g., "Unknown key 'tset' in [test] — did you mean 'test'?" — simple suggestion, not full fuzzy matching).
  - Exit code 1.

#### FR-3.2: Path Validation
- After successful schema validation, checks all path-like config fields for existence:
  - `test.test_dirs`: Warn for each directory that does not exist on disk.
  - `godot.binary`: Warn if a custom binary path is set (not None) but the file doesn't exist. Skip if None (auto-detect).
  - `coverage.output_dir`: Warn if the **parent** directory of `output_dir` doesn't exist (the dir itself may not exist yet — it gets created on first coverage run).
  - `lint.exclude`, `format.exclude`, `coverage.exclude`: Warn for each excluded directory that doesn't exist (could indicate a typo or stale config).
- Path warnings are non-fatal — the config is still structurally valid.
- Paths are resolved relative to the project root (where `project.godot` lives).

#### FR-3.3: Deprecated Settings Check
- A deprecation registry is implemented in `config.py`:
  - A module-level dict `_DEPRECATED_FIELDS` mapping field paths (e.g., `[coverage].min_percent`) to a `DeprecatedField` dataclass containing: `field_path`, `since_version`, `replacement` (or None), `migration_message`.
  - Currently empty — no fields are deprecated yet.
- `validate` reads the **raw TOML data** (before Pydantic validation) and checks for any deprecated keys present.
- If a deprecated key is found, prints a warning with the migration message and replacement field.
- This check runs even if Pydantic validation fails, so users see deprecation warnings alongside schema errors.

#### FR-3.4: Output
- **On success (no issues found):** Prints a summary including:
  - Config file path (or "using defaults — no gd-tools.toml found" if no file).
  - Number of sections validated (5: godot, test, lint, format, coverage).
  - Confirmation: "✓ Configuration is valid" (or "✓ Configuration is valid (using defaults)").
- **On issues found:** Prints all warnings/errors grouped by type (schema errors, path warnings, deprecation warnings), then a summary count.
- Exit code 0 on valid config (no errors; path warnings are non-fatal). Exit code 1 if schema validation fails or deprecated settings are present.

## Non-Functional Requirements

### NFR-1: Performance
- Both commands complete in <1 second (no network calls, no Godot binary detection, no subprocess invocations).

### NFR-2: Consistency
- Output styling (Rich table, colors, error format) matches existing gd-tools conventions (`doctor`, `version`, `lint`).
- Error messages follow the project's pattern: actionable, with fix hints where possible.

### NFR-3: Non-Interactive
- Both commands are fully non-interactive (no prompts). Suitable for CI use.

## Acceptance Criteria

1. `gd-tools config show` prints resolved config as a Rich table with all defaults applied.
2. `gd-tools config show --format toml` prints valid TOML output.
3. `gd-tools config show --json` produces valid JSON output.
4. `gd-tools config show` works with no config file (shows all defaults).
5. `--format` and `--json` together produce an error (exit code 2).
6. `gd-tools config validate` exits 0 on valid config with a summary message.
7. `gd-tools config validate` exits 1 on schema validation failure (invalid TOML, unknown keys, Pydantic errors).
8. `gd-tools config validate` detects and reports nonexistent paths in `test.test_dirs`.
9. `gd-tools config validate` detects and reports a missing `godot.binary` path (when set).
10. `gd-tools config validate` detects and reports nonexistent `coverage.output_dir` parent directory.
11. `gd-tools config validate` detects and reports nonexistent directories in `exclude` lists.
12. `gd-tools config validate` reports deprecated settings with migration messages (verifiable with a test fixture).
13. Path warnings are non-fatal (exit code 0 if schema is valid, even with path warnings).
14. Deprecation warnings are fatal (exit code 1 if deprecated settings are present).
15. Config file path is shown in validate output.
16. Unit tests cover: show (table, toml, json, no-config), validate (valid, schema-error, path-warnings, deprecated-settings), mutual exclusion error.

## Out of Scope

- Auto-fixing or migrating deprecated settings (read-only validation only).
- Fuzzy matching / typo suggestions for unknown keys beyond simple hardcoded lookups.
- Config file creation or editing (use `gd-tools init` for that).
- Validation of GUT-specific config files (`.gutconfig.json`).
- Validation of `gdlintrc` / `gdformat` config files generated by `gd-tools init`.
- Deprecation of any actual config fields (registry is empty; this is future-proofing infrastructure).
