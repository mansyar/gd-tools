# Testing Strategy: gd-tools

**Version:** 0.1.0 (draft)
**Date:** 2026-07-09
**Status:** Phase 1 Implementation — Track 1 Complete, Test Infrastructure Established

---

## 1. Overview

This document defines how we test `gd-tools` itself — the Python CLI, its
modules, the GDScript coverage addon, and the integration between them. The
goal is confidence: every feature should have tests that verify it works and
guard against regressions.

### Testing Principles

1. **Test behavior, not implementation.** Tests should verify what the code
   does, not how it does it. Refactoring shouldn't break tests.
2. **Fast feedback first.** Unit tests run in milliseconds without external
   dependencies. Integration tests are slower and marked separately.
3. **Fixture-driven.** GDScript sample files with known structures are the
   backbone of coverage testing. They make assertions precise and verifiable.
4. **Eat our own dog food.** `gd-tools` is tested with pytest + pytest-cov.
   We measure our own coverage with the same standards we set for users.
5. **No Godot in unit tests.** Godot is slow to launch (~1-3s) and not always
   available. Unit tests mock it. Integration tests use it.

---

## 2. Test Pyramid

```
            ┌───────────┐
            │   E2E     │   Few — full real-world scenarios
            │  (Godot)  │   (gd-tools test --coverage on sample project)
            └─────┬─────┘
            ┌─────┴─────┐
            │ Integration│   Moderate — Python + real Godot/GUT
            │  (Godot)   │   (test_runner, coverage e2e, init)
            └─────┬─────┘
        ┌─────────┴─────────┐
        │     Unit          │   Many — pure Python, mocked deps
        │  (no Godot)      │   (config, plan gen, reporters, etc.)
        └───────────────────┘
```

| Layer         | Count (est.) | Speed      | Dependencies        |
|---------------|-------------|------------|----------------------|
| Unit          | ~150-200    | <5s total  | None (all mocked)    |
| Integration   | ~20-30      | ~60s total | Godot binary, GUT    |
| E2E           | ~5-8        | ~120s total| Godot + sample project|

---

## 3. Tooling

### Python Test Stack

| Tool              | Purpose                                    |
|-------------------|--------------------------------------------|
| `pytest`          | Test runner, fixtures, parametrize         |
| `pytest-cov`      | Coverage for gd-tools Python code           |
| `pytest-mock`     | Mocking (mocker fixture)                    |
| `pytest-tmp-files`| Temporary directory fixtures (or built-in `tmp_path`) |
| `coverage`        | Coverage measurement (via pytest-cov)      |
| `freezegun`       | Mock datetime for deterministic timestamps |

### Test Discovery

```
tests/
├── unit/              # Fast, no Godot
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_godot.py
│   ├── test_plan_generator.py
│   ├── test_reporter.py
│   ├── test_html_reporter.py
│   ├── test_lcov_reporter.py
│   ├── test_cobertura_reporter.py
│   ├── test_lint_runner.py
│   ├── test_format_runner.py
│   ├── test_init.py
│   ├── test_doctor.py
│   └── test_cli.py
├── integration/       # Real Godot
│   ├── conftest.py    # Godot binary fixture, sample project
│   ├── test_test_runner.py
│   ├── test_coverage_e2e.py
│   └── test_init.py
├── e2e/               # Full scenarios
│   ├── conftest.py
│   └── test_full_workflow.py
└── fixtures/          # Shared test data
    ├── gdscript/      # Sample .gd files
    │   ├── simple.gd
    │   ├── branches.gd
    │   ├── loops.gd
    │   ├── match_stmt.gd
    │   ├── nested.gd
    │   └── edge_cases.gd
    ├── plans/         # Expected instrumentation plans
    │   ├── simple.expected.json
    │   ├── branches.expected.json
    │   └── ...
    ├── coverage_data/ # Mock coverage hits
    │   ├── full_coverage.json
    │   ├── partial_coverage.json
    │   └── zero_coverage.json
    └── projects/      # Mini Godot projects for integration
        └── sample_project/
            ├── project.godot
            ├── scripts/
            │   ├── calculator.gd
            │   └── player.gd
            └── test/
                └── test_calculator.gd
```

### pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "unit: fast tests, no external dependencies",
    "integration: requires Godot binary",
    "e2e: full end-to-end scenarios",
    "slow: tests that take >5s",
]
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
    "--cov=gd_tools",
    "--cov-report=term-missing",
    "--cov-report=html",
]

[tool.coverage.run]
source = ["gd_tools"]
omit = [
    "*/tests/*",
    "*/addons/*",  # GDScript files, not Python
]

[tool.coverage.report]
fail_under = 80
show_missing = true
```

### Running Tests

```bash
# All tests (requires Godot for integration/e2e)
pytest

# Unit tests only (fast, no Godot needed)
pytest tests/unit/ -m unit

# Integration tests only (requires Godot)
pytest tests/integration/ -m integration

# E2E only
pytest tests/e2e/ -m e2e

# Skip slow tests
pytest -m "not slow"

# With coverage report
pytest --cov=gd_tools --cov-report=html --cov-report=term

# Single test file
pytest tests/unit/test_plan_generator.py -v

# Single test
pytest tests/unit/test_plan_generator.py::test_if_else_branches -v
```

---

## 4. Unit Tests

### 4.1 `config.py` — Configuration Loading

**What to test:**
- Load valid `gd-tools.toml`, verify all fields parsed correctly
- Apply defaults for missing fields
- CLI flag overrides config values
- Invalid TOML raises `ConfigError`
- Invalid values (e.g., negative `min_percent`) raises `ConfigError`
- Config file not found → use all defaults (no error)
- Project root detection (walk up to find `project.godot`)
- Exclude list replace semantics (TOML value replaces defaults when present)

**Fixtures:**
```python
@pytest.fixture
def valid_config_toml():
    return """
    [godot]
    binary = "/usr/local/bin/godot"
    
    [test]
    test_dirs = ["test"]
    
    [coverage]
    enabled = true
    min_percent = 80
    """
```

**Key test cases:**
```python
def test_load_valid_config(tmp_path):
    """Full config with all sections loads correctly."""

def test_defaults_applied_for_missing_sections(tmp_path):
    """Missing sections get default values."""

def test_cli_overrides_config():
    """CLI --min flag overrides config min_percent."""

def test_invalid_toml_raises_config_error(tmp_path):
    """Malformed TOML raises ConfigError with helpful message."""

def test_negative_min_percent_raises(tmp_path):
    """min_percent < 0 or > 100 raises ConfigError."""

def test_project_root_detection(tmp_path):
    """Walks up from CWD to find project.godot."""

def test_exclude_list_replace(tmp_path):
    """User excludes replace, not extend, defaults."""
```

---

### 4.2 `godot.py` — Godot Binary Detection & Invocation

**What to test:**
- Binary detection resolution chain (config → env → PATH → common locations)
- Version parsing (`4.5.stable.linux` → `4.5`)
- Version comparison (4.5 vs 4.4 → error; 4.5 vs 4.6 → OK)
- `run_godot()` invokes correct subprocess args
- Timeout handling
- Binary not found → `GodotNotFoundError`

**Mocking strategy:** Mock `shutil.which`, `os.environ`, `subprocess.run`.
Never call real Godot in unit tests.

```python
def test_binary_from_config():
    """Config [godot] binary takes highest priority."""

def test_binary_from_env_var(monkeypatch):
    """GODOT_BIN env var used when config doesn't specify."""

def test_binary_from_path(monkeypatch):
    """shutil.which('godot') found on PATH."""

def test_binary_not_found_raises(monkeypatch):
    """All detection methods fail → GodotNotFoundError."""

def test_version_parsing():
    """Parses '4.5.stable.linux.123' → (4, 5)."""

def test_version_too_old_raises():
    """Godot 4.3 raises error suggesting upgrade."""

def test_version_check_passes_for_4_5_plus():
    """Godot 4.5, 4.6, 4.7 all pass."""

def test_run_godot_passes_correct_args(mocker):
    """run_godot builds correct subprocess command."""
```

---

### 4.3 `coverage/plan_generator.py` — Instrumentation Plan Generation

**This is the most critical unit test target.** Plan generation must correctly
identify all executable lines and branch points from GDScript source.

**What to test:**
- Each GDScript construct produces correct plan entries
- Line numbers are accurate (from Lark metadata)
- Branch types are correct (if_true, if_false, elif_true, loop_body, match_case)
- Declarative statements are excluded
- Multiple files in a project
- Empty file → empty plan
- File with only declarations → empty plan
- Nested structures (if inside for inside while)

**Fixtures:** GDScript sample files in `tests/fixtures/gdscript/`, with
corresponding expected plans in `tests/fixtures/plans/`.

**Key test cases:**

```python
@pytest.mark.parametrize("fixture_name", [
    "simple",       # Functions with basic statements
    "branches",     # if/elif/else
    "loops",        # while, for, for_typed
    "match_stmt",   # match/case
    "nested",       # Nested control flow
    "edge_cases",   # break, continue, pass, empty functions
])
def test_plan_generation_matches_expected(fixture_name):
    """Generated plan matches expected plan fixture."""
    source = read_fixture(f"gdscript/{fixture_name}.gd")
    expected = read_fixture(f"plans/{fixture_name}.expected.json")
    
    plan = PlanGenerator().generate(source, "res://test.gd")
    
    assert plan.to_dict() == json.loads(expected)


def test_empty_file_produces_empty_plan():
    """File with no executable code → empty lines list."""

def test_declarations_not_tracked():
    """const, signal, enum, class_var, func_def excluded."""

def test_assignment_is_expr_stmt():
    """'x = 5' inside a function is tracked as expr_stmt."""

def test_func_var_with_assignment_tracked():
    """'var x = 5' tracked; 'var x' not tracked."""

def test_branch_ids_are_unique_per_file():
    """Each line entry has a unique ID within its file."""

def test_if_else_produces_two_branch_entries():
    """if true branch and else false branch both tracked."""

def test_elif_produces_additional_branch():
    """elif branch tracked as elif_true."""

def test_while_loop_body_tracked():
    """While loop body entry tracked as loop_body."""

def test_for_loop_body_tracked():
    """For loop body entry tracked as loop_body."""

def test_match_each_case_tracked():
    """Each match case tracked as match_case."""

def test_nested_control_flow():
    """If inside for inside while — all tracked correctly."""

def test_multiple_files_in_project():
    """Multiple .gd files → multiple file entries in plan."""

def test_source_hash_computed():
    """Plan includes SHA-256 hash of source for staleness detection."""
```

**Fixture example — `branches.gd`:**
```gdscript
extends Node

func check_value(x: int) -> String:
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
```

**Fixture example — `branches.expected.json`:**
```json
{
  "version": 1,
  "files": [
    {
      "path": "res://test.gd",
      "lines": [
        {"line": 4, "id": 0, "type": "branch", "branch_type": "if_true"},
        {"line": 5, "id": 1, "type": "statement"},
        {"line": 6, "id": 2, "type": "branch", "branch_type": "elif_true"},
        {"line": 7, "id": 3, "type": "statement"},
        {"line": 9, "id": 4, "type": "branch", "branch_type": "if_false"},
        {"line": 10, "id": 5, "type": "statement"}
      ]
    }
  ]
}
```

---

### 4.4 `coverage/reporter.py` — Coverage Computation

**What to test:**
- Line coverage % (hits / total executable lines)
- Branch coverage % (branches hit / total branches)
- Per-file and overall aggregation
- `--min` threshold enforcement
- Source hash mismatch detection (source changed since plan generated)
- Empty coverage data (0% coverage)
- Full coverage data (100%)

**Fixtures:** Mock coverage data in `tests/fixtures/coverage_data/`.

```python
def test_line_coverage_calculation():
    """15 of 20 lines hit → 75% coverage."""

def test_branch_coverage_calculation():
    """3 of 5 branches hit → 60% branch coverage."""

def test_aggregate_coverage_across_files():
    """Multiple files aggregated into overall percentage."""

def test_threshold_pass():
    """Coverage above min_percent → no error."""

def test_threshold_fail():
    """Coverage below min_percent → CoverageThresholdError."""

def test_zero_coverage():
    """No hits at all → 0% coverage reported correctly."""

def test_full_coverage():
    """All lines hit → 100% coverage."""

def test_source_hash_mismatch_warning():
    """Source changed since plan generated → warning."""
```

---

### 4.5 Coverage Reporters (HTML, LCOV, Cobertura)

**What to test:**

**HTML (`html_reporter.py`):**
- Generated HTML is valid
- Source code is rendered with syntax highlighting
- Covered/uncovered lines have correct CSS classes
- File list index page generated
- Branch coverage annotations present

**LCOV (`lcov_reporter.py`):**
- Output conforms to LCOV format specification
- `SF:` (source file), `DA:` (data, line + hit count), `BRDA:` (branch data)
- `LF:` (lines found), `LH:` (lines hit), `BRF:`, `BRH:`
- `end_of_record` delimiter present

**Cobertura (`cobertura_reporter.py`):**
- Valid XML
- `<coverage>` root with `line-rate` and `branch-rate` attributes
- `<class>` elements per file
- `<line>` elements with `hits` and `branch` attributes

```python
def test_html_report_has_file_index():
    """HTML report includes index.html listing all files."""

def test_html_report_highlights_uncovered_lines():
    """Uncovered lines have 'uncovered' CSS class."""

def test_lcov_format_compliance():
    """Output passes lcov format validation."""

def test_lcov_includes_branch_data():
    """BRDA records present for branch points."""

def test_cobertura_valid_xml():
    """Output is valid XML, parseable by ElementTree."""

def test_cobertura_line_rate_attribute():
    """<coverage> element has correct line-rate value."""
```

---

### 4.6 `lint_runner.py` & `format_runner.py` — Tool Wrappers

**What to test:**
- Correct subprocess invocation (args, flags)
- Exclude list passed to gdlint/gdformat
- `--check` flag for format (CI mode)
- Exit code propagation
- stderr capture and formatting
- No files found → graceful message, exit 0

**Mocking strategy:** Mock `subprocess.run` to return canned results.

```python
def test_lint_invokes_gdlint_with_correct_args(mocker):
    """gdlint called with correct file paths."""

def test_lint_respects_exclude_list(mocker):
    """Excluded directories not passed to gdlint."""

def test_lint_exit_code_on_errors(mocker):
    """gdlint exit 1 → gd-tools exit 1."""

def test_lint_no_files_found():
    """No .gd files → message, exit 0."""

def test_format_check_mode(mocker):
    """--check flag passed to gdformat."""

def test_format_exit_code_on_unformatted(mocker):
    """gdformat --check finds unformatted → exit 1."""

def test_format_diff_output(mocker):
    """--diff shows diff of changes."""
```

---

### 4.7 `init.py` — Project Bootstrapping

**What to test:**
- GUT not installed → download correct version for Godot version
- GUT already installed → version check, no re-download
- Coverage addon files copied
- `project.godot` plugin enabling (idempotent)
- `.gutconfig.json` created/merged
- `gd-tools.toml` created (preserving existing)
- `.gd-tools/` created + added to `.gitignore`
- Network failure during GUT download → error with retry hint

**Mocking strategy:** Mock `requests.get` (network), `shutil.which` /
`subprocess.run` (Godot), use `tmp_path` for filesystem.

```python
def test_init_gut_not_installed_downloads(mocker, tmp_path):
    """GUT absent → downloads correct version for detected Godot."""

def test_init_gut_already_installed(mocker, tmp_path):
    """GUT present → no download, version compatibility checked."""

def test_init_gut_version_mismatch_warning(mocker, tmp_path):
    """Incompatible GUT version → warning printed."""

def test_init_copies_coverage_addon(tmp_path):
    """Coverage addon files copied to addons/gd-tools-coverage/."""

def test_init_enables_plugin_in_project_godot(tmp_path):
    """[editor_plugins] added to project.godot."""

def test_init_plugin_enabling_idempotent(tmp_path):
    """Running init twice doesn't duplicate plugin entry."""

def test_init_creates_gutconfig(tmp_path):
    """.gutconfig.json created with coverage hook paths."""

def test_init_merges_existing_gutconfig(tmp_path):
    """Existing .gutconfig.json preserved, hooks added."""

def test_init_creates_gd_tools_toml(tmp_path):
    """gd-tools.toml created with defaults."""

def test_init_preserves_existing_config(tmp_path):
    """Existing gd-tools.toml not overwritten."""

def test_init_creates_gdtools_dir_and_gitignore(tmp_path):
    """.gd-tools/ created, added to .gitignore."""

def test_init_network_failure(mocker, tmp_path):
    """GUT download fails → error with retry instructions."""
```

---

### 4.8 `doctor.py` — Diagnostics

**What to test:**
- All checks run and report correct status
- Each check can pass/fail independently
- Actionable suggestions for failures
- Exit code (0 if all pass, 1 if any fail)

```python
def test_doctor_all_pass(mocker, tmp_path):
    """Healthy environment → all checks pass, exit 0."""

def test_doctor_godot_not_found(mocker):
    """Godot binary missing → that check fails, suggestion shown."""

def test_doctor_gut_not_installed(mocker, tmp_path):
    """GUT missing → check fails, 'run gd-tools init' suggested."""

def test_doctor_gut_version_mismatch(mocker, tmp_path):
    """GUT version wrong → warning, correct version suggested."""

def test_doctor_coverage_addon_missing(mocker, tmp_path):
    """Coverage addon files absent → check fails."""

def test_doctor_gdlintrc_missing(mocker, tmp_path):
    """gdlintrc absent → check fails, 'run gd-tools init' suggested."""
```

---

### 4.9 `cli.py` — Command Interface

**What to test:**
- Each command exists and accepts expected flags
- Help text is present and accurate
- Exit codes propagate from underlying logic
- `--version` prints version
- `--help` works for all commands and subcommands
- Config file loading from various locations
- Non-interactive mode (`--non-interactive`) doesn't prompt

**Using Click's test runner:**
```python
from click.testing import CliRunner
from gd_tools.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_cli_version(runner):
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'gd-tools' in result.output

def test_test_command_help(runner):
    result = runner.invoke(cli, ['test', '--help'])
    assert '--coverage' in result.output
    assert '--min' in result.output

def test_doctor_non_interactive(runner, mocker):
    """--non-interactive flag prevents prompts."""
```

---

## 5. Integration Tests

Integration tests require a real Godot binary and GUT installation. They are
slower (~2-5s each due to Godot startup) and marked with `@pytest.mark.integration`.

### 5.1 Test Environment

```python
# tests/integration/conftest.py

import pytest
import shutil
from pathlib import Path

@pytest.fixture(scope="session")
def godot_binary():
    """Find Godot binary or skip integration tests."""
    binary = shutil.which("godot") or shutil.which("godot4")
    if not binary:
        pytest.skip("Godot binary not found — skipping integration tests")
    return binary

@pytest.fixture(scope="session")
def sample_project(tmp_path_factory):
    """Create a mini Godot project with GUT installed."""
    project_dir = tmp_path_factory.mktemp("godot_project")
    # Copy project.godot, scripts/, test/ from fixtures
    # Install GUT (or use pre-installed copy)
    return project_dir
```

### 5.2 `test_test_runner.py` — GUT Orchestration

**What to test:**
- `gd-tools test` runs GUT and produces correct exit code
- JUnit XML output is parseable and contains expected test results
- `--suite` filters correctly
- `--test` filters by name
- Test failure → exit code 1
- `--no-exit-code` → exit 0 even on failures
- Godot crashes → meaningful error

```python
@pytest.mark.integration
class TestTestRunner:
    def test_passing_tests_exit_zero(self, sample_project, godot_binary):
        """All-passing test suite → exit 0."""

    def test_failing_tests_exit_one(self, sample_project, godot_binary):
        """Test with failures → exit 1."""

    def test_junit_xml_generated(self, sample_project, godot_binary):
        """JUnit XML file created and parseable."""

    def test_suite_filter(self, sample_project, godot_binary):
        """--suite runs only matching suite."""

    def test_name_filter(self, sample_project, godot_binary):
        """--test runs only matching test names."""

    def test_no_exit_code_flag(self, sample_project, godot_binary):
        """--no-exit-code → exit 0 regardless of test results."""
```

---

### 5.3 `test_coverage_e2e.py` — Full Coverage Pipeline

**This is the most important integration test.** It verifies the entire
Architecture C flow end-to-end.

**What to test:**
- Plan generation produces correct instrumentation points
- GDScript addon instruments scripts at runtime
- Coverage data is collected and saved
- Reports are generated correctly
- Coverage percentages match expected values

```python
@pytest.mark.integration
@pytest.mark.slow
class TestCoverageE2E:
    def test_full_coverage_flow(self, sample_project, godot_binary):
        """End-to-end: plan → instrument → test → collect → report."""
        # 1. Generate plan
        plan = generate_plan(sample_project / "scripts")
        assert len(plan.files) > 0
        
        # 2. Run tests with coverage
        result = run_gd_tools_test(
            sample_project,
            coverage=True,
            godot_binary=godot_binary
        )
        assert result.exit_code == 0
        
        # 3. Verify coverage data exists
        coverage_data = read_coverage_json(sample_project)
        assert coverage_data is not None
        
        # 4. Generate report
        report = generate_report(coverage_data, plan)
        
        # 5. Verify coverage matches expected
        # (all lines in simple test should be covered)
        assert report.overall_line_coverage == 100.0

    def test_partial_coverage(self, sample_project, godot_binary):
        """Some code paths not exercised → < 100% coverage."""
        
    def test_branch_coverage_tracking(self, sample_project, godot_binary):
        """Both branches of if/else tracked."""
        
    def test_html_report_generated(self, sample_project, godot_binary):
        """HTML report files exist and contain expected content."""
        
    def test_lcov_report_format(self, sample_project, godot_binary):
        """LCOV output is parseable by geninfo/lcov tools."""
        
    def test_threshold_enforcement(self, sample_project, godot_binary):
        """--min 90 with 80% coverage → exit 1."""
```

---

### 5.4 `test_init.py` — Real Bootstrapping

**What to test:**
- `gd-tools init` on a fresh project installs GUT correctly
- Godot can launch after init (plugin enabled)
- Coverage addon files are present and functional

```python
@pytest.mark.integration
class TestInit:
    def test_init_fresh_project(self, tmp_path, godot_binary):
        """Init on project without GUT → GUT installed and enabled."""
        
    def test_init_project_with_existing_gut(self, tmp_path, godot_binary):
        """Init on project with GUT → no re-download."""
        
    def test_init_idempotent(self, tmp_path, godot_binary):
        """Running init twice → no errors, no duplicates."""
```

---

## 6. E2E Tests

Full scenario tests that exercise the entire CLI as a user would.

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestFullWorkflow:
    def test_init_lint_format_test_coverage(self, tmp_path, godot_binary):
        """Complete user journey: init → lint → format → test --coverage."""
        # 1. Copy sample project
        # 2. gd-tools init
        # 3. gd-tools lint (exit 0)
        # 4. gd-tools format --check (exit 0)
        # 5. gd-tools test --coverage --min 80 (exit 0)
        # 6. gd-tools coverage show (displays summary)
        # 7. gd-tools coverage report --format lcov (file generated)

    def test_doctor_on_fresh_project(self, tmp_path, godot_binary):
        """gd-tools doctor before init → reports missing components."""
        
    def test_doctor_after_init(self, tmp_path, godot_binary):
        """gd-tools doctor after init → all checks pass."""
```

---

## 7. Test Fixtures

### 7.1 GDScript Sample Files

Each fixture exercises specific grammar constructs. These are the backbone
of plan generation testing.

#### `fixtures/gdscript/simple.gd`

```gdscript
extends Node

var health: int = 100
const MAX_HP: int = 200

func take_damage(amount: int) -> void:
    health -= amount

func is_alive() -> bool:
    return health > 0
```

**Expected tracked lines:** `health -= amount` (expr_stmt), `return health > 0`
(return_stmt). `var health` and `const MAX_HP` are declarative → not tracked.

---

#### `fixtures/gdscript/branches.gd`

```gdscript
extends Node

func classify(x: int) -> String:
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"

func nested_check(a: int, b: int) -> bool:
    if a > 0:
        if b > 0:
            return true
        else:
            return false
    else:
        return false
```

**Expected:** if_true, elif_true, if_false branches for `classify`. Nested
if/else branches for `nested_check`.

---

#### `fixtures/gdscript/loops.gd`

```gdscript
extends Node

func sum_array(arr: Array) -> int:
    var total: int = 0
    for item in arr:
        total += item
    return total

func count_down(n: int) -> void:
    var i: int = n
    while i > 0:
        print(i)
        i -= 1

func find_first(values: Array, target: Variant) -> int:
    for i: int in range(values.size()):
        if values[i] == target:
            return i
    return -1
```

**Expected:** `for` loop body tracked as `loop_body`, `while` body tracked as
`loop_body`. `var total` with assignment tracked; `var i` with assignment
tracked.

---

#### `fixtures/gdscript/match_stmt.gd`

```gdscript
extends Node

func handle_state(state: String) -> void:
    match state:
        "idle":
            print("Idling")
        "running":
            print("Running")
        "jumping":
            print("Jumping")
        _:
            print("Unknown state")
```

**Expected:** Each `match_branch` tracked as `match_case` (4 cases).

---

#### `fixtures/gdscript/nested.gd`

```gdscript
extends Node

func complex_logic(items: Array) -> Dictionary:
    var result: Dictionary = {}
    for item in items:
        if item is Dictionary:
            if item.has("type"):
                match item["type"]:
                    "weapon":
                        result["weapons"] = result.get("weapons", 0) + 1
                    "armor":
                        result["armor"] = result.get("armor", 0) + 1
                    _:
                        continue
            else:
                continue
        elif item is Array:
            result["arrays"] = result.get("arrays", 0) + 1
    return result
```

**Expected:** Deeply nested control flow — for loop body, if/elif/else branches,
match cases, continue statements all tracked at correct line numbers.

---

#### `fixtures/gdscript/edge_cases.gd`

```gdscript
extends Node

signal health_changed(new_value: int)

enum State { IDLE, RUNNING, JUMPING }

func empty_function() -> void:
    pass

func with_break(arr: Array) -> int:
    for i in arr:
        if i == 42:
            break
        print(i)
    return 0

func with_continue(arr: Array) -> void:
    for i in arr:
        if i % 2 == 0:
            continue
        print(i)

func ternary(x: int) -> String:
    return "positive" if x > 0 else "non-positive"
```

**Expected:** `pass` not tracked. `break` tracked. `continue` tracked. Ternary
tracked as return_stmt (GDScript ternary is an expression). `signal`, `enum`
not tracked.

---

### 7.2 Mock Coverage Data

#### `fixtures/coverage_data/full_coverage.json`

```json
{
  "version": 1,
  "generated_at": "2026-07-09T12:00:00Z",
  "files": [
    {
      "path": "res://scripts/calculator.gd",
      "hits": {
        "0": 10, "1": 5, "2": 5, "3": 3, "4": 2
      }
    }
  ]
}
```

#### `fixtures/coverage_data/partial_coverage.json`

```json
{
  "version": 1,
  "generated_at": "2026-07-09T12:00:00Z",
  "files": [
    {
      "path": "res://scripts/calculator.gd",
      "hits": {
        "0": 10, "1": 5, "2": 0, "3": 0, "4": 0
      }
    }
  ]
}
```

#### `fixtures/coverage_data/zero_coverage.json`

```json
{
  "version": 1,
  "generated_at": "2026-07-09T12:00:00Z",
  "files": [
    {
      "path": "res://scripts/calculator.gd",
      "hits": {}
    }
  ]
}
```

---

### 7.3 Sample Integration Project

A minimal Godot project for integration/E2E tests:

```
fixtures/projects/sample_project/
├── project.godot
├── scripts/
│   ├── calculator.gd       # Simple class with add/subtract/multiply
│   └── player.gd           # Class with health, take_damage, is_alive
├── test/
│   ├── test_calculator.gd   # GUT tests for calculator
│   └── test_player.gd       # GUT tests for player
└── addons/
    └── gut/                  # Installed by test setup or git submodule
```

**`scripts/calculator.gd`:**
```gdscript
extends RefCounted

func add(a: int, b: int) -> int:
    return a + b

func subtract(a: int, b: int) -> int:
    return a - b

func divide(a: int, b: int) -> float:
    if b == 0:
        push_error("Cannot divide by zero")
        return 0.0
    return float(a) / float(b)
```

**`test/test_calculator.gd`:**
```gdscript
extends GutTest

var calc = null

func before_each():
    calc = Calculator.new()

func test_add():
    assert_eq(calc.add(2, 3), 5)

func test_subtract():
    assert_eq(calc.subtract(5, 3), 2)

func test_divide_normal():
    assert_eq(calc.divide(10, 2), 5.0)

func test_divide_by_zero():
    # Tests the error branch
    assert_eq(calc.divide(10, 0), 0.0)
```

---

## 8. Mocking Strategy

### What to Mock

| Component         | Unit Tests         | Integration Tests  | E2E Tests       |
|-------------------|--------------------|--------------------|-----------------|
| `subprocess.run`  | Mock (no Godot)    | Real (Godot runs)  | Real             |
| `requests.get`    | Mock (no network)  | Real (downloads)   | Real             |
| `shutil.which`    | Mock (control PATH) | Real               | Real             |
| `os.environ`      | Mock (monkeypatch)  | Real               | Real             |
| Filesystem        | `tmp_path`         | `tmp_path`         | `tmp_path`      |
| `gdtoolkit.parse` | Real (fast, pure)  | Real               | Real             |
| Godot binary      | N/A (mocked away)  | Real               | Real             |

### Mocking Patterns

```python
# Subprocess mocking for Godot invocation
mocker.patch("subprocess.run", return_value=CompletedProcess(
    args=["godot", "--version"],
    returncode=0,
    stdout="4.5.stable.win\n",
    stderr=""
))

# Network mocking for GUT download
mock_response = mocker.Mock()
mock_response.status_code = 200
mock_response.content = b"fake-zip-data"
mocker.patch("requests.get", return_value=mock_response)

# Environment variable mocking
monkeypatch.setenv("GODOT_BIN", "/fake/godot")
monkeypatch.delenv("GODOT_BIN", raising=False)
```

---

## 9. CI/CD Test Pipeline

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -m unit --cov=gd_tools --cov-report=xml
      - uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Godot
        run: |
          wget https://github.com/godotengine/godot/releases/download/4.5-stable/Godot_v4.5-stable_linux.x86_64.zip
          unzip Godot_v4.5-stable_linux.x86_64.zip
          sudo mv Godot_v4.5-stable_linux.x86_64 /usr/local/bin/godot
          sudo chmod +x /usr/local/bin/godot
      - run: pip install -e ".[dev]"
      - run: pytest tests/integration/ -m integration
      - run: pytest tests/e2e/ -m e2e

  matrix:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -m unit
```

### Test Stage Gating

```
Unit Tests (fast, no Godot)
    │
    ├── PASS → Integration Tests (real Godot)
    │           │
    │           ├── PASS → E2E Tests (full workflow)
    │           │           │
    │           │           └── PASS → Deploy / Release
    │           │
    │           └── FAIL → Block
    │
    └── FAIL → Block (fast feedback, no point running slow tests)
```

---

## 10. Coverage for gd-tools Itself

We practice what we preach. `gd-tools` Python code is measured with
`pytest-cov`.

### Targets

| Metric         | Target | Enforcement            |
|----------------|--------|------------------------|
| Line coverage  | ≥ 80%  | CI fails below threshold |
| Branch coverage| ≥ 70%  | CI warns below threshold  |

### Exclusions from Our Own Coverage

```toml
[tool.coverage.run]
omit = [
    "*/tests/*",
    "*/addons/*",          # GDScript, not Python
    "gd_tools/__init__.py", # Usually just imports
]
```

### What Must Be Covered

- **Critical paths:** plan generation (100% — it's the core feature),
  coverage computation, threshold enforcement
- **Config parsing:** all config keys, defaults, overrides, error cases
- **Binary detection:** all resolution chain levels, failure paths
- **Report generation:** all output formats

### What Can Have Lower Coverage

- `init.py` network operations (hard to test all failure modes)
- `doctor.py` (mostly integration — unit tests cover individual checks)
- CLI help text formatting

---

## 11. Test Data Management

### Fixture Loading Helper

```python
# tests/conftest.py

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def read_fixture():
    def _read(rel_path: str) -> str:
        path = FIXTURES_DIR / rel_path
        return path.read_text(encoding="utf-8")
    return _read

@pytest.fixture
def read_json_fixture():
    def _read(rel_path: str) -> dict:
        path = FIXTURES_DIR / rel_path
        return json.loads(path.read_text(encoding="utf-8"))
    return _read
```

### GDScript Fixture Generation

For maintainability, expected plan fixtures can be auto-generated and
manually verified:

```python
# tools/generate_expected_plans.py
"""Regenerate expected plan fixtures from GDScript fixtures.

Run after modifying GDScript fixtures. Manually verify the output before
committing.
"""
def regenerate():
    fixtures = FIXTURES_DIR / "gdscript"
    for gd_file in fixtures.glob("*.gd"):
        source = gd_file.read_text()
        plan = PlanGenerator().generate(source, f"res://{gd_file.name}")
        expected_path = FIXTURES_DIR / "plans" / f"{gd_file.stem}.expected.json"
        expected_path.write_text(json.dumps(plan.to_dict(), indent=2))
```

---

## 12. Test Maintenance

### When GDScript Fixtures Change

1. Modify the `.gd` fixture file
2. Run `python tools/generate_expected_plans.py` to regenerate expected plans
3. **Manually verify** the diff — ensure new line numbers/types are correct
4. Commit both the fixture and expected plan together

### When Grammar Changes (gdtoolkit update)

1. Bump `gdtoolkit` version in `pyproject.toml`
2. Run full test suite — plan generation tests will catch grammar changes
3. Update expected plans if line numbers shift
4. Check for new statement types in grammar that should be tracked

### When Adding New Features

1. Write the test first (TDD where practical)
2. Ensure both success and failure paths are tested
3. Add integration test if feature touches Godot/GUT
4. Update this document if testing patterns change

---

## 13. Test Checklist (Per Module)

Before marking any module as "done," verify:

- [ ] Unit tests pass for all public functions
- [ ] Error paths tested (invalid input, missing files, etc.)
- [ ] Edge cases tested (empty input, single item, large input)
- [ ] Mocking verified — no real external calls in unit tests
- [ ] Integration test covers the happy path
- [ ] Exit codes verified
- [ ] Output format verified (JSON, XML, HTML as applicable)
- [ ] Docstrings/examples in tests explain intent
