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
7. [Editor Plugin](#7-editor-plugin)
8. [Pre-commit Hooks](#8-pre-commit-hooks)


## 1. Getting Started

### 1.1 Prerequisites

| Requirement | Minimum Version | Notes |
|---|---|---|
| Python | 3.10 | Required for modern type hints and tomllib support. |
| Godot Engine | 4.5 | Must be accessible via PATH or a GODOT_BIN environment variable. |

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

Existing GUT suites cannot run: the compatibility bridge was removed in
v0.6.0 and `gd-tools init` never installs GUT. Migrate legacy suites with
`gd-tools migrate`; see the [migration guide](./gut-migration.md).

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
| `runtime` | string | `"native"` | Test runtime. Only `native` is supported since v0.6.0. |
| `test_dirs` | list of strings | `["test", "tests"]` | Directories scanned for test files. |
| `timeout_seconds` | number | `5.0` | Default native per-test async timeout in seconds. |
| `retries` | integer | `0` | Default native retry count. |
| `parallel` | integer | None | Persistent parallel worker count (1-32) for the native runtime. Omit for sequential execution; `--parallel` overrides this for one invocation. |
| `durations` | integer | None | Number of slowest tests to report after a run (`0` lists every executed test). Omit to disable durations reporting; `--durations` overrides this for one invocation. |
| `tags` | list of strings | `[]` | Native class-level tag filters; an empty list matches all tags. |
| `prefix` | string | `"test_"` | Filename prefix for test scripts (GUT convention). |
| `suffix` | string | `".gd"` | Filename suffix for test scripts. |

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
| `format` | string | `"html"` | `html`, `lcov`, `cobertura`, `text`, `json`, `github-actions` | Report output format. |
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

**Cleanup of Undeployed Files:**

`init` also removes bundled files it no longer deploys. When an upgraded
gd-tools version stops shipping a file that an older version deployed (for
example, the legacy GUT hook scripts `pre_run_hook.gd` and
`post_run_hook.gd`, removed with the GUT compatibility bridge in v0.6.0),
each stale copy found on the project is backed up to
`addons/gd-tools-coverage/.backups/<name>.gd.bak`, deleted, and a notice is
printed. Files you created yourself under `addons/` are never touched.

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
| 4 | Legacy GUT | warning | Informational advisory: detects `addons/gut`, `.gutconfig.json`, and `extends GutTest` suites. Always passes; when artifacts are found they are reported as migration advice pointing at `gd-tools migrate`. |
| 5 | Coverage Addon | warning | All `gd-tools-coverage` addon files are present and not stale. |
| 6 | Editor Plugin | warning | The editor plugin is deployed (enable it in Godot's Project Settings → Plugins). |
| 7 | gd-tools.toml | critical | `gd-tools.toml` exists and is valid TOML. |
| 8 | GD Toolkit | critical | `gdlint` and `gdformat` CLI tools are installed. |
| 9 | Autoload | warning | `_GDTCoverage` is legacy; native coverage does not use an autoload. |

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

Run GDScript tests using the bundled native runtime. Suites must extend
`GdToolsTest`; `GutTest` suites are rejected with exit 2 and migration
guidance -- the GUT compatibility bridge was removed in v0.6.0 (run
`gd-tools migrate` or see the [migration guide](./gut-migration.md)).

**Usage:**

```bash
gd-tools test [PATHS]... [OPTIONS]
```

**Arguments:**

| Argument | Required | Default | Description |
|---|---|---|---|
| `paths` | no | Config `[test].test_dirs` | One or more test files or directories to scan. File paths are selected exactly; directories are scanned recursively. |
| `--runtime` | choice | Config `[test].runtime` (`native`) | Select the test runtime (default: native). `gut` was removed in v0.6.0 and is rejected with exit 2. |

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--coverage` | flag | `false` | Generate a coverage report during the test run. |
| `--min` | integer | None | Minimum coverage percentage threshold. Fails if coverage is below this value. Requires `--coverage`; pass both together. |
| `--min-branch` | integer | None | Minimum branch coverage threshold. Fails (exit 1) if branch coverage is below this value. Requires `--coverage`; ternary arms are measured independently, so an uncovered arm fails this gate. Projects with zero branch points are exempt (pass with a note). |
| `--suite` | string | None | Run only the specified test suite. |
| `--test` | string | None | Run only the specified test. |
| `--tag` | string, repeatable | Config `[test].tags` | Run native suites matching a class-level tag. |
| `--test-timeout` | number | Config `[test].timeout_seconds` | Per-test timeout in seconds for native tests. |
| `--parallel` | integer | Config `[test].parallel` | Run suites with up to N concurrent workers (1-32). Bare `--parallel` defaults to 4 workers — note it overrides a configured value even if that value is higher. Omit for sequential execution. |
| `--durations` | integer | Config `[test].durations` | Report the N slowest tests after the run in a "Slowest Tests" table (pass, fail, and skip rows, sorted slowest-first). Bare `--durations` defaults to 10; `--durations 0` lists every executed test. Omit to disable. |
| `--junit-xml` | string | None | Path to write a JUnit XML report. |
| `--no-exit-code` | flag | `false` | Do not exit with non-zero on test failure. |
| `--timeout` | integer | None | Godot import and per-suite process timeout in seconds. |
| `--show-uncovered` | flag | `false` | Show uncovered lines and branches as Rich panels when coverage is below 100%. Requires `--coverage`; pass both together. |
| `--no-cache` | flag | `false` | Force plan regeneration, bypassing the coverage plan cache. Only effective with `--coverage`; has no effect without it. |
| `--changed` | flag | `false` | Run only the suites mapped from git-changed files (working tree vs `HEAD`). A change that maps to no suite falls back to the full suite with a notice; an empty change set exits 0 without launching Godot. |
| `--base` | string | None | With `--changed`: diff committed changes from `merge-base(<ref>, HEAD)` instead of the working tree (the form for pull-request CI). Requires `--changed`; incompatible with `--watch` (exit 2). |

**Examples:**

```bash
# Run all tests
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

# Run only suites mapped from git-changed files (working tree vs HEAD)
gd-tools test --changed

# PR/CI: run suites mapped from committed changes since branching from main
gd-tools test --changed --base main

# Changed-file selection composes with the other flags
gd-tools test --changed --parallel 4 --coverage --min 80

# Run exactly one native test file
gd-tools test tests/unit/test_player.gd

# Accept new snapshot output after an intentional change
gd-tools test --snapshot-update
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
  A script error that aborts a test body mid-run (for example a call to a
  nonexistent method) is reported as `error` for that test rather than a
  false `passed`.
- Async tests may await process frames, physics frames, timers, and signals.
  The default per-test timeout is `5.0` seconds (`[test].timeout_seconds`);
  `--test-timeout` overrides it for one invocation, while `--timeout` limits
  Godot import and suite processes. Failed or timed-out tests are retried
  according to `[test].retries`.
- Class-level tags can be configured with `[test].tags` or selected with
  repeatable `--tag` options. Explicit file paths are never broadened to
  sibling suites.
- If discovery finds a suite extending `GutTest`, it fails with exit 2 and
  migration guidance (the compatibility bridge was removed in v0.6.0); if no
  suites are found, the error explains that suites must extend `GdToolsTest`.
- Opt-in parallel execution: `--parallel N` or `[test].parallel` dispatches
  suites to at most N concurrent Godot processes. Results, JUnit XML, and
  merged coverage are identical to a sequential run; a failed, timed-out, or
  crashed suite never cancels its neighbors. Ctrl+C (or SIGTERM) kills every
  in-flight process tree and marks the artifact index `incomplete`
  (exit `130`) — in both sequential and parallel runs.
- The runtime provides an editor UI through the gd-tools editor plugin
  (see [Editor Plugin](#7-editor-plugin)).

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
  `.to_return(value)` replaces the response, `.to_return_seq([values])`
  answers with the values in registration order and repeats the final
  value once exhausted, `.to_call_super()` invokes the parent
  implementation, and `.to_fail(message)` records a test failure with the
  given message at call time (the call still yields the return type's
  zero value, so the code under test keeps executing). Argument matching
  supports exact values, the
  `"any"` wildcard per argument, and a no-args default fallback; a more
  specific match wins, and the last registered stub wins within a tier.
- Call assertions: `assert_called`, `assert_not_called`,
  `assert_call_count(double, "method", n)`, and
  `assert_call_arguments(double, "method", [args], call_index)` (index `0`
  is the first recorded call, `-1` the most recent; `"any"` elements are
  per-argument wildcards). `assert_call_order(double, ["a", "b"])`
  verifies relative order as a subsequence: every listed method must
  appear in the recorded order, and calls to unlisted methods are
  ignored.
- Property-value assertions: `assert_property_is(target, "prop", expected)`
  reads the current value via `get()` and works on any Object -- real
  instances and doubles alike. GDScript has no property-access
  interception for declared members, so property checks assert values
  rather than access events.
- Rich failure diagnostics: spy failures name the method or property,
  show expected versus actual values with per-argument diffs, and list
  recorded calls (bounded) so the mismatch is visible without a debugger.
- Fail-fast validation: stubbing a method the target does not have, or
  doubling a non-script value, fails the test immediately with a diagnostic
  naming the method and the target.
- Doubles and stubs are per-test: every test gets fresh instances, so no
  state leaks between tests.

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


func test_first_two_reads_come_from_the_sequence() -> void:
    var inventory = double(SUBJECT)
    # The last value repeats once the sequence runs out.
    stub(inventory, "count").to_return_seq([3, 2])
    assert_eq(inventory.count(), 3)
    assert_eq(inventory.count(), 2)
    assert_eq(inventory.count(), 2)


func test_calls_happened_in_the_expected_order() -> void:
    var inventory = partial_double(SUBJECT)
    inventory.remove("sword")
    inventory.add("shield")

    # Subsequence check: other calls in between are ignored.
    assert_call_order(inventory, ["remove", "add"])


func test_state_matches_after_the_call() -> void:
    # Property-value assertions work on doubles and real objects alike.
    var inventory = partial_double(SUBJECT)
    inventory.add("gem")
    assert_property_is(inventory, "items", ["gem"])
```

**Signal assertions:**

`watch_signals(obj)` starts recording every emission of every declared
signal on any Object - Nodes, RefCounteds, and doubles alike. Assertions
read the recording; the watch auto-resets between tests.

- `watch_signals(obj)` must be called before the emissions you want to
  assert on; asserting against an unwatched object fails the test with
  guidance pointing at `watch_signals`.
- `assert_signal_emitted(obj, "signal")` and
  `assert_signal_not_emitted(obj, "signal")` assert on any emission count
  other than the stated one.
- `assert_signal_emit_count(obj, "signal", n)` asserts the exact count.
- `assert_signal_emitted_with_args(obj, "signal", [args])` passes when any
  recorded emission matches element-wise; `"any"` is a per-element
  wildcard. Diagnostics list every captured emission.
- `await assert_signal_emitted_after(sig, timeout_seconds := 5.0)` awaits
  the emission and fails with a timeout diagnostic if it does not arrive.

```gdscript
extends GdToolsTest

signal health_changed(new_value)

func test_health_change_is_reported() -> void:
    watch_signals(self)
    health_changed.emit(2)
    assert_signal_emitted(self, "health_changed")
    assert_signal_emitted_with_args(self, "health_changed", [2])

func test_health_change_arrives_within_budget() -> void:
    _heal_after(2)
    await assert_signal_emitted_after(health_changed, 5.0)

func _heal_after(frames: int) -> void:
    for index in frames:
        await get_tree().process_frame
    health_changed.emit(2)
```

**Snapshot assertions:**

`assert_snapshot(value, name := "")` compares the rendered value against a
stored snapshot file under `.gd-tools/snapshots/`. The first sighting writes
the snapshot and the test passes; later runs compare and fail with a unified
diff when the rendered output differs from the stored file.

- `name` is optional; without it snapshots are auto-named `<test>_1`,
  `<test>_2`, ... in call order, so one test can take several snapshots.
- Serialization is deterministic: dictionary keys are sorted, script-object
  properties are dumped recursively, Nodes render as an indented tree with
  paths and class names, and cycles render as `<ref>` markers instead of
  recursing.
- Snapshot files carry a `# gd-tools snapshot v1` header naming the format
  version, suite, test, and snapshot name -- commit them and review changes
  like any other test expectation.
- `gd-tools test --snapshot-update` rewrites mismatched snapshots with the
  freshly rendered output instead of failing their tests. Use it to accept
  intentional changes; it is CI-safe and never prompts.
- The run summary prints snapshot counts (written / updated / matched /
  failed) and lists obsolete snapshots -- stored files whose owning test no
  longer ran. Prune obsolete files with `gd-tools clean --snapshots`.

```gdscript
extends GdToolsTest

const HUD := preload("res://scripts/hud.gd")

func test_hud_renders_expected_layout() -> void:
    var hud := HUD.new()
    assert_snapshot(hud.build_layout(), "layout")
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
| `--report-format` | choice | `text` | Output format: `text`, `json`, or `github-actions`. |
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
| `--report-format` | choice | Config `[coverage].format` | Output format for the report: `text`, `html`, `lcov`, `cobertura`, `json`, or `github-actions`. Invalid values fail fast with a usage error. |
| `--output-dir` | string | Config `[coverage].output_dir` | Directory to write the report to. |

> **Note:** `--format` remains as a hidden backwards-compatible alias
> for `--report-format` on this command. Supplying both is an error.
> Prefer `--report-format`, which is the canonical flag across all
> `coverage` subcommands (`report`, `run`, `diff`).

**Examples:**

```bash
# Generate an HTML report (uses config default)
gd-tools coverage report

# Generate an LCOV report
gd-tools coverage report --report-format lcov

# Emit a machine-readable JSON report
gd-tools coverage report --report-format json

# Write report to a custom directory
gd-tools coverage report --report-format html --output-dir reports/coverage
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
| `--min-branch` | integer | None | Minimum branch coverage threshold. Exits with code 1 if branch coverage is below this value. Projects with zero branch points are exempt (pass with a note). |

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

#### 3.7.7 coverage run

Collect coverage during a **manual playtest session**. Launches the game
windowed (not headless) with the coverage tracker activated in playtest
mode, lets you play normally, and produces the same reports as a test
coverage run when the session ends.

**Usage:**

```bash
gd-tools coverage run [OPTIONS]
```

**Flags:**

| Flag | Type | Default | Description |
|---|---|---|---|
| `--scene` | string | Project's `run/main_scene` from `project.godot` | Scene to launch for the playtest session. |
| `--timeout` | int | None (wait for manual close) | Automatically close the game after N seconds. Useful for scripted/automated playtest sessions. |
| `--min` | int | None | Exit 1 when line coverage falls below this percentage. |
| `--min-branch` | int | None | Exit 1 when branch coverage falls below this percentage. Projects with zero branch points are exempt (pass with a note). |
| `--report-format` | string | Config `[coverage].format` | Report format (`text`, `html`, `lcov`, `cobertura`, `json`, `github-actions`). |

**Examples:**

```bash
# Play the game manually; coverage is reported when you close the window
gd-tools coverage run

# Launch a specific scene instead of the main scene
gd-tools coverage run --scene res://scenes/level1.tscn

# Automated session: auto-close after 60 seconds
gd-tools coverage run --timeout 60

# Gate the session result like any other coverage run
gd-tools coverage run --min 50

# Also require 80% branch coverage
gd-tools coverage run --min 80 --min-branch 80

# Produce an HTML report of the session
gd-tools coverage run --report-format html
```

**How it works:**

- A full-project coverage plan is generated (same plan as test
  coverage, honoring `# gd-tools: no cover` annotations and the
  `[coverage]` includes/excludes in `gd-tools.toml`).
- The game is launched windowed with the coverage addon's tracker in
  playtest mode (`GD_TOOLS_COVERAGE_PLAYTEST=1`).
- Hits are flushed to disk periodically (every 5 seconds, or
  `--timeout / 2` when `--timeout` is set) and again when the game
  exits, so data survives a crash: the report is built from the last
  periodic snapshot.
- After the session, the summary table and threshold footer print and
  the report is written to `[coverage].output_dir` -- reuse
  `coverage show`, `coverage report`, `coverage save-baseline`, and
  `coverage diff` on the result as usual.

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Session completed and the report was generated. |
| 1 | `--min` threshold not met. |
| 2 | Configuration error, invalid scene, missing project, launch failure, or no coverage data produced. |

**Requires:** the coverage addon installed (`gd-tools init`) with the
`_GDTCoverage` autoload registered. If the game crashes, a warning
notes that partial data from the last periodic snapshot was reported.

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
| gdtoolkit | The installed `gdtoolkit` package version (provides `gdlint` and `gdformat`). |
| Python | The running Python interpreter version. |

When a component is not found, the table displays "not detected" for
Godot and "not installed" for gdtoolkit. In JSON output, missing
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


### 3.11 gd-tools clean

Remove generated artifacts under `.gd-tools/`. With no flags, the command
prints an inventory of what exists (with sizes) and a hint — it deletes
nothing, so it is safe to run anywhere, including CI.

**Usage:**

```bash
gd-tools clean [flags]
```

**Options:**

| Flag | Target | Description |
|---|---|---|
| `--coverage` | `.gd-tools/coverage` | Remove the coverage output directory, including the plan cache (`plan.json`) and `baseline.json`. |
| `--artifacts` | `.gd-tools/artifacts` | Remove native test artifacts (per-run diagnostics, JUnit XML, screenshots). |
| `--baselines` | `.gd-tools/coverage/baseline.json` | Remove only the saved coverage baseline. |
| `--cache` | `.gd-tools/native` | Remove the native worker scratch directory. |
| `--all` | all of the above | Remove every target directory (overrides individual flags). |
| `--dry-run` | — | Report what would be removed, with sizes, without deleting anything. |

`--dry-run` composes with any selection, including `--all`. Overlapping
selections are handled gracefully: `--baselines` is subsumed by
`--coverage`, and explicit flags are subsumed by `--all` (the summary
counts each byte exactly once).

**Never touched:** the `addons/` tree (including `.backups/` copies made
by `gd-tools init`), `gd-tools.toml`, `.gutconfig.json`, and the user-level
cache in your home directory. `clean` only removes the fixed targets above
under the project's `.gd-tools/` directory.

> **Note:** `clean` targets the default coverage location
> (`.gd-tools/coverage`). If you moved the coverage output via
> `[coverage].output_dir` in `gd-tools.toml`, `--coverage` will not match
> it; remove the custom directory manually.

**Examples:**

```bash
# See what gd-tools artifacts exist and their sizes (deletes nothing)
gd-tools clean

# Preview what --all would remove
gd-tools clean --all --dry-run

# Remove only coverage output
gd-tools clean --coverage

# Remove stored test snapshots
gd-tools clean --snapshots

# Full reset of generated artifacts
gd-tools clean --all
```

**Exit Codes:**

| Code | Condition |
|---|---|
| 0 | Targets removed, nothing to remove, dry run, or inventory. |
| 2 | One or more targets could not be removed (the failing path is printed). |


### 3.12 Global Verbosity Flags

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
| `--verbose` | `-v` | Show underlying commands (Godot, gdlint, gdformat) and timing information for each operation. |
| `--quiet` | `-q` | Suppress non-essential output: update checks, info/progress messages, and detailed tables. Only essential results are shown. |

The `--verbose` and `--quiet` flags are mutually exclusive. Using both
together produces a usage error with exit code 2.

When neither flag is provided, the default verbosity level is used,
which matches the existing behavior -- no visible change to output.

#### Verbose Mode (`--verbose` / `-v`)

Verbose mode is designed for debugging and understanding what
`gd-tools` is doing under the hood. When active, the CLI displays:

- **Underlying commands:** The full external command being executed
  (e.g., the complete Godot process invocation for a test run, the
  file being linted, the file being formatted).
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

### 4.5 GitHub Actions Annotations

The `github-actions` report format emits
[workflow log commands](https://docs.github.com/en/actions/reference/workflow-commands-for-github-actions)
so lint violations and coverage shortfalls show up as inline
annotations on pull requests instead of plain log text. No extra
action is needed --- GitHub picks annotation lines up from the step
log automatically.

**Lint annotations.** Every violation becomes an `::error`
annotation pointing at the offending file and position:

```bash
gd-tools lint --report-format github-actions
```

```text
::error file=src/player.gd,line=42,col=1,title=GD3000::unused variable 'x'
```

**Coverage annotations.** Configure a threshold with
`[coverage].min_percent` and use the `github-actions` format. One
`::warning` is emitted per file below the threshold:

```toml
[coverage]
min_percent = 80
format = "github-actions"
```

```text
::warning file=src/enemy.gd::Coverage 66.7%25 below minimum 80%25
```

When the overall coverage gate fails (via `gd-tools coverage run`),
a summary `::error` is emitted before the per-file warnings:

```text
::error title=Coverage gate::Total coverage 78.0%25 is below minimum 80%25
```

> Note: `%` characters in annotation text are escaped as `%25` per
> the workflow log-command spec; GitHub renders them as `%` in the
> annotation UI.

**Example workflow steps:**

```yaml
- name: Lint
  run: gd-tools lint --report-format github-actions

- name: Test with coverage annotations
  run: gd-tools coverage run --report-format github-actions
```

> Notes:
>
> - `lint --report-format github-actions` still exits 1 when
>   violations are found, and all coverage exit codes are unchanged.
> - `gd-tools coverage report --report-format github-actions` emits
>   per-file warnings only (informational, exit 0); the failing
>   `::error` summary comes from `coverage run`, which enforces the
>   gate.


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

### 5.2 Legacy GUT Artifacts Detected

**Symptom:** Doctor check "Legacy GUT" reports a warning.

**Cause:** The project contains legacy GUT artifacts (`addons/gut/`,
`.gutconfig.json`, or suites that `extend GutTest`). Since the v0.6.0
bridge removal these artifacts are unused by gd-tools and harmless, but
`GutTest` suites will not run. GUT is never required by gd-tools.

**Resolution:**

1. Migrate `GutTest` suites with `gd-tools migrate`; see the
   [migration guide](./gut-migration.md) to move them onto `GdToolsTest`.
2. Optionally remove `addons/gut/` and `.gutconfig.json` once migrated.
3. Re-run `gd-tools doctor` to confirm the warning is gone.

### 5.3 Godot Version Mismatch

**Symptom:** Doctor check "Godot Version" fails.

**Cause:** The installed Godot version is below 4.5.0, which gd-tools
requires.

**Resolution:**

1. Verify your Godot version: `godot --version`.
2. If below 4.5.0, upgrade Godot from
   [godotengine.org](https://godotengine.org).
3. Re-run `gd-tools doctor` to confirm detection.

Leftover GUT artifacts (`addons/gut/`, `.gutconfig.json`, `extends GutTest`
suites) are reported by the doctor's informational Legacy GUT advisory
(see section 5.2); no gd-tools runtime uses the GUT addon.

### 5.4 Coverage Not Generating

**Symptom:** `gd-tools test --coverage` runs tests but no coverage
report appears in `.gd-tools/coverage/`.

**Cause:** The coverage addon is not installed, or the coverage plan is
empty.

**Resolution:**

1. Run `gd-tools doctor` and verify the Coverage Addon check passes.
2. If it fails, run `gd-tools init` to reinstall the coverage components.
3. Re-run the coverage test:
   ```bash
   gd-tools test --coverage
   ```

Native coverage does not use the `_GDTCoverage` autoload or
`.gutconfig.json` hook scripts; those belong to the legacy GUT-hook path
and only matter if you deployed them explicitly.

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


## 7. Editor Plugin

The gd-tools editor plugin brings test running and coverage inspection
directly into the Godot editor — no terminal or context switch needed.

### 7.1 Deployment and Enabling

Run `gd-tools init` in your project root. The plugin addon is deployed
to `addons/gd-tools-editor/` alongside the test and coverage addons.

Then enable it once in Godot:

1. Open your project in Godot (4.5 or newer).
2. Project → Project Settings → Plugins.
3. Enable the **gd-tools** plugin.

The **gd-tools** dock appears in the editor's right-hand panel.

### 7.2 The Dock Panel

The dock has two buttons and a results area:

- **Run Tests** — launches `gd-tools test` as a background process.
  Buttons are disabled while a run is in flight; clicking again has no
  effect until the run finishes. When it completes, the results area
  shows pass/fail/skip counts, total duration, every failed test with
  its assertion message, and the artifact directory
  (`.gd-tools/artifacts/<run_id>/`) for full details.
- **Run Coverage** — launches `gd-tools test --coverage`. Results
  include the same test summary plus a coverage line
  (`lines X%, branches Y%`), and the script-editor heatmap refreshes
  automatically when the run finishes.

If the `gd-tools` command is not found (not installed or not on
`PATH`), the dock shows the exact install hint
(`pip install gd-tools-cli`) and re-enables the buttons.

### 7.3 Coverage Heatmap

After a coverage run, gd-tools colors the lines of the script you are
editing in the script editor:

| Color | Meaning |
|-------|---------|
| Green | Line executed during the test run |
| Red | Line never executed |
| Yellow | Branch point that executed but only partially |

The overlay loads automatically when the editor opens (if coverage data
exists) and refreshes after each dock coverage run. If you edit a file
after the coverage run, its colors turn muted (dimmed) — the overlay
never shows stale data as fresh, and never clears it silently. Run
coverage again to refresh.

Files with more than 5000 planned coverage lines are skipped by the
overlay to keep the editor responsive.

### 7.4 Troubleshooting

- **Dock does not appear** — make sure the addon was deployed
  (re-run `gd-tools init`) and the plugin is enabled in Project
  Settings → Plugins.
- **"gd-tools not found"** — install the CLI
  (`pip install gd-tools-cli`), make sure the `gd-tools` script is on
  your `PATH`, and restart the Godot editor.
- **Overlay does not appear** — run coverage once from the dock (or
  `gd-tools test --coverage` in a terminal); data lives in
  `.gd-tools/coverage/`.
- **Colors look dimmed** — the source file changed after the coverage
  run; re-run coverage to refresh.
- **Godot version caveats** — the plugin targets the Godot editor API
  for 4.5+ and is verified against 4.5, 4.6, and 4.7 per the CI
  compatibility matrix. Editor UI behaviors that depend on the
  `CodeEdit`/`ScriptEditor` API may differ slightly between editor
  versions; see the track's manual testing checklist for the
  per-version caveats.

---

## 8. Pre-commit Hooks

The `gd-tools install-hooks` command wires gd-tools into the
[pre-commit](https://pre-commit.com) framework so your format check, lint,
and test suite run automatically on every commit.

### 8.1 Running the Installer

```bash
gd-tools install-hooks
```

Interactive by default: the installer asks you to confirm each hook.

| Prompt | Default | Hook entry |
|---|---|---|
| Install the format hook? | yes | `gd-tools format --check` |
| Install the lint hook? | yes | `gd-tools lint` |
| Install the test hook? | no | `gd-tools test` |

### 8.2 Generated Files

Two files are produced in the project root:

1. **`.pre-commit-hooks.yaml`** - hook metadata for the gd-tools local
   repository (ids, names, entries, `language: system`, and
   `files: \.gd$` filters so only GDScript files trigger the fast hooks).
2. **`.pre-commit-config.yaml`** - a `repos: local:` block referencing the
   three hooks:

```yaml
repos:
- repo: local
  hooks:
  - id: gd-tools-format
    name: gd-tools format --check
    entry: gd-tools format --check
    language: system
    files: \.gd$
  - id: gd-tools-lint
    name: gd-tools lint
    entry: gd-tools lint
    language: system
    files: \.gd$
  - id: gd-tools-test
    name: gd-tools test
    entry: gd-tools test
    language: system
    pass_filenames: false
```

The test hook runs the whole suite via plain `gd-tools test` - any
`[test]` configuration (including `min_coverage`) in `gd-tools.toml`
applies as usual.

### 8.3 Merge Behavior on Re-runs

Re-running `install-hooks` is safe and idempotent:

- gd-tools entries are matched **by id** (`gd-tools-format`,
  `gd-tools-lint`, `gd-tools-test`); drifted entries are corrected in
  place and missing ones are added.
- Foreign hooks (your own or from other repositories) are never touched.
- Previously installed hooks that you deselect are **kept** and reported
  as `Present but not selected`; remove them manually if unwanted.

### 8.4 Non-Interactive and CI Usage

| Invocation | Result |
|---|---|
| `gd-tools install-hooks --non-interactive` | Installs the default pair (format + lint) without prompting. |
| `gd-tools install-hooks --all` | Installs all three hooks. |
| `gd-tools install-hooks --hooks format,lint` | Installs exactly the listed hooks. |
| `gd-tools install-hooks --hooks` (empty) | Nothing to do; exits 1. |

Without a TTY (e.g. in a CI step or piped shell), the installer never
prompts and falls back to the default pair unless `--all` or `--hooks`
is given.

Exit codes: `0` hooks installed or updated; `1` nothing to do (e.g. an
empty selection); `2` config or environment error (bad project root,
malformed `.pre-commit-config.yaml`).
