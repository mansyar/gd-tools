# Contributing to gd-tools

Contributions to `gd-tools` are welcome. This guide covers development setup,
code style, testing requirements, the pull request process, project structure,
and debugging tips.

For user-facing documentation, see the [User Guide](./USER_GUIDE.md). For
coverage system internals, see the [Architecture
document](./ARCHITECTURE.md). The project follows a spec-driven development
process managed by the Conductor framework --- see `conductor/workflow.md` for
the full workflow definition.

---

## 1. Development Setup

### 1.1 Prerequisites

| Dependency | Minimum Version | Purpose |
|------------|----------------|---------|
| Python | 3.10 | Runtime |
| Godot | 4.5 | Test execution, coverage instrumentation |
| GUT | 9.5.0 | Godot test framework (installed by `gd-tools init`) |
| Git | Any recent | Version control |

### 1.2 Clone and Install

```bash
git clone https://github.com/mansyar/gd-tools.git
cd gd-tools
pip install -e ".[dev]"
```

The `.[dev]` extra installs all development dependencies: `pytest`,
`pytest-cov`, `ruff`, `black`, `build`, and `commitizen`.

### 1.3 Godot Binary Configuration

`gd-tools` needs a Godot 4.5+ binary to run tests and coverage. The tool
searches for the binary in the following order:

1. `[godot] binary` key in `gd-tools.toml`
2. `GODOT_BIN` environment variable
3. `GODOT4_BIN` environment variable
4. `GODOT_PATH` environment variable
5. System `PATH` (via `shutil.which`)
6. Common installation locations

Set the binary path via an environment variable for development:

```bash
# Linux / macOS
export GODOT_BIN=/path/to/godot

# Windows (PowerShell)
$env:GODOT_BIN = "C:\path\to\godot.exe"
```

Or configure it permanently in `gd-tools.toml`:

```toml
[godot]
binary = "/path/to/godot"
```

Verify the setup with `gd-tools doctor`:

```bash
gd-tools doctor
```

All nine checks should pass. See the [User Guide](./USER_GUIDE.md) for details
on each diagnostic check.

---

## 2. Code Style

### 2.1 Linting and Formatting

The project uses `ruff` for linting and `black` for formatting. Both enforce a
maximum line length of 80 characters.

```bash
# Lint all Python source and test files
ruff check src/ tests/

# Check formatting without modifying files
black --check src/ tests/

# Apply formatting
black src/ tests/
```

### 2.2 Naming Conventions

Follow the naming conventions from Product Guidelines section 3:

| Context | Convention | Examples |
|---------|-----------|----------|
| CLI commands and flags | `kebab-case` | `gd-tools test`, `--junit-xml`, `--report-format` |
| Python modules and functions | `snake_case` | `test_runner.py`, `run_tests()`, `find_godot()` |
| Python classes | `PascalCase` | `Config`, `GodotInfo`, `TestResult`, `LintResult` |
| Python constants | `UPPER_SNAKE_CASE` | `DEFAULT_EXCLUDES`, `GUT_VERSION_MAP` |
| GDScript classes | `PascalCase` | `_GDTCoverage`, `GDTTracker` |
| GDScript functions | `snake_case` | `hit()`, `get_data()`, `set_active()` |
| GDScript variables | `snake_case` | `file_id`, `line_id`, `hit_count` |
| Config keys (TOML) | `snake_case` | `min_percent`, `output_dir`, `test_dirs` |
| Environment variables | `UPPER_SNAKE_CASE` | `GD_TOOLS_COVERAGE_PLAN`, `GODOT_BIN` |

### 2.3 Python Style Guide

The project follows the Google Python Style Guide. Key rules:

- Maximum line length: 80 characters.
- Indentation: 4 spaces --- never tabs.
- Two blank lines between top-level definitions; one between methods.
- Docstrings on all public modules, functions, classes, and methods --- use
  `"""triple double quotes"""` with `Args:`, `Returns:`, and `Raises:`
  sections.
- Type hints on all function signatures (the project targets Python 3.10+).
- Imports grouped: standard library, third-party, then application imports ---
  each on a separate line.
- Use f-strings for string formatting.
- `TODO` comments use the format `TODO(username): description`.

See `conductor/code_styleguides/python.md` for the full summary.

### 2.4 Pre-Commit Checks

Run all quality gates before committing:

```bash
ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest
```

This chain runs lint, format check, and the full test suite. All three must
pass before a pull request is submitted.

---

## 3. Testing Requirements

### 3.1 Test Framework

The project uses `pytest` with `pytest-cov` for coverage measurement. Tests are
organized into three tiers:

| Tier | Directory | Purpose | Marker |
|------|-----------|---------|--------|
| Unit | `tests/unit/` | Isolated tests with mocked dependencies | `@pytest.mark.unit` |
| Integration | `tests/integration/` | Tests with real file I/O and fixtures | `@pytest.mark.integration` |
| End-to-end | `tests/e2e/` | Full CLI flows requiring Godot binary | `@pytest.mark.e2e` |

### 3.2 Running Tests

```bash
# Full test suite (CI mode --- single execution, no watch behavior)
CI=true pytest

# Unit tests only (fast, no external dependencies)
CI=true pytest -m unit

# Specific test file
CI=true pytest tests/unit/test_config.py

# With coverage report
CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing
```

On Windows (PowerShell), set the environment variable inline:

```powershell
$env:CI='true'; pytest -m unit -x -q
```

### 3.3 Coverage Thresholds

All source code must meet the following coverage thresholds:

- **Line coverage:** >80%
- **Branch coverage:** >70%

Coverage is measured against Python source files in `src/gd_tools/` only.
Configuration files, documentation, and GDScript addon files are excluded from
coverage measurement. The `pyproject.toml` enforces `fail_under=80`.

### 3.4 Test File Naming

Test files follow the pattern `test_<module_name>.py` and live in the
directory matching their tier:

```text
tests/unit/test_config.py          # Unit tests for src/gd_tools/config.py
tests/unit/test_plan_generator.py  # Unit tests for src/gd_tools/coverage/plan_generator.py
tests/integration/test_lint_integration.py
tests/e2e/test_full_workflow.py
```

### 3.5 Mocking Guidelines

Mock external dependencies --- never invoke real Godot binaries or network
requests in unit tests.

- **Godot subprocess:** Mock `subprocess.run` or use `unittest.mock.patch`.
- **Network requests:** Mock `requests.get` for GUT download tests.
- **File system:** Use `tmp_path` or `tmp_path_factory` fixtures for file I/O.
- **Environment variables:** Use `monkeypatch.setenv` / `monkeypatch.delenv`.

Integration tests may use real file fixtures (in `tests/fixtures/`) but should
still mock Godot subprocess invocations where possible.

### 3.6 Test Fixtures

Test fixtures live in `tests/fixtures/`:

| Fixture Directory | Contents |
|-------------------|----------|
| `fixtures/gdscript/` | Sample `.gd` files for lint, format, and coverage tests |
| `fixtures/coverage_data/` | Pre-generated coverage JSON for reporter tests |
| `fixtures/coverage_plans/` | Instrumentation plan JSON for hook tests |
| `fixtures/plans/` | Expected plan JSON for plan generator validation |
| `fixtures/junit/` | Sample JUnit XML for test runner parsing |
| `fixtures/projects/` | Minimal Godot project for integration tests |

---

## 4. Pull Request Process

### 4.1 Branch Naming

Use descriptive branch names prefixed with the change type:

```text
feat/coverage-threshold-enforcement
fix/godot-version-detection
docs/user-guide
chore/update-dependencies
```

### 4.2 Commit Message Format

Follow the Conventional Commits format defined in `conductor/workflow.md`:

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Conventional commits are enforced via CI. The `commit-check.yml` workflow
runs `cz check` on all pull requests to validate commit messages against
the Conventional Commits specification.

**Types:**

| Type | Use |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, missing semicolons, etc. |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding missing tests |
| `chore` | Maintenance tasks |

**Examples:**

```bash
git commit -m "feat(config): Implement gd-tools.toml loading and validation"
git commit -m "fix(godot): Correct Godot 4.6 version detection"
git commit -m "test(coverage): Add tests for plan generator branch detection"
git commit -m "docs(user-guide): Create comprehensive user guide with CLI reference"
```

### 4.3 Review Checklist

Before requesting review, verify:

1. **Functionality**
   - Feature works as specified in the track spec.
   - Edge cases handled.
   - Error messages are actionable with fix hints (Product Guidelines section 4).

2. **Code Quality**
   - Follows the style guide (`conductor/code_styleguides/python.md`).
   - DRY principle applied --- no unnecessary duplication.
   - Clear variable and function names (`snake_case` for Python).
   - Comments explain *why*, not *what*.

3. **Testing**
   - Unit tests comprehensive and passing.
   - Integration tests pass (if applicable).
   - Coverage meets thresholds (>80% line, >70% branch).

4. **Security**
   - No hardcoded secrets.
   - Input validation present.
   - Safe subprocess invocation --- no shell injection.
   - Safe file path handling.

5. **Documentation**
   - Docstrings on all new public functions and classes.
   - Type hints on all function signatures.
   - `plan.md` updated if working through a Conductor track.

### 4.4 CI Checks

All pull requests must pass CI. The CI pipeline runs:

1. `cz check` --- conventional commit message validation (commit-check.yml)
2. `ruff check src/ tests/` --- lint
3. `black --check src/ tests/` --- format verification
4. `CI=true pytest` --- full test suite with coverage

Coverage must remain above 80% line and 70% branch. If coverage drops, add
tests for the uncovered code paths.

---

## 5. Project Structure

```text
gd-tools/
|-- src/gd_tools/              # Python package source
|   |-- cli.py                 # Click CLI entry point (6 commands)
|   |-- config.py              # Pydantic config model for gd-tools.toml
|   |-- doctor.py              # Environment diagnostics (9 checks)
|   |-- errors.py              # Exception hierarchy and exit code mapping
|   |-- file_discovery.py      # GDScript file discovery utility
|   |-- format_runner.py       # gdformat wrapper
|   |-- godot.py               # Godot binary detection (5-level chain)
|   |-- init.py                # Project initialization (GUT, addon, config)
|   |-- lint_runner.py         # gdlint wrapper
|   |-- output.py              # Shared terminal output module (Rich-based)
|   |-- test_runner.py         # GUT test execution and JUnit parsing
|   |-- coverage/              # Coverage subsystem
|   |   |-- orchestrator.py    # Coverage flow orchestration
|   |   |-- plan_generator.py  # Lark AST traversal for instrumentation plan
|   |   |-- reporter.py        # Coverage data model and report orchestration
|   |   |-- html_reporter.py   # HTML report generation (Jinja2)
|   |   |-- lcov_reporter.py   # LCOV format output
|   |   |-- cobertura_reporter.py  # Cobertura XML output
|   |   |-- terminal_reporter.py   # Rich terminal table output
|   |   `-- templates/         # HTML report templates
|   `-- addons/gd-tools-coverage/  # GDScript coverage addon
|       |-- coverage.gd        # Instrumentation + tracker autoload
|       |-- pre_run_hook.gd    # Activates coverage tracker
|       `-- post_run_hook.gd   # Coverage data serialization
|-- tests/                     # Test suite
|   |-- unit/                  # Unit tests (mocked dependencies)
|   |-- integration/           # Integration tests (real fixtures)
|   |-- e2e/                   # End-to-end tests (require Godot)
|   `-- fixtures/              # Test fixtures (GDScript, JSON, projects)
|-- docs/                      # Project documentation
|   |-- USER_GUIDE.md          # CLI reference and user guide
|   |-- CONTRIBUTING.md        # This file
|   |-- ARCHITECTURE.md        # Coverage system architecture
|   |-- PRD.md                 # Product Requirements Document
|   |-- ROADMAP.md             # Product roadmap
|   |-- TESTING_STRATEGY.md    # Testing strategy and guidelines
|   |-- TDD.md                 # Test-driven development notes
|   `-- SPIKE_coverage_instrumentation.md  # Coverage spike document
|-- conductor/                 # Conductor project management
|   |-- index.md               # Conductor index
|   |-- product.md             # Product definition
|   |-- tech-stack.md          # Technology stack
|   |-- workflow.md            # Development workflow
|   |-- product-guidelines.md  # Product guidelines (prose, naming, errors)
|   |-- tracks.md              # Tracks registry
|   |-- tracks/                # Track specifications and plans
|   `-- code_styleguides/      # Code style guides (python.md, general.md)
|-- pyproject.toml             # Build, dependency, and tool configuration
|-- README.md                  # Project README (PyPI + GitHub)
`-- LICENSE                    # MIT License
```

### 5.1 Module Overview

Each Python module in `src/gd_tools/` maps to a specific responsibility:

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Click command definitions, flag parsing, exit code dispatch |
| `config.py` | `Config` Pydantic model, TOML loading and validation |
| `doctor.py` | `CheckResult` dataclass, nine diagnostic checks, Rich table output |
| `errors.py` | `GdToolsError` base, exit code convention (0/1/2) |
| `file_discovery.py` | Recursive GDScript file discovery with exclude support |
| `format_runner.py` | `gdtoolkit.formatter` wrapper, `FormatResult` dataclass |
| `godot.py` | `GodotInfo`, 5-level binary detection, `GUT_VERSION_MAP` |
| `init.py` | Full project bootstrap: GUT install, addon deploy, config creation |
| `lint_runner.py` | `gdtoolkit.linter` wrapper, `LintResult` dataclass |
| `output.py` | Shared terminal output module — Rich-based rendering helpers (`print_success`, `print_error`, `print_warning`, `print_info`, `print_summary`, `print_table`) and shared `Console` instance |
| `test_runner.py` | GUT argument construction, subprocess execution, JUnit parsing |
| `coverage/` | Coverage plan generation, runtime instrumentation, reporting |

For coverage system architecture details, see
[ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 6. Debugging Tips

### 6.1 Godot Binary Not Found

If `gd-tools doctor` reports "Godot Binary: FAIL":

1. Verify Godot is installed and accessible.
2. Set `GODOT_BIN` to the full path of the Godot executable.
3. On Windows, ensure the path uses forward slashes or escaped backslashes in
   TOML: `binary = "C:/path/to/godot.exe"`.
4. Run `gd-tools doctor` again to confirm detection.

### 6.2 Tests Time Out or Hang

If `pytest` hangs or times out:

- Integration and e2e tests require a Godot binary. Run unit tests only:
  `CI=true pytest -m unit -x -q`.
- Ensure `CI=true` is set --- some tests watch for file changes without it.
- On Windows, use `$env:CI='true'` rather than `CI=true` (which is not
  recognized as a shell variable).

### 6.3 Coverage Instrumentation Fails

If `gd-tools test --coverage` fails during instrumentation:

1. Verify the coverage addon is installed: check for
   `addons/gd-tools-coverage/coverage.gd` in the project.
2. Run `gd-tools init` to reinstall the addon if missing.
3. Check that the GDScript files parse without errors: run `gd-tools lint`
   before coverage.
4. Examine the instrumentation plan JSON in `.gd-tools/coverage/` for malformed
   entries.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full coverage flow and
data formats.

### 6.4 Import Errors After Installing

If `import gd_tools` fails after `pip install -e ".[dev]"`:

1. Verify the virtual environment is activated.
2. Reinstall: `pip install -e ".[dev]" --force-reinstall`.
3. Check `sys.path` includes the project root:
   ```python
   python -c "import sys; print(sys.path)"
   ```

### 6.5 Ruff or Black Conflicts

If `ruff` and `black` produce conflicting formatting suggestions:

1. Ensure both use 80-character line length (configured in `pyproject.toml`).
2. Run `black` first, then `ruff check --fix` to resolve lint issues.
3. If conflicts persist, prioritize `black` for formatting and `ruff` for
   linting rules only.

---

## 7. Additional Resources

| Resource | Location | Description |
|----------|----------|-------------|
| User Guide | [./USER_GUIDE.md](./USER_GUIDE.md) | CLI reference for all 6 commands |
| Architecture | [./ARCHITECTURE.md](./ARCHITECTURE.md) | Coverage system design and data formats |
| PRD | [./PRD.md](./PRD.md) | Product Requirements Document |
| Roadmap | [./ROADMAP.md](./ROADMAP.md) | Product development roadmap |
| Testing Strategy | [./TESTING_STRATEGY.md](./TESTING_STRATEGY.md) | Testing approach and guidelines |
| TDD Notes | [./TDD.md](./TDD.md) | Test-driven development practices |
| Workflow | `conductor/workflow.md` | Development workflow and task lifecycle |
| Product Guidelines | `conductor/product-guidelines.md` | Prose style, naming, error messages |
| Python Style Guide | `conductor/code_styleguides/python.md` | Google Python Style Guide summary |
| General Style Guide | `conductor/code_styleguides/general.md` | Readability and maintainability principles |
