# TDD: gd-tools — Technical Design Document

**Version:** 0.1.0 (draft)
**Date:** 2026-07-08
**Status:** Phase 3 In Progress — Coverage Tracker Addon delivered (Track 10)
**Companion to:** `PRD.md`, `SPIKE_coverage_instrumentation.md`

---

## 1. Overview

This document specifies the technical design for `gd-tools`: module
architecture, function signatures, data structures, error handling, and the
Python↔GDScript interface contracts. It bridges the PRD (what we build) and the
implementation (how we code it).

### Design Principles

- **Type safety first** — Pydantic models for all config and data contracts.
- **Single responsibility** — Each module has one job; dependencies flow one
  direction (no circular imports).
- **Fail fast, fail loud** — Validate inputs at boundaries; raise typed
  exceptions with actionable messages.
- **Testable** — Pure functions where possible; I/O isolated to specific
  modules for mocking.

---

## 2. Module Architecture

```
src/gd_tools/
├── __init__.py
├── __main__.py               # Entry: python -m gd_tools
├── cli.py                    # Click CLI definitions
├── config.py                 # Pydantic models for gd-tools.toml
├── godot.py                  # Godot binary detection + invocation
├── init.py                   # `gd-tools init` bootstrap flow
├── doctor.py                 # `gd-tools doctor` diagnostics
├── test_runner.py            # `gd-tools test` — GUT orchestration
├── lint_runner.py            # `gd-tools lint` — gdlint wrapper
├── format_runner.py          # `gd-tools format` — gdformat wrapper
├── errors.py                 # Exception hierarchy
├── coverage/
│   ├── __init__.py
│   ├── plan_generator.py     # Lark AST → instrumentation plan (JSON)
│   ├── reporter.py           # Coverage data → report dispatch
│   ├── html_reporter.py     # Jinja2 HTML report
│   ├── lcov_reporter.py      # LCOV format
│   └── cobertura_reporter.py # Cobertura XML
└── addons/
    └── gd-tools-coverage/
        ├── coverage.gd       # Autoload singleton — hit tracking
        ├── pre_run_hook.gd   # GUT pre-run hook — instruments scripts
        └── post_run_hook.gd  # GUT post-run hook — saves coverage JSON
```

### Dependency Graph

```
cli.py
├── config.py
├── godot.py
├── init.py (→ config, godot)
├── doctor.py (→ config, godot)
├── test_runner.py (→ config, godot, coverage/plan_generator, coverage/reporter)
├── lint_runner.py (→ config)
└── format_runner.py (→ config)

coverage/plan_generator.py → gdtoolkit (external)
coverage/reporter.py → coverage/html_reporter, coverage/lcov_reporter, coverage/cobertura_reporter
```

No circular dependencies. `config.py` and `godot.py` are leaf modules with no
internal dependencies.

---

## 3. Module Specifications

### 3.1 `errors.py` — Exception Hierarchy

> **Implemented:** Track 1 (scaffolding_20260709). See `src/gd_tools/errors.py`.
> The constructor accepts a message and an optional keyword-only `exit_code`
> override. `TestFailureError` has `__test__ = False` to prevent pytest
> collection.

```python
class GdToolsError(Exception):
    """Base exception for all gd-tools errors."""
    exit_code: int = 2

class ConfigError(GdToolsError):
    """Configuration file missing, invalid, or incomplete."""

class GodotNotFoundError(GdToolsError):
    """Godot binary not found via detection chain."""

class GUTNotInstalledError(GdToolsError):
    """GUT addon not present in project."""

class CoveragePlanError(GdToolsError):
    """Failed to generate or parse instrumentation plan."""

class CoverageThresholdError(GdToolsError):
    """Coverage below minimum threshold."""
    exit_code: int = 1

class TestFailureError(GdToolsError):
    """One or more tests failed."""
    exit_code: int = 1

class LintError(GdToolsError):
    """Linting found errors (not warnings)."""
    exit_code: int = 1

class FormatError(GdToolsError):
    """Formatting failed or files need formatting (--check mode)."""
    exit_code: int = 1
```

**Usage pattern:** CLI commands catch `GdToolsError`, print message to stderr,
and `sys.exit(e.exit_code)`. Unknown exceptions propagate (bug report).

---

### 3.2 `config.py` — Configuration

#### Pydantic Models

```python
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_EXCLUDES = ["addons", ".godot", ".gd-tools", ".git"]

class GodotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    binary: str | None = None  # Path to Godot binary; None = auto-detect

class TestConfig(BaseModel):
    __test__ = False  # Prevent pytest from collecting this as a test class
    model_config = ConfigDict(extra="forbid")
    test_dirs: list[str] = Field(default_factory=lambda: ["test", "tests"])
    prefix: str = "test_"
    suffix: str = ".gd"
    gutconfig: str = ".gutconfig.json"

class LintConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exclude: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDES.copy())

class FormatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exclude: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDES.copy())

class CoverageConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    min_percent: int = 0
    format: str = "html"  # html | lcov | cobertura | text
    output_dir: str = ".gd-tools/coverage"
    exclude: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDES.copy())
    test_dirs: list[str] = Field(default_factory=lambda: ["test", "tests"])

class GdToolsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    godot: GodotConfig = Field(default_factory=GodotConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    lint: LintConfig = Field(default_factory=LintConfig)
    format: FormatConfig = Field(default_factory=FormatConfig)
    coverage: CoverageConfig = Field(default_factory=CoverageConfig)

    @field_validator("coverage")
    @classmethod
    def validate_coverage(cls, v: CoverageConfig) -> CoverageConfig:
        if v.format not in ("html", "lcov", "cobertura", "text"):
            raise ValueError(f"Invalid coverage format: {v.format}")
        if not 0 <= v.min_percent <= 100:
            raise ValueError(f"min_percent must be 0-100, got {v.min_percent}")
        return v
```

All models use `extra="forbid"` to reject unknown keys — catches typos like `[covrage]`.
Exclude lists use **replace** semantics: if the `exclude` key is present in TOML, it
replaces `DEFAULT_EXCLUDES`; if absent, `DEFAULT_EXCLUDES` from code is used.

#### Functions

```python
def find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (default: CWD) to find nearest project.godot.
    Raises ConfigError if not found."""

def load_config(project_root: Path | None = None) -> GdToolsConfig:
    """Load gd-tools.toml from project root. Returns defaults if file missing.
    Raises ConfigError if file exists but is invalid TOML or fails validation."""

def save_config(config: GdToolsConfig, project_root: Path) -> None:
    """Write gd-tools.toml. Used by `gd-tools init`."""

def generate_gdlintrc(config: GdToolsConfig, project_root: Path) -> None:
    """Generate gdlintrc from [lint] exclude list. Overwrites if exists."""

def generate_gdformatrc(config: GdToolsConfig, project_root: Path) -> None:
    """Generate gdformatrc from [format] exclude list. Overwrites if exists."""
```

#### Config File Resolution

1. Walk up from CWD to find `project.godot` → that's project root.
2. Look for `gd-tools.toml` in project root.
3. If found → parse with `tomllib` (Python 3.11+) or `tomli` (backport) →
   validate with Pydantic.
4. If not found → return `GdToolsConfig()` with all defaults.

---

### 3.3 `godot.py` — Godot Binary Detection & Invocation

> **Implemented:** Track 3 (`godot-detection_20260710`, archived). See
> `src/gd_tools/godot.py`. All 6 success criteria passed. Key deviation from
> the original design below: `find_godot_binary()` was renamed to
> `find_godot()` and returns `GodotInfo` (not `str`). Added `_is_executable()`
> and `_build_not_found_message()` helpers.

#### Binary Detection

```python
def find_godot(config: GodotConfig) -> GodotInfo:
    """Resolve Godot binary path via priority chain.
    Returns GodotInfo (path, version, is_valid).
    Raises GodotNotFoundError if not found."""

def _check_config(config: GodotConfig) -> str | None:
    """Check gd-tools.toml [godot] binary setting."""

def _check_env_vars() -> str | None:
    """Check GODOT_BIN, GODOT4_BIN, GODOT_PATH env vars."""

def _check_path() -> str | None:
    """Check shutil.which('godot'), shutil.which('godot4')."""

def _check_common_locations() -> str | None:
    """Platform-specific common install paths."""

def get_godot_version(binary: str) -> str:
    """Run `godot --version`, return version string (e.g., '4.5.1').
    Raises GodotNotFoundError if binary fails to run."""

def check_version_compatible(version: str) -> bool:
    """Return True if version >= 4.5.0."""
```

#### Detection Chain (priority order)

1. `config.godot.binary` (user-specified in `gd-tools.toml`)
2. Env vars: `GODOT_BIN` → `GODOT4_BIN` → `GODOT_PATH`
3. `shutil.which("godot")` → `shutil.which("godot4")`
4. Common install locations (platform-specific):
   - **Windows:** `C:\Program Files\Godot\`, `%LOCALAPPDATA%\Godot\`,
     Scoop (`~\scoop\apps\godot\`), Chocolatey, Steam
   - **macOS:** `/Applications/Godot.app/Contents/MacOS/Godot`,
     `/opt/homebrew/bin/godot`
   - **Linux:** `~/.local/bin/godot`, `/usr/bin/godot`, `/usr/local/bin/godot`
5. Not found → `GodotNotFoundError` with platform-specific install instructions

#### GUT Version Mapping

```python
GUT_VERSION_MAP = {
    "4.5": "9.5.0",
    "4.6": "9.6.0",
    "4.7": "9.7.0",
}

def get_gut_version_for_godot(godot_version: str) -> str:
    """Map Godot version to compatible GUT version.
    Uses major.minor prefix (e.g., '4.5.1' → '4.5' → '9.5.0').
    Raises ConfigError if Godot version not in map."""
```

#### Godot Invocation

```python
def run_godot(
    binary: str,
    project_path: Path,
    args: list[str],
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Invoke Godot with given args. Sets --path to project_path.
    Merges env with current environment. Returns completed process.
    Raises subprocess.TimeoutExpired if timeout exceeded."""
```

---

### 3.4 `cli.py` — CLI Definitions (Click)

> **Implemented (stubs):** Track 1 (scaffolding_20260709). See
> `src/gd_tools/cli.py`. All commands raise `NotImplementedError`, caught by
> a custom `GdToolsGroup` class that exits with code 2. Full implementation
> in Tracks 4-8, 13.

```python
import click

@click.group()
@click.version_option()
def cli():
    """gd-tools — GDScript development toolkit."""

@cli.command()
@click.option("--non-interactive", is_flag=True, help="Skip prompts, use defaults")
def init(non_interactive: bool):
    """Bootstrap project: install GUT, coverage addon, generate configs."""

@cli.command()
def doctor():
    """Diagnose environment and configuration."""

@cli.command()
@click.option("--coverage", is_flag=True, help="Enable coverage instrumentation")
@click.option("--min", "min_percent", type=int, help="Min coverage % to pass")
@click.option("--suite", type=str, help="Run only named suite")
@click.option("--test", "test_name", type=str, help="Run tests matching name")
@click.option("--junit-xml", type=str, help="JUnit XML output path")
@click.option("--no-exit-code", is_flag=True, help="Always exit 0")
def test(coverage, min_percent, suite, test_name, junit_xml, no_exit_code):
    """Run unit tests via GUT."""

@cli.command()
@click.argument("path", required=False, default=".")
@click.option("--report-format", type=click.Choice(["text", "json"]), default="text")
def lint(path, report_format):
    """Lint GDScript files via gdlint."""

@cli.command()
@click.argument("path", required=False, default=".")
@click.option("--check", is_flag=True, help="Check only, don't modify (CI mode)")
@click.option("--diff", is_flag=True, help="Show diff of changes")
def format(path, check, diff):
    """Format GDScript files via gdformat."""

@cli.group()
def coverage():
    """Coverage reporting and data management."""

@coverage.command()
@click.option("--format", "fmt", type=click.Choice(["html", "lcov", "cobertura", "text"]),
              default="html")
@click.option("--output-dir", type=str)
def report(fmt, output_dir):
    """Generate report from last coverage run."""

@coverage.command()
@click.argument("files", nargs=-1, required=True)
@click.option("--output", type=str, required=True)
def merge(files, output):
    """Merge multiple coverage data files."""

@coverage.command()
@click.option("--min", "min_percent", type=int, help="Min coverage % to pass")
def show(min_percent):
    """Print coverage summary to terminal."""
```

#### Entry Point

> **Implemented:** Track 1 (scaffolding_20260709). See
> `src/gd_tools/__main__.py`.

```python
# __main__.py
from gd_tools.cli import cli

if __name__ == "__main__":
    try:
        cli()
    except GdToolsError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(e.exit_code)
```

---

### 3.5 `init.py` — Project Bootstrapping

```python
def run_init(non_interactive: bool = False) -> None:
    """Main entry point for `gd-tools init`.
    Orchestrates the full bootstrap flow."""

def find_project_root(start: Path | None = None) -> Path:
    """Walk up to find project.godot. Raises ConfigError if not found."""

def detect_godot_version(config: GdToolsConfig) -> str:
    """Find Godot binary, run --version. Raises GodotNotFoundError."""

def check_gut_installed(project_root: Path) -> bool:
    """Check if addons/gut/gut.gd exists."""

def install_gut(project_root: Path, godot_version: str,
                non_interactive: bool) -> bool:
    """Download GUT from GitHub, extract, copy addons/gut/.
    Prompts user unless non_interactive.
    Returns True if GUT installed or already present, False if user declines."""

def download_gut(version: str, dest: Path) -> Path:
    """Download GUT zip from GitHub releases. Returns path to downloaded zip.
    URL: https://github.com/bitwes/Gut/archive/refs/tags/v{version}.zip"""

def extract_gut(zip_path: Path, project_root: Path) -> None:
    """Extract zip, copy addons/gut/ to project_root/addons/gut/."""

def enable_gut_plugin(project_root: Path) -> None:
    """Edit project.godot to add [editor_plugins] enabled entry.
    Idempotent — checks before adding."""

def install_coverage_addon(project_root: Path) -> None:
    """Copy bundled GDScript files from package data to
    addons/gd-tools-coverage/. Overwrites if stale."""

def update_gutconfig(project_root: Path, config: GdToolsConfig) -> None:
    """Create or update .gutconfig.json with coverage hook paths.
    Merges with existing config if present."""

def create_config_file(project_root: Path, config: GdToolsConfig) -> None:
    """Write gd-tools.toml. Preserves existing if present."""

def create_data_dir(project_root: Path) -> None:
    """Create .gd-tools/ directory. Add to .gitignore if not present."""

def register_autoload(project_root: Path) -> None:
    """Add _GDTCoverage autoload to project.godot [autoload] section.
    Idempotent."""

def print_summary(project_root: Path, actions: list[str]) -> None:
    """Print what was installed/configured, next steps."""
```

#### `project.godot` Modifications

Two sections are modified by `init`:

```ini
# Plugin enabling (GUT)
[editor_plugins]
enabled=PackedStringArray("res://addons/gut/plugin.gd")

# Autoload registration (coverage tracker)
[autoload]
_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"
```

Both are idempotent — `init` checks for existing entries before adding.

#### `.gutconfig.json` Generation

```python
GUTCONFIG_TEMPLATE = {
    "dirs": ["res://test/", "res://tests/"],
    "include_subdirs": True,
    "prefix": "test_",
    "suffix": ".gd",
    "should_exit": True,
    "junit_xml_file": ".gd-tools/results.xml",
    "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
    "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd",
}
```

When merging with existing config: preserve user's `dirs`, `prefix`, `suffix`,
`include_subdirs`. Always set/overwrite `pre_run_script`, `post_run_script`,
`junit_xml_file`, `should_exit`.

**Implementation notes (Track 7, 2026-07-11):**

- `install_gut()` returns `bool`: `True` when GUT installed or already
  present, `False` when user declines. `run_init()` calls `sys.exit(0)` when
  `install_gut()` returns `False` (spec FR-3: user decline = exit 0) —
  prevents enabling a non-existent plugin downstream.
- 14 functions in `init.py` (561 lines). Added `generate_lint_format_rcs()`
  helper (not in original spec) for `gdlintrc`/`gdformatrc` generation with
  generate-if-missing/warn-if-differs policy.
- Coverage addon stubs deployed as package data via
  `[tool.setuptools.package-data]` in `pyproject.toml` (3 placeholder `.gd`
  files: `coverage.gd`, `pre_run_hook.gd`, `post_run_hook.gd` with TODO
  comments — real implementation in Phase 3, Tracks 10-11).
- `print_summary()` uses ASCII `-` bullets (not `•`) per product-guidelines
  §7 (ASCII-only terminal output).
- CLI `init` command catches `GdToolsError` and calls `ctx.exit(e.exit_code)`
  (consistent with test/lint/format commands).

---

### 3.6 `doctor.py` — Diagnostics

```python
def run_doctor() -> DoctorResult:
    """Main entry point for `gd-tools doctor`.
    Runs all 9 checks, returns aggregated result.
    Never raises — all exceptions caught and converted to failed CheckResults.
    Exit code: 0 if all pass, 1 if any check fails (critical or warning)."""

@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    fix_hint: str = ""
    severity: str = "critical"  # "critical" or "warning"

@dataclass
class DoctorResult:
    checks: list[CheckResult]
    all_passed: bool

def check_godot_binary(config: GdToolsConfig) -> CheckResult:
    """Verify Godot binary found and runs."""

def check_godot_version(config: GdToolsConfig) -> CheckResult:
    """Verify Godot version >= 4.5."""

def check_gut_installed(project_root: Path) -> CheckResult:
    """Verify addons/gut/gut.gd exists."""

def check_gut_version(project_root: Path, godot_version: str) -> CheckResult:
    """Verify GUT version matches Godot version."""

def check_coverage_addon(project_root: Path) -> CheckResult:
    """Verify addons/gd-tools-coverage/*.gd all exist."""

def check_gutconfig(project_root: Path) -> CheckResult:
    """Verify .gutconfig.json is valid JSON and has hook paths."""

def check_gd_tools_toml(project_root: Path) -> CheckResult:
    """Verify gd-tools.toml exists and is valid."""

def check_gdtoolkit() -> CheckResult:
    """Verify gdlint and gdformat are installed (run --version)."""

def check_autoload(project_root: Path) -> CheckResult:
    """Verify _GDTCoverage autoload registered in project.godot."""
```

Output format: `format_doctor_table(result: DoctorResult) -> Table` — Rich table
with ✓/✗ per check, message, and fix hint. Status color-coded: green ✓ (pass),
red ✗ (critical fail), yellow ⚠ (warning fail). Caption shows pass count.

---

### 3.7 `test_runner.py` — GUT Orchestration

```python
def run_tests(
    config: GdToolsConfig,
    coverage: bool = False,
    min_percent: int | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
) -> TestResult:
    """Main entry point for `gd-tools test`.
    Orchestrates GUT execution, optionally with coverage."""

@dataclass
class TestResult:
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
    junit_xml_path: Path | None
    coverage_data_path: Path | None

def build_gut_args(
    config: GdToolsConfig,
    suite: str | None,
    test_name: str | None,
    junit_xml: str | None,
) -> list[str]:
    """Build GUT CLI args list.
    Base: ['-s', 'addons/gut/gut_cmdln.gd', '-d', '--path', str(project_root), '-gexit']
    Add: ['-gdir=<test_dirs>'], ['-gselect=<suite>'], ['-gunit_test_name=<test_name>']
    Add: ['-gjunit_xml_file=<path>']"""

def run_gut_with_coverage(
    config: GdToolsConfig,
    gut_args: list[str],
    project_root: Path,
) -> None:
    """Generate coverage plan, set env vars, run Godot+GUT.
    1. Call coverage/plan_generator.generate_plan()
    2. Write plan to .gd-tools/coverage/plan.json
    3. Set env: GD_TOOLS_COVERAGE_ACTIVE=1, GD_TOOLS_COVERAGE_PLAN, GD_TOOLS_COVERAGE_OUTPUT
    4. Run Godot with GUT args
    5. After completion, call coverage/reporter.generate_report()"""

def parse_junit_xml(path: Path) -> TestResult:
    """Parse JUnit XML using junitparser. Extract totals."""

def check_coverage_threshold(
    coverage_data: CoverageData,
    min_percent: int,
) -> None:
    """Raise CoverageThresholdError if overall coverage < min_percent."""
```

#### GUT CLI Invocation

```
godot -s addons/gut/gut_cmdln.gd -d --path <project_root> -gexit \
  [-gdir=res://test/] \
  [-gselect=<suite>] \
  [-gunit_test_name=<test_name>] \
  [-gjunit_xml_file=<path>] \
  [-gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd] \
  [-gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd]
```

When `--coverage` is NOT specified, the pre/post run hooks are omitted from
args (GUT runs normally without instrumentation). The autoload tracker is
still present but inactive (checks `GD_TOOLS_COVERAGE_ACTIVE` env var).

**Implementation notes (Track 6 + post-Track 10 fixes, 2026-07-11):**

- `run_tests()` runs `godot --headless --import` before GUT to register
  class names in `.godot/` cache. Without this, GUT silently fails on
  fresh projects (exit 0, no JUnit XML). Import step does NOT check
  returncode (benign import warnings may produce non-zero exit).
- `build_gut_args()` base args include `--headless` as first element
  (GUT tests are pure GDScript, no display needed).
- `-gselect` strips `res://` prefix and extracts filename via
  `Path(select_name).name` — GUT's `-gselect` matches filename only,
  not `res://`-prefixed paths.
- Exit code check changed from `returncode != 0` to `returncode > 1`.
  GUT with `-gexit` exits 0 (all pass) or 1 (some fail). Exit code 1
  means tests ran but some failed — proceeds to parse JUnit XML for
  details and raises `TestFailureError`. Exit code > 1 indicates a crash.
- Integration test skip condition: `not (os.environ.get("GODOT_BIN") or
  shutil.which("godot"))` — checks both env var and PATH.

---

### 3.8 `lint_runner.py` — gdlint Wrapper

```python
def run_lint(
    config: GdToolsConfig,
    path: str = ".",
    report_format: str = "text",
) -> LintResult:
    """Run gdlint on path, respecting excludes.
    Calls: gdlint <path> (gdlint reads gdlintrc for excludes)
    Parses output, returns structured result."""

@dataclass
class LintResult:
    files_checked: int
    errors: list[LintIssue]
    warnings: list[LintIssue]

@dataclass
class LintIssue:
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str  # "error" | "warning"
```

gdlint reads `gdlintrc` automatically for `excluded_directories`. No need to
filter paths in Python — the config file handles it.

---

### 3.9 `format_runner.py` — gdformat Wrapper

```python
def run_format(
    config: GdToolsConfig,
    path: str = ".",
    check: bool = False,
    diff: bool = False,
) -> FormatResult:
    """Run gdformat on path, respecting excludes.
    check=True: gdformat --check <path>
    diff=True: gdformat --diff <path>
    normal: gdformat <path>
    gdformat reads gdformatrc for excludes."""

@dataclass
class FormatResult:
    files_checked: int = 0
    files_formatted: int = 0
    files_needing_format: int = 0  # when --check
    files_needing_format_paths: list[str] = field(default_factory=list)
    diffs: list[str] = field(default_factory=list)  # when --diff
```

**Implementation notes (Track 5, 2026-07-10):**

- `run_format()` uses `gdtoolkit.formatter.format_code()` Python API (not
  subprocess) with `max_line_length=100`.
- `files_needing_format_paths` (not in original spec) lists specific file
  paths that need formatting in `--check` mode.
- `--check` mode returns data; the CLI layer decides exit code (0 or 1),
  consistent with `run_lint` pattern. `run_format` does not raise
  `FormatError` in check mode.
- `--diff` mode uses `difflib.unified_diff` and renders via `rich.Console`
  + `rich.syntax.Syntax`.
- Syntax errors (`LarkError`) are caught and reported as warnings to
  stderr (`"Warning: Skipping {file_path}: {e}"`), then the file is
  skipped — does not crash the tool.
- Mutual exclusion of `--check` and `--diff` raises
  `FormatError(exit_code=2)`.
- File discovery extracted to shared `file_discovery.py` module
  (`discover_gd_files(path, excludes)`), used by both `lint_runner` and
  `format_runner`.

---

### 3.10 `coverage/plan_generator.py` — Instrumentation Plan Generation

This is the core Python-side component of Architecture C. It uses gdtoolkit's
Lark parser to identify executable lines and branch points.

```python
from lark import Tree
from gdtoolkit.parser import parser

def generate_plan(
    project_root: Path,
    source_dirs: list[str],
    exclude_dirs: list[str],
    test_dirs: list[str],
) -> CoveragePlan:
    """Walk project, parse each .gd file, generate instrumentation plan.
    1. Find all .gd files in source_dirs, excluding exclude_dirs and test_dirs
    2. For each file: parse with gdtoolkit, walk AST, extract trackable points
    3. Assign unique IDs to each point
    4. Return CoveragePlan"""

@dataclass
class CoveragePlan:
    version: int  # 1
    generated_by: str  # "gd-tools 0.1.0"
    files: list[FilePlan]

@dataclass
class FilePlan:
    path: str  # res:// path
    source_hash: str  # sha256 of source, for staleness detection
    lines: list[LinePlan]

@dataclass
class LinePlan:
    line: int  # 1-indexed line number
    id: int  # unique within file
    type: str  # "statement" | "branch"
    branch_type: str | None  # "if_true" | "if_false" | "elif_true" | "loop_body" | "match_case"

class CoverageVisitor:
    """Lark Visitor that walks the AST and collects trackable points.
    Uses tree.meta.line (available with gather_metadata=True)."""

    def __init__(self):
        self.points: list[LinePlan] = []
        self._next_id: int = 0

    def expr_stmt(self, tree: Tree) -> None:
        """Track expression statements (includes assignments)."""
        self._add_point(tree, "statement")

    def return_stmt(self, tree: Tree) -> None:
        """Track return statements."""
        self._add_point(tree, "statement")

    def func_var_assigned(self, tree: Tree) -> None:
        """Track local variable assignments."""
        self._add_point(tree, "statement")

    def func_var_typed_assgnd(self, tree: Tree) -> None:
        """Track typed local variable assignments."""
        self._add_point(tree, "statement")

    def func_var_inf(self, tree: Tree) -> None:
        """Track inferred-type local variable assignments (:=)."""
        self._add_point(tree, "statement")

    def break_stmt(self, tree: Tree) -> None:
        """Track break statements."""
        self._add_point(tree, "statement")

    def continue_stmt(self, tree: Tree) -> None:
        """Track continue statements."""
        self._add_point(tree, "statement")

    def if_stmt(self, tree: Tree) -> None:
        """Track if/elif/else branches.
        if_branch → if_true, elif_branch → elif_true, else_branch → if_false"""
        for child in tree.children:
            if child.data == "if_branch":
                self._add_point(child, "branch", "if_true")
            elif child.data == "elif_branch":
                self._add_point(child, "branch", "elif_true")
            elif child.data == "else_branch":
                self._add_point(child, "branch", "if_false")

    def while_stmt(self, tree: Tree) -> None:
        """Track while loop body entry."""
        self._add_point(tree, "branch", "loop_body")

    def for_stmt(self, tree: Tree) -> None:
        """Track for loop body entry."""
        self._add_point(tree, "branch", "loop_body")

    def for_stmt_typed(self, tree: Tree) -> None:
        """Track typed for loop body entry."""
        self._add_point(tree, "branch", "loop_body")

    def match_stmt(self, tree: Tree) -> None:
        """Track match statement — each match_branch is a branch point."""
        for child in tree.children:
            if hasattr(child, 'data') and child.data == "match_branch":
                self._add_point(child, "branch", "match_case")

    def _add_point(self, tree: Tree, type_: str, branch_type: str | None = None) -> None:
        """Extract line number from tree.meta and create LinePlan."""
        line = tree.meta.line  # 1-indexed
        self.points.append(LinePlan(
            line=line,
            id=self._next_id,
            type=type_,
            branch_type=branch_type,
        ))
        self._next_id += 1

def parse_gdscript(source: str) -> Tree:
    """Parse GDScript source with gdtoolkit.
    Uses parser.parse(source, gather_metadata=True)."""

def write_plan_json(plan: CoveragePlan, output_path: Path) -> None:
    """Serialize CoveragePlan to JSON file."""

def read_plan_json(path: Path) -> CoveragePlan:
    """Read and validate plan JSON. Raises CoveragePlanError if invalid."""
```

#### Statement Classification (from grammar research)

| Lark Node             | Classification | Track? | Branch Type     |
|-----------------------|---------------|--------|-----------------|
| `expr_stmt`           | executable    | yes    | statement       |
| `return_stmt`         | executable    | yes    | statement       |
| `func_var_assigned`   | executable    | yes    | statement       |
| `func_var_typed_assgnd`| executable   | yes    | statement       |
| `func_var_inf`        | executable    | yes    | statement       |
| `break_stmt`          | executable    | yes    | statement       |
| `continue_stmt`       | executable    | yes    | statement       |
| `if_branch`           | branch        | yes    | if_true         |
| `elif_branch`         | branch        | yes    | elif_true       |
| `else_branch`         | branch        | yes    | if_false        |
| `while_stmt`          | branch        | yes    | loop_body       |
| `for_stmt`            | branch        | yes    | loop_body       |
| `for_stmt_typed`      | branch        | yes    | loop_body       |
| `match_branch`        | branch        | yes    | match_case      |
| `pass_stmt`           | no-op         | no     | —               |
| `breakpoint_stmt`     | debug         | no     | —               |
| `const_stmt`          | declarative   | no     | —               |
| `class_var_stmt`      | declarative   | no     | —               |
| `signal_stmt`         | declarative   | no     | —               |
| `enum_stmt`           | declarative   | no     | —               |
| `func_def`            | declarative   | no     | —               |
| `static_func_def`      | declarative   | no     | —               |
| `extends_stmt`        | declarative   | no     | —               |
| `classname_stmt`      | declarative   | no     | —               |

**Note:** `func_var_empty` and `func_var_typed` (declarations without
assignment) are NOT tracked — they're declarations, not executable statements.

**Implementation notes (Track 9, 2026-07-11):**

- `CoveragePlan`, `FilePlan`, `LinePlan` dataclasses with `to_dict()`/
  `from_dict()` methods for JSON serialization.
- `CoverageVisitor` is a Lark `Visitor` subclass — Lark calls methods by
  matching node names (e.g., `expr_stmt()` is called for every `expr_stmt`
  node in the tree).
- `if_stmt()` visitor iterates `tree.children` and matches `if_branch`,
  `elif_branch`, `else_branch` child nodes — each gets its own `LinePlan`
  with the appropriate `branch_type`.
- `match_stmt()` visitor iterates `tree.children` and matches `match_branch`
  nodes — each case gets a `LinePlan` with `branch_type="match_case"`.
- `parse_gdscript()` uses `gdtoolkit.parser.parse(source,
  gather_metadata=True)` — the `gather_metadata=True` flag populates
  `tree.meta.line` with 1-indexed line numbers.
- `generate_plan()` signature: `(project_root, source_dirs, exclude_dirs,
  test_dirs)` — reuses `discover_gd_files()` from `file_discovery.py` for
  file discovery, then filters out test_dirs from coverage targets.
- Source hash: SHA-256 with `sha256:` prefix (e.g., `sha256:abc123...`).
- `read_plan_json` validates schema on read: checks `data` is a dict,
  `version` is present, `files` is a list, each file entry is a dict with
  required fields (`file_id`, `path`, `source_hash`). All failures raise
  `CoveragePlanError` (not raw `KeyError`).
- `tools/generate_expected_plans.py` — CLI script that regenerates all 6
  expected plan JSON fixtures from GDScript fixture files. Used to verify
  fixture correctness and detect drift.
- 6 GDScript fixtures in `tests/fixtures/gdscript/`: `simple.gd`,
  `branches.gd`, `loops.gd`, `match_stmt.gd`, `nested.gd`, `edge_cases.gd`.
- 6 expected JSON plans in `tests/fixtures/plans/`: corresponding
  `.expected.json` files verified correct against fixtures.
- 49 unit tests in `test_plan_generator.py` + 2 in
  `test_generate_expected_plans.py`. `plan_generator.py` at 100% coverage.

---

### 3.11 `coverage/reporter.py` — Report Generation

```python
def generate_report(
    plan: CoveragePlan,
    coverage_data: CoverageData,
    output_dir: Path,
    format: str = "html",
) -> Path:
    """Generate coverage report in specified format.
    Dispatches to format-specific reporter.
    Returns path to generated report."""

@dataclass
class CoverageData:
    version: int
    generated_at: str  # ISO 8601
    files: list[FileCoverage]

@dataclass
class FileCoverage:
    path: str  # res:// path
    hits: dict[int, int]  # line_id → hit_count

@dataclass
class CoverageSummary:
    total_lines: int
    covered_lines: int
    line_rate: float  # 0.0 - 1.0
    total_branches: int
    covered_branches: int
    branch_rate: float  # 0.0 - 1.0

def compute_summary(plan: CoveragePlan, data: CoverageData) -> CoverageSummary:
    """Cross-reference plan + data to compute coverage percentages."""

def compute_file_summary(
    file_plan: FilePlan,
    file_data: FileCoverage,
) -> FileSummary:
    """Per-file coverage breakdown."""

@dataclass
class FileSummary:
    path: str
    total_lines: int
    covered_lines: int
    line_rate: float
    total_branches: int
    covered_branches: int
    branch_rate: float
    uncovered_lines: list[int]

def read_coverage_json(path: Path) -> CoverageData:
    """Read and validate coverage JSON from GDScript addon output."""

def merge_coverage_data(files: list[Path]) -> CoverageData:
    """Merge multiple coverage data files (for parallel CI shards).
    Sums hit counts per line_id."""
```

---

### 3.12 `coverage/html_reporter.py` — HTML Report

```python
def generate_html_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_dir: Path,
) -> Path:
    """Generate HTML coverage report using Jinja2.
    - index.html: summary table (file → line %, branch %)
    - per-file pages: syntax-highlighted source with covered/uncovered lines
    Returns path to index.html."""
```

HTML report features:
- Index page: table of all files with line/branch coverage percentages
- Per-file pages: source code with green (covered) / red (uncovered) /
  yellow (partial branch) highlighting
- Summary bar at top of each page
- Sortable columns on index page
- CSS/JS bundled (no external dependencies)

---

### 3.13 `coverage/lcov_reporter.py` — LCOV Format

```python
def generate_lcov_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_path: Path,
) -> Path:
    """Generate LCOV trace file.
    Format: TN, SF, DA, BRDA, BRF, BRH, LF, LH, end_of_record
    Compatible with codecov.io, coveralls, genhtml."""
```

LCOV format example:
```
TN:
SF:res://scripts/player.gd
DA:5,15
DA:8,12
DA:10,0
BRDA:8,0,1,12
BRDA:8,0,2,0
BRF:2
BRH:1
LF:3
LH:2
end_of_record
```

---

### 3.14 `coverage/cobertura_reporter.py` — Cobertura XML

```python
def generate_cobertura_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_path: Path,
) -> Path:
    """Generate Cobertura XML report.
    Compatible with Jenkins, GitLab CI coverage visualization."""
```

---

## 4. GDScript Addon Specifications

### 4.1 `coverage.gd` — Autoload Coverage Tracker

> **Spike-validated:** The spike (`spike_coverage_20260709`) confirmed this design
> works. Key changes from original spec: added `set_active()` method for
> testability, env var check now validates value (not just existence).
>
> **Implemented:** Track 10 (`coverage_tracker_20260711`, archived). See
> `src/gd_tools/addons/gd-tools-coverage/coverage.gd`. All 7 success criteria
> passed. File named `coverage.gd` (not `tracker.gd` as in original spec).
> Autoload registered via `register_coverage_autoload()` in `init.py` with
> `COVERAGE_AUTOLOAD_PATH` constant. 6 GUT tests in
> `tests/fixtures/gdscript/test_coverage_tracker.gd`.

```gdscript
extends Node
## Coverage tracker autoload singleton.
## Registered as _GDTCoverage in project.godot.
## No-op when GD_TOOLS_COVERAGE_ACTIVE env var is not set or is "0"/"false".

var _active: bool = false
var _hits: Dictionary = {}  # file_id → {line_id → hit_count}

func _ready() -> void:
    var env_val := OS.get_environment("GD_TOOLS_COVERAGE_ACTIVE")
    _active = env_val != "" and env_val != "0" and env_val.to_lower() != "false"
    if not _active:
        return
    _hits.clear()

func set_active(active: bool) -> void:
    ## Enable/disable tracking. Used by tests and pre_run_hook.
    _active = active
    if active and _hits.is_empty():
        pass  # Ready to track
    elif not active:
        pass  # No-op when inactive

func hit(file_id: int, line_id: int) -> void:
    if not _active:
        return
    if not _hits.has(file_id):
        _hits[file_id] = {}
    var file_hits: Dictionary = _hits[file_id]
    if file_hits.has(line_id):
        file_hits[line_id] += 1
    else:
        file_hits[line_id] = 1

func get_hits() -> Dictionary:
    return _hits

func reset() -> void:
    _hits.clear()

func is_active() -> bool:
    return _active
```

**Key design points:**
- Registered as autoload `_GDTCoverage` in `project.godot` during `gd-tools init`
- Checks `GD_TOOLS_COVERAGE_ACTIVE` env var in `_ready()` — no-op when not set
- Injected code calls `_GDTCoverage.hit(file_id, line_id)` — minimal overhead
  (one bool check + dictionary lookup when active, one bool check when inactive)
- `file_id` and `line_id` are integers from the instrumentation plan (compact,
  fast lookup vs. string keys)

---

### 4.2 `pre_run_hook.gd` — GUT Pre-Run Hook

> **Spike-validated:** GUT hooks must `extends GutHookScript` (not `RefCounted`)
> and use `run()` method (not `_init()`). GUT instantiates the hook script and
> calls `run()`. The `_inject_trackers` method is `static` for testability.

```gdscript
extends GutHookScript
## GUT pre-run hook. Reads instrumentation plan, instruments scripts.
## Invoked by GUT before tests run.

func run() -> void:
    ## Main entry point called by GUT.
    var plan_path := OS.get_environment("GD_TOOLS_COVERAGE_PLAN")
    if plan_path.is_empty():
        push_warning("gd-tools: GD_TOOLS_COVERAGE_PLAN not set, skipping instrumentation")
        return

    var plan := _load_plan(plan_path)
    if plan.is_empty():
        push_error("gd-tools: Failed to load coverage plan")
        return

    for file_entry in plan["files"]:
        _instrument_file(file_entry)

func _load_plan(path: String) -> Dictionary:
    ## Load plan JSON from file path.
    var file := FileAccess.open(path, FileAccess.READ)
    if not file:
        push_error("gd-tools: Cannot open plan file: %s" % path)
        return {}
    var json_text := file.get_as_text()
    file.close()
    var parsed = JSON.parse_string(json_text)
    if parsed == null or not parsed is Dictionary:
        push_error("gd-tools: Invalid plan JSON")
        return {}
    return parsed

static func _inject_trackers(source: String, file_id: int, lines: Array) -> String:
    ## Inject tracker calls into source code.
    ## Works bottom-to-top so line numbers don't shift.
    ## Returns the instrumented source string.
    var source_lines := source.split("\n")
    var sorted_lines := lines.duplicate()
    sorted_lines.sort_custom(func(a, b): return int(a["line"]) > int(b["line"]))

    for line_entry in sorted_lines:
        var line_num: int = int(line_entry["line"])
        var line_id: int = int(line_entry["id"])
        var idx: int = line_num - 1

        if idx < 0 or idx >= source_lines.size():
            continue

        var original_line := source_lines[idx]
        var indent := _extract_indent(original_line)
        var tracker_call := "%s_GDTCoverage.hit(%d, %d)" % [indent, file_id, line_id]
        source_lines.insert(idx, tracker_call)

    return "\n".join(source_lines)

static func _extract_indent(line: String) -> String:
    ## Extract leading whitespace from a line.
    var indent := ""
    for ch in line:
        if ch == " " or ch == "\t":
            indent += ch
        else:
            break
    return indent

func _instrument_file(file_entry: Dictionary) -> void:
    ## Instrument a single script file.
    var res_path: String = file_entry["path"]
    var file_id: int = int(file_entry.get("file_id", 0))
    var lines: Array = file_entry["lines"]

    var script := load(res_path)
    if script == null:
        push_warning("gd-tools: Cannot load script: %s" % res_path)
        return

    var source := script.source_code
    var instrumented_source := _inject_trackers(source, file_id, lines)

    script.source_code = instrumented_source
    var err := script.reload()
    if err != OK:
        push_error("gd-tools: Failed to reload instrumented script: %s (error %d)" % [res_path, err])
```

**Instrumentation approach:** String manipulation — split source into lines,
insert tracker calls before each instrumented line (bottom-to-top to preserve
line numbers), set `source_code`, call `reload()`.

---

### 4.3 `post_run_hook.gd` — GUT Post-Run Hook

> **Spike-validated:** GUT hooks must `extends GutHookScript` (not `RefCounted`)
> and use `run()` method (not `_init()`).

```gdscript
extends GutHookScript
## GUT post-run hook. Saves coverage data to JSON.
## Invoked by GUT after all tests complete.

func run() -> void:
    ## Main entry point called by GUT.
    var output_path := OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")
    if output_path.is_empty():
        push_warning("gd-tools: GD_TOOLS_COVERAGE_OUTPUT not set, skipping save")
        return

    var tracker := _get_tracker()
    if tracker == null:
        push_error("gd-tools: _GDTCoverage autoload not found")
        return

    var hits := tracker.get_hits()
    var data := _build_coverage_json(hits)
    _write_json(data, output_path)

func _get_tracker() -> Node:
    ## Get the _GDTCoverage autoload node.
    var tree := Engine.get_main_loop() as SceneTree
    if tree == null:
        return null
    return tree.root.get_node_or_null("_GDTCoverage")

func _build_coverage_json(hits: Dictionary) -> Dictionary:
    ## Build coverage data JSON structure.
    var files := []
    for file_id in hits.keys():
        var file_hits: Dictionary = hits[file_id]
        var hit_dict := {}
        for line_id in file_hits.keys():
            hit_dict[str(line_id)] = file_hits[line_id]
        files.append({
            "file_id": file_id,
            "hits": hit_dict
        })
    return {
        "version": 1,
        "generated_at": Time.get_datetime_string_from_system(false, true),
        "files": files
    }

func _write_json(data: Dictionary, path: String) -> void:
    ## Write JSON to file. Creates parent directories if needed.
    var dir := path.get_base_dir()
    if not dir.is_empty() and not DirAccess.dir_exists_absolute(dir):
        DirAccess.make_dir_recursive_absolute(dir)
    var file := FileAccess.open(path, FileAccess.WRITE)
    if not file:
        push_error("gd-tools: Cannot write coverage file: %s" % path)
        return
    file.store_string(JSON.stringify(data, "  "))
    file.close()
```

---

## 5. Data Contracts

### 5.1 Instrumentation Plan JSON

Written by Python (`plan_generator.py`), read by GDScript (`pre_run_hook.gd`).

**Env var:** `GD_TOOLS_COVERAGE_PLAN` (res:// path to plan.json)

```json
{
  "version": 1,
  "generated_by": "gd-tools 0.1.0",
  "files": [
    {
      "file_id": 0,
      "path": "res://scripts/player.gd",
      "source_hash": "sha256:abc123...",
      "lines": [
        { "line": 5, "id": 0, "type": "statement" },
        { "line": 8, "id": 1, "type": "branch", "branch_type": "if_true" },
        { "line": 10, "id": 2, "type": "branch", "branch_type": "if_false" },
        { "line": 12, "id": 3, "type": "statement" }
      ]
    }
  ]
}
```

| Field         | Type   | Description                                    |
|---------------|--------|------------------------------------------------|
| `version`     | int    | Plan format version (currently 1)              |
| `generated_by`| string | Tool name + version                            |
| `files`       | array  | One entry per instrumented file                |
| `file_id`     | int    | Unique file identifier (used in tracker calls) |
| `path`        | string | res:// path to the script                      |
| `source_hash` | string | SHA-256 of original source (staleness check)   |
| `lines`       | array  | Trackable points in this file                  |
| `line`        | int    | 1-indexed line number in source               |
| `id`          | int    | Unique line identifier within file             |
| `type`        | string | "statement" or "branch"                       |
| `branch_type` | string | Branch sub-type (null for statements)          |

### 5.2 Coverage Data JSON

Written by GDScript (`post_run_hook.gd`), read by Python (`reporter.py`).

**Env var:** `GD_TOOLS_COVERAGE_OUTPUT` (res:// path to coverage.json)

```json
{
  "version": 1,
  "generated_at": "2026-07-08T12:00:00Z",
  "files": [
    {
      "file_id": 0,
      "hits": {
        "0": 15,
        "1": 12,
        "2": 3,
        "3": 0
      }
    }
  ]
}
```

| Field           | Type         | Description                              |
|-----------------|--------------|------------------------------------------|
| `version`       | int          | Data format version (currently 1)       |
| `generated_at`  | string       | ISO 8601 timestamp                      |
| `files`         | array        | One entry per instrumented file         |
| `file_id`       | int          | Matches file_id in plan                 |
| `hits`          | object       | Map of line_id (string) → hit_count     |

**Note:** `hits` keys are strings (JSON limitation), but represent integers.
Line IDs with 0 hits mean the line was never executed (uncovered).

### 5.3 Environment Variables

| Variable                       | Set By  | Read By    | Purpose                          |
|--------------------------------|---------|------------|----------------------------------|
| `GD_TOOLS_COVERAGE_ACTIVE`     | Python  | coverage.gd | Enable/disable tracker (0 or 1)  |
| `GD_TOOLS_COVERAGE_PLAN`       | Python  | pre_run_hook.gd | Path to plan.json           |
| `GD_TOOLS_COVERAGE_OUTPUT`     | Python  | post_run_hook.gd | Path to coverage.json        |

### 5.4 GUT Configuration (`.gutconfig.json`)

Managed by `gd-tools init`. Coverage hook paths are always set.

```json
{
  "dirs": ["res://test/", "res://tests/"],
  "include_subdirs": true,
  "prefix": "test_",
  "suffix": ".gd",
  "should_exit": true,
  "junit_xml_file": ".gd-tools/results.xml",
  "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
  "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd"
}
```

### 5.5 Autoload Registration (`project.godot`)

```ini
[autoload]
_GDTCoverage="*res://addons/gd-tools-coverage/coverage.gd"
```

The `*` prefix means the autoload is a singleton (always available as
`_GDTCoverage` in code).

---

## 6. Coverage Flow — End to End

### `gd-tools test --coverage --min 80`

```
Python (test_runner.py)
│
├─ 1. Load config (config.py)
├─ 2. Find Godot binary (godot.py)
├─ 3. Generate coverage plan (coverage/plan_generator.py)
│     ├─ Walk project, find .gd files (excluding addons, .godot, .gd-tools, .git, test dirs)
│     ├─ Parse each file with gdtoolkit (parser.parse(source, gather_metadata=True))
│     ├─ Walk AST with CoverageVisitor
│     │   ├─ Visit expr_stmt, return_stmt, func_var_assigned, etc. → statement points
│     │   └─ Visit if_stmt, while_stmt, for_stmt, match_stmt → branch points
│     ├─ Assign file_ids and line_ids
│     └─ Write plan to .gd-tools/coverage/plan.json
│
├─ 4. Set environment variables:
│     GD_TOOLS_COVERAGE_ACTIVE=1
│     GD_TOOLS_COVERAGE_PLAN=<abs_path>/plan.json
│     GD_TOOLS_COVERAGE_OUTPUT=<abs_path>/coverage.json
│
├─ 5. Run Godot with GUT:
│     godot -s addons/gut/gut_cmdln.gd -d --path <project> -gexit
│       -gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd
│       -gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd
│       -gjunit_xml_file=.gd-tools/results.xml
│
│  ┌─────────────────────────────────────────────────────────┐
│  │ Godot + GUT                                             │
│  │                                                         │
│  │  6. GUT loads, calls pre_run_hook.run()                │
│  │     ├─ Read plan.json from GD_TOOLS_COVERAGE_PLAN       │
│  │     ├─ For each file in plan:                           │
│  │     │   ├─ load(res_path) → GDScript object            │
│  │     │   ├─ Split source_code into lines                 │
│  │     │   ├─ Insert _GDTCoverage.hit(file_id, line_id)   │
│  │     │   │   before each instrumented line (bottom-up)   │
│  │     │   ├─ Set script.source_code = instrumented        │
│  │     │   └─ script.reload()                              │
│  │     └─ Tracker is now active (env var set)             │
│  │                                                         │
│  │  7. GUT runs tests                                      │
│  │     └─ Instrumented code fires _GDTCoverage.hit() calls │
│  │                                                         │
│  │  8. GUT calls post_run_hook.run()                      │
│  │     ├─ Get _GDTCoverage autoload node                  │
│  │     ├─ Build coverage JSON from tracker.get_hits()      │
│  │     └─ Write to GD_TOOLS_COVERAGE_OUTPUT path           │
│  │                                                         │
│  │  9. GUT exports JUnit XML to .gd-tools/results.xml     │
│  └─────────────────────────────────────────────────────────┘
│
├─ 10. Read JUnit XML (junitparser) → TestResult
├─ 11. Read coverage.json (coverage/reporter.py) → CoverageData
├─ 12. Cross-reference plan + data → CoverageSummary
│      ├─ For each file: match plan lines to data hits
│      ├─ Line coverage = covered_lines / total_lines
│      └─ Branch coverage = covered_branches / total_branches
│
├─ 13. Generate report (coverage/reporter.py)
│      ├─ HTML: Jinja2 template → .gd-tools/coverage/html/index.html
│      ├─ LCOV: .gd-tools/coverage/lcov.info
│      └─ Cobertura: .gd-tools/coverage/cobertura.xml
│
├─ 14. Check threshold: if overall_coverage < 80% → CoverageThresholdError
│
└─ 15. Print summary (Rich table): test results + coverage summary
```

---

## 7. Coverage Metrics Computation

### Line Coverage

```
line_rate = covered_lines / total_executable_lines
```

A line is "covered" if its hit count > 0. A line is "uncovered" if hit count
is 0 or the line_id is missing from coverage data.

### Branch Coverage

```
branch_rate = covered_branches / total_branch_points
```

Branch points are: `if_true`, `if_false`, `elif_true`, `loop_body`,
`match_case`. A branch is "covered" if its hit count > 0.

**Example:** An `if` statement with no `else`:
- `if_true` branch: tracked, covered if hit > 0
- `if_false` (implicit else): tracked as a branch point on the line after the
  if-block, covered if the condition was ever false

### Overall Coverage

For the `--min` threshold check, overall coverage is the weighted average:

```
overall = (total_covered_lines + total_covered_branches) /
          (total_executable_lines + total_branch_points)
```

Alternatively, line coverage alone can be used for the threshold (simpler, more
common). This is a configuration decision — default to line coverage for the
threshold, report both in the summary.

---

## 8. Error Handling Strategy

### Exception Flow

```
GDScript errors (push_error/push_warning)
    ↓
Godot stderr (captured by subprocess)
    ↓
Python: parse stderr for "gd-tools:" prefixed messages
    ↓
Raise appropriate GdToolsError subclass
    ↓
CLI catches GdToolsError → prints to stderr → sys.exit(exit_code)
```

### Error Categories

| Error                    | Exit Code | When                                      |
|--------------------------|-----------|-------------------------------------------|
| `ConfigError`            | 2         | Invalid gd-tools.toml, missing project.godot |
| `GodotNotFoundError`     | 2         | Godot binary not found                    |
| `GUTNotInstalledError`  | 2         | GUT addon missing when running tests     |
| `CoveragePlanError`      | 2         | Plan generation or parsing failed         |
| `TestFailureError`       | 1         | One or more tests failed                  |
| `CoverageThresholdError` | 1         | Coverage below --min threshold            |
| `LintError`             | 1         | Lint errors found                         |
| `FormatError`           | 1         | Files need formatting (--check mode)     |

### GDScript Error Propagation

GDScript `push_error()` and `push_warning()` output to Godot's stderr. The
Python `test_runner` captures stderr and scans for `gd-tools:` prefixed
messages. These are surfaced to the user with context.

If `script.reload()` fails (returns non-OK error), the pre_run_hook calls
`push_error()` with the script path and error code. Python detects this and
raises `CoveragePlanError`.

---

## 9. File Discovery & Exclusion

### File Discovery Algorithm

```python
def find_gdscript_files(
    project_root: Path,
    source_dirs: list[str],
    exclude_dirs: list[str],
) -> list[Path]:
    """Find all .gd files in source_dirs, excluding exclude_dirs.
    1. For each source_dir: walk recursively
    2. Skip any directory matching exclude_dirs (by name)
    3. Collect all .gd files
    4. Return sorted list"""
```

### Exclude Application

| Tool     | Excludes Applied Via          |
|----------|-------------------------------|
| lint     | `gdlintrc` (generated by init)|
| format   | `gdformatrc` (generated by init)|
| coverage | Python file discovery (plan_generator) |
| test     | GUT config `dirs` (test files are included, not excluded) |

**Note:** gdlint and gdformat read their own config files for excludes. The
Python wrappers don't filter paths — they pass the path to the tool and let
the tool's config handle exclusion. Coverage does its own file discovery
because it needs to parse each file individually.

---

## 10. GUT Installation Details

### Download & Extract

```python
GUT_DOWNLOAD_URL = "https://github.com/bitwes/Gut/archive/refs/tags/v{version}.zip"

def download_gut(version: str, dest: Path) -> Path:
    """Download GUT release zip.
    1. Build URL: GUT_DOWNLOAD_URL.format(version=version)
    2. Download with requests.get(url, stream=True)
    3. Save to dest/gut-{version}.zip
    4. Return path to downloaded zip"""

def extract_gut(zip_path: Path, project_root: Path) -> None:
    """Extract and install GUT.
    1. Extract zip to temp directory
    2. Zip structure: Gut-{version}/addons/gut/
    3. Copy temp/Gut-{version}/addons/gut/ → project_root/addons/gut/
    4. Clean up temp directory"""
```

### Plugin Enabling

```python
def enable_gut_plugin(project_root: Path) -> None:
    """Add GUT to [editor_plugins] in project.godot.
    1. Read project.godot
    2. Check if [editor_plugins] section exists
    3. Check if gut/plugin.gd already in enabled list
    4. If not, add it
    5. Write back
    Idempotent — safe to call multiple times."""
```

Result in `project.godot`:
```ini
[editor_plugins]
enabled=PackedStringArray("res://addons/gut/plugin.gd")
```

---

## 11. Testing Approach (Summary)

Detailed testing strategy is in `TESTING_STRATEGY.md`. Summary:

- **Python unit tests** (pytest): config parsing, plan generation, report
  generation, file discovery, error handling. Mock Godot/gdlint/gdformat.
- **Integration tests**: real Godot + GUT + sample GDScript project with known
  coverage expectations.
- **Fixtures**: sample .gd files with known AST structures and expected
  coverage points.

---

## 12. Open Implementation Questions

1. **`gdlintrc`/`gdformatrc` generation policy** — Generate if missing, warn if
   existing and differs? *Default: generate if missing, warn if differs.*

2. **Coverage of addon files** — Include as "0% covered" or exclude entirely?
   *Default: exclude entirely.*

3. **Threshold metric** — Line coverage only, or combined line+branch?
   *Default: line coverage for threshold, report both.*

4. **Instrumentation edge cases** — How to handle:
   - One-liner if/for/while (single-line body)
   - Match statements with complex patterns
   - Nested functions/lambdas
   - Setters/getters
   *To be resolved during spike implementation.*

5. **Concurrent test runs** — If GUT runs tests in parallel (it doesn't by
   default, but future), is the tracker thread-safe? *GDScript is
   single-threaded by default; not a concern for v1.*

6. **Script reload side effects** — Does `reload()` reset instance state?
   `keep_state=true` preserves variables but may not preserve everything.
   *To be tested during spike.*
