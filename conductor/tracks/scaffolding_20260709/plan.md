<protect>
# Implementation Plan: Project Scaffolding

## Phase 1: Project Scaffolding

- [x] Task: Read spec.md and workflow.md before starting implementation
    - [ ] Read `conductor/tracks/scaffolding_20260709/spec.md`
    - [ ] Read `conductor/workflow.md`
    - [ ] Verify: understand TDD methodology, commit patterns, and task lifecycle

- [x] Task: Create build configuration (`pyproject.toml`) [d0cc81a]
    - [ ] Create `pyproject.toml` with PEP 621 metadata (name: `gd-tools`, version: `0.1.0`, requires-python: `>=3.10`)
    - [ ] Declare runtime dependencies: `gdtoolkit`, `click`, `junitparser`, `jinja2`, `rich`, `tomli; python_version < "3.11"`, `requests`
    - [ ] Declare dev dependencies: `pytest`, `pytest-cov`, `ruff`, `black`
    - [ ] Configure setuptools build backend with `src/gd_tools` package layout
    - [ ] Register console script entry point: `gd-tools = gd_tools.cli:cli`
    - [ ] Set MIT license, author from git config, PyPI classifiers
    - [ ] Configure `[tool.pytest.ini_options]` (testpaths, markers, addopts with coverage)
    - [ ] Configure `[tool.coverage.run]` and `[tool.coverage.report]` (fail_under=80)
    - [ ] Configure `[tool.ruff]` and `[tool.black]` defaults
    - [ ] Verify: `pip install -e ".[dev]"` succeeds without errors

- [x] Task: Create package structure and version (`__init__.py`) [d329fa3]
    - [ ] Write failing test: `tests/unit/test_package.py` — test that `gd_tools.__version__` equals `"0.1.0"`
    - [ ] Create `src/gd_tools/__init__.py` with `__version__ = "0.1.0"`
    - [ ] Verify: test passes, `from gd_tools import __version__` works

- [x] Task: Implement exception hierarchy (`errors.py`) — TDD [5105c97]
    - [ ] Write failing tests: `tests/unit/test_errors.py`
        - [ ] Test `GdToolsError` is an `Exception` subclass with `exit_code` defaulting to `2`
        - [ ] Test `GdToolsError` accepts custom `exit_code` via constructor
        - [ ] Test `ConfigError` inherits from `GdToolsError` with exit code `2`
        - [ ] Test `GodotNotFoundError` inherits from `GdToolsError` with exit code `2`
        - [ ] Test `GUTNotInstalledError` inherits from `GdToolsError` with exit code `2`
        - [ ] Test `CoveragePlanError` inherits from `GdToolsError` with exit code `2`
        - [ ] Test `CoverageThresholdError` inherits from `GdToolsError` with exit code `1`
        - [ ] Test `TestFailureError` inherits from `GdToolsError` with exit code `1`
        - [ ] Test `LintError` inherits from `GdToolsError` with exit code `1`
        - [ ] Test `FormatError` inherits from `GdToolsError` with exit code `1`
    - [ ] Implement `src/gd_tools/errors.py` with full exception hierarchy per TDD §3.1
    - [ ] Verify: all tests pass, coverage >=80%

- [x] Task: Implement CLI skeleton (`cli.py`) — TDD [e3d0e7f]
    - [ ] Write failing tests: `tests/unit/test_cli.py`
        - [ ] Test `cli` is a Click group
        - [ ] Test `gd-tools --version` outputs `gd-tools 0.1.0` (using Click's `CliRunner`)
        - [ ] Test `gd-tools --help` exits with code `0` and shows all command names: `init`, `doctor`, `test`, `lint`, `format`, `coverage`
        - [ ] Test `gd-tools init --help` shows `--non-interactive` option
        - [ ] Test `gd-tools test --help` shows options: `--coverage`, `--min`, `--suite`, `--test`, `--junit-xml`, `--no-exit-code`
        - [ ] Test `gd-tools lint --help` shows `path` argument and `--report-format` option
        - [ ] Test `gd-tools format --help` shows `path` argument and `--check`, `--diff` options
        - [ ] Test `gd-tools coverage --help` shows subcommands: `report`, `merge`, `show`
        - [ ] Test `gd-tools coverage report --help` shows `--format`, `--output-dir` options
        - [ ] Test `gd-tools coverage merge --help` shows `files` argument and `--output` option
        - [ ] Test `gd-tools coverage show --help` shows `--min` option
        - [ ] Test invoking `gd-tools test` (no args beyond options) raises error with exit code `2`
        - [ ] Test invoking `gd-tools lint` raises error with exit code `2`
        - [ ] Test invoking `gd-tools format` raises error with exit code `2`
        - [ ] Test invoking `gd-tools init` raises error with exit code `2`
        - [ ] Test invoking `gd-tools doctor` raises error with exit code `2`
        - [ ] Test invoking `gd-tools coverage report` raises error with exit code `2`
    - [ ] Implement `src/gd_tools/cli.py` with Click group and all command stubs per TDD §3.4
        - [ ] Stubs raise `NotImplementedError` wrapped to exit with code `2`
    - [ ] Verify: all tests pass, coverage >=80%

- [ ] Task: Implement module entry point (`__main__.py`) — TDD
    - [ ] Write failing tests: `tests/unit/test_main.py`
        - [ ] Test `python -m gd_tools --version` outputs `gd-tools 0.1.0` (subprocess test)
        - [ ] Test `python -m gd_tools --help` exits with code `0`
        - [ ] Test `python -m gd_tools test` exits with code `2` (stub error propagation)
    - [ ] Implement `src/gd_tools/__main__.py` — import `cli`, catch `GdToolsError`, print to stderr, `sys.exit(e.exit_code)`
    - [ ] Verify: all tests pass, coverage >=80%

- [ ] Task: Create supporting files
    - [ ] Create `.gitignore` with Python ignores, `.gd-tools/`, `.godot/`
    - [ ] Create `README.md` placeholder with project name, brief description, install instructions
    - [ ] Create `tests/` subdirectories with `__init__.py`: `unit/`, `integration/`, `e2e/`, `fixtures/`
    - [ ] Verify: files exist and are correctly formatted

- [ ] Task: Conductor - User Manual Verification 'Project Scaffolding' (Protocol in workflow.md)
</protect>
