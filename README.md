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
signals, and assert on real engine objects without leaving the engine. The
older GUT runtime still works and remains selectable while projects migrate.

One install, one config, one mental model.

## 2. Features

| Feature | Description |
|---------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. Consistent terminal output with colored markers and summary footers across all commands. |
| **Native test runtime** | Tests extend `GdToolsTest` and run inside Godot itself. Scene and resource integration tests reach the real scene tree through an explicit context object rather than a proxy. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute -- native test and coverage addons deployed, configs generated. GUT is opt-in via `--with-gut`. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript -- HTML, LCOV, and Cobertura reports that integrate with CI and code review tools. |
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

GUT is a legacy migration path, not part of the default bootstrap. To install
and enable it alongside the native runtime, pass `--with-gut`.

A test suite is any class extending `GdToolsTest`:

```gdscript
extends GdToolsTest

func test_health_starts_at_full() -> void:
    assert_eq(health.current(), 100)
```

## 5. CLI Command Summary

| Command | Description |
|---------|-------------|
| `gd-tools init` | Bootstrap a Godot project -- deploy the native test and coverage addons, generate configs. Add `--with-gut` to also install the legacy GUT runtime. |
| `gd-tools doctor` | Diagnose the development environment -- Godot, native test addon, GUT (if installed), coverage addon, tooling. |
| `gd-tools test` | Run tests with optional coverage, thresholds, and JUnit XML output. Runs the native runtime by default; `--runtime gut` selects the legacy path. Accepts optional path arguments to override configured test directories. |
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
gd-tools test --runtime gut                # use the legacy GUT path
```

`--tag` is repeatable, and `--test-timeout` (per test) is separate from
`--timeout` (per suite process).

### Native Runtime vs. GUT

GUT remains supported as a migration bridge and is planned for removal once
projects have moved. The native runtime is the default and the forward path.

| Capability | Native runtime | GUT (legacy) |
|------------|----------------|--------------|
| Base class | `GdToolsTest` extends `Node` | `GutTest` |
| Discovery | `test_*` methods, by directory or exact file selector | Gut convention |
| Lifecycle hooks | `before_all`, `after_all`, `before_each`, `after_each` | Full hook set |
| Assertions | 7 core assertions plus `fail()` | Broad assertion library |
| Async waits | `wait_process_frame`, `wait_physics_frames`, `wait_seconds`, `wait_for_signal` | Broader helpers |
| Tags | Class-level tags, filtered with `--tag` | Yes |
| Test selectors | `--suite`, `--test`, `--test-timeout` | Via `.gutconfig.json` |
| Scene and resource integration | `const INTEGRATION` plus `GdToolsTestContext` for scene root, node lookup, named resources, and bounded signal waits | Partial |
| Retries | Configurable per test (`[test].retries`) | No |
| Line and branch coverage | Yes | Yes |
| JUnit XML output | Yes | Yes |
| Mocking and stubbing | Not yet | Yes |
| Parameterized tests | Not supported | Yes |
| Skipping a test at runtime | Not yet | Yes |
| Parallel execution | Not yet -- suites run sequentially | Partial |
| Editor plugin | Not yet | Not applicable |

**Known limitations of the native runtime.** It is new, and the gaps above are
real. If a project depends on mocking, parameterized tests, or runtime
skipping, the legacy GUT path is the pragmatic choice until those land. See
[User Guide](./docs/USER_GUIDE.md#34-test) for the full flag reference and
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
gutconfig = ".gutconfig.json"
runtime = "native"        # native (default) or gut (legacy migration path)
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
  [bitwes](https://github.com/bitwes): the GDScript test framework that the
  legacy `--runtime gut` path drives. GUT remains supported as a migration
  bridge.
- **[gdtoolkit](https://github.com/Scony/godot-gdscript-toolkit)** by
  [Scony](https://github.com/Scony): provides `gdlint` and `gdformat`, which
  `gd-tools lint` and `gd-tools format` wrap.

The native test runtime (`GdToolsTest`) and the custom hybrid coverage system
(plan generation, runtime instrumentation, and reporting) are the original work
of `gd-tools` and fill the gaps these tools do not cover.
