---
name: gd-tools
description: |
  Use this skill when working with gd-tools, a CLI for GDScript/Godot 4.5+ development
  workflows. Activate whenever the user mentions gd-tools, wants to run GDScript tests,
  lint GDScript, format GDScript, check code coverage for Godot projects, initialize a
  Godot project for testing, or diagnose environment issues. Also trigger on any mention
  of GUT (Godot Unit Test), gd-tools.toml, GDScript linting, GDScript formatting, or
  Godot coverage reports. This skill ensures correct command usage, flag combinations,
  and exit code interpretation. When in doubt about which gd-tools command or flag to use,
  consult this skill before guessing.
---

# gd-tools Agent Skill

## What is gd-tools?

gd-tools is a Python CLI tool (`pip install gd-tools-cli`) that provides a modern
development workflow for GDScript projects targeting Godot 4.5+. It wraps GUT
(Godot Unit Test) for test execution, gdtoolkit for linting/formatting, and implements
a custom hybrid coverage architecture (Python plan generation + GDScript runtime
instrumentation).

## Quick Reference

### Commands

| Command | Purpose |
|---------|---------|
| `gd-tools init` | Initialize project: install GUT, deploy coverage addon, generate config |
| `gd-tools doctor` | Diagnose environment (Godot, GUT, gdtoolkit, config) |
| `gd-tools test` | Run GDScript tests via GUT |
| `gd-tools lint` | Lint GDScript files (wraps gdlint) |
| `gd-tools format` | Format GDScript files (wraps gdformat) |
| `gd-tools coverage report` | Generate coverage report from test data |
| `gd-tools coverage merge` | Merge multiple coverage data files |
| `gd-tools coverage show` | Display coverage summary with threshold check |

### Exit Code Convention

- **0** — Success
- **1** — Tool failure (tests failed, lint errors, coverage below threshold, format needed)
- **2** — Configuration/environment error (missing Godot, bad config, missing GUT)

## Command Reference

### `gd-tools init`

Initialize a new gd-tools project configuration.

**Flags:**
- `--non-interactive` — Run without interactive prompts (use defaults)

**Exit codes:**
- `0` — Success
- `2` — Configuration error (GdToolsError)

**What it does:**
- Detects Godot version
- Downloads and installs the correct GUT version (mapped to Godot version)
- Deploys the coverage addon to `addons/gd-tools-coverage/`
- Generates `gd-tools.toml`, `.gutconfig.json`, `gdlintrc`, `gdformatrc`
- Registers `_GDTCoverage` autoload in `project.godot`

### `gd-tools doctor`

Check the environment for required tools and configuration.

**Exit codes:**
- `0` — All checks passed
- `1` — One or more checks failed

**Checks performed (9 total):**
1. Godot Binary — found via detection chain
2. Godot Version — >= 4.5.0
3. GUT Installed — `addons/gut/gut.gd` exists
4. GUT Version — matches expected version for Godot
5. Coverage Addon — `addons/gd-tools-coverage/` files present
6. GUT Config — `.gutconfig.json` valid with hook scripts
7. gd-tools.toml — exists and is valid TOML
8. GD Toolkit — `gdlint` and `gdformat` available
9. Autoload — `_GDTCoverage` registered in `project.godot`

### `gd-tools test`

Run GDScript tests using GUT.

**Flags:**
- `--coverage` — Generate coverage report during test run
- `--min <int>` — Minimum coverage threshold percentage
- `--suite <name>` — Specify which test suite to run
- `--test <name>` — Specify which test to run
- `--junit-xml <path>` — Path to write JUnit XML report
- `--no-exit-code` — Don't exit with non-zero on test failure
- `--timeout <int>` — Timeout in seconds for the test run

**Exit codes:**
- `0` — All tests passed
- `1` — Test failure (TestFailureError)
- `2` — Configuration error (ConfigError)

### `gd-tools lint`

Lint GDScript files using gdlint.

**Arguments:**
- `path` (optional, default: `.`) — Path to lint

**Flags:**
- `--report-format {text,json}` — Output format (default: text)
- `--fix` — Attempt to fix lint issues (no-op for gdlint; prints warning)

**Exit codes:**
- `0` — No lint errors
- `1` — Lint errors found
- `2` — Configuration error (ConfigError)

### `gd-tools format`

Format GDScript files using gdformat.

**Arguments:**
- `path` (optional, default: `.`) — Path to format

**Flags:**
- `--check` — Check only, don't modify files
- `--diff` — Show diff of changes

**Exit codes:**
- `0` — Files formatted (or already formatted)
- `1` — Files need formatting (with `--check`)
- `2` — Configuration error, or `--check` and `--diff` used together

### `gd-tools coverage report`

Generate a coverage report from existing coverage data.

**Flags:**
- `--format <format>` — Output format (html, lcov, cobertura, text)
- `--output-dir <dir>` — Directory to write the report to

**Exit codes:**
- `0` — Success
- `2` — Configuration error (GdToolsError)

### `gd-tools coverage merge`

Merge multiple coverage data files.

**Arguments:**
- `files` (required, variadic) — Coverage files to merge

**Flags:**
- `--output <path>` — Path for the merged output file

**Exit codes:**
- `0` — Success
- `2` — Configuration error (GdToolsError)

### `gd-tools coverage show`

Display coverage summary with optional threshold check.

**Flags:**
- `--min <int>` — Minimum coverage threshold percentage

**Exit codes:**
- `0` — Coverage at or above threshold
- `1` — Coverage below threshold (CoverageThresholdError)
- `2` — Configuration error (ConfigError)

## Configuration

Configuration is stored in `gd-tools.toml` at the project root (where `project.godot`
lives). If missing, defaults are used. The file is validated by Pydantic v2 with
`extra='forbid'` — unknown keys cause errors.

### `[godot]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `binary` | string \| null | `null` | Path to Godot binary. If null, auto-detection is used. |

### `[test]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `test_dirs` | list[string] | `["test", "tests"]` | Directories containing test files |
| `prefix` | string | `"test_"` | Test file prefix (GUT convention) |
| `suffix` | string | `".gd"` | Test file suffix |
| `gutconfig` | string | `".gutconfig.json"` | Path to GUT config file |

### `[lint]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `exclude` | list[string] | `["addons", ".godot", ".gd-tools", ".git"]` | Directories excluded from linting |

### `[format]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `exclude` | list[string] | `["addons", ".godot", ".gd-tools", ".git"]` | Directories excluded from formatting |

### `[coverage]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `false` | Whether coverage is enabled |
| `min_percent` | int | `0` | Minimum coverage threshold (0-100) |
| `format` | string | `"html"` | Report format: html, lcov, cobertura, text |
| `output_dir` | string | `".gd-tools/coverage"` | Directory for coverage data and reports |
| `exclude` | list[string] | `["addons", ".godot", ".gd-tools", ".git"]` | Directories excluded from coverage |
| `test_dirs` | list[string] | `["test", "tests"]` | Directories containing test files |

### Example `gd-tools.toml`

```toml
[godot]
binary = "/usr/local/bin/godot"

[test]
test_dirs = ["test"]
prefix = "test_"
suffix = ".gd"

[lint]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[format]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[coverage]
enabled = true
min_percent = 80
format = "html"
output_dir = ".gd-tools/coverage"
```

## Godot Binary Detection

gd-tools resolves the Godot binary using a 5-level priority chain (first match wins):

1. **Config:** `[godot].binary` in `gd-tools.toml`
2. **Environment variables:** `GODOT_BIN` -> `GODOT4_BIN` -> `GODOT_PATH`
3. **PATH:** `shutil.which("godot")` then `shutil.which("godot4")`
4. **Common install locations** (platform-specific):
   - Windows: `C:\Program Files\Godot\godot.exe`, `%LOCALAPPDATA%\Godot\godot.exe`
   - macOS: `/Applications/Godot.app/Contents/MacOS/Godot`, `/opt/homebrew/bin/godot`
   - Linux: `~/.local/bin/godot`, `/usr/bin/godot`, `/usr/local/bin/godot`
5. **Raise error** — `GodotNotFoundError` (exit code 2)

To configure manually, set `GODOT_BIN` or add `[godot].binary` to `gd-tools.toml`.

## CI Mode & Non-Interactive Usage

- Use `--non-interactive` with `gd-tools init` for automated/CI environments
- Set `CI=true` environment variable for watch-mode tools (tests, linters) to ensure
  single execution rather than watch mode
- In CI pipelines, use `--report-format json` for machine-readable lint output

## Common Workflows

### Bootstrap Workflow

Set up a new Godot project for gd-tools:

```bash
# 1. Install gd-tools
pip install gd-tools-cli

# 2. Initialize project (installs GUT, coverage addon, generates config)
gd-tools init

# 3. Run tests
gd-tools test

# 4. Run tests with coverage and minimum threshold
gd-tools test --coverage --min 80
```

### Pre-Commit Workflow

Before committing GDScript changes:

```bash
# 1. Lint
gd-tools lint

# 2. Check formatting (don't modify, just check)
gd-tools format --check

# 3. If format check fails, format the files
gd-tools format

# 4. Commit (only if lint and format pass)
git add .
git commit -m "feat(player): Add jump mechanic"
```

### CI Workflow

For GitHub Actions or other CI systems:

```bash
# 1. Lint with JSON output for parsing
gd-tools lint --report-format json

# 2. Check formatting
gd-tools format --check

# 3. Run tests with JUnit XML output
gd-tools test --junit-xml report.xml

# 4. Run tests with coverage and minimum threshold
gd-tools test --coverage --min 80
```

### Diagnosis Workflow

When something isn't working:

```bash
# 1. Check environment
gd-tools doctor

# 2. If Godot not found, set the binary path
#    Option A: Environment variable
export GODOT_BIN=/path/to/godot
#    Option B: Config file
#    Add to gd-tools.toml: [godot]
#                          binary = "/path/to/godot"

# 3. Re-run doctor to verify
gd-tools doctor

# 4. Re-initialize if needed
gd-tools init
```

## Error Handling

All gd-tools errors inherit from `GdToolsError` and carry an `exit_code`:

| Error | Exit Code | Meaning |
|-------|-----------|---------|
| `ConfigError` | 2 | Invalid or missing configuration |
| `GodotNotFoundError` | 2 | Godot binary not found |
| `GUTNotInstalledError` | 2 | GUT not installed in project |
| `TestFailureError` | 1 | Tests failed |
| `LintError` | 1 | Lint issues found |
| `FormatError` | 1 | Formatting issues found |
| `CoverageThresholdError` | 1 | Coverage below threshold |
| `CoveragePlanError` | 2 | Error generating coverage plan |

## GUT Version Mapping

GUT versions are mapped to Godot versions:

| Godot Version | GUT Version |
|---------------|-------------|
| 4.5 | 9.5.0 |
| 4.6 | 9.6.0 |
| 4.7 | 9.7.0 |

## Further Reading

For edge cases and deep configuration details, refer to the project documentation:

- [User Guide](../../docs/USER_GUIDE.md) — Detailed usage instructions
- [Architecture](../../docs/ARCHITECTURE.md) — Coverage architecture deep dive
- [PRD](../../docs/PRD.md) — Product requirements and design decisions
- [Contributing](../../docs/CONTRIBUTING.md) — Development setup and guidelines
