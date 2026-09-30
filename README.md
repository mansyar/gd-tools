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
suites that `extend GutTest` run through the built-in compatibility bridge --
no GUT addon required -- while projects migrate.

One install, one config, one mental model.

## 2. Features

| Feature | Description |
|---------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. Consistent terminal output with colored markers and summary footers across all commands. |
| **Native test runtime** | Tests extend `GdToolsTest` and run inside Godot itself. Scene and resource integration tests reach the real scene tree through an explicit context object rather than a proxy. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute -- native test and coverage addons deployed, configs generated. Existing `GutTest` suites run through the built-in compatibility bridge with no addon install. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript -- HTML, LCOV, and Cobertura reports that integrate with CI and code review tools. `# gd-tools: no cover` annotations exclude debug-only code from the numbers. |
| **CI/CD friendly** | Exit codes, `--check` flags, machine-readable output (JSON, JUnit XML, LCOV, Cobertura), no interactive prompts in CI mode. |
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

The legacy GUT runtime has been replaced by the built-in compatibility bridge:
suites extending `GutTest` run on the native runtime with no GUT addon
installed. See the [migration guide](./docs/gut-migration.md) for the
supported subset and the steps to move fully onto `GdToolsTest`.

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
| `gd-tools doctor` | Diagnose the development environment -- Godot, native test addon, bridge-eligible GUT suites, coverage addon, tooling. |
| `gd-tools test` | Run tests with optional coverage, thresholds, and JUnit XML output. Suites extending `GdToolsTest` and `GutTest` are detected and routed automatically (`GutTest` suites run through the compatibility bridge). Accepts optional path arguments to override configured test directories. `--parallel N` runs suites through a bounded worker pool. `--watch` re-runs affected suites on `.gd` file changes. Every run publishes a machine-readable artifact index under `.gd-tools/artifacts/<run_id>/`. |
| `gd-tools migrate` | Guided GUT-to-native migration. Default: read-only report with unsupported-construct inventory and proposed base-class rewrites. `--apply` renames clean suites to `GdToolsTest` and translates `.gutconfig.json` into `gd-tools.toml` (merge, never clobber). `--config-only` translates config only. |
| `gd-tools lint` | Lint GDScript files using gdlint with text or JSON output. Accepts one or more file or directory paths. |
| `gd-tools format` | Format GDScript files using gdformat with check and diff modes. Accepts one or more file or directory paths. |
| `gd-tools coverage` | Coverage subcommands -- `report`, `merge`, `show`. |
| `gd-tools config` | Configuration management -- `show` (display resolved config), `validate` (check config validity). |
| `gd-tools version` | Display versions of all gd-tools components (gd-tools, Godot, gdtoolkit, Python, and GUT when installed) in a table or JSON. |
| `gd-tools completion` | Generate shell completion scripts for bash, zsh, fish, or PowerShell. |

### Selecting and Filtering Tests

```bash
gd-tools test                              # every discovered suite
gd-tools test --suite PlayerTests          # one suite, by class name
gd-tools test --test test_takes_damage     # one test method
gd-tools test --tag smoke                  # suites with that class-level tag
gd-tools test --test-timeout 30            # per-test timeout, in seconds
gd-tools test --parallel 4                 # run suites with 4 concurrent workers
```

`--tag` is repeatable, and `--test-timeout` (per test) is separate from
`--timeout` (per suite process). `--parallel` dispatches suites to a bounded
worker pool (1-32 workers; bare `--parallel` means 4) while keeping results,
JUnit XML, and merged coverage identical to a sequential run. Persist the
choice with `parallel = 4` under `[test]` in `gd-tools.toml`.

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

- Native runtime only: the removed legacy GUT runtime (`--runtime gut`) is
  rejected with exit 2; `GutTest` suites run through the compatibility bridge.
- Interactive only: `--watch` combined with `CI=true` exits 2.
- The terminal is cleared between runs; the banner shows how many files are
  watched. While idle, `Ctrl+C` exits 0; interrupting an in-flight run kills
  its Godot processes and exits 130.
- Positional path arguments are not supported with `--watch`; the watched
  scope is the project root minus standard excludes (`.godot/`, `.gd-tools/`,
  `.git/`, and the gd-tools addons).

### Native Runtime vs. GUT Compatibility Bridge

The native runtime is the default and the forward path. Suites extending
`GutTest` run through the built-in compatibility bridge on the same native
runner; the bridge is a temporary, one-release migration path planned for
removal once projects have moved.

| Capability | Native runtime (`GdToolsTest`) | Bridge (`GutTest`) |
|------------|----------------|--------------|
| Base class | `GdToolsTest` extends `Node` | `GutTest`, provided by gd-tools (no GUT addon) |
| Discovery | `test_*` methods, by directory or exact file selector | Same; routed automatically per file |
| Lifecycle hooks | `before_all`, `after_all`, `before_each`, `after_each` | Same, plus `prerun_setup` and `postrun_teardown` |
| Assertions | Full native assertion set plus `fail()`, `skip_test()`, `pending_test()` | Documented GUT core subset -- unsupported constructs fail at preflight |
| Async waits | `wait_process_frame`, `wait_physics_frames`, `wait_seconds`, `wait_for_signal(signal, timeout)` | GUT helper family, incl. `wait_until`, `wait_while`, `yield_*` |
| Tags | Class-level tags, filtered with `--tag` | Same |
| Test selectors | `--suite`, `--test`, `--test-timeout` | Same |
| Scene and resource integration | `const INTEGRATION` plus `GdToolsTestContext` for scene root, node lookup, named resources, and bounded signal waits | Not wired into the bridge shim |
| Retries | Configurable per test (`[test].retries`) | Same |
| Line and branch coverage | Yes | Yes |
| JUnit XML output | Yes | Yes |
| Mocking and stubbing | `double()`, `partial_double()`, `stub()` (`.to_return`/`.to_call_super`), `assert_called*` family | Same -- inherited from `GdToolsTest` with identical semantics |
| Parameterized tests | Not supported | Not supported -- preflight rejects `parameterize()` |
| Skipping a test at runtime | `skip_test()` and `pending_test()` | Yes |
| Parallel execution | Opt-in -- `--parallel N` or `[test].parallel` (bounded worker pool, 1-32) | Bridge suites run in the same pool |
| Editor plugin | Not yet | Not applicable |

**Known limitations of the native runtime.** It is new, and the gaps above are
real. A project that depends on parameterized tests has no supported
execution path yet -- the bridge deliberately refuses those constructs at
preflight rather than mis-running them. See the
[migration guide](./docs/gut-migration.md) for the bridge's supported subset,
[User Guide](./docs/USER_GUIDE.md#34-test) for the full flag reference, and
[Roadmap](./docs/ROADMAP.md#8-temporary-native-test-runtime-migration-roadmap)
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

## 7. Configuration

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
gutconfig = ".gutconfig.json"  # legacy; not read by the native runtime or the bridge
runtime = "native"        # native (default); "gut" is no longer a runnable runtime
timeout_seconds = 5.0     # default per-test timeout for async native tests
retries = 0               # opt-in retries per native test
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

See the [User Guide](./docs/USER_GUIDE.md) for a full configuration reference
with all keys, defaults, and examples.

## 8. Documentation

| Document | Description |
|----------|-------------|
| [User Guide](./docs/USER_GUIDE.md) | Complete CLI reference -- all commands, flags, examples, and troubleshooting. |
| [Contributing Guide](./docs/CONTRIBUTING.md) | Development setup, code style, testing requirements, and PR process. |
| [Architecture](./docs/ARCHITECTURE.md) | System architecture -- hybrid coverage instrumentation and the native test runtime. |
| [Product Requirements](./docs/PRD.md) | Full product specification -- features, design decisions, technical detail. |
| [Roadmap](./docs/ROADMAP.md) | Release phases and milestones. |
| [Testing Strategy](./docs/TESTING_STRATEGY.md) | Test pyramid, coverage targets, and CI integration. |

## 9. Development

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

## 10. License

MIT

## 11. Acknowledgements

`gd-tools` stands on the shoulders of two excellent community tools. It
wraps them; it does not replace them. Full credit to their authors for the
hard parts.

- **[GUT (Godot Unit Test)](https://github.com/bitwes/Gut)** by
  [bitwes](https://github.com/bitwes): the GDScript test framework whose
  core API the built-in compatibility bridge reproduces while projects
  migrate to the native runtime.
- **[gdtoolkit](https://github.com/Scony/godot-gdscript-toolkit)** by
  [Scony](https://github.com/Scony): provides `gdlint` and `gdformat`, which
  `gd-tools lint` and `gd-tools format` wrap.

The native test runtime (`GdToolsTest`) and the custom hybrid coverage system
(plan generation, runtime instrumentation, and reporting) are the original work
of `gd-tools` and fill the gaps these tools do not cover.
