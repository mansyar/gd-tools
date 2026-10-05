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
| `jinja2` | HTML coverage report generation | Templates for source-highlighted coverage views |
| `rich` | Terminal output — tables, colors, progress bars | All user-facing CLI output |
| `tomli` | TOML config parsing | Backport for Python < 3.11; `tomllib` used natively on 3.11+ |
| `tomli_w` | TOML config writing | Write companion to `tomli`/`tomllib`; used by `save_config()` |
| `pydantic` | Config model validation (Pydantic v2) | Validates `gd-tools.toml` structure; `extra='forbid'` catches typo'd keys |
| `pyyaml` | YAML config file generation | Used by `gd-tools init` and config to generate `gdlintrc` (YAML set format) |
| `requests` | Query PyPI for update notifications | Used by the `gd-tools` update-check feature (`update_check.py`) |
| `packaging` | Version comparison for PyPI update check | Used by `gd-tools` update notification feature |
| `watchdog` | Cross-platform file-system event watching | Used by `gd-tools test --watch` (Watch Mode track, 2026-09-28); observes `.gd` files and feeds the debounce/run loop |

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
| **Coverage Addon** (`addons/gd-tools-coverage/`) | Runtime instrumentation + hit tracking. Ships as package data inside the Python distribution. Files: `coverage.gd` (the legacy GUT hook scripts were removed; `gd-tools init` self-heals stale copies) |
| **Native Test Addon** (`addons/gd-tools-test/`) | `GdToolsTest` base class, transient native runner, assertions, lifecycle management, and native coverage integration. Ships as package data; no new runtime dependency. Files: `gd_tools_test.gd`, `gd_tools_mock.gd`, `gd_tools_parameter_naming.gd`, `gd_tools_test_context.gd`, `gd_tools_test_runner.gd`, `gd_tools_test_preflight.gd`, `gd_tools_native_coverage.gd`, `gd_tools_snapshot_serializer.gd`, `gd_tools_snapshot_store.gd` — all are managed by `gd-tools init` and verified by `gd-tools doctor`. |
| **GUT** (legacy, not supported) | GDScript test framework. Since v0.6.0, gd-tools does not install, download, or run GUT, and no Godot-to-GUT version mapping exists. Projects that still carry `addons/gut/`, `.gutconfig.json`, or `extends GutTest` suites get an informational `doctor` advisory pointing at `gd-tools migrate`. Not a runtime dependency. |
| **Editor Plugin** (`addons/gd-tools-editor/`) | Godot editor plugin: test/coverage dock panel (async CLI runs, results summary, missing-CLI fallback) and a `CodeEdit` coverage heatmap overlay (green/red/yellow line backgrounds from `.gd-tools/` artifacts). Ships as package data. Files: `plugin.gd`, `dock.gd`, `coverage_overlay.gd` — deployed by `gd-tools init` and verified by `gd-tools doctor`. |

---

## 5. External Dependencies (not pip-installable)

| Component | Version | Purpose |
|-----------|---------|---------|
| **Godot Engine** | 4.5+ | Runs the native test runtime and instrumented tests. Required by `gd-tools test` and `gd-tools init` (version detection). Not required by lint/format/coverage-plan-gen (those are pure Python via gdtoolkit) |

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
- **Runtime mode:** Native execution is the only supported runtime; `GutTest` suites are rejected with exit `2` and migration guidance (`gd-tools migrate`).
- **Packaging:** One bundled native test addon with the Python distribution.
- **Execution:** Suite-scoped Godot processes, fresh test instances, async-first test methods, and sequential execution by default (opt-in bounded parallel worker pool via `--parallel N` / `[test].parallel`).
- **Integration protocol:** Native protocol v3. One headless preflight per command reads suite `INTEGRATION` constants through Godot metadata, validates and merges them into the per-suite manifest. Python never parses GDScript.
- **Execution modes:** Headless by default; `windowed` suites run without `--headless`, require a real display, and fail with exit `2` when the renderer is headless.
- **Artifacts:** `.gd-tools/artifacts/<run_id>/` holds a machine-readable index plus preflight and per-suite artifacts; only the latest run is retained.
- **Coverage:** Native runtime owns activation; the versioned coverage plan schema (currently v7 — v3 anchors ternary branch points to their enclosing statement, v4 drops points recorded on class-member declaration and signature lines, v5 additionally drops bracket/backslash continuation lines, v6 adds ternary `operand_span` value-preserving arm wrapping, v7 adds `and`/`or` short-circuit and `assert` condition branch points) is reused where possible for line and branch metrics. Collectors reject plans carrying branch types they do not implement, so a stale addon fails loudly against a newer plan.
- **Dependencies:** No third-party GDScript runtime dependency. GUT is not required.
- **Compatibility:** `.gutconfig.json` is not read by any runtime; `gd-tools migrate` translates its mapped options into `gd-tools.toml` (merge, never clobber) and preserves the file. `gd-tools.toml` is canonical.
- **Exit condition:** Met — the temporary bridge was removed in v0.6.0 and the durable decisions were folded into the main roadmap.
