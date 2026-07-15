# User Guide

This guide covers installation, configuration, and the full command reference
for `gd-tools` -- a CLI workflow tool for GDScript development in Godot 4.5+.

For deep technical command surface details, see the [PRD](./PRD.md) section 5.


## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Configuration](#2-configuration)
3. [Command Reference](#3-command-reference)
4. [Examples](#4-examples)
5. [Troubleshooting](#5-troubleshooting)


## 1. Getting Started

### 1.1 Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.10 | Required for modern type hints and tomllib support. |
| Godot Engine | 4.5 | Must be accessible via PATH or a GODOT_BIN environment variable. |
| GUT (Godot Unit Test) | 9.5.0 | Installed automatically by `gd-tools init`. |

The `gdtoolkit` package (providing `gdlint` and `gdformat`) is installed as
a dependency of `gd-tools` -- no separate installation is needed.

### 1.2 Installation

```bash
pip install gd-tools-cli
```

Verify the installation:

```bash
gd-tools --version
```

### 1.3 Initialization Walkthrough

Before running tests or coverage, initialize `gd-tools` in your Godot
project root (the directory containing `project.godot`):

```bash
cd /path/to/your/godot/project
gd-tools init
```

The `init` command performs the following steps:

1. Detects the project root by walking up from the current directory to
   find `project.godot`.
2. Detects the installed Godot version and maps it to the compatible GUT
   release.
3. Downloads and installs GUT into `addons/gut/`.
4. Enables the GUT plugin in `project.godot`.
5. Deploys the `gd-tools-coverage` addon into `addons/gd-tools-coverage/`
   (including a `_version.txt` file for staleness detection).
6. Registers the `_GDTCoverage` autoload in `project.godot`.
7. Creates or updates `.gutconfig.json` with pre- and post-run hook scripts.
8. Creates `gd-tools.toml` with default configuration if absent.
9. Generates `gdlintrc` and `gdformatrc` exclude files.
10. Creates the `.gd-tools/` working directory.

The `init` command is idempotent -- running it again updates components
to the expected state without duplicating files.

After initialization, run `gd-tools doctor` to verify the environment:

```bash
gd-tools doctor
```


### 1.4 Update Notifications

When you run any `gd-tools` command, the CLI silently checks PyPI for a
newer version of `gd-tools-cli`. If an update is available, a message is
printed to **stderr** (it does not interfere with command output or
scripts):

```
A new version of gd-tools is available: 0.2.0 (you have 0.1.0).
Run `pip install --upgrade gd-tools-cli` to update.
```

The check is cached for 24 hours to avoid network delays on every run.
It fails silently on any error (network issues, PyPI downtime) and never
prevents command execution.

To disable the update check entirely, set the `GD_TOOLS_NO_UPDATE_CHECK`
environment variable to `1`:

```bash
export GD_TOOLS_NO_UPDATE_CHECK=1
```

In addition to the PyPI version check, `gd-tools` checks whether the
deployed coverage addon files are up-to-date with the installed package
version. If the addon is outdated (or the version file is missing), a
warning is printed to stderr:

```
WARNING: Coverage addon is outdated (v0.2.0 deployed, v0.3.0 available).
Run `gd-tools init` to update.
```

This check is also suppressed by `GD_TOOLS_NO_UPDATE_CHECK=1`. The
`gd-tools doctor` command reports addon staleness as part of the
Coverage Addon check.


## 2. Configuration

All configuration lives in a single `gd-tools.toml` file in the project
root. This file is created by `gd-tools init` with sensible defaults.

### 2.1 Full Default Configuration

```toml
[godot]
binary = ""

[test]
test_dirs = ["test", "tests"]
prefix = "test_"
suffix = ".gd"
gutconfig = ".gutconfig.json"

[lint]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[format]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[coverage]
enabled = false
min_percent = 0
format = "html"
output_dir = ".gd-tools/coverage"
exclude = ["addons", ".godot", ".gd-tools", ".git"]
test_dirs = ["test", "tests"]
```

### 2.2 Section: [godot]

| Key | Type | Default | Description |
|---|---|---|---|
| `binary` | string or empty | `""` (auto-detect) | Path to the Godot binary. Leave empty to use auto-detection. |

When `binary` is empty, `gd-tools` searches in this order:

1. The `GODOT_BIN` environment variable.
2. The `GODOT4_BIN` environment variable.
3. The `GODOT_PATH` environment variable.
4. The system `PATH` (via `shutil.which`).
5. Common installation locations for the current platform.

If none of these yield a Godot binary, a `GodotNotFoundError` is raised
(exit code 2).

Example -- pinning a specific Godot binary:

```toml
[godot]
binary = "/usr/local/bin/godot"
```

### 2.3 Section: [test]

| Key | Type | Default | Description |
|---|---|---|---|
| `test_dirs` | list of strings | `["test", "tests"]` | Directories scanned for test files. |
| `prefix` | string | `"test_"` | Filename prefix for test scripts (GUT convention). |
| `suffix` | string | `".gd"` | Filename suffix for test scripts. |
| `gutconfig` | string | `".gutconfig.json"` | Path to the GUT configuration file. |

Example -- custom test layout:

```toml
[test]
test_dirs = ["tests/unit", "tests/integration"]
prefix = "test_"
suffix = ".gd"
```

### 2.4 Section: [lint]

| Key | Type | Default | Description |
|---|---|---|---|
| `exclude` | list of strings | `["addons", ".godot", ".gd-tools", ".git"]` | Directories excluded from linting. |

The `exclude` list is written to `gdlintrc` during `init`. Add or remove
entries here and re-run `gd-tools init` to regenerate the rc file.

Example -- excluding a vendored library:

```toml
[lint]
exclude = ["addons", ".godot", ".gd-tools", ".git", "vendor"]
```

### 2.5 Section: [format]

| Key | Type | Default | Description |
|---|---|---|---|
| `exclude` | list of strings | `["addons", ".godot", ".gd-tools", ".git"]` | Directories excluded from formatting. |
| `max_line_length` | integer | `100` | Maximum line length for the formatter. |

The `exclude` list and `max_line_length` are written to `gdformatrc` during `init`.

Example:

```toml
[format]
exclude = ["addons", ".godot", ".gd-tools", ".git", "third_party"]
```

### 2.6 Section: [coverage]

| Key | Type | Default | Valid Values | Description |
|---|---|---|---|---|
| `enabled` | boolean | `false` | `true`, `false` | Whether coverage is active by default. |
| `min_percent` | integer | `0` | 0--100 | Minimum coverage percentage threshold. |
| `format` | string | `"html"` | `html`, `lcov`, `cobertura`, `text` | Report output format. |
| `output_dir` | string | `".gd-tools/coverage"` | Any path | Directory for coverage data and reports. |
| `exclude` | list of strings | `["addons", ".godot", ".gd-tools", ".git"]` | Any list | Directories excluded from coverage measurement. |
| `test_dirs` | list of strings | `["test", "tests"]` | Any list | Directories containing test files (for plan generation). |

Example -- enabling coverage with a threshold:

```toml
[coverage]
enabled = true
min_percent = 80
format = "lcov"
output_dir = ".gd-tools/coverage"
```


## 3. Command Reference

### 3.1 Exit Code Convention

All `gd-tools` commands follow a consistent exit code convention:

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | Tool failure (test failures, lint errors, files need formatting, coverage threshold not met). |
| 2 | Configuration or environment error (missing config, invalid TOML, Godot not found). |

### 3.2 gd-tools init

Initialize or update the `gd-tools` configuration in a Godot project.

**Usage:**

```bash
gd-tools init [--non-interactive]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--non-interactive` | flag | `false` | Run without interactive prompts. |

**Examples:**

```bash
# Interactive initialization (default)
gd-tools init

# Non-interactive (for CI/CD pipelines)
gd-tools init --non-interactive
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Initialization completed successfully. |
| 1 | User declined GUT installation when prompted. |
| 2 | Configuration or environment error (e.g., Godot not found). |

### 3.3 gd-tools doctor

Run diagnostic checks on the development environment.

**Usage:**

```bash
gd-tools doctor
```

**Checks Performed:**

| # | Check | Severity | Description |
|---|---|---|---|
| 1 | Godot Binary | critical | Godot binary is found via the detection chain. |
| 2 | Godot Version | critical | Godot version is >= 4.5.0. |
| 3 | GUT Installed | critical | GUT is present in `addons/gut/`. |
| 4 | GUT Version | warning | Installed GUT version matches the expected version for the detected Godot. |
| 5 | Coverage Addon | warning | All `gd-tools-coverage` addon files are present and not stale. |
| 6 | GUT Config | warning | `.gutconfig.json` exists, is valid JSON, and contains hook script keys. |
| 7 | gd-tools.toml | critical | `gd-tools.toml` exists and is valid TOML. |
| 8 | GD Toolkit | critical | `gdlint` and `gdformat` CLI tools are installed. |
| 9 | Autoload | critical | `_GDTCoverage` autoload is registered in `project.godot`. |

**Output:**

Results are displayed in a color-coded Rich table with columns for Check,
Status, Message, and Fix Hint. Passing checks show a green checkmark,
critical failures show a red X, and warning failures show a yellow warning
symbol.

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | All checks passed. |
| 1 | One or more checks failed. |

### 3.4 gd-tools test

Run GDScript tests using GUT (Godot Unit Test).

**Usage:**

```bash
gd-tools test [PATHS]... [OPTIONS]
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `paths` | no | Config `[test].test_dirs` | One or more directories to scan for test files. Overrides `test_dirs` from config for this invocation only. |

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--coverage` | flag | `false` | Generate a coverage report during the test run. |
| `--min` | integer | None | Minimum coverage percentage threshold. Fails if coverage is below this value. Requires `--coverage`; if passed without it, a warning is printed and the flag is ignored. |
| `--suite` | string | None | Run only the specified test suite. |
| `--test` | string | None | Run only the specified test. |
| `--junit-xml` | string | None | Path to write a JUnit XML report. |
| `--no-exit-code` | flag | `false` | Do not exit with non-zero on test failure. |
| `--timeout` | integer | None | Timeout in seconds for the test run. |

**Examples:**

```bash
# Run all tests (uses config test_dirs)
gd-tools test

# Run tests with coverage
gd-tools test --coverage

# Run tests with coverage and enforce an 80% threshold
gd-tools test --coverage --min 80

# Run a specific test suite
gd-tools test --suite PlayerTests

# Run a specific test and write JUnit XML
gd-tools test --test test_movement --junit-xml report.xml

# Run tests without exit code (useful in CI pre-steps)
gd-tools test --no-exit-code

# Run tests from a specific directory (overrides config test_dirs)
gd-tools test tests/unit

# Run tests from multiple directories
gd-tools test tests/unit tests/integration
```

**Output Format:**

Test results are rendered as a Rich table with columns for Status, Suite,
and Test name. Passing tests show a green ✓; failing tests show a red ✗
with the failure message printed below (indented, including the suite
name and error message). A summary footer line shows pass/fail counts,
and a `[OK]` success message is displayed when all tests pass.

When `--coverage` is used, an inline coverage summary is printed after
the test results showing line and branch coverage rates with color-coded
threshold status (green if meeting threshold, red if below).

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | All tests passed. |
| 1 | One or more tests failed, or coverage threshold not met. |
| 2 | Configuration or environment error. |

### 3.5 gd-tools lint

Lint GDScript files using `gdlint` from the `gdtoolkit` package.

**Usage:**

```bash
gd-tools lint [PATHS]... [OPTIONS]
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `paths` | no | `.` | One or more files or directories to lint. Files are deduplicated across paths. |

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--report-format` | choice | `text` | Output format: `text` or `json`. |
| `--fix` | flag | `false` | Attempt to fix lint issues. Note: `gdlint` is read-only, so this flag prints a warning and has no effect. |

**Examples:**

```bash
# Lint the current directory
gd-tools lint

# Lint a specific file
gd-tools lint src/player.gd

# Lint multiple files or directories
gd-tools lint src/player.gd src/enemy.gd scripts/

# Output JSON for CI integration
gd-tools lint --report-format json

# Lint a specific directory
gd-tools lint src/scripts/
```

**Output Format (text):**

Issues are rendered as flat, line-based output — one issue per line in
`file:line:col: rule: message  [SEVERITY]` format, sorted by file path
then line number. This format is recognized by editors and IDEs for
click-to-navigate (VS Code, JetBrains, Vim/Emacs, GitHub Actions).

```
src/player.gd:10:1: function-name: Function name BadFunctionName is not valid  [ERROR]
src/enemy.gd:5:3: some-rule: Warning message  [WARN]

1 errors, 1 warnings, 2 files checked
```

- Severity tags `[ERROR]` (red) and `[WARN]` (yellow) are colored when
  output goes to a terminal; piped/redirected output is plain text.
- The summary line is colored red (errors present), yellow (warnings
  only), or the `[OK] No lint issues found.` message is green when clean.
- File paths and rule names of any length appear in full — no truncation.
- Use `--report-format json` for stable, machine-readable output.

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | No lint errors found. |
| 1 | One or more lint errors found. |
| 2 | Configuration or environment error. |

### 3.6 gd-tools format

Format GDScript files using `gdformat` from the `gdtoolkit` package.

**Usage:**

```bash
gd-tools format [PATHS]... [OPTIONS]
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `paths` | no | `.` | One or more files or directories to format. Files are deduplicated across paths. |

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--check` | flag | `false` | Check formatting without modifying files. |
| `--diff` | flag | `false` | Show a diff of changes that would be applied. |

The `--check` and `--diff` flags are mutually exclusive. Using both
together results in an error with exit code 2.

**Examples:**

```bash
# Format all .gd files in the current directory
gd-tools format

# Check if files need formatting (exit 1 if any do)
gd-tools format --check

# Show diffs of formatting changes
gd-tools format --diff

# Format a specific file
gd-tools format src/player.gd

# Format multiple files or directories
gd-tools format src/player.gd src/enemy.gd scripts/
```

**Output Format:**

In `--check` mode, files needing formatting are listed with their paths
rendered in dim text. When all files are already formatted, a green
`[OK]` success message is displayed.

In `--diff` mode, each file's diff is shown with the file path in dim
text preceding the diff output.

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | All files are correctly formatted (with `--check`), or formatting completed successfully. |
| 1 | One or more files need formatting (with `--check`). |
| 2 | Configuration or environment error, or `--check` and `--diff` used together. |

### 3.7 gd-tools coverage

Coverage reporting commands. This group provides subcommands for
generating reports, merging coverage data, and viewing summaries.

#### 3.7.1 coverage report

Generate a coverage report from existing coverage data.

**Usage:**

```bash
gd-tools coverage report [OPTIONS]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--format` | string | Config `[coverage].format` | Output format for the report (e.g., `html`, `lcov`, `cobertura`, `text`). |
| `--output-dir` | string | Config `[coverage].output_dir` | Directory to write the report to. |

**Examples:**

```bash
# Generate an HTML report (uses config default)
gd-tools coverage report

# Generate an LCOV report
gd-tools coverage report --format lcov

# Write report to a custom directory
gd-tools coverage report --format html --output-dir reports/coverage
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Report generated successfully. |
| 2 | Configuration or environment error, or no coverage data found. |

#### 3.7.2 coverage merge

Merge multiple coverage data files into one.

**Usage:**

```bash
gd-tools coverage merge FILES... [OPTIONS]
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `files` | yes (one or more) | -- | Coverage data files to merge. |

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--output` | string | Config `[coverage].output_dir` merged path | Path for the merged output file. |

**Examples:**

```bash
# Merge two coverage files
gd-tools coverage merge .gd-tools/coverage/run1.json .gd-tools/coverage/run2.json

# Merge with a custom output path
gd-tools coverage merge run1.json run2.json run3.json --output merged.json
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Merge completed successfully. |
| 2 | Configuration or environment error. |

#### 3.7.3 coverage show

Display a coverage summary in the terminal.

**Usage:**

```bash
gd-tools coverage show [OPTIONS]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--min` | integer | Config `[coverage].min_percent` | Minimum coverage threshold. Exits with code 1 if coverage is below this value. |

**Examples:**

```bash
# Show coverage summary
gd-tools coverage show

# Enforce a 80% minimum threshold
gd-tools coverage show --min 80
```

**Output Format:**

Coverage is displayed as a Rich table with per-file line and branch
coverage rates. Rate cells are color-coded: green when at or above the
threshold, red when below. A summary footer shows the overall coverage
and threshold status (green if meeting threshold, red if below).

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Coverage summary displayed and meets threshold. |
| 1 | Coverage is below the specified threshold. |
| 2 | Configuration or environment error, or no coverage data found. |

### 3.8 gd-tools version

Display the versions of all gd-tools components.

**Usage:**

```bash
gd-tools version [OPTIONS]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--json` | flag | `false` | Output versions as a JSON object instead of a table. |

**Components Detected:**

| Component | Source |
|---|---|
| gd-tools | The installed `gd-tools-cli` package version. |
| Godot | The detected Godot engine binary version. |
| GUT | The installed GUT (Godot Unit Test) addon version. |
| gdtoolkit | The installed `gdtoolkit` package version (provides `gdlint` and `gdformat`). |
| Python | The running Python interpreter version. |

When a component is not found, the table displays "not detected" for
Godot and "not installed" for GUT and gdtoolkit. In JSON output, missing
components are `null`.

**Examples:**

```bash
# Display versions in a table
gd-tools version

# Output as JSON (for scripting)
gd-tools version --json
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Always -- version detection never fails. |


### 3.9 gd-tools config

Manage and validate your `gd-tools.toml` configuration.

#### 3.9.1 gd-tools config show

Display the resolved configuration (including defaults applied).

**Usage:**

```bash
gd-tools config show [OPTIONS]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--format` | choice (`toml`) | `none` | Output as TOML instead of a Rich table. |
| `--json` | flag | `false` | Output as a JSON object instead of a Rich table. |

`--format` and `--json` are mutually exclusive. Using both exits with code 2.

**Output Formats:**

- **Rich table** (default) — Three columns (Section, Key, Value), one row per
  setting across all 5 sections (godot, test, lint, format, coverage).
- **TOML** (`--format toml`) — Valid TOML output using `tomli_w`, with `None`
  values stripped.
- **JSON** (`--json`) — JSON object with `indent=2`, suitable for scripting.

Works with no config file — shows all defaults.

**Examples:**

```bash
# Show resolved config as a Rich table
gd-tools config show

# Output as TOML
gd-tools config show --format toml

# Output as JSON (for scripting)
gd-tools config show --json
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Configuration displayed successfully. |
| 2 | Config file is invalid (parse error or Pydantic validation failure), or `--format` and `--json` were both specified. |

#### 3.9.2 gd-tools config validate

Check your `gd-tools.toml` for schema validity, deprecated settings, and
non-existent paths — without running a command that uses the config.

**Usage:**

```bash
gd-tools config validate
```

**Validation Checks:**

| Check | Symbol | Severity |
|---|---|---|
| Schema errors (unknown keys, type mismatches, constraint violations) | ✗ | Fatal (exit 1) |
| Deprecated settings | ✗ | Fatal (exit 1) |
| Path warnings (non-existent directories/files referenced in config) | ! | Advisory (non-fatal) |

When a schema error is an unknown key, a "did you mean" suggestion is shown
with the valid field names for that section.

**Summary Output:**

The summary includes:
- The config file path being validated
- Sections validated: 5 (godot, test, lint, format, coverage)
- Count of schema errors, deprecated settings, and path warnings
- "✓ Configuration is valid." on success

**Examples:**

```bash
# Validate config in current project
gd-tools config validate

# Use in CI to catch config issues early
gd-tools config validate || exit 1
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Configuration is valid (path warnings may be present but are non-fatal). |
| 1 | Schema errors or deprecated settings found. |
| 2 | Config file could not be read or parsed. |


## 4. Examples

### 4.1 First Test Run

After installing `gd-tools` and navigating to your Godot project:

```bash
# 1. Initialize gd-tools
gd-tools init

# 2. Verify the environment
gd-tools doctor

# 3. Run tests
gd-tools test

# 4. Run tests with coverage
gd-tools test --coverage
```

Coverage reports are written to `.gd-tools/coverage/` in the format
specified by `[coverage].format` in `gd-tools.toml` (HTML by default).

### 4.2 CI/CD Pipeline Setup

A typical GitHub Actions workflow using `gd-tools`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Download Godot
        run: |
          wget -q https://github.com/godotengine/godot/releases/download/4.5-stable/Godot_v4.5-stable_linux.x86_64 -O godot
          chmod +x godot
          sudo mv godot /usr/local/bin/

      - name: Install gd-tools
        run: pip install gd-tools-cli

      - name: Initialize
        run: gd-tools init --non-interactive

      - name: Run tests with coverage
        run: gd-tools test --coverage --min 80 --junit-xml report.xml

      - name: Lint
        run: gd-tools lint --report-format json

      - name: Format check
        run: gd-tools format --check
```

### 4.3 Coverage Threshold Enforcement

To enforce a minimum coverage percentage in CI:

```bash
# Fail the build if coverage is below 80%
gd-tools test --coverage --min 80
```

A coverage summary table (Lines/Branches: Found/Hit/Rate) is printed
to stdout in all cases --- on success, and before the threshold error
when below the minimum.

You can also check coverage independently after a test run:

```bash
# Run tests first
gd-tools test --coverage

# Then check the threshold
gd-tools coverage show --min 80
```

### 4.4 Lint and Format in CI

For CI pipelines, use the check modes that exit non-zero without
modifying files:

```bash
# Lint -- exits 1 if errors found
gd-tools lint

# Format check -- exits 1 if any file needs formatting
gd-tools format --check
```

To auto-format locally before committing:

```bash
# Format all .gd files
gd-tools format

# Verify everything passes
gd-tools format --check
```


## 5. Troubleshooting

### 5.1 Godot Not Found

**Symptom:** `Error: Godot binary not found` (exit code 2).

**Cause:** `gd-tools` cannot locate a Godot binary through the detection
chain.

**Resolution:**

1. Verify Godot is installed: run `godot --version` in a terminal.
2. Set the `GODOT_BIN` environment variable:
   ```bash
   # Linux/macOS
   export GODOT_BIN=/path/to/godot

   # Windows (PowerShell)
   $env:GODOT_BIN = "C:\path\to\godot.exe"
   ```
3. Alternatively, set the binary path in `gd-tools.toml`:
   ```toml
   [godot]
   binary = "/path/to/godot"
   ```
4. Re-run `gd-tools doctor` to confirm detection.

### 5.2 GUT Not Installed

**Symptom:** `Error: GUT is not installed` or doctor check "GUT
Installed" fails.

**Cause:** The GUT addon is not present in `addons/gut/`.

**Resolution:**

```bash
gd-tools init
```

The `init` command downloads and installs the correct GUT version for the
detected Godot version. If the download fails (network issues), you can
manually install GUT from [the GUT GitHub
repository](https://github.com/bitwes/Gut).

### 5.3 Godot or GUT Version Mismatch

**Symptom:** Doctor check "Godot Version" or "GUT Version" fails.

**Cause:** The installed Godot version is below 4.5.0, or the GUT version
does not match the expected version for the detected Godot.

**Resolution:**

The GUT version mapping is:

| Godot Version | Expected GUT Version |
|---|---|
| 4.5 | 9.5.0 |
| 4.6 | 9.6.0 |
| 4.7 | 9.7.0 |

1. Verify your Godot version: `godot --version`.
2. If below 4.5.0, upgrade Godot from
   [godotengine.org](https://godotengine.org).
3. Re-run `gd-tools init` to install the correct GUT version.

### 5.4 Coverage Not Generating

**Symptom:** `gd-tools test --coverage` runs tests but no coverage
report appears in `.gd-tools/coverage/`.

**Cause:** The coverage addon is not installed, the autoload is not
registered, or the coverage environment variables are not set.

**Resolution:**

1. Run `gd-tools doctor` and verify these checks pass:
   - Coverage Addon
   - Autoload
   - GUT Config (must contain `pre_run_script` and `post_run_script` keys)
2. If any check fails, run `gd-tools init` to reinstall the coverage
   components.
3. Verify `.gutconfig.json` contains the hook script paths:
   ```json
   {
     "pre_run_script": "addons/gd-tools-coverage/pre_run_hook.gd",
     "post_run_script": "addons/gd-tools-coverage/post_run_hook.gd"
   }
   ```
4. Ensure the `_GDTCoverage` autoload is registered in `project.godot`:
   ```ini
   [autoload]

   _GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"
   ```
5. Re-run the coverage test:
   ```bash
   gd-tools test --coverage
   ```
