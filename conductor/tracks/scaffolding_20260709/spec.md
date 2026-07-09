# Track: Project Scaffolding

## Overview

This track establishes the foundational Python package structure, build system, and CLI skeleton for the `gd-tools` project. It creates the scaffolding upon which all subsequent tracks (test runner, linter, coverage, etc.) will build. No functional command logic is implemented — only the package structure, entry points, and CLI command group stubs.

**Track Type:** Feature  
**Phase:** 1 — Foundation  
**Dependencies:** None  
**Effort:** 0.5 day  
**Risk:** LOW  

## Functional Requirements

### FR-1: Project Build Configuration (`pyproject.toml`)
- **FR-1.1:** Create `pyproject.toml` following PEP 621 metadata standard.
- **FR-1.2:** Set project name to `gd-tools`, version `0.1.0`.
- **FR-1.3:** Set minimum Python version to `3.10`.
- **FR-1.4:** Declare runtime dependencies per TDD §12: `gdtoolkit`, `click`, `junitparser`, `jinja2`, `rich`, `tomli; python_version < "3.11"`, `requests`.
- **FR-1.5:** Declare dev dependencies: `pytest`, `pytest-cov`, `ruff`, `black`.
- **FR-1.6:** Configure `setuptools` build backend with `src/gd_tools` package layout.
- **FR-1.7:** Register console script entry point: `gd-tools = gd_tools.cli:cli`.
- **FR-1.8:** Set license to MIT, author from git config, standard PyPI classifiers.
- **FR-1.9:** Configure `[tool.pytest.ini_options]` per TESTING_STRATEGY.md: `testpaths=["tests"]`, markers (`unit`, `integration`, `e2e`, `slow`), `addopts` with `--cov=gd_tools`, `--cov-report=term-missing`.
- **FR-1.10:** Configure `[tool.coverage.run]` with `source=["gd_tools"]`, omit `tests/` and `addons/`.
- **FR-1.11:** Configure `[tool.coverage.report]` with `fail_under=80`.
- **FR-1.12:** Configure `[tool.ruff]` and `[tool.black]` with sensible defaults for the project.

### FR-2: Package Structure
- **FR-2.1:** Create `src/gd_tools/` directory with `__init__.py` (version string: `__version__ = "0.1.0"`).
- **FR-2.2:** Create `src/gd_tools/__main__.py` entry point that imports `cli` from `gd_tools.cli`, catches `GdToolsError`, prints to stderr, and calls `sys.exit(e.exit_code)`.
- **FR-2.3:** Create `src/gd_tools/errors.py` with the exception hierarchy from TDD §3.1:
  - `GdToolsError(Exception)` base class with `exit_code: int = 2`
  - Subclasses: `ConfigError`, `GodotNotFoundError`, `GUTNotInstalledError`, `CoveragePlanError`, `CoverageThresholdError` (exit 1), `TestFailureError` (exit 1), `LintError` (exit 1), `FormatError` (exit 1)
- **FR-2.4:** Create `tests/` directory with subdirectories: `unit/`, `integration/`, `e2e/`, `fixtures/` (each with `__init__.py`).

### FR-3: CLI Skeleton (`src/gd_tools/cli.py`)
- **FR-3.1:** Create a Click group `cli` decorated with `@click.version_option(version=__version__, package_name="gd-tools")`.
- **FR-3.2:** Implement the following command groups/commands per TDD §3.4:
  - `init` — with `--non-interactive` flag
  - `doctor` — no arguments
  - `test` — with options `--coverage`, `--min`, `--suite`, `--test`, `--junit-xml`, `--no-exit-code`
  - `lint` — with `path` argument and `--report-format` option
  - `format` — with `path` argument and `--check`, `--diff` options
  - `coverage` — a Click group with subcommands:
    - `report` — with `--format`, `--output-dir` options
    - `merge` — with `files` argument and `--output` option
    - `show` — with `--min` option
- **FR-3.3:** All command stubs raise `NotImplementedError` (wrapped to exit with code 2 per the PRD convention) when invoked. The command structure and help text must be visible via `--help`.

### FR-4: Supporting Files
- **FR-4.1:** Create `.gitignore` with Python ignores, `.gd-tools/`, and `.godot/`.
- **FR-4.2:** Create `README.md` placeholder with project name, brief description, and install instructions placeholder.

## Non-Functional Requirements

### NFR-1: Code Quality
- **NFR-1.1:** All Python source files must pass `ruff check` with zero errors.
- **NFR-1.2:** All Python source files must pass `black --check` formatting.
- **NFR-1.3:** Test coverage for source files (`cli.py`, `errors.py`, `__main__.py`) must be >=80% line coverage.

### NFR-2: Compatibility
- **NFR-2.1:** Package must install and run on Python 3.10, 3.11, and 3.12.
- **NFR-2.2:** `tomli` must only be installed on Python < 3.11 (conditional dependency).

### NFR-3: Conventions
- **NFR-3.1:** Follow Product Guidelines: kebab-case for CLI, snake_case for Python, no emoji in output.
- **NFR-3.2:** Error messages must be actionable with Cause/Fix hints where applicable.

## Acceptance Criteria

1. **AC-1:** `pip install -e ".[dev]"` succeeds without errors on Python 3.10+.
2. **AC-2:** `gd-tools --version` outputs `gd-tools 0.1.0`.
3. **AC-3:** `gd-tools --help` shows all command groups: `init`, `doctor`, `test`, `lint`, `format`, `coverage`.
4. **AC-4:** `python -m gd_tools --version` works as an alias and outputs `gd-tools 0.1.0`.
5. **AC-5:** `from gd_tools import cli` imports cleanly without side effects.
6. **AC-6:** `from gd_tools.errors import GdToolsError` imports cleanly; all exception subclasses are accessible.
7. **AC-7:** Invoking any stub command (e.g., `gd-tools test`) raises an error with exit code 2.
8. **AC-8:** `CI=true pytest` passes with all tests green and coverage >=80% for source files.
9. **AC-9:** `ruff check src/ tests/` passes with zero errors.
10. **AC-10:** `black --check src/ tests/` passes with zero formatting issues.

## Out of Scope

- Implementation of any command logic (test, lint, format, coverage, init, doctor) — these are stubs only.
- Configuration file (`gd-tools.toml`) parsing and loading — deferred to a later track.
- Godot integration, GUT detection, or addon installation — deferred to later tracks.
- CI/CD pipeline setup (GitHub Actions) — deferred to a later track.
- PyPI publishing configuration — deferred to a later track.
- GDScript addon files (`coverage.gd`, hooks) — deferred to the coverage track.
- Any modules beyond `cli.py`, `errors.py`, `__main__.py`, `__init__.py` (e.g., `config.py`, `godot.py`, `test_runner.py`) — these are placeholders for future tracks.
