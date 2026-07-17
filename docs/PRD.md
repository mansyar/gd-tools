# PRD: gd-tools — GDScript Development Toolkit

**Version:** 0.1.0 (draft)
**Date:** 2026-07-08
**Status:** Post-v1.0 — Shell Completion delivered (Track 26)
**Target Godot Version:** 4.5+

---

## 1. Overview

`gd-tools` is a Python CLI that brings a modern development workflow to GDScript
projects in Godot 4.5+. It wraps mature, community-trusted tools for unit
testing, linting, and formatting, and fills the one remaining gap — **code
coverage** — with a custom hybrid instrumentation system.

The tool is designed to feel familiar to developers coming from JavaScript
(Jest), Python (pytest + coverage.py), or Go (`go test -cover`), while
respecting the realities of the Godot/GDScript ecosystem.

### Design Philosophy

- **Wrap, don't reinvent.** GUT, gdlint, and gdformat are battle-tested. We
  orchestrate them; we do not replace them.
- **Build only what's missing.** No production-quality GDScript line/branch
  coverage tool exists for Godot 4. This is the unique value of `gd-tools`.
- **Convention over configuration.** Sensible defaults out of the box; config
  for when conventions don't fit.
- **Single source of truth.** One `gd-tools.toml` config drives all tools.
  `gd-tools init` generates per-tool config files (`.gutconfig.json`,
  `gdlintrc`, `gdformatrc`) from it, so individual tools still work standalone.

---

## 2. Goals & Non-Goals

### Goals

1. **Unified CLI** for test, lint, format, and coverage — one install, one
   config, one mental model.
2. **Zero-friction bootstrap** — `gd-tools init` gets a project fully set up in
   under a minute (GUT installed, coverage addon deployed, configs generated).
3. **Production-quality coverage** — line and branch coverage for GDScript,
   with HTML and LCOV/Cobertura reports that integrate with CI and code
   review tools.
4. **CI/CD friendly** — exit codes, `--check` flags, `--quiet` for minimal
   CI output, machine-readable output, no interactive prompts when run
   non-interactively.
5. **Standalone tool compatibility** — gdlint, gdformat, and GUT continue to
   work if invoked directly. `gd-tools` is a layer on top, not a lock-in.

### Non-Goals

1. **Not a test framework.** We use GUT. We do not write our own test runner.
2. **Not a linter/formatter engine.** We use gdtoolkit. We do not implement
   our own static analysis or code formatting rules.
3. **Not a Godot plugin manager.** We bootstrap GUT and our own coverage addon.
   We do not manage arbitrary addons.
4. **No C# support.** GDScript only. C# projects should use coverlet + GoDotTest.
5. **No Godot < 4.5 support.** The coverage instrumentation relies on Godot 4.x
   Script APIs. Older versions are out of scope.
6. **No IDE/editor integration in v1.** CLI only. Editor plugins are a future
   possibility.

---

## 3. Target Users

- **GDScript developers** on Godot 4.5+ who want professional tooling parity
  with other languages.
- **Teams** needing CI/CD pipelines with test results, lint gates, and coverage
  thresholds.
- **Open-source Godot project maintainers** who want contributor-friendly
  setup (`gd-tools init` + `gd-tools doctor`).

---

## 4. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    gd-tools CLI (Python)                 │
│                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────────┐  │
│  │  test   │  │  lint   │  │ format  │  │  coverage  │  │
│  │ (GUT    │  │(gdlint  │  │(gdformat│  │ (custom    │  │
│  │ wrapper)│  │ wrapper)│  │ wrapper)│  │ Arch. C)   │  │
│  └────┬────┘  └─────────┘  └─────────┘  └─────┬──────┘  │
│       │                                      │         │
│       │     ┌──────────────────────┐          │         │
│       └────►│  Godot binary (CLI)  │◄─────────┘         │
│             └──────────┬──────────┘                    │
│                        │                                 │
│             ┌──────────▼──────────┐                      │
│             │  GUT + coverage     │                      │
│             │  addon (GDScript)   │                      │
│             └─────────────────────┘                      │
│                                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │  gdtoolkit (Python — Lark parser)               │   │
│  │  Used by: lint, format, coverage (plan gen)     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Tool Wrapping Strategy

| Feature    | Underlying Tool      | Our Role                                      |
|------------|----------------------|-----------------------------------------------|
| Test       | GUT (GDScript)       | Orchestrate Godot CLI, parse JUnit XML        |
| Lint       | gdlint (Python)      | Wrap CLI, manage config, apply excludes       |
| Format     | gdformat (Python)    | Wrap CLI, manage config, apply excludes       |
| Coverage   | Custom (Arch. C)     | Full implementation — plan gen + report gen    |

---

## 5. CLI Command Surface

```
gd-tools init                    Bootstrap project (GUT, coverage addon, configs)
gd-tools doctor                  Diagnose environment and configuration
gd-tools test [options] [paths]   Run unit tests via GUT
gd-tools lint [paths]...           Lint GDScript files via gdlint
gd-tools format [options] [paths]...  Format GDScript files via gdformat
gd-tools coverage report          Generate report from last coverage run
gd-tools coverage merge           Merge multiple coverage data files
gd-tools coverage show            Print coverage summary to terminal
gd-tools config show             Display resolved configuration (Rich table, TOML, or JSON)
gd-tools config validate         Validate gd-tools.toml — schema, deprecated settings, paths
gd-tools version                 Print all component versions (gd-tools, Godot, GUT, gdtoolkit, Python)
gd-tools completion [shell]      Generate shell completion script (bash, zsh, fish, powershell)
```

### `gd-tools test`

```
gd-tools test [paths]... [--coverage] [--min N] [--suite NAME] [--test NAME]
              [--junit-xml PATH] [--no-exit-code] [--show-uncovered]
```

| Flag/Arg         | Description                                              |
|------------------|----------------------------------------------------------|
| `paths`          | One or more test directories to run (default: config test_dirs) |
| `--coverage`     | Enable coverage instrumentation during test run         |
| `--min N`        | Fail if coverage falls below N% (requires `--coverage`) |
| `--suite NAME`   | Run only the named test suite                            |
| `--test NAME`    | Run only tests matching the name substring              |
| `--junit-xml P`  | Write JUnit XML to path (default: `.gd-tools/results.xml`)|
| `--no-exit-code` | Always exit 0 regardless of test failures               |
| `--show-uncovered` | Show uncovered lines and branches when coverage < 100% (requires `--coverage`) |

When `paths` are provided, they override `test_dirs` from config. Each path
is formatted as `res://path/` and passed to GUT's `-gdir` flag.

**Exit codes:** 0 = pass, 1 = test failures, 2 = environment/config error.

### `gd-tools lint`

```
gd-tools lint [paths]... [--fix] [--report-format text|json]
```

- `paths` — one or more directories/files to lint (default: `.`).
  Files are discovered across all paths and deduplicated.
- `--fix` is a no-op placeholder (gdlint is read-only; reserved for future).
- Exits non-zero if any lint errors (not warnings).

### `gd-tools format`

```
gd-tools format [paths]... [--check] [--diff]
```

- `paths` — one or more directories/files to format (default: `.`).
  Files are discovered across all paths and deduplicated.
- `--check` — report unformatted files without modifying; exit 1 if any
  need formatting (CI mode).
- `--diff` — show a diff of what would change (does not modify).

### `gd-tools coverage`

```
gd-tools coverage report [--format html|lcov|cobertura|text]
                          [--output-dir PATH]
gd-tools coverage merge <files...> [--output PATH]
gd-tools coverage show [--min N]
```

- `report` — regenerate reports from saved `.gd-tools/coverage/coverage.json`
  without re-running tests.
- `merge` — combine multiple coverage data files (e.g., from parallel CI
  shards or multiple test runs).
- `show` — print a terminal summary table (file -> line %, branch %),
  followed by per-file uncovered detail panels (lines and branches).

### `gd-tools version`

```
gd-tools version [--json]
```

Prints version information for all gd-tools components in a Rich table.
Useful for environment diagnostics and bug reports.

- **Components**: gd-tools (`__version__`), Godot (`find_godot()`), GUT
  (`addons/gut/plugin.cfg`), gdtoolkit (`importlib.metadata`), Python
  (`sys.version`).
- **Missing components**: Godot shows "not detected"; GUT and gdtoolkit show
  "not installed". In `--json` output, missing components are `null`.
- **`--json`**: Flat JSON object keyed by component name (machine-readable).
- **Exit code**: Always 0 — version detection never fails.
- **No network calls**: All detection is local.

### `gd-tools completion`

```
gd-tools completion [bash|zsh|fish|powershell]
```

Generates a shell completion script for the specified shell. The script
is printed to stdout and can be sourced directly or saved to a file.

- **Shell argument**: Restricted to `bash`, `zsh`, `fish`, `powershell`
  via `click.Choice`. Invalid shells exit with code 2.
- **PowerShell**: Click 8.2.x does not include a native PowerShell
  completion class. `gd-tools` provides a custom `PowerShellComplete`
  class (subclass of `BashComplete`) with a `Register-ArgumentCompleter`
  template.
- **Alternative**: Click's built-in env-var approach
  (`_GD_TOOLS_COMPLETE=<shell>_source gd-tools`) also works without
  sourcing a script.

### Update Notification

On every CLI invocation, `gd-tools` checks PyPI for a newer version of
`gd-tools-cli`. If an update is available, a notification is printed to
**stderr** (does not interfere with stdout output or scripts):

```
A new version of gd-tools is available: 0.2.0 (you have 0.1.0).
Run `pip install --upgrade gd-tools-cli` to update.
```

Features:
- **Cached**: The PyPI check is cached for 24 hours in
  `~/.gd-tools/update-check.json` to avoid network delays on every run.
- **Non-blocking**: The check fails silently on any error (network
  issues, PyPI downtime, parse errors). It never prevents command
  execution.
- **Skips dev installs**: No check is performed when running from an
  editable/development install (`__version__ == "0.0.0"`).
- **Disabling**: Set the `GD_TOOLS_NO_UPDATE_CHECK=1` environment
  variable to disable the check entirely. This also disables the addon
  version staleness check (see below).

### Addon Version Staleness Check

On every CLI invocation, `gd-tools` also checks whether the deployed
coverage addon files are up-to-date with the installed package version.
A `_version.txt` file in `addons/gd-tools-coverage/` records the version
at deploy time (written by `gd-tools init`). If the addon version is
older than the package version (or the version file is missing), a
warning is printed to **stderr** (does not interfere with command
execution):

```
WARNING: Coverage addon is outdated (v0.2.0 deployed, v0.3.0 available).
Run `gd-tools init` to update.
```

- **Non-blocking**: The warning never prevents command execution.
- **Suppressed by `GD_TOOLS_NO_UPDATE_CHECK=1`**: The same environment
  variable that disables the PyPI update check also disables this check.
- **Doctor integration**: The `gd-tools doctor` command reports addon
  staleness in the Coverage Addon check.

### `gd-tools config`

```
gd-tools config show [--format toml] [--json]
gd-tools config validate
```

- `show` — Print the resolved configuration (including defaults applied):
  - Default: Rich table (Section, Key, Value) — one row per setting across
    all 5 sections (godot, test, lint, format, coverage).
  - `--format toml` — Output as TOML (uses `tomli_w.dumps`, strips `None`
    values).
  - `--json` — Output as JSON (`json.dumps` with `indent=2`).
  - `--format` and `--json` are mutually exclusive (exit code 2 if both
    given).
  - Works with no config file — shows all defaults.

- `validate` — Check config validity without running a command:
  - **Schema errors** (✗): Unknown keys, type mismatches, constraint
    violations. Includes "did you mean" suggestions for misspelled keys.
  - **Deprecated settings** (✗): Warns on deprecated config keys (future
    deprecation infrastructure, currently empty).
  - **Path warnings** (!): Advisory, non-fatal — `test_dirs`, `godot.binary`,
    `coverage.output_dir` parent, and `exclude` directories checked for
    existence.
  - Summary: file path, sections validated (5: godot, test, lint, format,
    coverage), counts, and "✓ Configuration is valid." on success.

**Exit codes:** `show` — 0 on success, 2 on config error or conflicting
flags. `validate` — 0 on valid config, 1 on schema errors or deprecated
settings, 2 on config read error.

---

## 6. Configuration — `gd-tools.toml`

Single source of truth, located at project root.

```toml
[gd-tools]
# Currently no top-level keys; reserved for future.

[godot]
# Path to Godot binary. If omitted, auto-detection chain is used.
# binary = "/usr/local/bin/godot"

[test]
# Directories containing test files.
test_dirs = ["test", "tests"]
# Test file prefix/suffix (GUT convention).
prefix = "test_"
suffix = ".gd"
# GUT config file path (default: .gutconfig.json in project root).
gutconfig = ".gutconfig.json"

[lint]
exclude = ["addons", ".godot", ".gd-tools", ".git"]
# Additional gdlint rule overrides go in gdlintrc (generated by init).

[format]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[coverage]
enabled = false
# Minimum coverage percentage. `gd-tools test --coverage --min 80` fails below this.
min_percent = 0
# Report format for `gd-tools test --coverage` (auto-generates after run).
format = "html"
# Where to store coverage data and reports.
output_dir = ".gd-tools/coverage"
# Directories excluded from coverage measurement.
exclude = ["addons", ".godot", ".gd-tools", ".git"]
# Directories containing test files (excluded from coverage targets, but
# their execution is still tracked for test-side coverage).
test_dirs = ["test", "tests"]
```

### Config Resolution

1. CLI flags override config file values.
2. `gd-tools.toml` in project root (found by walking up from CWD to nearest
   `project.godot`).
3. If no config file exists, built-in defaults apply.

---

## 7. `gd-tools init` — Project Bootstrapping

### Flow

1. **Detect project root** — walk up from CWD to find `project.godot`.
2. **Detect Godot version** — run `godot --version`, parse output.
   - Require 4.5+. Error with instructions if older.
3. **Check GUT installation** — does `addons/gut/gut.gd` exist?
   - **YES** → verify version compatibility → warn if mismatch.
   - **NO** → prompt: *"GUT not found. Install automatically? [Y/n]"*
     - **Y** → download correct GUT version from GitHub releases → extract →
       copy `addons/gut/` → enable plugin in `project.godot`.
     - **n** → print manual install instructions (Asset Library link + zip URL).
4. **Install coverage addon** — copy bundled GDScript files to
   `addons/gd-tools-coverage/` (always, idempotent — overwrites if stale).
   Writes a `_version.txt` file recording the package version for
   staleness detection.
5. **Create/update `.gutconfig.json`** — add coverage hook paths
   (`pre_run_script`, `post_run_script`). Merge with existing config if present.
6. **Create `gd-tools.toml`** — generate with defaults, preserving existing
   values if file already exists.
7. **Generate `gdlintrc` and `gdformatrc`** — from `[lint]`/`[format]` exclude
   lists, so gdlint/gdformat work standalone.
8. **Create `.gd-tools/` directory** — add to `.gitignore` if not already
   present.
9. **Print summary** — what was installed/configured, next steps.

### GUT Version Mapping

Hardcoded table in `gd-tools` (updated per release):

| Godot Version | GUT Version | GitHub Tag |
|---------------|-------------|------------|
| 4.5           | 9.5.0       | v9.5.0     |
| 4.6           | 9.6.0       | v9.6.0     |
| 4.7           | 9.7.0       | v9.7.0     |

Download URL: `https://github.com/bitwes/Gut/archive/refs/tags/v{VERSION}.zip`

### Plugin Enabling in `project.godot`

```ini
[editor_plugins]
enabled=PackedStringArray("res://addons/gut/plugin.gd")
```

- Idempotent: check if already present before adding.
- The coverage addon does **not** need to be enabled as a plugin — it's
  invoked by GUT hooks, not the editor.

### Coverage Addon Bundling

The GDScript coverage addon files ship as **package data** inside the Python
distribution:

```
gd_tools/
  addons/
    gd-tools-coverage/
      coverage.gd           # Core instrumentation + tracking
      pre_run_hook.gd       # GUT pre-run hook — activates coverage tracker
      post_run_hook.gd      # GUT post-run hook — saves coverage JSON
```

- On `gd-tools init`, these are copied to the project's `addons/gd-tools-coverage/`.
- Always version-matched with the CLI — no separate download.
- A `_version.txt` file is written alongside the addon files, recording
  the gd-tools package version at deploy time. This enables stale-addon
  detection on subsequent CLI invocations (see §5 Addon Version
  Staleness Check).
- After upgrading `gd-tools` via pip, re-run `init` to refresh addon files.

---

## 8. `gd-tools doctor` — Diagnostics

Runs a series of checks and reports status:

| Check                          | Pass Condition                                    |
|--------------------------------|---------------------------------------------------|
| Godot binary accessible        | Binary found via detection chain, runs without error |
| Godot version                   | 4.5 or higher                                     |
| GUT installed                   | `addons/gut/gut.gd` exists                        |
| GUT version compatible          | Matches Godot version per mapping table           |
| Coverage addon files present   | `addons/gd-tools-coverage/*.gd` all exist; version not stale  |
| `.gutconfig.json` valid        | Parseable JSON, has coverage hook paths           |
| `gd-tools.toml` exists & valid | File present, parseable TOML                      |
| gdtoolkit installed            | `gdlint --version` and `gdformat --version` succeed |
| `_GDTCoverage` autoload        | `project.godot` has `_GDTCoverage=` autoload entry |

Output: table with ✓/✗ per check, plus actionable fix suggestions for failures.

---

## 9. Godot Binary Detection

Resolution chain (first match wins):

1. **Config:** `gd-tools.toml` → `[godot]` → `binary` (user-specified, highest priority)
2. **Environment variables:** `GODOT_BIN` → `GODOT4_BIN` → `GODOT_PATH`
3. **PATH lookup:** `shutil.which("godot")` → `shutil.which("godot4")`
4. **Common install locations** (platform-specific):
   - **Windows:** `C:\Program Files\Godot\`, `%LOCALAPPDATA%\Godot\`, Scoop,
     Chocolatey, Steam install paths
   - **macOS:** `/Applications/Godot.app/Contents/MacOS/Godot`,
     `/opt/homebrew/bin/godot`
   - **Linux:** `~/.local/bin/godot`, `/usr/bin/godot`, `/usr/local/bin/godot`
5. **Not found** → error with platform-specific install instructions

**Note:** gdtoolkit (lint/format/coverage parser) does **not** need the Godot
binary — it's pure Python. Only `gd-tools test` and `gd-tools init` (version
detection) require finding Godot.

---

## 10. Coverage Architecture (Architecture C — Hybrid)

### Overview

Coverage is the core differentiator. No production-quality GDScript coverage
tool exists for Godot 4. `gd-tools` implements a **hybrid architecture**:

- **Python side** (gdtoolkit/Lark): Parses GDScript, identifies executable
  lines and branch points, generates an **instrumentation plan** (JSON).
- **GDScript side** (coverage addon): Reads the plan at runtime, instruments
  scripts via Godot's Script API, tracks execution, writes **coverage data**
  (JSON).
- **Python side** (reporter): Reads coverage data, generates reports (HTML,
  LCOV, Cobertura, text).

### Why Hybrid?

| Architecture | Pros | Cons |
|-------------|------|------|
| A (Pure Python) | No runtime component | Lark Reconstructor is experimental; code generation from modified tree is unreliable |
| B (Fork jamie-pate) | Fastest to MVP | Depends on unmaintained code; GDScript-only parsing is less robust than Lark |
| **C (Hybrid)** ✅ | Best parsing (Lark) + safest instrumentation (Godot Script API) | Most moving parts; requires GDScript addon |

### Full Flow: `gd-tools test --coverage`

```
┌──────────────────────────────────────────────────────────────┐
│ PYTHON                                                       │
│                                                              │
│  1. Parse project with gdtoolkit (Lark parser)              │
│     - Identify executable lines (expr_stmt, return_stmt,    │
│       if_stmt, while_stmt, for_stmt, match_stmt, etc.)      │
│     - Identify branch points (if/elif/else, match cases,    │
│       for/while loops, ternary)                             │
│                                                              │
│  2. Generate instrumentation plan (JSON)                    │
│     {                                                       │
│       "version": 1,                                         │
│       "files": [                                            │
│         {                                                   │
│           "path": "res://scripts/player.gd",                │
│           "lines": [                                        │
│             {"line": 5, "id": 0, "type": "statement"},      │
│             {"line": 8, "id": 1, "type": "branch_true"},    │
│             {"line": 10, "id": 2, "type": "branch_false"}   │
│           ]                                                 │
│         }                                                   │
│       ]                                                     │
│     }                                                       │
│                                                              │
│  3. Write plan to .gd-tools/coverage/plan.json              │
│  4. Set env vars:                                            │
│     GD_TOOLS_COVERAGE_PLAN=res://path/to/plan.json           │
│     GD_TOOLS_COVERAGE_OUTPUT=res://path/to/output.json       │
│                                                              │
│  5. Invoke Godot with GUT CLI:                              │
│     godot --headless -s addons/gut/gut_cmdln.gd --path . \  │
│       -gpre_run_script=res://addons/gd-tools-coverage/...   │
│       -gpost_run_script=res://addons/gd-tools-coverage/...   │
│       -gexit                                                │
│                                                              │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ GODOT + GUT (GDScript)                                       │
│                                                              │
│  6. Pre-run hook (pre_run_hook.gd):                         │
│     - Read instrumentation plan from env var path           │
│     - For each file in plan:                                │
│       - Load script via ResourceLoader                       │
│       - Use Godot Script API to instrument:                  │
│         inject tracker calls at identified line/branch IDs   │
│       - Reload instrumented scripts                          │
│     - Initialize coverage tracker (visited IDs set)          │
│                                                              │
│  7. GUT runs tests                                           │
│     - Instrumented code fires trackers on execution          │
│     - Tracker records: {file, line_id, hit_count}            │
│                                                              │
│  8. Post-run hook (post_run_hook.gd):                       │
│     - Serialize coverage data to JSON                        │
│     - Write to path from GD_TOOLS_COVERAGE_OUTPUT env var    │
│                                                              │
│  9. GUT exports JUnit XML (test results)                    │
│                                                              │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ PYTHON                                                       │
│                                                              │
│ 10. Read JUnit XML (test results)                           │
│ 11. Read coverage JSON (coverage data)                      │
│ 12. Cross-reference plan + data → compute:                  │
│     - Line coverage % per file                              │
│     - Branch coverage % per file                            │
│     - Overall coverage %                                    │
│ 13. Generate reports:                                        │
│     - HTML (detailed, syntax-highlighted source view)        │
│     - LCOV (for CI integration, codecov.io, coveralls)       │
│     - Cobertura (Jenkins, GitLab CI)                        │
│     - Terminal summary table                                 │
│     ✅ Implemented — Track 12 (see below)                    │
│ 14. Apply --min threshold (exit 1 if below)                 │
│     ✅ Implemented — Track 13 (coverage/orchestrator.py)     │
│ 15. Print coverage summary table on success AND before      │
│     threshold error (Lines/Branches: Found/Hit/Rate)       │
│     ✅ Track: coverage_success_display_20260714             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Instrumentation Plan Format (JSON)

> **Implemented:** Track 9 (`coverage-plan-generator_20260711`, archived).
> See `src/gd_tools/coverage/plan_generator.py`. All 12 acceptance criteria
> passed. `plan_generator.py` at 100% coverage.
>
> **Tracker implemented:** Track 10 (`coverage_tracker_20260711`, archived).
> See `src/gd_tools/addons/gd-tools-coverage/coverage.gd`. All 7 success
> criteria passed. Tracker deployed via `register_coverage_autoload()` in
> `init.py`. 6 GUT tests in `test_coverage_tracker.gd`.
>
> **Hooks implemented:** Track 11 (`coverage_hooks_20260711`, archived). See
> `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd` (228 lines) and
> `post_run_hook.gd` (113 lines). All 12 acceptance criteria passed. Key
> deviations from spec: added plan schema validation (`_validate_plan`,
> `_validate_file_entry`), Cause/Fix error format (`_log_error`), tracker
> activation guard (`is_active` check in post-run). 28+13 GUT tests + 11
> integration tests in `test_coverage_hooks.py`.
>
> **Reporter implemented:** Track 12 (`coverage_reporter_20260711`,
> archived). See `src/gd_tools/coverage/reporter.py` (~510 lines,
> orchestrator), `html_reporter.py`, `lcov_reporter.py`,
> `cobertura_reporter.py`, `terminal_reporter.py`. All 8 success criteria
> passed. Generates reports in 4 formats: HTML (Jinja2 templates),
> LCOV, Cobertura XML, Text (Rich table). 73 unit tests across 5
> test files; coverage modules at 96-100%. Key functions:
> `read_coverage_json()`, `merge_coverage_data()`, `compute_summary()`,
> `generate_report(plan, data, output_dir, format, min_threshold)`.
> Review fixes (commit `e9457ec`): error messages updated to Cause/Fix
> format, HTML templates added to package-data, dead code removed.
> Known limitation: HTML source view not populated (spec FR-4.3
> partially met — deferred). **Resolved** (commit `8e48360`): HTML
> report now reads and displays source code lines.

```json
{
  "version": 1,
  "generated_by": "gd-tools 0.1.0",
  "files": [
    {
      "file_id": 0,
      "path": "res://scripts/player.gd",
      "source_hash": "sha256:...",
      "lines": [
        {
          "line": 5,
          "id": 0,
          "type": "statement"
        },
        {
          "line": 8,
          "id": 1,
          "type": "branch",
          "branch_type": "if_true"
        },
        {
          "line": 10,
          "id": 2,
          "type": "branch",
          "branch_type": "if_false"
        }
      ]
    }
  ]
}
```

### Coverage Data Format (JSON, written by GDScript addon)

```json
{
  "version": 1,
  "generated_at": "2026-07-08T12:00:00Z",
  "files": [
    {
      "path": "res://scripts/player.gd",
      "hits": {
        "0": 15,
        "1": 12,
        "2": 3
      }
    }
  ]
}
```

### Executable Line Identification (gdtoolkit/Lark)

Using `parser.parse(code, gather_metadata=True)`, the following Lark tree node
types are identified as **executable** (have line coverage):

| Statement Type   | Lark Node                | Coverage Type           |
|------------------|--------------------------|-------------------------|
| Expression       | `expr_stmt`              | statement               |
| Return           | `return_stmt`            | statement               |
| Assignment       | `func_var_assigned`       | statement               |
| Typed assignment | `func_var_typed_assgnd`   | statement               |
| Inferred assign  | `func_var_inf`            | statement               |
| If branch        | `if_branch`              | branch (if_true)        |
| Elif branch      | `elif_branch`            | branch (elif_true)      |
| Else branch      | `else_branch`            | branch (if_false)       |
| While loop       | `while_stmt`             | branch (loop_body)      |
| For loop         | `for_stmt`               | branch (loop_body)      |
| For loop (typed) | `for_stmt_typed`         | branch (loop_body)      |
| Match            | `match_branch`           | branch (match_case)     |
| Break            | `break_stmt`             | statement               |
| Continue         | `continue_stmt`          | statement               |

**Declarative** (not executable, excluded from coverage):
`class_var_stmt`, `const_stmt`, `signal_stmt`, `enum_stmt`, `func_def`,
`static_func_def`, `extends_stmt`, `classname_stmt`.

**Skipped** (no-op, not tracked): `pass_stmt`, `breakpoint_stmt`.

### Instrumentation Approach (GDScript side)

Inspired by felix-hellman/godot-code-coverage: inject a tracker call at the
start of each executable block. The coverage addon maintains a registry of
visited line IDs.

```gdscript
# Before instrumentation:
func take_damage(amount: int) -> void:
    if amount > 0:
        health -= amount
        if health <= 0:
            die()
    return

# After instrumentation (Conceptual):
func take_damage(amount: int) -> void:
    _gd_tools_cov.hit(0)          # line 2: expr entry
    if amount > 0:
        _gd_tools_cov.hit(1)      # line 3: if_true branch
        health -= amount
        if health <= 0:
            _gd_tools_cov.hit(2)  # line 5: nested if_true
            die()
    _gd_tools_cov.hit(3)          # line 7: return
    return
```

**Implementation note:** The exact instrumentation mechanism (source text
manipulation vs. Script API bytecode injection) is an implementation detail to
be resolved during development. The plan JSON provides line numbers and IDs;
the GDScript addon decides how to inject trackers.

**Branch injection strategy (Track 21):** Two injection strategies are used
depending on branch type:

- **Before the line** (statements, `if_true`, `loop_body`): tracker injected
  at the target line's indentation, before it.
- **After the keyword line, inside the body** (`match_case`, `if_false`,
  `elif_true`): tracker injected on the line after `pattern:`, `else:`, or
  `elif:` at the body indentation level. Injecting before these keyword
  lines would insert a statement between the `if`/`elif`/`else` keywords,
  breaking the GDScript block structure (orphaned `else`/`elif` = syntax
  error). The `_detect_body_indent()` helper scans forward from the
  keyword line to find the body indentation.

**Null guard (Track 20/21):** The plan JSON uses `null` for non-branch
entries. GDScript's `Dictionary.get(key, default)` returns `null` when the
key exists with a null value. An explicit null check prevents assigning
`null` to a `String`-typed variable, which would crash instrumentation for
all files.

**Autoload-based instrumentation (Track 24.5):** Coverage instrumentation now
happens in `_GDTCoverage._ready()`, which runs as the first autoload (position
0) before any other autoload's `_ready()`. This eliminates `ERR_ALREADY_IN_USE`
errors: by instrumenting before autoloads create instances, all subsequent
`load()` calls return the instrumented source. The `_GDTCoverage` autoload is
prepended to the `[autoload]` section by `register_coverage_autoload()` in
`init.py`, with an auto-fix that moves it to position 0 if needed. Autoload
scripts (including scripts they instantiate) are now included in coverage.

---

## 11. Directory & File Exclusion

### Default Exclude List

Applied to lint, format, and coverage:

```python
DEFAULT_EXCLUDES = ["addons", ".godot", ".gd-tools", ".git"]
```

**Rationale:**
- `addons/` — third-party code (GUT, other plugins). Not user code; shouldn't
  be linted, formatted, or measured for coverage.
- `.godot/` — Godot's generated cache directory.
- `.gd-tools/` — our own output directory (coverage data, reports, results).
- `.git/` — version control metadata.

### Hybrid Exclude Matching

Exclude entries support both bare names and path prefixes:

- **Bare names** (no `/` or `\`): Matched against the basename of each
  discovered file's path. This is the original behavior and remains
  backward-compatible (e.g., `"addons"` excludes any directory named
  `addons` at any depth).
- **Path prefixes** (containing `/` or `\`): Normalized to the OS separator
  and matched as a path prefix via `os.path.relpath`. This allows
  excluding specific subdirectories while keeping same-named directories
  elsewhere (e.g., `"src/vendor/addons"` excludes only that specific path).

### Autoload Inclusion in Coverage (Track 24.5)

Autoload scripts are now **included** in coverage instrumentation. The
`_GDTCoverage` autoload (registered as the first autoload, position 0)
instruments all files in its `_ready()` before any other autoload
initializes. This ensures that when autoloads create instances of other
scripts during their `_ready()`, those instances use the instrumented
source. The previous `resolve_autoload_paths()` exclusion was removed ---
autoloads and the scripts they instantiate are fully covered.

### gdtoolkit Config Generation

`gd-tools init` generates `gdlintrc` and `gdformatrc` from the `[lint]` and
`[format]` sections of `gd-tools.toml`:

```yaml
# gdlintrc (generated)
excluded_directories: !!set { .git: null, addons: null, .godot: null, .gd-tools: null }
```

This ensures gdlint and gdformat work correctly when invoked standalone
(without `gd-tools`).

### Coverage-Specific Excludes

Coverage additionally excludes test directories from **coverage targets**
(test files are not measured for coverage — they ARE the measurement tool):

```toml
[coverage]
exclude = ["addons", ".godot", ".gd-tools", ".git"]
test_dirs = ["test", "tests"]
```

Test files are still linted and formatted (they are user code).

---

## 12. Dependencies

### Python (runtime)

| Package        | Purpose                                      |
|----------------|----------------------------------------------|
| `gdtoolkit`    | Lark-based GDScript parser (lint, format, coverage plan gen) |
| `junitparser`  | Parse GUT's JUnit XML output                 |
| `jinja2`       | HTML coverage report generation              |
| `rich`         | Terminal output (tables, colors, progress)   |
| `tomli`        | TOML config parsing (Python < 3.11 backport) |
| `requests`     | Download GUT releases from GitHub            |
| `click`        | CLI framework (or `typer` — TBD)             |
| `packaging`    | Version comparison for PyPI update notification |

### Python (dev)

| Package      | Purpose                          |
|--------------|----------------------------------|
| `pytest`     | Test gd-tools itself             |
| `ruff`       | Lint gd-tools Python code        |
| `black`      | Format gd-tools Python code       |
| `commitizen` | Conventional commit enforcement, automated semantic versioning, changelog generation |

### GDScript (bundled, not a pip dependency)

| Component              | Purpose                          |
|------------------------|----------------------------------|
| GUT (installed by init)| Test framework                   |
| Coverage addon (bundled)| Runtime instrumentation + tracking |

### External (not pip-installable)

| Component     | Purpose                          |
|---------------|----------------------------------|
| Godot 4.5+    | Runs GUT + instrumented tests    |

---

## 13. Project File Layout (gd-tools itself)

```
gd-tools/
├── docs/
│   ├── PRD.md                    # This document
│   ├── USER_GUIDE.md             # Complete CLI reference and user guide
│   ├── CONTRIBUTING.md           # Contributor onboarding guide
│   ├── ARCHITECTURE.md           # Coverage system architecture document
│   ├── ROADMAP.md                # Development roadmap and track status
│   ├── TDD.md                    # Technical design document
│   ├── TESTING_STRATEGY.md       # Test pyramid and coverage targets
│   └── SPIKE_coverage_instrumentation.md  # Coverage spike results
├── src/
│   └── gd_tools/
│       ├── __init__.py
│       ├── __main__.py           # Entry point: python -m gd_tools
│       ├── cli.py                # Click/Typer CLI definitions
│       ├── update_check.py       # PyPI update notification on CLI invocation
│       ├── addon_check.py        # Stale addon version detection on CLI invocation
│       ├── config.py             # gd-tools.toml loading & validation
│       ├── godot.py              # Godot binary detection + invocation
│       ├── init.py               # `gd-tools init` logic
│       ├── doctor.py             # `gd-tools doctor` logic
│       ├── test_runner.py        # `gd-tools test` — GUT orchestration
│       ├── lint_runner.py       # `gd-tools lint` — gdlint wrapper
│       ├── output.py           # Shared terminal output module (Rich-based)
│       ├── verbosity.py        # Global verbosity context (Verbosity enum + accessors)
│       ├── format_runner.py     # `gd-tools format` — gdformat wrapper
│       ├── version.py           # `gd-tools version` — component version detection
│       ├── coverage/
│       │   ├── __init__.py
│       │   ├── orchestrator.py    # Coverage CLI orchestration (test --coverage, report, merge, show)
│       │   ├── plan_generator.py # Parse GDScript, build instrumentation plan
│       │   ├── reporter.py       # Read coverage data, generate reports
│       │   ├── html_reporter.py  # Jinja2 HTML report
│       │   ├── lcov_reporter.py  # LCOV format
│       │   ├── cobertura_reporter.py  # Cobertura XML
│       │   ├── terminal_reporter.py   # Rich terminal table
│       │   └── templates/
│       │       ├── index.html    # HTML report index page
│       │       └── file.html     # HTML per-file page
│       └── addons/
│           └── gd-tools-coverage/
│               ├── coverage.gd          # Core instrumentation + tracker
│               ├── pre_run_hook.gd      # GUT pre-run hook
│               └── post_run_hook.gd     # GUT post-run hook
├── tests/                        # Python tests for gd-tools itself
├── pyproject.toml
└── README.md
```

---

## 14. Data Storage

### `.gd-tools/` directory (project root, gitignored)

```
.gd-tools/
├── coverage/
│   ├── plan.json              # Instrumentation plan (regenerated per run)
│   ├── coverage.json          # Raw coverage data from last run
│   ├── results.xml            # JUnit XML from last test run
│   └── html/                  # HTML report output
│       ├── index.html
│       └── ...
└── results.xml                # JUnit XML (if --junit-xml not specified)
```

### `.gutconfig.json` (project root, committed)

Generated/managed by `gd-tools init`. Contains GUT config + coverage hook paths:

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

---

## 15. CI/CD Integration

### GitHub Actions Example

```yaml
- name: Install gd-tools
  run: pip install gd-tools-cli

- name: Bootstrap
  run: gd-tools init --non-interactive

- name: Lint
  run: gd-tools lint

- name: Format check
  run: gd-tools format --check

- name: Test with coverage
  run: gd-tools test --coverage --min 80 --junit-xml .gd-tools/results.xml

- name: Upload test results
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: .gd-tools/results.xml

- name: Upload coverage
  uses: actions/upload-artifact@v4
  with:
    name: coverage-report
    path: .gd-tools/coverage/html/
```

### Exit Codes (all commands)

| Code | Meaning            |
|------|--------------------|
| 0    | Success            |
| 1    | Test/lint/format failure or coverage below threshold |
| 2    | Environment/config error, or `--verbose` and `--quiet` used together |

### Project CI/CD Pipeline

gd-tools' own CI/CD pipeline is implemented in `.github/workflows/`:

- **`ci.yml`** — Staged gating: `lint-format-unit` → `integration` →
  `e2e`, plus a cross-platform matrix (Ubuntu + Windows, Python
  3.10/3.11/3.12). Coverage uploaded to codecov.io. JUnit XML results
  uploaded as artifacts.
- **`commit-check.yml`** — Conventional commit message validation on
  pull requests via `cz check` (commitizen).
- **`release.yml`** — Tag push (`v*`) triggers build + TestPyPI upload,
  then production PyPI upload (requires `PYPI_API_TOKEN` secret).
- **`.github/SECRETS.md`** — Required GitHub secrets documentation.

---

## 16. Open Questions (Deferred to Implementation)

These were raised during design discussion but not yet resolved. They should be
addressed during implementation, with the simplest reasonable default chosen
first:

1. **`gdlintrc`/`gdformatrc` generation policy** — Should `init` always
   overwrite these, or only generate if they don't exist? *Default: generate if
   missing, warn if existing and differs from expected.*

2. **Coverage of addon files** — Should coverage reports include addon files
   as "0% covered" (informational) or exclude them entirely? *Default: exclude
   entirely (clean reports).*

3. **Additional default excludes** — Beyond `addons`, `.godot`, `.gd-tools`,
   `.git`, are there other directories to exclude by default? *Default: no;
   users can add via config.*

4. **CLI framework choice** — `click` vs `typer`? Both are mature. *Default:
   decide during implementation; `click` has broader ecosystem, `typer` has
   better type hints.*

5. **Instrumentation mechanism** — Source text manipulation vs. Godot Script
   API bytecode injection? *This is the core implementation risk and should be
   prototyped early.*

6. **Coverage for manual playtesting** — Future: `gd-tools coverage run` to
   instrument and track coverage during manual game playtesting (not just
   tests). Out of scope for v1.

---

## 17. Future Roadmap (Post-v1)

- **`gd-tools coverage run`** — Coverage during manual playtesting (instrument
  the game, play, collect coverage).
- **Editor plugin** — Godot editor dock for running tests and viewing coverage
  inline.
- **Watch mode** — `gd-tools test --watch` re-runs affected tests on file
  change.
- **Coverage diff** — Show coverage changes between branches (like `codecov`).
- **GdUnit4 support** — Alternative test framework support (currently GUT only).
- **Pre-commit hooks** — `gd-tools install-hooks` for pre-commit framework
  integration.

---

## 18. Glossary

| Term | Definition |
|------|-----------|
| **GUT** | Godot Unit Test — the dominant GDScript test framework |
| **gdtoolkit** | Python package (Scony/godot-gdscript-toolkit) providing gdlint + gdformat + Lark-based parser |
| **Lark** | Python parsing library used by gdtoolkit; supports LALR and Earley parsers |
| **Architecture C** | Hybrid coverage architecture: Python plan generation + GDScript runtime instrumentation + Python reporting |
| **Instrumentation plan** | JSON file describing which lines/branches to track, generated by Python, consumed by GDScript addon |
| **LCOV** | Line coverage data format (GNU toolchain standard, used by codecov.io, coveralls) |
| **Cobertura** | XML-based coverage report format (used by Jenkins, GitLab CI) |
| **JUnit XML** | Standard XML format for test results (Jenkins, GitHub Actions, GitLab CI) |
