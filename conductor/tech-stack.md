# Technology Stack

## 1. Primary Languages

| Language | Role | Version |
|----------|------|---------|
| **Python** | CLI tool implementation, discovery, reporting (gd-tools itself) | 3.10+ (3.11+ preferred for native `tomllib`) |
| **GDScript** | Native test runtime and coverage addon (runtime execution + tracking) | Godot 4.5+ dialect |

---

## 2. Runtime Dependencies (Python)

| Package | Purpose | Notes |
|---------|---------|-------|
| `gdtoolkit` | Lark-based GDScript parser — used by lint, format, and coverage plan generation | Core dependency; provides `gdlint`, `gdformat`, and `parser.parse()` |
| `click` | CLI framework | Chosen over `typer` for broader ecosystem and simpler group/subcommand structure. PRD §16 Open Question resolved. |
| `junitparser` | Parse native and GUT-bridge JUnit XML test results | Converts XML → structured `TestResult` |
| `jinja2` | HTML coverage report generation | Templates for source-highlighted coverage views |
| `rich` | Terminal output — tables, colors, progress bars | All user-facing CLI output |
| `tomli` | TOML config parsing | Backport for Python < 3.11; `tomllib` used natively on 3.11+ |
| `tomli_w` | TOML config writing | Write companion to `tomli`/`tomllib`; used by `save_config()` |
| `pydantic` | Config model validation (Pydantic v2) | Validates `gd-tools.toml` structure; `extra='forbid'` catches typo'd keys |
| `pyyaml` | YAML config file generation | Used by `gd-tools init` and config to generate `gdlintrc` (YAML set format) |
| `requests` | Download optional GUT bridge releases from GitHub | Used by `gd-tools init` only when the migration bridge is requested; native tests do not require it |
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
| **Native Test Addon** (`addons/gd-tools-test/`) | `GdToolsTest` base class, transient native runner, assertions, lifecycle management, and native coverage integration. Ships as package data; no new runtime dependency. Files: `gd_tools_test.gd`, `gd_tools_test_runner.gd`, `gd_tools_test_context.gd`, `gd_tools_test_preflight.gd`, `gd_tools_native_coverage.gd` — all five are managed by `gd-tools init` and verified by `gd-tools doctor`. |
| **GUT** (optional migration bridge) | GDScript test framework downloaded by `gd-tools init` only when requested. Not a native runtime dependency. Version-mapped to Godot version during the migration period (4.5→9.5.0, 4.6→9.6.0, 4.7→9.7.0). |

---

## 5. External Dependencies (not pip-installable)

| Component | Version | Purpose |
|-----------|---------|---------|
| **Godot Engine** | 4.5+ | Runs the native test runtime, optional GUT bridge, and instrumented tests. Required by `gd-tools test` and `gd-tools init` (version detection). Not required by lint/format/coverage-plan-gen (those are pure Python via gdtoolkit) |

---

## 6. Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    gd-tools CLI (Python)                 │
│                                                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────────┐  │
│  │  test   │  │  lint   │  │ format  │  │  coverage  │  │
│  │ (native │  │(gdlint  │  │(gdformat│  │ (custom    │  │
│  │ runtime)│  │ wrapper)│  │ wrapper)│  │ Arch. C)   │  │
│  └────┬────┘  └─────────┘  └─────────┘  └─────┬──────┘  │
│       │                                      │         │
│       │     ┌──────────────────────┐          │         │
│       └────►│  Godot binary (CLI)  │◄─────────┘         │
│             └──────────┬──────────┘                    │
│                        │                                │
│             ┌──────────▼──────────┐                      │
│             │ Native test runtime │                      │
│             │ + coverage addon    │                      │
│             │ (GDScript)          │                      │
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
- **Native GDScript side** (native test runtime + coverage addon): Activates coverage for native tests, instruments scripts via Godot's Script API, tracks execution, and writes coverage data (JSON).
- **GUT bridge side** (temporary): Uses the existing GUT hook/autoload path only for legacy migration runs.
- **Python side** (reporter): Reads coverage data, generates reports (HTML, LCOV, Cobertura, terminal).

---

## 7. Configuration

- **Build system:** `pyproject.toml` (PEP 621), `src/gd_tools/` layout
- **Config format:** TOML (`gd-tools.toml` as single source of truth)
- **Native test protocol:** Versioned JSON manifest from Python to Godot plus atomic native JSON/NDJSON result data
- **Package data:** GDScript native-test and coverage addon files bundled via `setuptools` package_data
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

## 9. Native Test Runtime Migration

- **Public API:** `GdToolsTest` / `GdToolsTestRunner`, plus `GdToolsTestContext` returned by `get_test_context()`
- **Runtime mode:** Native execution is the default; the existing GUT subprocess path remains a temporary migration option.
- **Packaging:** One bundled native test addon with the Python distribution.
- **Execution:** Suite-scoped Godot processes, fresh test instances, async-first test methods, and sequential execution by default.
- **Integration protocol:** Native protocol v2. One headless preflight per command reads suite `INTEGRATION` constants through Godot metadata, validates and merges them into the per-suite manifest. Python never parses GDScript.
- **Execution modes:** Headless by default; `windowed` suites run without `--headless`, require a real display, and fail with exit `2` when the renderer is headless.
- **Artifacts:** `.gd-tools/artifacts/<run_id>/` holds a machine-readable index plus preflight and per-suite artifacts; only the latest run is retained.
- **Coverage:** Native runtime owns activation; existing coverage plan schema v1 is reused where possible for line and branch metrics.
- **Dependencies:** No new third-party GDScript runtime dependency. GUT is optional during the bounded migration period.
- **Compatibility:** `.gutconfig.json` is translated and preserved; `gd-tools.toml` is canonical.
- **Exit condition:** Remove the temporary bridge and fold the durable decisions into the main roadmap after native migration is complete.
