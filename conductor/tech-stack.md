# Technology Stack

## 1. Primary Languages

| Language | Role | Version |
|----------|------|---------|
| **Python** | CLI tool implementation (gd-tools itself) | 3.10+ (3.11+ preferred for native `tomllib`) |
| **GDScript** | Coverage addon (runtime instrumentation + tracking) | Godot 4.5+ dialect |

---

## 2. Runtime Dependencies (Python)

| Package | Purpose | Notes |
|---------|---------|-------|
| `gdtoolkit` | Lark-based GDScript parser — used by lint, format, and coverage plan generation | Core dependency; provides `gdlint`, `gdformat`, and `parser.parse()` |
| `click` | CLI framework | Chosen over `typer` for broader ecosystem and simpler group/subcommand structure. PRD §16 Open Question resolved. |
| `junitparser` | Parse GUT's JUnit XML test results | Converts XML → structured `TestResult` |
| `jinja2` | HTML coverage report generation | Templates for source-highlighted coverage views |
| `rich` | Terminal output — tables, colors, progress bars | All user-facing CLI output |
| `tomli` | TOML config parsing | Backport for Python < 3.11; `tomllib` used natively on 3.11+ |
| `tomli_w` | TOML config writing | Write companion to `tomli`/`tomllib`; used by `save_config()` |
| `pydantic` | Config model validation (Pydantic v2) | Validates `gd-tools.toml` structure; `extra='forbid'` catches typo'd keys |
| `pyyaml` | YAML config file generation | Used by `gd-tools init` and config to generate `gdlintrc` (YAML set format) |
| `requests` | Download GUT releases from GitHub | Used by `gd-tools init` |
| `packaging` | Version comparison for PyPI update check | Used by `gd-tools` update notification feature |

---

## 3. Development Dependencies (Python)

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework for gd-tools itself |
| `pytest-cov` | Coverage measurement for gd-tools's own code |
| `ruff` | Linter for gd-tools Python code |
| `black` | Formatter for gd-tools Python code |
| `commitizen` | Conventional commit enforcement, automated semantic versioning, and changelog generation |

> **Note (2026-07-13):** `commitizen` was added to enforce [Conventional Commits](https://www.conventionalcommits.org/) across the project. It provides automated version bumping via `cz bump` (driven by `v$version` tags) and changelog generation via `cz changelog`. Configuration lives in `pyproject.toml` under `[tool.commitizen]`. The CI pipeline validates commit messages on pull requests (see §8).

---

## 4. Bundled Components (GDScript, not pip-installable)

| Component | Purpose |
|-----------|---------|
| **Coverage Addon** (`addons/gd-tools-coverage/`) | Runtime instrumentation + hit tracking. Ships as package data inside the Python distribution. Files: `coverage.gd`, `pre_run_hook.gd`, `post_run_hook.gd` |
| **GUT** (installed by `gd-tools init`) | GDScript unit test framework. Downloaded from GitHub releases, not bundled. Version-mapped to Godot version (4.5→9.5.0, 4.6→9.6.0, 4.7→9.7.0) |

---

## 5. External Dependencies (not pip-installable)

| Component | Version | Purpose |
|-----------|---------|---------|
| **Godot Engine** | 4.5+ | Runs GUT + instrumented tests. Required by `gd-tools test` and `gd-tools init` (version detection). Not required by lint/format/coverage-plan-gen (those are pure Python via gdtoolkit) |

---

## 6. Architecture Summary

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
│                        │                                │
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

**Hybrid Coverage Architecture (Architecture C):**
- **Python side** (gdtoolkit/Lark): Parses GDScript, identifies executable lines and branch points, generates an instrumentation plan (JSON).
- **GDScript side** (coverage addon): Reads the plan at runtime, instruments scripts via Godot's Script API, tracks execution, writes coverage data (JSON).
- **Python side** (reporter): Reads coverage data, generates reports (HTML, LCOV, Cobertura, terminal).

---

## 7. Configuration

- **Build system:** `pyproject.toml` (PEP 621), `src/gd_tools/` layout
- **Config format:** TOML (`gd-tools.toml` as single source of truth)
- **Package data:** GDScript addon files bundled via `setuptools` package_data
- **Entry points:** Console script `gd-tools` + `python -m gd_tools`

---

## 8. CI/CD Stack

| Tool | Purpose |
|------|---------|
| **GitHub Actions** | CI/CD pipeline (lint, format, test, coverage) |
| **pytest + pytest-cov** | Test runner + coverage for gd-tools |
| **commitizen** | Conventional commit message validation on pull requests |
| **codecov.io** | Coverage upload (via `coverage.xml`, `codecov-action@v4`) |
| **build** | Package building (`python -m build` → sdist + wheel) |
| **twine** | Package upload to TestPyPI/PyPI |
| **PyPI** | Package distribution (`pip install gd-tools-cli`) |
| **TestPyPI** | Pre-release testing |
