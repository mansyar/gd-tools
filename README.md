# gd-tools

A modern development workflow CLI for GDScript projects in Godot 4.5+.

[![CI](https://github.com/mansyar/gd-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/mansyar/gd-tools/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/mansyar/gd-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/mansyar/gd-tools)
[![PyPI version](https://img.shields.io/pypi/v/gd-tools-cli.svg)](https://pypi.org/project/gd-tools-cli/)
[![Python versions](https://img.shields.io/pypi/pyversions/gd-tools-cli.svg)](https://pypi.org/project/gd-tools-cli/)
[![Godot version](https://img.shields.io/badge/Godot-4.5%2B-blue.svg)](https://godotengine.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Overview

`gd-tools` brings professional development tooling to GDScript -- test, lint,
format, and code coverage in a single CLI. It wraps gdtoolkit for linting and
formatting, runs its own Godot-native test runtime, and fills the remaining
gap with a custom hybrid coverage system -- production-quality line and branch
coverage for GDScript that no existing tool provides.

Tests are written against `GdToolsTest`, a native GDScript base class that runs
inside your Godot project, so a test can touch the real scene tree, await real
signals, and assert on real engine objects without leaving the engine. Existing
suites that `extend GutTest` are no longer runnable -- the GUT compatibility
bridge was removed in v0.6.0; run `gd-tools migrate` to move them onto
`GdToolsTest`.

One install, one config, one mental model.

## 2. Features

| Feature | Description |
|---------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. Consistent terminal output with colored markers and summary footers across all commands. |
| **Native test runtime** | Tests extend `GdToolsTest` and run inside Godot itself. Scene and resource integration tests reach the real scene tree through an explicit context object rather than a proxy. Doubles, partial doubles, and stubbing isolate collaborators; spy assertions cover calls, argument wildcards, call order, and property values. |
| **Snapshot testing** | `assert_snapshot(value)` pins rendered values -- including object property dumps and node trees -- against versioned, diffable `.snap` files. First run writes and passes; mismatches fail with a unified diff, and `--snapshot-update` accepts the new output. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute -- native test and coverage addons deployed, configs generated. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript -- HTML, LCOV, Cobertura, and JSON reports, plus GitHub Actions annotations that surface failures inline on pull requests. Independent line (`--min`) and branch (`--min-branch`) gates. `# gd-tools: no cover` annotations exclude debug-only code from the numbers. `coverage run` collects coverage during manual playtest sessions, not just automated tests. |
| **CI/CD friendly** | Exit codes, `--check` flags, machine-readable output (JSON, JUnit XML, LCOV, Cobertura), and GitHub Actions annotations for lint violations and coverage gates. No interactive prompts in CI mode. |
| **Standalone compatibility** | gdlint and gdformat continue to work if invoked directly. `gd-tools` is a layer on top, not a lock-in. |

## 3. Installation

```bash
pip install gd-tools-cli
```

`gd-tools` requires Python 3.10+ and a Godot 4.5+ binary on your system.
The Godot binary is auto-detected from configuration, environment variables
(`GODOT_BIN`, `GODOT4_BIN`, `GODOT_PATH`), `PATH`, or common install locations.

## 4. Quick Start

```bash
# 1. Install
pip install gd-tools-cli

# 2. Bootstrap your Godot project
cd your-godot-project
gd-tools init

# 3. Run your tests
gd-tools test

# 4. Run tests with coverage
gd-tools test --coverage --min 80

# 5. Show uncovered lines and branches when coverage is below 100%
gd-tools test --coverage --show-uncovered

# 6. Force plan regeneration, bypassing the coverage plan cache
gd-tools test --coverage --no-cache
```

`gd-tools init` deploys the native test addon and the coverage addon, generates
`gd-tools.toml`, `gdlintrc`, and `gdformatrc`, and creates the `.gd-tools/`
directory. The command is idempotent -- safe to re-run. If you've modified
coverage addon files, they are automatically backed up to
`addons/gd-tools-coverage/.backups/` before being overwritten.

The GUT compatibility bridge was removed in v0.6.0: suites extending `GutTest`
are no longer runnable -- `gd-tools test` rejects them with exit 2 and
migration guidance. Run `gd-tools migrate` and see the
[migration guide](./docs/gut-migration.md) for the steps to move fully onto
`GdToolsTest`.

A test suite is any class extending `GdToolsTest`:

```gdscript
extends GdToolsTest

func test_health_starts_at_full() -> void:
    assert_eq(health.current(), 100)
```

## 5. CLI Command Summary

| Command | Description |
|---------|-------------|
| `gd-tools init` | Bootstrap a Godot project -- deploy the native test and coverage addons, generate configs. |
| `gd-tools doctor` | Diagnose the development environment -- Godot, native test addon, coverage addon, tooling; reports legacy GUT artifacts as migration advice. |
| `gd-tools test` | Run tests with optional coverage, thresholds, and JUnit XML output. Suites must extend `GdToolsTest`; `GutTest` suites are rejected with exit 2 and migration guidance. Accepts optional path arguments to override configured test directories. `--parallel N` runs suites through a bounded worker pool. `--changed` runs only the suites mapped from git-changed files. `--watch` re-runs affected suites on `.gd` file changes. `--durations N` reports the N slowest tests after the run. `--exitfirst` (`-x`) stops dispatching new suites after the first failing suite; `--shard K/N` runs one round-robin shard for CI matrix splitting. Every run publishes a machine-readable artifact index under `.gd-tools/artifacts/<run_id>/`. |
| `gd-tools migrate` | Guided GUT-to-native migration. Default: read-only report with unsupported-construct inventory and proposed base-class rewrites. `--apply` renames clean suites to `GdToolsTest` and translates `.gutconfig.json` into `gd-tools.toml` (merge, never clobber). `--config-only` translates config only. |
| `gd-tools lint` | Lint GDScript files using gdlint with text, JSON, or GitHub Actions annotation output. Accepts one or more file or directory paths. |
| `gd-tools format` | Format GDScript files using gdformat with check and diff modes. Accepts one or more file or directory paths. |
| `gd-tools coverage` | Coverage subcommands -- `report`, `merge`, `show`, `save-baseline`, `diff` (baseline comparison for CI regression gates), and `run` (collect coverage during a manual playtest session). |
| `gd-tools config` | Configuration management -- `show` (display resolved config), `validate` (check config validity), `schema` (print or write the JSON Schema for `gd-tools.toml`). |
| `gd-tools version` | Display versions of all gd-tools components (gd-tools, Godot, gdtoolkit, Python) in a table or JSON. |
| `gd-tools completion` | Generate shell completion scripts for bash, zsh, fish, or PowerShell. |

### Selecting and Filtering Tests

```bash
gd-tools test                              # every discovered suite
gd-tools test --suite PlayerTests          # one suite, by class name
gd-tools test --test test_takes_damage     # one test method
gd-tools test --tag smoke                  # suites with that class-level tag
gd-tools test --test-timeout 30            # per-test timeout, in seconds
gd-tools test --parallel 4                 # run suites with 4 concurrent workers
gd-tools test --durations 10               # report the 10 slowest tests
gd-tools test --changed                    # only suites mapped from git-changed files
gd-tools test --changed --base main        # PR/CI mode: diff from merge-base with main
gd-tools test --exitfirst                  # stop dispatching after the first failing suite
gd-tools test --shard 2/4                  # CI sharding: run suite shard 2 of 4
```

`--tag` is repeatable, and `--test-timeout` (per test) is separate from
`--timeout` (per suite process). `--parallel` dispatches suites to a bounded
worker pool (1-32 workers; bare `--parallel` means 4) while keeping results,
JUnit XML, and merged coverage identical to a sequential run. Persist the
choice with `parallel = 4` under `[test]` in `gd-tools.toml`.

`--durations N` prints a "Slowest Tests" table after the run, sorted
slowest-first, covering pass, fail, and skip outcomes. Bare `--durations`
means 10; `--durations 0` lists every executed test (pytest parity). Persist
the choice with `durations = 10` under `[test]` in `gd-tools.toml`; the flag
overrides the config for one invocation. The table renders identically under
`--watch` re-runs and `--parallel` runs.

`--changed` selects suites from git instead of running everything: uncommitted
changes (staged, unstaged, and untracked) map to suites by the same
file→suite convention as `--watch` — `src/enemy.gd` selects
`tests/test_enemy.gd` or `tests/enemy_test.gd`. A change that maps to no
suite (e.g. `project.godot` or a scene file) falls back to the full suite
with an explicit notice, so the selection is safe for CI. The summary line
reports how many suites were selected; per-file mapping detail prints under
`--verbose`. Add `--base <ref>` to diff committed changes from
`merge-base(<ref>, HEAD)` instead of the working tree — the form to use on
pull-request CI. `--changed` composes with `--parallel`, `--coverage`, and
the `--suite`/`--test`/`--tag` filters (the active filters bound the
mapping domain); an empty change set exits 0 without launching Godot.

`--exitfirst` (short form `-x`) stops dispatching **new** suites after the
first suite whose final result is a failure — a test failure or an
infrastructure error. In-flight suites finish and are collected; suites that
were never started are reported as skipped (`not_run`) and summarized in a
`Stopped early: fail-fast after suite <id> (K of M suites skipped)` line.
Passes and skips never trigger the gate, and a suite that passes after a
retry does not either — only final suite results decide. The exit code stays
1 for test failures. `--exitfirst` composes with `--parallel` (the pool
drains instead of killing workers), with `--coverage` (the report covers the
suites that ran, labeled partial when plan targets went unmeasured), and with
`--watch` (the gate resets for every re-run).

`--shard K/N` runs only the suites assigned to shard `K` of `N` — suite *i*
of the deterministic plan order belongs to shard `(i mod N) + 1` — for
splitting one test run across CI jobs. Selection happens after `--changed`
filtering and before `--parallel`, so each flag keeps exactly one job.
`--shard 1/1` is valid and equivalent to no sharding; malformed values
(`--shard 4/3`, `--shard 3`) exit 2 before any work. Each shard produces its
own coverage report; merge the shards with `gd-tools coverage merge`.
`--shard` and `--watch` are rejected together (exit 2). See the
[sharding recipe](./docs/USER_GUIDE.md#sharding-a-test-run-across-ci-jobs)
for a GitHub Actions matrix example.

Repeat runs are faster: the `godot --headless --import` step is cached under
`.gd-tools/native/import-cache/` and skipped when `project.godot`, any
project source/resource file (scripts, scenes, import sidecars, addons), or
the Godot version is unchanged. The integration preflight is likewise cached
under `.gd-tools/native/preflight-cache/` and skipped when the suites, test
files, `project.godot`, Godot version, and bundled addons are unchanged. Cache
hit/miss reasons are reported under `--verbose`; `--no-cache` bypasses the
import, preflight, and coverage plan caches, and `gd-tools clean --cache`
removes the cache directory.

Each run writes a machine-readable artifact index under
`.gd-tools/artifacts/<run_id>/`, listing the manifest, result, event stream,
engine log, coverage data, and any failure screenshots the run actually
produced. Only the latest run is retained. See the
[User Guide](./docs/USER_GUIDE.md#34-test) for the full artifact tree.

### Watch Mode

```bash
gd-tools test --watch                      # watch .gd files, re-run on change
gd-tools test --watch --coverage           # every re-run includes coverage
gd-tools test --watch --tag smoke          # filters apply to every run
```

`--watch` runs the full suite once, then keeps watching: saving a `.gd` file
re-runs the tests affected by the change. The changed file is mapped to its
suite by convention — `src/enemy.gd` re-runs `tests/test_enemy.gd` or
`tests/enemy_test.gd` — with a full-suite fallback (announced explicitly)
when no suite matches. Rapid successive saves are coalesced into a single
re-run, and a save during a running suite queues exactly one follow-up run.
The same file→suite mapping powers the non-interactive `gd-tools test
--changed` selection (see [Selecting and Filtering
Tests](#selecting-and-filtering-tests)).

- Native runtime only: the removed legacy GUT runtime (`--runtime gut`) is
  rejected with exit 2; `GutTest` suites must be migrated (`gd-tools migrate`).
- Interactive only: `--watch` combined with `CI=true` exits 2.
- The terminal is cleared between runs; the banner shows how many files are
  watched. While idle, `Ctrl+C` exits 0; interrupting an in-flight run kills
  its Godot processes and exits 130.
- Positional path arguments are not supported with `--watch`; the watched
  scope is the project root minus standard excludes (`.godot/`, `.gd-tools/`,
  `.git/`, and the gd-tools addons).

### Migrating Legacy GUT Suites

The GUT compatibility bridge was removed in v0.6.0; the native runtime
(`GdToolsTest`) is the only supported runtime. Suites extending `GutTest` are
rejected by `gd-tools test` with exit 2 and migration guidance, and
`--runtime gut` is rejected the same way. Run `gd-tools migrate` and see the
[migration guide](./docs/gut-migration.md) to move legacy suites onto the
native runtime.

**Known limitations.** Parallel execution is opt-in and off by default
(`--parallel N` / `[test].parallel`); suites run sequentially without it. See
the [User Guide](./docs/USER_GUIDE.md#34-test) for the full flag reference and
[Roadmap](./docs/ROADMAP.md#native-runtime-transition-completed-foundation)
for what is planned.

### Verbosity Control

`gd-tools` supports two global flags that control output verbosity. Place
them before the subcommand:

| Flag | Short | Description |
|------|-------|-------------|
| `--verbose` | `-v` | Show underlying commands and timing information. |
| `--quiet` | `-q` | Suppress non-essential output (update checks, info messages, detailed tables). |

The flags are mutually exclusive -- using both exits with code 2.

```bash
# Verbose: see the Godot command and elapsed time
gd-tools --verbose test

# Quiet: minimal output for CI pipelines
gd-tools --quiet lint
gd-tools --quiet doctor

# Default: current behavior (no change)
gd-tools test
```

**Always shown** (regardless of flag): test pass/fail summaries, lint
violations, coverage reports, error messages, and exit codes.

See the [User Guide](./docs/USER_GUIDE.md) for full command reference,
flags, examples, and exit codes.

## 6. Shell Completion

`gd-tools` supports tab completion for bash, zsh, fish, and PowerShell.
Generate a completion script with `gd-tools completion <shell>` and
source it in your shell configuration.

**Bash:**

```bash
# Add to ~/.bashrc or ~/.bash_profile
eval "$(gd-tools completion bash)"
```

**Zsh:**

```bash
# Add to ~/.zshrc
eval "$(gd-tools completion zsh)"
# Or save to a file in your fpath:
gd-tools completion zsh > ~/.zsh/completions/_gd-tools
```

**Fish:**

```bash
gd-tools completion fish > ~/.config/fish/completions/gd-tools.fish
```

**PowerShell:**

```powershell
gd-tools completion powershell | Out-String | Add-Content $PROFILE
```

**Alternative -- Click's environment variable:**

Click also supports completion via the `_GD_TOOLS_COMPLETE` environment
variable. This is useful for advanced users who prefer not to modify
their shell profile:

```bash
# Bash example
export _GD_TOOLS_COMPLETE=bash_source
eval "$(gd-tools)"
```

See the [User Guide](./docs/USER_GUIDE.md) for detailed per-shell
instructions.

## 7. Pre-commit Hooks

Wire gd-tools into the [pre-commit](https://pre-commit.com) framework so
every commit runs your format check, lint, and (optionally) your test suite:

```bash
gd-tools install-hooks
```

The command generates `.pre-commit-hooks.yaml` and merges a `repos: local:`
entry into `.pre-commit-config.yaml`. Existing hooks — including your own —
are preserved; re-runs update only the gd-tools entries in place.

Interactive by default: confirm each hook (`format`, `lint`, `test`). For
scripted or CI use, pass flags instead:

```bash
gd-tools install-hooks --non-interactive      # format + lint (defaults)
gd-tools install-hooks --all                  # format + lint + test
gd-tools install-hooks --hooks format,lint    # explicit selection
```

| Flag | Behavior |
|---|---|
| `--all` | Enable every hook (format, lint, test). |
| `--hooks HOOKS` | Comma-separated selection, e.g. `--hooks format,lint`. |
| `--non-interactive` | Never prompt; use defaults or explicit flags. |

Exit codes follow the gd-tools convention: `0` installed, `1` nothing to do,
`2` config/environment error.

See the [User Guide](./docs/USER_GUIDE.md#8-pre-commit-hooks) for the
generated file contents and per-hook details.

## 8. Configuration

`gd-tools` uses a single `gd-tools.toml` file as the source of truth for
all tool configuration. `gd-tools init` generates this file with sensible
defaults.

```toml
[godot]
binary = ""  # Optional -- auto-detected if unset

[test]
test_dirs = ["test", "tests"]
prefix = "test_"
suffix = ".gd"
runtime = "native"        # native (default); "gut" is no longer a runnable runtime
timeout_seconds = 5.0     # default per-test timeout for async native tests
retries = 0               # opt-in retries per native test
# parallel = 4            # opt-in parallel suite execution (1-32; unset runs sequentially)
tags = []                 # native suite tag filters

[lint]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[format]
exclude = ["addons", ".godot", ".gd-tools", ".git"]

[coverage]
enabled = false
min_percent = 0
format = "html"  # html, lcov, cobertura, text
output_dir = ".gd-tools/coverage"
exclude = ["addons", ".godot", ".gd-tools", ".git"]
test_dirs = ["test", "tests"]
```

### Editor Autocomplete & Validation

`gd-tools` publishes a JSON Schema for `gd-tools.toml` at
[`docs/gd-tools.schema.json`](./docs/gd-tools.schema.json). Add a
`"$schema"` key to your config to enable autocomplete and inline
validation in editors that support TOML schemas:

```toml
"$schema" = "https://raw.githubusercontent.com/mansyar/gd-tools/main/docs/gd-tools.schema.json"
```

The key is accepted and ignored by the CLI — it carries no runtime
meaning.

- **VS Code** (with [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml)):
  the `"$schema"` key above is picked up automatically. Alternatively,
  associate the schema by filename in your settings:
  `"even-better-toml.schema.associations": {"gd-tools.toml": "https://raw.githubusercontent.com/mansyar/gd-tools/main/docs/gd-tools.schema.json"}`
- **taplo** (CLI / LSP): the `"$schema"` key works out of the box, or
  add a `schema` entry to your `taplo.toml` pointing at the URL above.

The schema is regenerated with
`gd-tools config schema --output docs/gd-tools.schema.json`;
a unit test keeps the checked-in snapshot in sync with the installed
version's config model.

See the [User Guide](./docs/USER_GUIDE.md) for a full configuration reference
with all keys, defaults, and examples.

## 9. Documentation

| Document | Description |
|----------|-------------|
| [User Guide](./docs/USER_GUIDE.md) | Complete CLI reference -- all commands, flags, examples, and troubleshooting. |
| [Contributing Guide](./docs/CONTRIBUTING.md) | Development setup, code style, testing requirements, and PR process. |
| [Architecture](./docs/ARCHITECTURE.md) | System architecture -- hybrid coverage instrumentation and the native test runtime. |
| [Product Requirements](./docs/PRD.md) | Full product specification -- features, design decisions, technical detail. |
| [Roadmap](./docs/ROADMAP.md) | Release phases and milestones. |
| [Testing Strategy](./docs/TESTING_STRATEGY.md) | Test pyramid, coverage targets, and CI integration. |

## 10. Development

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/mansyar/gd-tools.git
cd gd-tools
pip install -e ".[dev]"
```

### Running Tests

Unit tests run without Godot. Integration tests require a Godot 4.5+
binary -- configure via `.env` (see `.env.example`):

```bash
cp .env.example .env
# Edit .env: set GODOT_BIN to your Godot binary path

# Run all tests with coverage
CI=true pytest
```

`CI=true` is what makes a missing Godot binary a failure rather than a skip.
Without it, integration and end-to-end tests skip quietly when Godot is
absent, so a run can report success having executed nothing.

See [Testing Strategy](./docs/TESTING_STRATEGY.md) for the full testing
guide and [Contributing Guide](./docs/CONTRIBUTING.md) for development
setup details.

## 11. License

MIT

## 12. Acknowledgements

`gd-tools` stands on the shoulders of excellent community tools, past and
present. Full credit to their authors for the hard parts.

- **[GUT (Godot Unit Test)](https://github.com/bitwes/Gut)** by
  [bitwes](https://github.com/bitwes): the GDScript test framework whose
  core API informed the native runtime's assertion surface.
- **[gdtoolkit](https://github.com/Scony/godot-gdscript-toolkit)** by
  [Scony](https://github.com/Scony): provides `gdlint` and `gdformat`, which
  `gd-tools lint` and `gd-tools format` wrap.

The native test runtime (`GdToolsTest`) and the custom hybrid coverage system
(plan generation, runtime instrumentation, and reporting) are the original work
of `gd-tools` and fill the gaps these tools do not cover.
