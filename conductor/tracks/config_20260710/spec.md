<protect>
# Track 2: Configuration System

## Overview

Implement the configuration system for gd-tools, providing typed loading, validation, and default resolution of `gd-tools.toml` configuration files. This module is the foundation that all subsequent tracks depend on — the `GdToolsConfig` object will be passed to every other module (test, lint, format, coverage).

## Functional Requirements

### FR-1: Pydantic Configuration Models

Define Pydantic v2 models for all config sections per TDD §3.2:

- `[godot]` — `GodotConfig`: `binary` (optional, auto-detected if omitted)
- `[test]` — `TestConfig`: `test_dirs`, `prefix`, `suffix`, `gutconfig`
- `[lint]` — `LintConfig`: `exclude`
- `[format]` — `FormatConfig`: `exclude`
- `[coverage]` — `CoverageConfig`: `enabled`, `min_percent`, `format`, `output_dir`, `exclude`, `test_dirs`
- `GdToolsConfig` — root model containing all sections, with a `field_validator` on `coverage` that validates `format` ∈ {html, lcov, cobertura, text} and `min_percent` ∈ [0, 100]

All models use `extra='forbid'` to reject unknown keys (catches typos like `[covrage]`).

### FR-2: Config File Discovery (`find_project_root`)

- Walk up from CWD (or a given start path) to find the nearest `project.godot` file
- The directory containing `project.godot` is the project root
- If `project.godot` is not found → raise `ConfigError` with a clear message
- Look for `gd-tools.toml` in the project root directory
- If `gd-tools.toml` is not found → return `GdToolsConfig()` with all defaults (no error)

### FR-3: TOML Loading (`load_config`)

- Use `tomllib` on Python 3.11+, `tomli` backport for Python 3.10
- Parse TOML → validate with Pydantic → return typed `GdToolsConfig`
- Invalid TOML syntax → raise `ConfigError` with file path and parse error details
- Invalid values (e.g., negative `min_percent`, invalid `format`) → raise `ConfigError` with field name and constraint

### FR-4: Default Values

- `DEFAULT_EXCLUDES = ["addons", ".godot", ".gd-tools", ".git"]`
- All sections have defaults per PRD §6 (see model definitions in TDD §3.2)
- Missing sections in TOML → use code defaults
- Missing config file entirely → all defaults

### FR-5: Exclude List Behavior

- If `exclude` key is present in TOML → use the TOML value (replaces `DEFAULT_EXCLUDES`)
- If `exclude` key is absent in TOML → use `DEFAULT_EXCLUDES` from code
- `gd-tools init` (Track 3) will write the full default exclude list to the generated TOML so users see them and can modify explicitly

### FR-6: Config Serialization (`save_config`)

- Write `gd-tools.toml` from a `GdToolsConfig` object
- Used by the `gd-tools init` command (Track 3)
- Produces valid TOML that round-trips through `load_config()`
- Requires a TOML writer: add `tomli_w` as a dependency (write companion to `tomli`/`tomllib`)

### FR-7: gdlintrc / gdformatrc Generation

- `generate_gdlintrc(config, project_root)`: Generate a `gdlintrc` file in the project root from the `[lint]` exclude list
- `generate_gdformatrc(config, project_root)`: Generate a `gdformatrc` file in the project root from the `[format]` exclude list
- Both overwrite existing files if present

### FR-8: CLI Flag Override Support

- The `GdToolsConfig` object is mutable — fields can be updated after loading
- CLI flags override config file values at the command level (e.g., `--min 90` sets `config.coverage.min_percent = 90`)
- Actual CLI override wiring happens in Track 3+ when commands are implemented
- Track 2 ensures the config object supports this pattern

## Non-Functional Requirements

### NFR-1: Dependency Management

- Add `pydantic >= 2.0` to `pyproject.toml` dependencies
- Add `tomli_w` to `pyproject.toml` dependencies
- Update `conductor/tech-stack.md` to document the pydantic and tomli_w additions

### NFR-2: Error Messages

- All config errors include the file path when available
- TOML parse errors include line number where available
- Validation errors clearly state which field and what constraint was violated

### NFR-3: Code Quality

- Type hints on all public functions
- Docstrings on all public functions
- Follow existing code style (ruff, black, line-length=80)

## Acceptance Criteria

1. Loading a valid `gd-tools.toml` returns a typed `GdToolsConfig` object with all fields correctly parsed
2. Missing config file falls back to defaults (no error raised)
3. Invalid TOML syntax produces a `ConfigError` with file path and error details
4. Invalid values (e.g., `min_percent = -5`, `format = "xml"`) produce `ConfigError` with a clear message
5. Unknown TOML keys (e.g., `[unkown_section]` or `unknown_key = 1`) produce `ConfigError` (extra='forbid')
6. `find_project_root()` walks up from CWD to nearest `project.godot`, raises `ConfigError` if not found
7. Exclude lists: if key present in TOML → use TOML value; if absent → use `DEFAULT_EXCLUDES`
8. `save_config()` writes valid TOML that round-trips through `load_config()`
9. `generate_gdlintrc()` and `generate_gdformatrc()` produce valid config files in the project root
10. The `GdToolsConfig` object is mutable and supports field-level updates for CLI flag overrides

## Out of Scope

- `gd-tools init` command implementation (Track 3)
- CLI flag override wiring in command callbacks (Track 3+)
- Godot binary auto-detection chain (Track 4)
- GUT configuration file (`.gutconfig.json`) generation
- Coverage instrumentation logic
</protect>
