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
format, and code coverage in a single CLI. It wraps mature, community-trusted
tools (GUT for testing, gdtoolkit for linting and formatting) and fills the
remaining gap with a custom hybrid coverage system -- production-quality line
and branch coverage for GDScript that no existing tool provides.

One install, one config, one mental model.

## 2. Features

| Feature | Description |
|---------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. Consistent terminal output with colored markers and summary footers across all commands. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute -- GUT installed, coverage addon deployed, configs generated. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript -- HTML, LCOV, and Cobertura reports that integrate with CI and code review tools. |
| **CI/CD friendly** | Exit codes, `--check` flags, machine-readable output (JSON, JUnit XML, LCOV, Cobertura), no interactive prompts in CI mode. |
| **Standalone compatibility** | gdlint, gdformat, and GUT continue to work if invoked directly. `gd-tools` is a layer on top, not a lock-in. |

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
```

`gd-tools init` installs GUT, deploys the coverage addon, generates
`gd-tools.toml`, and creates per-tool config files (`.gutconfig.json`,
`gdlintrc`, `gdformatrc`). The command is idempotent -- safe to re-run.

## 5. CLI Command Summary

| Command | Description |
|---------|-------------|
| `gd-tools init` | Bootstrap a Godot project -- install GUT, deploy coverage addon, generate configs. |
| `gd-tools doctor` | Diagnose the development environment -- Godot, GUT, coverage addon, tooling. |
| `gd-tools test` | Run GUT tests with optional coverage, thresholds, JUnit XML output. Accepts optional path arguments to override configured test directories. |
| `gd-tools lint` | Lint GDScript files using gdlint with text or JSON output. Accepts one or more file or directory paths. |
| `gd-tools format` | Format GDScript files using gdformat with check and diff modes. Accepts one or more file or directory paths. |
| `gd-tools coverage` | Coverage subcommands -- `report`, `merge`, `show`. |
| `gd-tools config` | Configuration management -- `show` (display resolved config), `validate` (check config validity). |
| `gd-tools version` | Display versions of all gd-tools components (gd-tools, Godot, GUT, gdtoolkit, Python) in a table or JSON. |
| `gd-tools completion` | Generate shell completion scripts for bash, zsh, fish, or PowerShell. |

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
| [Architecture](./docs/ARCHITECTURE.md) | Coverage system architecture -- hybrid instrumentation design and data flows. |
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
pytest --cov=src/gd_tools --cov-report=term-missing
```

See [Testing Strategy](./docs/TESTING_STRATEGY.md) for the full testing
guide and [Contributing Guide](./docs/CONTRIBUTING.md) for development
setup details.

## 10. License

MIT

## 11. Acknowledgements

`gd-tools` stands on the shoulders of two excellent community tools. It
wraps them; it does not replace them. Full credit to their authors for the
hard parts.

- **[GUT (Godot Unit Test)](https://github.com/bitwes/Gut)** by [bitwes](https://github.com/bitwes): the GDScript test framework that `gd-tools test` drives.
- **[gdtoolkit](https://github.com/Scony/godot-gdscript-toolkit)** by [Scony](https://github.com/Scony): provides `gdlint` and `gdformat`, which `gd-tools lint` and `gd-tools format` wrap.

The custom hybrid coverage system (plan generation, runtime instrumentation,
and reporting) is the original work of `gd-tools` and fills the gap these
tools do not cover.
