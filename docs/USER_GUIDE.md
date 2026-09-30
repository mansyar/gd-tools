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
6. [Shell Completion](#6-shell-completion)


## 1. Getting Started

### 1.1 Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.10 | Required for modern type hints and tomllib support. |
| Godot Engine | 4.5 | Must be accessible via PATH or a GODOT_BIN environment variable. |
| GUT (Godot Unit Test) | 9.5.0 | Optional legacy compatibility runtime; not installed by default. |

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
2. Detects the installed Godot version.
3. Deploys the bundled `addons/gd-tools-test/` native test addon.
4. Deploys the `gd-tools-coverage` addon into `addons/gd-tools-coverage/`
   (including a `_version.txt` file for staleness detection).
5. Creates `gd-tools.toml` with native runtime defaults if absent.
6. Generates `gdlintrc` and `gdformatrc` exclude files.
7. Creates the `.gd-tools/` working directory.
8. Leaves GUT, `.gutconfig.json`, and the legacy coverage autoload uninstalled.

`--with-gut` still installs the legacy GUT addon, but the addon now conflicts
with the built-in compatibility bridge (both provide `class_name GutTest`) and
`gd-tools doctor` warns about it. New projects should not use it. Existing GUT
suites can be migrated with `gd-tools migrate`; see the
[migration guide](./gut-migration.md).

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
runtime = "native"
test_dirs = ["test", "tests"]
timeout_seconds = 5.0
retries = 0
tags = []
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
| `runtime` | string | `"native"` | Test runtime: `native` or legacy `gut`. |
| `test_dirs` | list of strings | `["test", "tests"]` | Directories scanned for test files. |
| `timeout_seconds` | number | `5.0` | Default native per-test async timeout in seconds. |
| `retries` | integer | `0` | Default native retry count. |
| `parallel` | integer | None | Persistent parallel worker count (1-32) for the native runtime. Omit for sequential execution; `--parallel` overrides this for one invocation. |
| `tags` | list of strings | `[]` | Native class-level tag filters; an empty list matches all tags. |
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
gd-tools init [--non-interactive] [--with-gut]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--non-interactive` | flag | `false` | Run without interactive prompts. |
| `--with-gut` | flag | `false` | Also install/enable the legacy GUT runtime and compatibility files. The installed addon conflicts with the compatibility bridge and `doctor` warns about it. |

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
| 1 | User declined an optional legacy GUT installation when prompted. |
| 2 | Configuration or environment error (e.g., Godot not found). |

**Smart Backup of Modified Addon Files:**

When re-running `gd-tools init` on a project where native or coverage addon
files have been modified by the user, the modified file is backed up under
that addon's `.backups/<filename>.bak` before being overwritten with the
bundled version. A yellow warning is printed naming the file and its backup
path. Unmodified files are overwritten silently. The `.backups/` directory
is auto-created on the first backup.

This protects user customizations from being silently destroyed during
re-init (e.g., after upgrading `gd-tools` via pip).

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
| 3 | Native Test Addon | critical/warning | Bundled `gd-tools-test` files are present and the deployed version is current. |
| 4 | GUT Installed | warning | GUT is never required; an installed GUT addon conflicts with the compatibility bridge (duplicate `class_name GutTest`). |
| 5 | GUT Version | informational | Reports the installed GUT version; it no longer affects any runtime. |
| 6 | Coverage Addon | warning | All `gd-tools-coverage` addon files are present and not stale. |
| 7 | GUT Config | warning | `.gutconfig.json` is not read by any runtime; malformed JSON is reported as a warning. |
| 8 | gd-tools.toml | critical | `gd-tools.toml` exists and is valid TOML. |
| 9 | GD Toolkit | critical | `gdlint` and `gdformat` CLI tools are installed. |
| 10 | GUT Suites | informational | Lists `GutTest` suites in the project; they run through the compatibility bridge automatically. |
| 11 | Autoload | warning | `_GDTCoverage` is legacy; native coverage does not use an autoload. |

`doctor` additionally warns when `test.runtime = "gut"` is set in
`gd-tools.toml` -- that value is no longer runnable; `GutTest` suites run
through the bridge automatically.

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

Run GDScript tests using the bundled native runtime. Suites extending
`GdToolsTest` and `GutTest` are detected automatically; `GutTest` suites run
through the GUT compatibility bridge (see the
[migration guide](./gut-migration.md)). The legacy `--runtime gut` flag has
been removed and is rejected with migration guidance.

**Usage:**

```bash
gd-tools test [PATHS]... [OPTIONS]
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `paths` | no | Config `[test].test_dirs` | One or more test files or directories to scan. File paths are selected exactly; directories are scanned recursively. |
| `--runtime` | choice | Config `[test].runtime` (`native`) | Select `native` or legacy `gut`. |

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--coverage` | flag | `false` | Generate a coverage report during the test run. |
| `--min` | integer | None | Minimum coverage percentage threshold. Fails if coverage is below this value. Requires `--coverage`; if passed without it, a warning is printed and the flag is ignored. |
| `--suite` | string | None | Run only the specified test suite. |
| `--test` | string | None | Run only the specified test. |
| `--tag` | string, repeatable | Config `[test].tags` | Run native suites matching a class-level tag. |
| `--test-timeout` | number | Config `[test].timeout_seconds` | Per-test timeout in seconds for native tests. |
| `--parallel` | integer | Config `[test].parallel` | Run suites with up to N concurrent workers (1-32). Bare `--parallel` defaults to 4 workers — note it overrides a configured value even if that value is higher. Omit for sequential execution. |
| `--junit-xml` | string | None | Path to write a JUnit XML report. |
| `--no-exit-code` | flag | `false` | Do not exit with non-zero on test failure. |
| `--timeout` | integer | None | Godot import and per-suite process timeout in seconds. |
| `--show-uncovered` | flag | `false` | Show uncovered lines and branches as Rich panels when coverage is below 100%. Requires `--coverage`; if passed without it, a warning is printed and the flag is ignored. |
| `--no-cache` | flag | `false` | Force plan regeneration, bypassing the coverage plan cache. Only effective with `--coverage`; has no effect without it. |

**Examples:**

```bash
# Run all tests (GdToolsTest and GutTest suites are routed automatically)
gd-tools test

# Run a native suite and write JUnit XML
gd-tools test --suite NativeFixtureSuite --junit-xml .gd-tools/native.xml

# Run tests with coverage
gd-tools test --coverage

# Run tests with coverage and enforce an 80% threshold
gd-tools test --coverage --min 80

# Show uncovered lines and branches when coverage is below 100%
gd-tools test --coverage --show-uncovered

# Force plan regeneration, bypassing the cache
gd-tools test --coverage --no-cache

# Run a specific test suite
gd-tools test --suite PlayerTests

# Run a specific test and write JUnit XML
gd-tools test --test test_movement --junit-xml report.xml

# Run native suites with a class tag and a one-second per-test limit
gd-tools test --tag smoke --test-timeout 1.0

# Run tests without exit code (useful in CI pre-steps)
gd-tools test --no-exit-code

# Run tests from a specific directory (overrides config test_dirs)
gd-tools test tests/unit

# Run tests from multiple directories
gd-tools test tests/unit tests/integration

# Run exactly one native test file
gd-tools test tests/unit/test_player.gd
```

**Native runtime notes:**

- Native suites extend `GdToolsTest` and expose no-argument `test_*` methods.
- Python starts one headless Godot process per suite, retains suite-scoped
  state for the suite, and creates a fresh test instance for each test.
- `before_all`, `before_each`, `after_each`, and `after_all` failures appear
  in the native result and affect the run status; cleanup hooks are attempted
  after test timeouts.
- Native runs write structured result JSON under the run's artifact directory
  (`.gd-tools/artifacts/<run_id>/native/`, indexed by
  `.gd-tools/artifacts/<run_id>/artifacts.json`) and the requested JUnit XML;
  `--coverage` adds plan-v1 data and a merged report.
- Results include timestamps, assertion diagnostics, and Godot engine
  errors/warnings. Engine errors are infrastructure failures (exit `2`).
- Async tests may await process frames, physics frames, timers, and signals.
  The default per-test timeout is `5.0` seconds (`[test].timeout_seconds`);
  `--test-timeout` overrides it for one invocation, while `--timeout` limits
  Godot import and suite processes. Failed or timed-out tests are retried
  according to `[test].retries`.
- Class-level tags can be configured with `[test].tags` or selected with
  repeatable `--tag` options. Explicit file paths are never broadened to
  sibling suites.
- If discovery finds no suites, the error explains that suites must extend
  `GdToolsTest` (native) or `GutTest` (compatibility bridge).
- Opt-in parallel execution: `--parallel N` or `[test].parallel` dispatches
  suites to at most N concurrent Godot processes. Results, JUnit XML, and
  merged coverage are identical to a sequential run; a failed, timed-out, or
  crashed suite never cancels its neighbors. Ctrl+C (or SIGTERM) kills every
  in-flight process tree and marks the artifact index `incomplete`
  (exit `130`) — in both sequential and parallel runs.
- The runtime does not provide an editor UI.

**Parameterized tests:**

Test methods may take parameters. Declare the value sets once in
`before_all`, and the runner expands one case per value set:

```gdscript
extends GdToolsTest

func before_all() -> void:
    parameterize(["value", "label"], [[1, "admin"], [2, "user"]])

func test_ranked(value: int, label: String) -> void:
    assert_true(value > 0)
    assert_true(label != "")
```

This runs `test_ranked[1-admin]` and `test_ranked[2-user]` as separate
first-class tests: each case gets its own hooks, timeout, retry accounting,
and result entry. Cases are named with pytest-style suffixes --- a single
value renders as its string form, multiple values are hyphen-joined, and
values without a stable string form fall back to the case index.

The GUT legacy convention also works: call `use_parameters(values)` inside
the test body (an array of values, or a dictionary whose entries each
become one case):

```gdscript
func test_item() -> void:
    var item = use_parameters(["alpha", "beta"])
    assert_eq(item, "alpha")
```

Select one case with `--test "test_ranked[2-user]"`; a bare method name
matches every case of that method.

**Suite-level skip:**

`skip_test("reason")` called in `before_all` skips the whole suite: every
test --- and every expanded case --- is reported `skipped` with the reason,
no test body or hook runs, and the suite passes with zero failures. Calling
`skip_test()` inside a test method skips only that test, as before.

**Mocking and stubbing:**

`GdToolsTest` ships a GUT-compatible test-double facility so suites can
isolate collaborators. Doubles exist only in memory: they are runtime-
generated subclasses of the target script and never appear on disk, in
coverage plans, or in coverage reports.

- `double(script)` returns a fresh double of a script (preloaded `Script`
  or a `res://` path). Unstubbed methods return `null` for untyped returns
  or the type's zero value for typed returns, and never run the real
  implementation.
- `partial_double(script)` behaves like the real script; only stubbed
  methods are overridden.
- `stub(double, "method", [args...])` returns a chainable spec:
  `.to_return(value)` replaces the response, `.to_call_super()` invokes the
  parent implementation. Argument matching supports exact values, the
  `"any"` wildcard per argument, and a no-args default fallback; a more
  specific match wins, and the last registered stub wins within a tier.
- Call assertions: `assert_called`, `assert_not_called`,
  `assert_call_count(double, "method", n)`, and
  `assert_call_arguments(double, "method", [args], call_index)` (index `0`
  is the first recorded call, `-1` the most recent).
- Fail-fast validation: stubbing a method the target does not have, or
  doubling a non-script value, fails the test immediately with a diagnostic
  naming the method and the target.
- Doubles and stubs are per-test: every test gets fresh instances, so no
  state leaks between tests.
- Bridge suites (`extends GutTest`) inherit the same facility with
  identical semantics; the preflight scan no longer rejects mocking
  constructs.

```gdscript
extends GdToolsTest

const SUBJECT := preload("res://scripts/inventory.gd")

func test_removing_items_reports_remaining() -> void:
    var inventory = double(SUBJECT)
    stub(inventory, "count").to_return(3)
    inventory.remove("sword")

    assert_call_count(inventory, "remove", 1)
    assert_call_arguments(inventory, "remove", ["sword"])
    assert_eq(inventory.count(), 3)
```

**Scene and resource integration:**

Suites may declare scenes and named resources with a class-level
`INTEGRATION` constant. `gd-tools` reads the declaration through Godot
metadata before any suite is constructed, then runs one process per suite
using the merged metadata:

```gdscript
class_name PlayerSceneSuite

extends GdToolsTest

const INTEGRATION := {
    "scene": "res://scenes/player.tscn",
    "resources": {"balance": "res://data/balance.tres"},
    "mode": "headless",
    "tests": {
        "test_damage_flash": {"scene": "res://scenes/player_hit.tscn"},
        "test_stats_only": {"scene": null, "resources": {"stats": "res://data/stats.tres"}},
    },
}


func test_default_scene_loads() -> void:
    var context := get_test_context()
    var player := context.find_node("Player")
    assert_not_null(player, "Player node missing")
    assert_eq(context.get_integration()["scene"], "res://scenes/player.tscn")


func test_damage_flash() -> void:
    var context := get_test_context()
    assert_not_null(context.find_node("HitFlash"), "HitFlash node missing")


func test_stats_only() -> void:
    var context := get_test_context()
    assert_null(context.get_scene_root(), "this test declares no scene")
    assert_eq(context.get_resource("stats").level, 3)
```

Declaration rules:

- All paths are `res://` paths that must resolve at load time; a missing
  scene or resource is a configuration error and exits `2`.
- `mode` is `headless` (default) or `windowed` and is a suite-level setting
  because one process represents one suite. A `mode` inside a `tests` entry
  is rejected.
- Test entries override suite defaults field by field. Omitted fields are
  inherited, resource maps merge by logical name, and `null` removes an
  inherited scene or resource.
- Unknown fields, invalid modes, and overrides for methods that are not
  `test_*` methods are reported with the suite path and the expected shape.

**Test context API** (`get_test_context()` returns a `GdToolsTestContext`):

| Member | Behavior |
| --- | --- |
| `get_scene_root()` | Root node of the loaded primary scene, or `null` |
| `find_node("Panel/Icon")` | Relative node lookup; records a structured `integration_node` failure when missing |
| `find_nodes("Item*")` | Recursive lookup of nodes whose name contains the text; a trailing `*` is accepted so `Item*` reads as a prefix. Records `integration_node_pattern` when nothing matches |
| `get_resource("balance")` | Named resource lookup; records `integration_resource` on failure |
| `get_integration()` | Effective scene and resources for the current test. `mode` is suite-level and is not part of the per-test metadata |
| `wait_for_signal(sig, timeout)` | Bounded signal wait returning `false` on timeout and recording `integration_signal` |
| `capture_screenshot(path)` | Atomically writes a PNG of the viewport to an absolute path; returns `{"ok", "path", "message"}` |

Failure kinds recorded by the context: `integration_scene` (no primary scene
for this test), `integration_node` (missing or invalid node path),
`integration_node_pattern` (empty, invalid, or unmatched pattern),
`integration_resource` (missing or non-`Resource` value), `integration_signal`
(signal wait timed out), and `integration_context` (no active test for a
context-level operation).

Only no-argument `test_*` methods are discovered and run, so a method declared
as `func test_x(value: int = 1)` is not a runnable test; an `INTEGRATION` entry
targeting it is reported as an unknown test rather than silently accepted.

Integration behavior:

- Resources are loaded by logical name and are never assigned to nodes
  automatically; assign them explicitly in the test.
- The test context is available in `before_each`, the test, and
  `after_each`, so lifecycle hooks can inspect the live scene.
- Each attempt builds a fresh scene, context, and resource set, so retries
  never observe state from a previous attempt, including a resource that a
  previous attempt mutated and kept a reference to.
- Project autoloads behave exactly as they do in production and are never
  replaced by test-only autoloads.
- Order per attempt: metadata validation, resource loading, scene
  instantiation, `before_each`, test, `after_each`, failure evidence, teardown.

**Windowed suites and failure artifacts:**

Declare `"mode": "windowed"` to run a suite with a real display. A windowed
suite requires a display; when the renderer is headless the run fails with
exit `2` and no silent fallback occurs. Failed, timed-out, and errored tests
in a windowed suite capture a screenshot after `after_each` and before
teardown, and the path is reported in the test diagnostics and JUnit XML.
Each failing test writes its own capture, so several failures in one suite
are all retained. A capture that cannot be written turns the attempt into an
infrastructure error, and the original failure message is preserved alongside
the capture error.

Every run publishes its artifacts under `.gd-tools/artifacts/<run_id>/`:

```
.gd-tools/artifacts/<run_id>/
├── .gdtools-run            # written at run start, so a crashed run stays prunable
├── artifacts.json          # machine-readable index of the run
├── preflight/              # manifest, result, and log
└── native/                 # per-suite manifest, result, events, log, screenshots
```

The index is printed at the end of the run and recorded as an
`artifact_index` property on the JUnit `<testsuite>`. It lists only the
artifacts that were actually written, and `screenshots` lists the realized
captures for a suite.

Only the latest run is retained. Older run directories are pruned once the new
index is published, and a directory counts as a run only when it is named the
way this tool names them: it contains `.gdtools-run`, created at the start of
every run, or `artifacts.json`, the published index. `artifacts.json` still
counts so that runs from gd-tools 0.4.x and earlier are pruned rather than
accumulating forever. Retention matches on the name, so avoid placing your own
directory there if it would contain either file.

Everything else under the artifact root is left alone: plain files, symlinks,
and any other directory, including one that happens to contain `native/` or
`preflight/` subdirectories of its own.

**Plan Caching:**

When `--coverage` is used, `gd-tools` caches the coverage plan
(`plan.json`) to skip AST parsing on subsequent runs. The cache is
validated by comparing source file hashes -- any file added, deleted,
or modified invalidates the cache automatically. Use `--no-cache` to
force a full plan regeneration:

```bash
# Bypass the plan cache (useful after switching branches)
gd-tools test --coverage --no-cache
```

Cache hit/miss status is logged when `--verbose` is active.

**Output Format:**

Test results are rendered as a Rich table with columns for Status, Suite,
and Test name. Passing tests show a green ✓; failing tests show a red ✗
with the failure message printed below (indented, including the suite
name and error message). A summary footer line shows pass/fail counts,
and a `[OK]` success message is displayed when all tests pass.

When `--coverage` is used, an inline coverage summary is printed after
the test results showing line and branch coverage rates with color-coded
threshold status (green if meeting threshold, red if below).

When `--show-uncovered` is passed with `--coverage` and coverage is below
100%, per-file Rich panels are printed after the summary line. Each panel
shows the file path as its title and lists uncovered lines (as ranges) and
uncovered branches (with type annotations like `if`, `else`, `loop`,
`match`). Files with full coverage are omitted.

Example panel output:

```
╭───────────────────────────────────────────╮
│ res://scripts/player.gd                  │
│                                          │
│ Uncovered lines: 15-16, 23               │
│ Uncovered branches: 12 (if), 18 (loop)   │
╰───────────────────────────────────────────╯
```

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

When coverage is below 100%, per-file Rich panels are also printed after
the summary table showing uncovered lines (as ranges) and uncovered
branches (with type annotations). Files with full coverage are omitted.

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Coverage summary displayed and meets threshold. |
| 1 | Coverage is below the specified threshold. |
| 2 | Configuration or environment error, or no coverage data found. |

#### 3.7.4 coverage save-baseline

Save the latest coverage run as the diff baseline for
[coverage diff](#374-coverage-diff). The baseline is a single
self-contained JSON document (`.gd-tools/coverage/baseline.json`) that
embeds the instrumentation plan and the coverage data of the run, so it
stays valid even after the branch changes both files. Advisory
metadata (UTC timestamp, git branch and commit when available) is
stamped into the document; it is displayed for context but never
required for the diff computation.

**Usage:**

```bash
gd-tools coverage save-baseline [OPTIONS]
```

**Examples:**

```bash
# Save the latest coverage run as the baseline
gd-tools coverage save-baseline
```

**Output:**

```
Baseline saved to: .gd-tools/coverage/baseline.json
```

Saving again overwrites the previous baseline.

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Baseline saved successfully. |
| 2 | No coverage data found, or the existing data is malformed. Run `gd-tools test --coverage` first. |

#### 3.7.5 coverage diff

Compare current coverage against a saved baseline and report per-file
line and branch deltas — which files improved, regressed, were added,
or removed. This answers the code-review question a single coverage
snapshot cannot: *did this change add or remove coverage?*

**Usage:**

```bash
gd-tools coverage diff --base BASELINE [OPTIONS]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--base` | path | required | Path to a baseline file written by `coverage save-baseline`. |
| `--show-lines` | flag | off | List newly-uncovered line numbers for regressed files. |
| `--report-format` | `text` or `json` | `text` | `text` renders a Rich table; `json` emits deterministic machine-readable output. |
| `--fail-on-regression` | flag | off | Exit with code 1 when any file's line or branch coverage rate is lower than in the baseline. |

**Example output (`text`):**

```
                      Coverage diff vs baseline (on main @ abc1234)
┌─────────────────┬───────────┬───────────┬───────────┬───────────┬───────────┐
│ File            │ Lines     │ Lines     │ Branches  │ Branches  │ Change    │
│                 │ (base)    │ (head)    │ (base)    │ (head)    │           │
├─────────────────┼───────────┼───────────┼───────────┼───────────┼───────────┤
│ res://enemy.gd  │ 3/3 (100%)│ 0/3 (0%)  │ 1/1 (100%)│ 0/1 (0%)  │ -3 lines, │
│ res://player.gd │ 5/5 (100%)│ 5/5 (100%)│ 2/2 (100%)│ 2/2 (100%)│ -         │
│ TOTAL           │ 8/8 (100%)│ 5/8 (62%) │ 3/3 (100%)│ 2/3 (67%) │ -3 lines… │
└─────────────────┴───────────┴───────────┴───────────┴───────────┴───────────┘
```

Improvements are shown in green, regressions in red, and paths in dim.
New files are labeled `new` (with their head metrics only), removed
files `removed` (with their baseline metrics only). With
`--show-lines`, each regressed file is followed by a detail line such
as `res://enemy.gd: newly uncovered lines 3, 5, 8`.

**JSON output shape (`--report-format json`):**

```json
{
  "baseline_meta": {"saved_at": "...", "git_branch": "...", "git_commit": "..."},
  "files": [
    {
      "path": "res://enemy.gd",
      "classification": "regressed",
      "base": {"covered_lines": 3, "total_lines": 3, "line_rate": 1.0,
               "covered_branches": 1, "total_branches": 1, "branch_rate": 1.0},
      "head": {"covered_lines": 0, "total_lines": 3, "line_rate": 0.0,
               "covered_branches": 0, "total_branches": 1, "branch_rate": 0.0},
      "covered_line_delta": -3,
      "line_rate_delta": -1.0,
      "covered_branch_delta": -1,
      "branch_rate_delta": -1.0,
      "newly_uncovered_lines": [3, 5, 8]
    }
  ],
  "totals": {"base": {"covered_lines": 8, "total_lines": 8, "line_rate": 1.0, "...": "..."},
             "head": {"covered_lines": 5, "total_lines": 8, "line_rate": 0.625, "...": "..."}},
  "has_regression": true
}
```

`classification` is one of `improved`, `regressed`, `unchanged`,
`new`, `removed`. `base`/`head` metric objects are `null` for new and
removed files respectively. Files are sorted by path; the output is
deterministic for identical inputs.

**CI usage:** save the baseline on pushes to the main branch, then gate
pull requests against it:

```yaml
# .github/workflows/ci.yml (excerpt)
jobs:
  coverage-baseline:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - run: gd-tools test --coverage
      - run: gd-tools coverage save-baseline
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-baseline
          path: .gd-tools/coverage/baseline.json

  coverage-diff:
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: coverage-baseline
      - run: gd-tools test --coverage
      - run: gd-tools coverage diff --base baseline.json --fail-on-regression
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Diff computed and rendered (no regression, or `--fail-on-regression` not set). |
| 1 | `--fail-on-regression` is set and at least one file regressed. |
| 2 | The baseline or the current coverage data is missing or malformed, or a configuration/environment error occurred. |

#### 3.7.6 Coverage exclusions

Use `# gd-tools: no cover` annotations to exclude specific lines or
blocks from coverage measurement. Excluded lines are removed from the
coverage percentage entirely (they count in neither the covered nor
the total figure), so debug-only code, platform-specific branches, and
other intentionally untestable code no longer dilute your numbers.

**Annotation forms:**

```gdscript
# 1. Line form -- excludes this line only.
if OS.is_debug_build():  # gd-tools: no cover
    _load_debug_tools()

# 2. Block form -- excludes everything from the start line
#    through the end line, inclusive.
# gd-tools: no cover start
func _dev_only_menu():
    _build_debug_menu()
    _hook_debug_shortcuts()
# gd-tools: no cover end

# 3. Function form -- placing the annotation on a `func` line
#    excludes the entire function body.
func _test_helper():  # gd-tools: no cover
    return preload("res://test_helpers.gd")
```

The token must appear in a comment as
`# gd-tools: no cover` (whitespace around the token is flexible; the
optional `start`/`end` suffix selects the block form). Annotations
inside string literals or docstrings are
inert.

**Edge-case semantics:**

- Nesting is not tracked: a `start` inside an open block is ignored
  with a warning, and the outer block governs.
- An unterminated `start` excludes to the end of the file and warns.
- A stray `end` with no open block is ignored and warns.
- An annotation on a blank or comment-only line excludes just that
  line.

All annotation problems are **warnings, not errors**: plan generation
continues, warnings are printed to stderr, and exit codes are
unchanged.

**How exclusions appear in reports:**

- The instrumentation plan records the excluded lines in an
  `excluded_lines` field (machine-readable truth).
- The HTML report renders excluded lines in gray with strikethrough.
- The terminal report appends a compact summary, e.g.
  `Excluded: 12 lines across 3 files`, only when exclusions exist.
- The plan cache is versioned: plans generated before the annotation
  existed are regenerated automatically on the next run.
- LCOV, Cobertura, and coverage-diff outputs are unchanged; excluded
  lines simply never appear in their data.

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

### 3.10 gd-tools completion

Generate a shell completion script for bash, zsh, fish, or PowerShell.

**Usage:**

```bash
gd-tools completion <shell>
```

**Arguments:**

| Argument | Required | Choices | Description |
|---|---|---|---|
| `shell` | yes | `bash`, `zsh`, `fish`, `powershell` | The target shell for the completion script. |

The command prints the completion script to stdout. Redirect the
output to a file or pipe it into `eval` to activate completion in your
shell. See [Section 6 -- Shell Completion](#6-shell-completion) for
detailed per-shell setup instructions.

**Examples:**

```bash
# Print bash completion script
gd-tools completion bash

# Activate bash completion immediately
eval "$(gd-tools completion bash)"

# Save zsh completion to a file
gd-tools completion zsh > ~/.zsh/completions/_gd-tools

# Save fish completion to a file
gd-tools completion fish > ~/.config/fish/completions/gd-tools.fish

# Add PowerShell completion to profile
gd-tools completion powershell | Out-String | Add-Content $PROFILE
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Completion script generated successfully. |
| 2 | Invalid shell argument (not one of `bash`, `zsh`, `fish`, `powershell`). |


### 3.11 Global Verbosity Flags

`gd-tools` provides two global flags that control how much output a
command produces. These flags are placed **before** the subcommand and
apply to all commands.

**Usage:**

```bash
gd-tools [--verbose | --quiet] <command> [command-options]
```

**Flags:**

| Flag | Short | Description |
|---|---|---|
| `--verbose` | `-v` | Show underlying commands (Godot/GUT, gdlint, gdformat) and timing information for each operation. |
| `--quiet` | `-q` | Suppress non-essential output: update checks, info/progress messages, and detailed tables. Only essential results are shown. |

The `--verbose` and `--quiet` flags are mutually exclusive. Using both
together produces a usage error with exit code 2.

When neither flag is provided, the default verbosity level is used,
which matches the existing behavior -- no visible change to output.

#### Verbose Mode (`--verbose` / `-v`)

Verbose mode is designed for debugging and understanding what
`gd-tools` is doing under the hood. When active, the CLI displays:

- **Underlying commands:** The full external command being executed
  (e.g., the complete `godot --headless -s addons/gut/gut_cmdln.gd ...`
  invocation, the file being linted, the file being formatted).
- **Timing information:** Elapsed time for each major operation (test
  run, lint scan, format pass).

```bash
# See the Godot command and timing for a test run
gd-tools --verbose test

# See which files are being linted and how long it takes
gd-tools --verbose lint

# See which files are being formatted and timing
gd-tools --verbose format

# Short flag works the same
gd-tools -v test
```

Example verbose output (lint):

```
Linting: src/player.gd
Linting: src/enemy.gd
Elapsed: 0.12s
src/player.gd:10:1: function-name: Function name BadFunctionName is not valid  [ERROR]
1 errors, 0 warnings, 2 files checked
```

#### Quiet Mode (`--quiet` / `-q`)

Quiet mode is designed for CI pipelines and scripting where only
essential output matters. When active, the CLI suppresses:

- **Update check notifications** (PyPI version check and addon
  staleness warning are skipped entirely).
- **Info/progress messages** (e.g., "No GDScript files found",
  "Running tests...").
- **Init/doctor details** (init shows only `[OK] Initialized`; doctor
  shows only `[OK] All checks passed` or `[FAIL] Some checks failed`).

The following outputs are **always shown** regardless of quiet mode:

- Test pass/fail summaries
- Lint violations
- Coverage reports and threshold results
- Error messages
- Exit codes (unchanged)

```bash
# CI pipeline: minimal output, only failures shown
gd-tools --quiet lint
gd-tools --quiet format --check
gd-tools --quiet test --coverage --min 80

# Quick doctor check: one-line status only
gd-tools --quiet doctor

# Init without detailed summary
gd-tools --quiet init --non-interactive

# Short flag works the same
gd-tools -q lint
```

Example quiet output (doctor, all passing):

```
[OK] All checks passed
```

Example quiet output (doctor, failures):

```
[FAIL] Some checks failed
```

#### Mutual Exclusion

`--verbose` and `--quiet` cannot be used together. If both are
provided, the CLI exits with code 2 and prints an error:

```bash
$ gd-tools --verbose --quiet test
Error: --verbose and --quiet are mutually exclusive.
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Command completed successfully (same as without the flag). |
| 1 | Tool failure (test failures, lint errors, etc.) -- same as without the flag. |
| 2 | `--verbose` and `--quiet` used together, or configuration/environment error. |


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

### 5.5 Native Runtime or Protocol Mismatch

**Symptom:** `gd-tools test` exits `2` with a message mentioning
`protocol version`, or `gd-tools doctor` reports the "Native Test Addon"
check as failing.

**Cause:** The deployed `addons/gd-tools-test/` scripts were written by a
different `gd-tools` version than the one running the command. Python and
Godot exchange a versioned protocol; the current version is `2`, which adds
scene and resource integration metadata. A protocol-v1 payload, malformed
integration metadata, or a partially deployed addon is rejected as a
configuration failure rather than being guessed at.

**Resolution:**

1. Check what is deployed and how it compares:
   ```bash
   cat addons/gd-tools-test/_version.txt
   gd-tools version
   ```
2. Redeploy the managed runtime from the current version:
   ```bash
   gd-tools init --non-interactive
   ```
   `gd-tools init` installs all five managed scripts
   (`gd_tools_test.gd`, `gd_tools_test_runner.gd`, `gd_tools_test_context.gd`,
   `gd_tools_test_preflight.gd`, `gd_tools_native_coverage.gd`), backs up
   locally modified copies into `addons/gd-tools-test/.backups/`, and rewrites
   `_version.txt`.
3. Confirm with `gd-tools doctor` that the "Native Test Addon" check passes.
   A deployed addon that is merely older than the CLI is reported as a
   passing warning, so an outdated `_version.txt` means step 2 is still
   needed even when the check is not failing.

If a windowed suite reports exit `2` with a display or renderer message, the
suite declared `"mode": "windowed"` but the process has no display. Run it on a
machine with a display, or switch the suite back to the headless default.


## 6. Shell Completion

`gd-tools` provides tab completion for commands, subcommands, options,
and flags. Completion scripts are generated by Click's built-in shell
completion infrastructure and cover all `gd-tools` commands statically
(no dynamic value completion such as file paths or config names).

Use `gd-tools completion <shell>` to print the completion script for
your shell, then source it in your shell configuration.

### 6.1 Bash

**Option A -- Eval at shell startup (recommended):**

Add the following line to `~/.bashrc` (or `~/.bash_profile` on macOS):

```bash
eval "$(gd-tools completion bash)"
```

This evaluates the completion script every time a new shell starts. The
script defines a `_gd_tools_completion` function and registers it with
the `complete` builtin for the `gd-tools` command.

**Option B -- Source from a file:**

Save the script to a file and source it:

```bash
gd-tools completion bash > ~/.local/share/bash-completion/completions/gd-tools
```

Bash's completion system automatically loads scripts from
`~/.local/share/bash-completion/completions/` (or
`/etc/bash_completion.d/` on some systems) if they are in the
`bash-completion` `fpath`.

### 6.2 Zsh

**Option A -- Eval at shell startup (recommended):**

Add the following line to `~/.zshrc`:

```bash
eval "$(gd-tools completion zsh)"
```

**Option B -- Save to a directory in `fpath`:**

```bash
# Create the directory if it doesn't exist
mkdir -p ~/.zsh/completions

# Save the completion script
gd-tools completion zsh > ~/.zsh/completions/_gd-tools
```

Then ensure `~/.zsh/completions` is in your `fpath` by adding to
`~/.zshrc` (before `compinit`):

```bash
fpath+=(~/.zsh/completions)
autoload -Uz compinit && compinit
```

### 6.3 Fish

Save the completion script to Fish's completions directory:

```bash
# Create the directory if it doesn't exist
mkdir -p ~/.config/fish/completions

# Save the completion script
gd-tools completion fish > ~/.config/fish/completions/gd-tools.fish
```

Fish automatically loads completion scripts from
`~/.config/fish/completions/`. No additional configuration is needed ---
restart your shell or open a new terminal to activate completion.

### 6.4 PowerShell

Add the completion script to your PowerShell profile:

```powershell
# Generate the script and append it to your profile
gd-tools completion powershell | Out-String | Add-Content $PROFILE
```

If `$PROFILE` does not exist yet, create it first:

```powershell
if (!(Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
```

The script registers a `Register-ArgumentCompleter` for the `gd-tools`
command. Restart your PowerShell session or run `. $PROFILE` to activate
completion.

### 6.5 Alternative -- Click's Environment Variable

Click supports an alternative completion mechanism via the
`_GD_TOOLS_COMPLETE` environment variable. This approach does not
require modifying your shell profile -- instead, the variable tells
Click to emit the completion script when `gd-tools` is invoked.

```bash
# Bash / Zsh
export _GD_TOOLS_COMPLETE=bash_source
eval "$(gd-tools)"

# Fish
set -x _GD_TOOLS_COMPLETE fish_source
gd-tools | source

# PowerShell
$env:_GD_TOOLS_COMPLETE = "powershell_source"
gd-tools | Out-String | Invoke-Expression
```

> **Note:** The env-var approach is intended for advanced users. The
> `gd-tools completion <shell>` command is the recommended method for
> most users as it is simpler and more portable.
