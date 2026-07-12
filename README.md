# gd-tools

A modern development workflow CLI for GDScript projects in Godot 4.5+.

[![CI](https://github.com/mansyar/gd-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/mansyar/gd-tools/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/mansyar/gd-tools/branch/main/graph/badge.svg)](https://codecov.io/gh/mansyar/gd-tools)
[![PyPI version](https://img.shields.io/pypi/v/gd-tools.svg)](https://pypi.org/project/gd-tools/)
[![Python versions](https://img.shields.io/pypi/pyversions/gd-tools.svg)](https://pypi.org/project/gd-tools/)
[![Godot version](https://img.shields.io/badge/Godot-4.5%2B-blue.svg)](https://godotengine.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Overview

`gd-tools` brings professional development tooling to GDScript — test, lint,
format, and code coverage in a single CLI. It wraps mature, community-trusted
tools (GUT for testing, gdtoolkit for linting and formatting) and fills the
remaining gap with a custom hybrid coverage system — production-quality line
and branch coverage for GDScript that no existing tool provides.

One install, one config, one mental model.

## 2. Features

| Feature | Description |
|---------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute — GUT installed, coverage addon deployed, configs generated. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript — HTML, LCOV, and Cobertura reports that integrate with CI and code review tools. |
| **CI/CD friendly** | Exit codes, `--check` flags, machine-readable output (JSON, JUnit XML, LCOV, Cobertura), no interactive prompts in CI mode. |
| **Standalone compatibility** | gdlint, gdformat, and GUT continue to work if invoked directly. `gd-tools` is a layer on top, not a lock-in. |

## 3. Installation

```bash
pip install gd-tools
```

`gd-tools` requires Python 3.10+ and a Godot 4.5+ binary on your system.
The Godot binary is auto-detected from configuration, environment variables
(`GODOT_BIN`, `GODOT4_BIN`, `GODOT_PATH`), `PATH`, or common install locations.

## 4. Quick Start

```bash
# 1. Install
pip install gd-tools

# 2. Bootstrap your Godot project
cd your-godot-project
gd-tools init

# 3. Run your tests
gd-tools test

# 4. Run tests with coverage
gd-tools test --coverage --min 80
```

`gd-tools init` installs GUT, deploys the coverage addon, generates
`gd-tools.toml`, and creates per-tool config files (`.gutconfig.json`,
`gdlintrc`, `gdformatrc`). The command is idempotent — safe to re-run.

## 5. CLI Command Summary

| Command | Description |
|---------|-------------|
| `gd-tools init` | Bootstrap a Godot project — install GUT, deploy coverage addon, generate configs. |
| `gd-tools doctor` | Diagnose the development environment — Godot, GUT, coverage addon, tooling. |
| `gd-tools test` | Run GUT tests with optional coverage, thresholds, JUnit XML output. |
| `gd-tools lint` | Lint GDScript files using gdlint with text or JSON output. |
| `gd-tools format` | Format GDScript files using gdformat with check and diff modes. |
| `gd-tools coverage` | Coverage subcommands — `report`, `merge`, `show`. |

See the [User Guide](./docs/USER_GUIDE.md) for full command reference,
flags, examples, and exit codes.

## 6. Configuration

`gd-tools` uses a single `gd-tools.toml` file as the source of truth for
all tool configuration. `gd-tools init` generates this file with sensible
defaults.

```toml
[godot]
binary = ""  # Optional — auto-detected if unset

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
format = "html"  # html, lcov, cobertura, text
output_dir = ".gd-tools/coverage"
exclude = ["addons", ".godot", ".gd-tools", ".git"]
test_dirs = ["test", "tests"]
```

See the [User Guide](./docs/USER_GUIDE.md) for a full configuration reference
with all keys, defaults, and examples.

## 7. Documentation

| Document | Description |
|----------|-------------|
| [User Guide](./docs/USER_GUIDE.md) | Complete CLI reference — all commands, flags, examples, and troubleshooting. |
| [Contributing Guide](./docs/CONTRIBUTING.md) | Development setup, code style, testing requirements, and PR process. |
| [Architecture](./docs/ARCHITECTURE.md) | Coverage system architecture — hybrid instrumentation design and data flows. |
| [Product Requirements](./docs/PRD.md) | Full product specification — features, design decisions, technical detail. |
| [Roadmap](./docs/ROADMAP.md) | Release phases and milestones. |
| [Testing Strategy](./docs/TESTING_STRATEGY.md) | Test pyramid, coverage targets, and CI integration. |

## 8. Development

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/mansyar/gd-tools.git
cd gd-tools
pip install -e ".[dev]"
```

### Running Tests

Unit tests run without Godot. Integration tests require a Godot 4.5+
binary — configure via `.env` (see `.env.example`):

```bash
cp .env.example .env
# Edit .env: set GODOT_BIN to your Godot binary path

# Run all tests with coverage
pytest --cov=src/gd_tools --cov-report=term-missing
```

See [Testing Strategy](./docs/TESTING_STRATEGY.md) for the full testing
guide and [Contributing Guide](./docs/CONTRIBUTING.md) for development
setup details.

## 9. License

MIT
