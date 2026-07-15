# TDD: gd-tools — Technical Design Document

**Version:** 0.1.0 (draft)
**Date:** 2026-07-08
**Status:** Post-v1.0 — Config Show/Validate delivered (Track 25)
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
├── update_check.py           # PyPI update notification
├── addon_check.py            # Stale addon version detection
├── config.py                 # Pydantic models for gd-tools.toml
├── godot.py                  # Godot binary detection + invocation
├── init.py                   # `gd-tools init` bootstrap flow
├── doctor.py                 # `gd-tools doctor` diagnostics
├── file_discovery.py         # Shared .gd file discovery (hybrid exclude matching)
├── test_runner.py            # `gd-tools test` — GUT orchestration
├── lint_runner.py            # `gd-tools lint` — gdlint wrapper
├── format_runner.py            # `gd-tools format` — gdformat wrapper
├── version.py                 # `gd-tools version` — component version detection
├── errors.py                 # Exception hierarchy
├── coverage/
│   ├── __init__.py
│   ├── orchestrator.py        # Coverage CLI orchestration (test --coverage, report, merge, show)
│   ├── plan_generator.py     # Lark AST → instrumentation plan (JSON)
│   ├── reporter.py           # Coverage data → report dispatch
│   ├── html_reporter.py     # Jinja2 HTML report
│   ├── lcov_reporter.py      # LCOV format
│   ├── cobertura_reporter.py # Cobertura XML
│   ├── terminal_reporter.py  # Rich terminal table
│   └── templates/
│       ├── index.html        # HTML report index page (Jinja2)
│       └── file.html         # HTML per-file page (Jinja2)
└── addons/
    └── gd-tools-coverage/
        ├── coverage.gd       # Autoload singleton — instrumentation + hit tracking
        ├── pre_run_hook.gd   # GUT pre-run hook — activates coverage tracker
        └── post_run_hook.gd  # GUT post-run hook — saves coverage JSON
```

### Dependency Graph

```
cli.py
├── config.py
├── update_check.py (-> packaging, requests)
├── addon_check.py (-> packaging, config)
├── godot.py
├── init.py (→ config, godot)
├── doctor.py (→ config, godot)
├── test_runner.py (→ config, godot, coverage/plan_generator, coverage/reporter)
├── lint_runner.py (→ config)
├── format_runner.py (→ config)
├── version.py (→ config, godot, init)
└── coverage/
    ├── orchestrator.py (→ config, test_runner, plan_generator, reporter, errors)
    └── __init__.py (→ orchestrator: re-exports run_coverage_test, generate_coverage_report, merge_coverage_files, show_coverage_summary)

coverage/plan_generator.py → gdtoolkit (external)
coverage/reporter.py → coverage/html_reporter, coverage/lcov_reporter, coverage/cobertura_reporter, coverage/terminal_reporter
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
    """Coverage below minimum threshold.

    Carries an optional ``report_result`` so the caller can access the
    already-computed CoverageSummary (avoids recomputation when
    printing the coverage table before re-raising).
    """
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
    max_line_length: int = 100

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

#### Deprecation & Validation (Track 25)

```python
@dataclass
class DeprecatedField:
    """Represents a deprecated configuration field."""
    field_path: tuple[str, ...]   # e.g. ("godot", "path")
    since_version: str
    replacement: str | None        # New key path, if any
    migration_message: str | None  # Custom migration guidance

_DEPRECATED_FIELDS: dict[tuple[str, ...], DeprecatedField] = {}
    # Currently empty — future-proofing for deprecated settings.

def check_deprecated_settings(raw_toml_data: dict) -> list[DeprecatedField]:
    """Traverse raw TOML dict to find deprecated config keys.
    Returns list of DeprecatedField for each found."""

def validate_paths(config: GdToolsConfig, project_root: Path) -> list[str]:
    """Check that paths in config actually exist on disk.
    Returns list of warning strings (advisory, non-fatal).
    Checks: test_dirs, godot.binary, coverage.output_dir parent,
    lint/format/coverage exclude dirs."""

def format_config_table(config: GdToolsConfig) -> Rich.Table:
    """Render config as a Rich table (Section, Key, Value)."""

def format_config_toml(config: GdToolsConfig) -> str:
    """Serialize config to TOML string via tomli_w.dumps(). Strips None."""

def format_config_json(config: GdToolsConfig) -> str:
    """Serialize config to JSON string via json.dumps(indent=2)."""
```

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
@click.argument("paths", nargs=-1)
def test(coverage, min_percent, suite, test_name, junit_xml, no_exit_code, paths):
    """Run unit tests via GUT."""

@cli.command()
@click.argument("paths", nargs=-1)
@click.option("--report-format", type=click.Choice(["text", "json"]), default="text")
def lint(paths, report_format):
    """Lint GDScript files via gdlint."""

@cli.command()
@click.argument("paths", nargs=-1)
@click.option("--check", is_flag=True, help="Check only, don't modify (CI mode)")
@click.option("--diff", is_flag=True, help="Show diff of changes")
def format(paths, check, diff):
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

@cli.group()
def config():
    """Configuration management commands."""

@config.command(name="show")
@click.option("--format", "fmt", type=click.Choice(["toml"]), default=None)
@click.option("--json", "as_json", is_flag=True)
def config_show(fmt, as_json):
    """Display resolved configuration (Rich table, TOML, or JSON)."""

@config.command()
def validate():
    """Validate gd-tools.toml — schema, deprecated settings, paths."""
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

def is_gut_installed(project_root: Path) -> bool:
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
    addons/gd-tools-coverage/. Overwrites if stale. Also writes
    _version.txt with the current package version."""

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
  present, `False` when user declines. `run_init()` calls `sys.exit(1)` when
  `install_gut()` returns `False` (user decline = non-zero exit so CI
  detects it) —
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

**Stale addon detection (Track 23, 2026-07-15):**

- `install_coverage_addon()` now writes a `_version.txt` file to
  `addons/gd-tools-coverage/` containing the current package version
  (`__version__`). This file is read by `check_addon_version()` in
  `addon_check.py` on CLI invocation and by `check_coverage_addon()`
  in `doctor.py` to detect version skew between the deployed addon and
  the installed package.

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
    """Verify addons/gd-tools-coverage/*.gd all exist and version
    is not stale."""

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
    paths: list[str] | None = None,
) -> TestResult:
    """Main entry point for `gd-tools test`.
    Orchestrates GUT execution, optionally with coverage.
    When paths is provided, they override config.test_dirs."""

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
    paths: list[str] | None = None,
) -> list[str]:
    """Build GUT CLI args list.
    Base: ['--headless', '-s', 'addons/gut/gut_cmdln.gd', '-gexit']  (--path added by run_godot)
    Add: ['-gdir=<test_dirs>'], ['-gselect=<suite>'], ['-gunit_test_name=<test_name>']
    Add: ['-gjunit_xml_file=<path>']
    When paths is provided, uses paths instead of config.test_dirs,
    formatting each as 'res://path/'."""

def run_gut_with_coverage(
    config: GdToolsConfig,
    gut_args: list[str],
    project_root: Path,
) -> None:
    """Generate coverage plan, set env vars, run Godot+GUT.
    1. Call coverage/plan_generator.generate_plan()
    2. Write plan to .gd-tools/coverage/plan.json
    3. Set env: GD_TOOLS_COVERAGE_PLAN, GD_TOOLS_COVERAGE_OUTPUT
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
godot --headless -s addons/gut/gut_cmdln.gd --path <project_root> -gexit \
  [-gdir=res://test/] \
  [-gselect=<suite>] \
  [-gunit_test_name=<test_name>] \
  [-gjunit_xml_file=<path>] \
  [-gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd] \
  [-gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd]
```

When `--coverage` is NOT specified, the pre/post run hooks are omitted from
args (GUT runs normally without instrumentation). The autoload tracker is
still present but inactive (no plan path set, so `_ready()` skips
instrumentation and `_active` stays `false`).

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

**CI fixes (Track 15, 2026-07-12):**

- Removed `-d` (debug) flag from `build_gut_args()` — debug mode caused
  Godot to abort on `GDScript.reload()` errors during coverage
  instrumentation, preventing GUT's `_end_run()` from writing JUnit XML.
- `run_tests()` default `timeout` changed from `None` to `300` (5 min)
  to prevent infinite hangs in CI/local dev.
- Coverage env vars (`GD_TOOLS_COVERAGE_PLAN`, `GD_TOOLS_COVERAGE_OUTPUT`)
  now use `os.environ.get()` — respects existing env vars set by callers
  (e.g., tests) instead of always overriding with default paths.
- `format_test_results()` prints Godot stdout/stderr with `markup=False` —
  Godot output contains `[/path/to/file]` which Rich interprets as closing
  markup tags, causing `MarkupError` on Linux.
- When JUnit XML is not found, error message now includes Godot exit code,
  stdout (last 2000 chars), and stderr for diagnostics.

**Multi-path support (Track 20, 2026-07-14):**

- `run_tests()` and `build_gut_args()` accept `paths: list[str] | None`.
  When provided, `paths` overrides `config.test_dirs` — each path is
  formatted as `res://path/` and passed to GUT's `-gdir` flag. When `None`
  or empty, config `test_dirs` are used as before.
- `run_coverage_test()` in `orchestrator.py` also accepts `paths` and
  passes it through to `run_tests()`.

---

### 3.8 `lint_runner.py` — gdlint Wrapper

```python
def run_lint(
    config: GdToolsConfig,
    paths: list[str] | None = None,
    report_format: str = "text",
) -> LintResult:
    """Run gdlint on paths, respecting excludes.
    When paths is None or empty, defaults to ['.'].
    Discovers .gd files across all paths, deduplicates.
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
    paths: list[str] | None = None,
    check: bool = False,
    diff: bool = False,
) -> FormatResult:
    """Run gdformat on paths, respecting excludes.
    When paths is None or empty, defaults to ['.'].
    Discovers .gd files across all paths, deduplicates.
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
  subprocess) with `max_line_length` from `config.format.max_line_length`
  (default: 100, configurable via `[format]` section in `gd-tools.toml`).
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

**Multi-path support (Track 20, 2026-07-14):**

- `run_lint()` and `run_format()` accept `paths: list[str] | None`. When
  `None` or empty, defaults to `['.']`. Files are discovered across all
  provided paths and deduplicated via `dict.fromkeys()`.
- CLI `lint` and `format` commands use `@click.argument("paths", nargs=-1)`
  instead of a single `path` argument. Multiple paths are passed as a list.
- `file_discovery.py` now supports **hybrid exclude matching**: bare names
  (no path separator) match basenames (backward-compatible); entries with
  `/` or `\` are normalized to `os.sep` and matched as path prefixes via
  `os.path.relpath`. This allows excluding specific subdirectories while
  keeping same-named directories elsewhere (e.g., `"src/vendor/addons"`).

---

### 3.10 `coverage/plan_generator.py` — Instrumentation Plan Generation

This is the core Python-side component of Architecture C. It uses gdtoolkit's
Lark parser to identify executable lines and branch points.

```python
from lark import Tree
from gdtoolkit.parser import parser

def generate_plan(
    project_root: Path,
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
- `generate_plan()` signature: `(project_root, exclude_dirs,
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

**Autoload inclusion (Track 24.5, 2026-07-15):**

- `resolve_autoload_paths()` was removed. Autoload scripts are no longer
  excluded from the coverage plan.
- Autoloads are now included in instrumentation because `_GDTCoverage._ready()`
  (first autoload, position 0) instruments all files before any other
  autoload's `_ready()` creates instances. This eliminates `ERR_ALREADY_IN_USE`
  errors.
- `plan_generator.py` at 100% coverage after Track 24.5 changes.

---

### 3.11 `coverage/reporter.py` — Report Generation

> **Implemented:** Track 12 (`coverage_reporter_20260711`, archived). See
> `src/gd_tools/coverage/reporter.py` (~510 lines). All 8 success criteria
> passed. Key changes from spec: `FileCoverage` uses `file_id: int` (not
> `path: str`) to match Track 11's coverage data format; `hits` keys are
> `dict[str, int]` (string line IDs, normalized in `read_coverage_json`);
> `generate_report` takes `min_threshold` param and returns `ReportResult`;
> `merge_coverage_data` takes `list[CoverageData]` (not `list[Path]`).
> Errors use Cause/Fix format. 73 unit tests; reporter at 96% coverage.

```python
def generate_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_dir: Path,
    format: str = "html",
    min_threshold: float = 0.0,
) -> ReportResult:
    """Generate coverage report in specified format.
    Dispatches to format-specific reporter via lazy imports.
    Writes report file, then raises CoverageThresholdError if
    threshold not met (report IS written before exception — by design).
    The exception carries ``report_result`` so callers can access the
    summary without recomputation. Returns ReportResult with output
    path and summary."""

@dataclass
class CoverageData:
    version: int
    generated_at: str  # ISO 8601
    files: list[FileCoverage]

@dataclass
class FileCoverage:
    file_id: int  # matches plan FilePlan.file_id
    hits: dict[str, int]  # line_id (str) → hit_count

@dataclass
class CoverageSummary:
    total_lines: int
    covered_lines: int
    line_rate: float  # 0.0 - 1.0
    total_branches: int
    covered_branches: int
    branch_rate: float  # 0.0 - 1.0

@dataclass
class FileSummary:
    file_id: int
    path: str
    total_lines: int
    covered_lines: int
    line_rate: float
    total_branches: int
    covered_branches: int
    branch_rate: float
    uncovered_lines: list[int]

@dataclass
class ReportResult:
    output_path: Path
    summary: CoverageSummary

def compute_summary(plan: CoveragePlan, data: CoverageData) -> CoverageSummary:
    """Cross-reference plan + data to compute coverage percentages.
    Missing files in coverage data get empty FileCoverage (0 hits)."""

def compute_file_summary(
    file_plan: FilePlan,
    file_data: FileCoverage,
) -> FileSummary:
    """Per-file coverage breakdown. Uses line.type == 'branch'
    for branch detection. Tracks uncovered_lines."""

def read_coverage_json(path: Path) -> CoverageData:
    """Read and validate coverage JSON from GDScript addon output.
    Validates version==1, checks for 'files' list, 'file_id' and
    'hits' dict per entry. Normalizes hits keys to strings."""

def merge_coverage_data(files: list[CoverageData]) -> CoverageData:
    """Merge multiple coverage data objects (for parallel CI shards).
    Sums hit counts per file_id/line_id. Empty list returns
    empty CoverageData(version=1)."""
```

---

### 3.12 `coverage/html_reporter.py` — HTML Report

> **Implemented:** Track 12. See `src/gd_tools/coverage/html_reporter.py`.
> Uses Jinja2 `FileSystemLoader` from `templates/` directory.
> Creates `index.html` + `file_<id>.html` per file. CSS classes: covered
> (green), uncovered (red), partial (yellow for hit branches). Source
> code is now populated via `_read_source_lines()` helper which reads
> the original `.gd` file and displays it alongside coverage data
> (resolved commit `8e48360`). 100% test coverage.

```python
def generate_html_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_dir: Path,
) -> Path:
    """Generate HTML coverage report using Jinja2.
    - index.html: summary table (file → line %, branch %)
    - per-file pages: source listing with line numbers + covered/uncovered
    Returns path to index.html."""
```

HTML report features:
- Index page: table of all files with line/branch coverage percentages
- Per-file pages: line numbers with green (covered) / red (uncovered) /
  yellow (partial branch) highlighting
- Summary bar at top of each page
- CSS bundled (no external dependencies)
- Templates: `templates/index.html`, `templates/file.html`

---

### 3.13 `coverage/lcov_reporter.py` — LCOV Format

> **Implemented:** Track 12. See `src/gd_tools/coverage/lcov_reporter.py`
> (90 lines). Generates standard LCOV records. `BRDA` hardcodes block=0,
> branch=0 (acceptable for MVP — each branch on separate line). 100%
> test coverage.

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
SF:scripts/player.gd
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

> **Implemented:** Track 12. See
> `src/gd_tools/coverage/cobertura_reporter.py` (136 lines). Builds XML
> tree with `xml.etree.ElementTree`. `<coverage>` root with `line-rate`/
> `branch-rate` attributes, `<class>` per file, `<line>` elements with
> `number`/`hits`/`branch`/`condition-coverage` attributes. `_format_rate()`
> returns decimal string. 98% test coverage.

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

### 3.15 `coverage/terminal_reporter.py` — Terminal Summary

> **Implemented:** Track 12. See
> `src/gd_tools/coverage/terminal_reporter.py` (107 lines). Uses Rich
> `Table` with columns: File, Lines Found/Hit, Line %, Branches Found/Hit,
> Branch %. Color coding: green >=80%, yellow 50-79%, red <50%.
> `force_terminal=True` for ANSI codes. ASCII box style. 100% test
> coverage.

```python
def generate_terminal_report(
    plan: CoveragePlan,
    data: CoverageData,
) -> CoverageSummary:
    """Generate terminal summary table using Rich.
    Prints color-coded table to stdout.
    Returns CoverageSummary."""
```

---

### 3.16 `coverage/orchestrator.py` — Coverage CLI Orchestration

> **Implemented:** Track 13 (`coverage_cli_20260711`, archived). See
> `src/gd_tools/coverage/orchestrator.py` (275 lines). All 12 acceptance
> criteria passed. CLI commands are thin wrappers that delegate to
> orchestrator functions (NFR-1). Error precedence: `TestFailureError`
> reported before `CoverageThresholdError` (NFR-2). 547 unit tests total
> (25+ in `test_orchestrator.py`). Review fixes (commit `1f69f12`):
> `format` param renamed to `report_format`, `merge_coverage_files()` accepts
> optional `config` param for config-aware default output path,
> `write_coverage_json()` added to `reporter.py`, Cause/Fix error format
> applied to `show_coverage_summary()` threshold error.

```python
def run_coverage_test(
    config: GdToolsConfig,
    min_percent: int | None = None,
    suite: str | None = None,
    test_name: str | None = None,
    junit_xml: str | None = None,
    no_exit_code: bool = False,
    timeout: int | None = 300,
    paths: list[str] | None = None,
) -> TestResult:
    """Run tests with coverage instrumentation enabled.
    1. Generate plan (plan_generator.generate_plan)
    2. Write plan.json to config.coverage.output_dir
    3. Set env vars: GD_TOOLS_COVERAGE_PLAN, GD_TOOLS_COVERAGE_OUTPUT
    4. Run tests via test_runner.run_tests(coverage=True, paths=paths)
    5. Read coverage.json + plan.json
    6. Generate reports (reporter.generate_report)
    7. Apply --min threshold (raises CoverageThresholdError if below)
    8. Print coverage summary table (Lines/Branches: Found/Hit/Rate)
       — on success: after generate_report() returns
       — on threshold failure: BEFORE re-raising CoverageThresholdError
    Error precedence (NFR-2): TestFailureError reported first, then
    CoverageThresholdError. Coverage summary table is printed in both
    cases before any error propagates."""

def generate_coverage_report(
    config: GdToolsConfig,
    report_format: str | None = None,
    output_dir: str | None = None,
) -> ReportResult:
    """Regenerate reports from existing coverage data without re-running tests.
    Reads plan.json + coverage.json from config.coverage.output_dir.
    Calls reporter.generate_report() with format/output_dir overrides."""

def merge_coverage_files(
    files: list[Path],
    output: Path | None = None,
    config: GdToolsConfig | None = None,
) -> Path:
    """Merge multiple coverage data files into one.
    Uses reporter.merge_coverage_data() to sum hit counts per file_id/line_id.
    Writes merged JSON via reporter.write_coverage_json().
    Default output: config.coverage.output_dir / coverage.json (or .gd-tools/coverage/coverage.json)."""

def show_coverage_summary(
    config: GdToolsConfig,
    min_percent: int | None = None,
) -> CoverageSummary:
    """Print terminal summary table from existing coverage data.
    Reads plan.json + coverage.json, computes summary via reporter.
    Prints Rich table (Lines/Branches with Found/Hit/Rate).
    Raises CoverageThresholdError if line_rate*100 < min_percent (Cause/Fix format)."""
```

**Implementation notes (Track 13, 2026-07-12):**

- `orchestrator.py` contains all coverage CLI business logic; CLI commands
  in `cli.py` are thin wrappers that load config and delegate (NFR-1).
- `run_coverage_test()` error precedence (NFR-2): catches
  `TestFailureError` from `run_tests()`, stores it, still generates reports,
  then re-raises: `TestFailureError` first if both occurred (test failures
  take priority over coverage threshold).
- `test_runner.py` `run_tests()` accepts `min_percent` but stores it
  without enforcement ("enforcement deferred to orchestrator" comment) —
  no double-checking. Threshold enforcement happens in
  `reporter.generate_report()` via `min_threshold` parameter.
- `test_runner.py` env vars: `coverage=True` sets
  `GD_TOOLS_COVERAGE_PLAN` (absolute path to `plan.json`),
  `GD_TOOLS_COVERAGE_OUTPUT` (absolute path to `coverage.json`). Uses
  `config.coverage.output_dir`.
- `post_run_hook.gd` updated: converted flat hits dict
  (`"file_id:line_id"`) to per-file format
  (`{files:[{file_id, hits:{line_id:count}}]}`) to match reporter's
  `CoverageData` model. Added `_hits_to_files()` helper.
- CLI `test --coverage`: `TestFailureError` → exit 1,
  `CoverageThresholdError` → exit 1 (via `GdToolsError` handler),
  `CoveragePlanError` → exit 2 (via `GdToolsError` handler). ✅ NFR-4
- CLI `coverage merge`: loads config (with `ConfigError` handler → exit 2),
  passes `config=config` to `merge_coverage_files()`.
- CLI `coverage show`: `CoverageThresholdError` → exit 1,
  `GdToolsError` → exit `e.exit_code`.
- Deviations documented in plan.md: `--timeout` added, `--min` changed
  `float`→`int` in `test` and `show` commands.
- Phase 5 bug fixes: `post_run_hook.gd` format mismatch, missing
  `_GDTCoverage` autoload in fixture project, `pre_run_hook` `else:`
  injection workaround.

**Coverage summary display (Track: coverage_success_display_20260714,
2026-07-14):** Extracted `_print_coverage_table()` helper from
`show_coverage_summary()` (shared by both `show_coverage_summary()` and
`run_coverage_test()`). On success, `run_coverage_test()` now prints
the coverage summary table to stdout after `generate_report()` returns.
On threshold failure, the table is printed BEFORE re-raising
`CoverageThresholdError`. `CoverageThresholdError` now carries an
optional `report_result: ReportResult | None` so the caller can access
the already-computed summary without recomputation. `generate_report()`
passes `report_result=result` when raising. Uses `TYPE_CHECKING` guard
to avoid circular import with `reporter.py`. 5 new tests in
`test_orchestrator.py`; 623 unit tests total, 97.31% coverage.

---

### 3.17 `update_check.py` — PyPI Update Notification

> **Implemented:** Track 19 (`update_check_20260714`, archived). See
> `src/gd_tools/update_check.py` (113 lines). All 5 acceptance criteria
> passed. 14 unit tests in `test_update_check.py`, 4 CLI integration
> tests in `test_cli.py`. `update_check.py` at 95% coverage.

```python
PYPI_URL = "https://pypi.org/pypi/gd-tools-cli/json"
REQUEST_TIMEOUT = 3  # seconds
CACHE_TTL_HOURS = 24
CACHE_DIR = Path.home() / ".gd-tools"
CACHE_FILENAME = "update-check.json"

def check_for_update() -> Optional[str]:
    """Check PyPI for a newer version of gd-tools-cli.
    Returns the latest version string if an update is available,
    or None otherwise. The check is cached for 24 hours and
    fails silently on any error.

    Disabling: Set GD_TOOLS_NO_UPDATE_CHECK=1 to skip the check.
    Dev installs: Skipped when __version__ == "0.0.0"."""

def _read_cached_version() -> Optional[str]:
    """Read cached latest version from ~/.gd-tools/update-check.json.
    Returns None if cache is missing, expired (>24h), corrupt, or
    missing the 'latest_version' key."""

def _fetch_latest_version() -> Optional[str]:
    """Fetch latest version from PyPI JSON API.
    Returns None on any network or parsing error (timeout,
    RequestException, ValueError, KeyError)."""

def _write_cache(version: str) -> None:
    """Write latest version + timestamp to cache file.
    Creates cache directory if it does not exist."""
```

#### CLI Integration

The update check is integrated into the CLI via `GdToolsGroup.invoke()`
in `cli.py`. Before dispatching to the subcommand, `check_for_update()` is
called. If a newer version is found, a notification is printed to
**stderr** (via `click.echo(..., err=True)`) and execution continues
normally -- the check never blocks or fails the command.

```python
class GdToolsGroup(click.Group):
    def invoke(self, ctx) -> Any:
        latest = check_for_update()
        if latest is not None:
            click.echo(
                f"A new version of gd-tools is available: {latest} "
                f"(you have {__version__}).\n"
                f"Run `pip install --upgrade gd-tools-cli` to update.",
                err=True,
            )
        check_addon_version()
        try:
            return super().invoke(ctx)
        except NotImplementedError:
            click.echo("Error: This command is not yet implemented.", err=True)
            ctx.exit(2)
```

> **Addon version check (Track 23, `stale_addon_detection_20260714`,
> archived):** `check_addon_version()` (in `addon_check.py`) is called
> after the PyPI update check and before dispatching to the subcommand.
> It compares the version in `addons/gd-tools-coverage/_version.txt`
> against the installed package version using `packaging.version.parse()`.
> If the addon is stale or the version file is missing, a warning is
> printed to stderr. Suppressed by `GD_TOOLS_NO_UPDATE_CHECK=1`. Fails
> silently on any unexpected error. See §3.18.

#### Testing

An autouse fixture in `tests/unit/conftest.py` patches
`gd_tools.cli.check_for_update` (the imported reference, not the
original function) so all unit tests avoid network calls. Explicit
update-check tests unpatch this fixture when testing the notification
behavior.

---

### 3.18 `addon_check.py` — Stale Addon Version Detection

> **Implemented:** Track 23 (`stale_addon_detection_20260714`, archived).
> See `src/gd_tools/addon_check.py` (75 lines). All 6 success criteria
> passed. 9 unit tests in `test_addon_check.py`. `addon_check.py` at
> 100% coverage.

```python
ADDON_VERSION_FILENAME = "_version.txt"

def check_addon_version() -> None:
    """Check if the deployed coverage addon version is stale.

    Compares the version in _version.txt against the installed package
    version. Prints a warning to stderr if the addon is missing or stale.
    Fails silently on any unexpected error.

    Disabling: Set GD_TOOLS_NO_UPDATE_CHECK=1 to skip the check."""
```

#### CLI Integration

The addon version check is integrated into the CLI via
`GdToolsGroup.invoke()` in `cli.py`. After the PyPI update check and
before dispatching to the subcommand, `check_addon_version()` is called.
If the addon is stale or the version file is missing, a warning is
printed to **stderr** (via `click.echo(..., err=True)`) and execution
continues normally -- the check never blocks or fails the command.

#### Version Comparison

Versions are compared using `packaging.version.parse()`. If either
version string is unparseable, the addon is treated as stale (a warning
is printed showing both versions). An addon version newer than the
package version (downgrade scenario) produces no warning.

#### Doctor Integration

`check_coverage_addon()` in `doctor.py` also reads `_version.txt` and
reports staleness in its `CheckResult` message. A stale addon passes
the check (files are present) but shows a warning with both versions and
a fix hint to run `gd-tools init`.

#### Testing

`check_addon_version()` catches all exceptions silently (`except
Exception: pass`), so it is safe to call from `GdToolsGroup.invoke()`
during any CLI test without patching. Unit tests in
`test_addon_check.py` call `check_addon_version()` directly with mocked
`find_project_root()`, `__version__`, and environment variables to
test the warning, suppression, and version-comparison paths.

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
## Registered as _GDTCoverage in project.godot (first autoload, position 0).
## Instruments files in _ready() when GD_TOOLS_COVERAGE_PLAN is set.

const TRACKER_NAME = "_GDTCoverage"

var _active: bool = false
var _hits: Dictionary = {}  # file_id → {line_id → hit_count}

func _ready() -> void:
    var plan_path := OS.get_environment("GD_TOOLS_COVERAGE_PLAN")
    if plan_path.is_empty():
        return
    var plan := _load_plan(plan_path)
    if plan.is_empty():
        return
    if not _validate_plan(plan):
        return
    _instrument_files(plan)
    # _active stays false — activated later by pre_run_hook.gd

func set_active(active: bool) -> void:
    _active = active

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

# Instrumentation methods (moved from pre_run_hook.gd in Track 24.5):
# _load_plan(path), _validate_plan(plan), _validate_file_entry(entry),
# _instrument_files(plan), _instrument_file(file_entry),
# _inject_trackers(source, file_id, lines), _extract_indent(line),
# _detect_body_indent(source_lines, pattern_index), _log_error(what, cause, fix)
```

**Key design points:**
- Registered as first autoload `_GDTCoverage` (position 0) in `project.godot`
  during `gd-tools init` — ensures `_ready()` runs before any other autoload
- Checks `GD_TOOLS_COVERAGE_PLAN` env var in `_ready()` — if set, loads plan,
  validates, and instruments all files. If not set, skips instrumentation
  (no-op)
- After instrumentation, `_active` stays `false` — activated later by
  `pre_run_hook.gd` calling `set_active(true)`, ensuring hits are only
  recorded during test execution
- Injected code calls `_GDTCoverage.hit(file_id, line_id)` — minimal overhead
  (one bool check + dictionary lookup when active, one bool check when inactive)
- `file_id` and `line_id` are integers from the instrumentation plan (compact,
  fast lookup vs. string keys)
- All instrumentation logic moved from `pre_run_hook.gd` to `coverage.gd` in
  Track 24.5 (eliminates `ERR_ALREADY_IN_USE` by instrumenting before autoloads
  create instances)

---

### 4.2 `pre_run_hook.gd` — GUT Pre-Run Hook

> **Spike-validated:** GUT hooks must `extends GutHookScript` (not `RefCounted`)
> and use `run()` method (not `_init()`). GUT instantiates the hook script and
> calls `run()`.
>
> **Implemented:** Track 11 (`coverage_hooks_20260711`, archived). See
> `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`. All 12 acceptance
> criteria passed.
>
> **Track 24.5 update (2026-07-15):** Simplified to just
> `_GDTCoverage.set_active(true)`. All instrumentation logic (`_load_plan`,
> `_validate_plan`, `_instrument_files`, `_instrument_file`,
> `_inject_trackers`, `_extract_indent`, `_detect_body_indent`, `_log_error`)
> moved to `coverage.gd._ready()`. 38 GUT tests moved to
> `test_coverage_instrumentation.gd`. `pre_run_hook.gd` now has 2 GUT tests.

```gdscript
extends GutHookScript
## GUT pre-run hook. Activates the coverage tracker before tests run.
## Track 24.5: Instrumentation moved to coverage.gd._ready().

func run() -> void:
    _GDTCoverage.set_active(true)
```

**Instrumentation approach (Track 24.5):** All instrumentation logic now lives
in `coverage.gd._ready()` (see Section 4.1). The approach is the same string
manipulation — split source into lines, insert tracker calls (bottom-to-top
to preserve line numbers), set `source_code`, call `reload()`. Two injection
strategies depending on branch type:

- **Before the line** (statements, `if_true`, `loop_body`): tracker is
  injected at the same indentation as the target line, before it.
- **After the keyword line, inside the body** (`match_case`, `if_false`,
  `elif_true`): tracker is injected on the line after `pattern:`, `else:`,
  or `elif:` at the body indentation level. Injecting before these keyword
  lines would insert a statement between the `if`/`elif`/`else` keywords,
  breaking the GDScript block structure (orphaned `else`/`elif` = syntax
  error). The `_detect_body_indent()` helper scans forward from the
  keyword line to find the first non-empty body line and returns its
  indentation.

**`branch_type` null handling:** The plan JSON uses `null` for non-branch
entries. GDScript's `Dictionary.get(key, default)` returns `null` when the
key exists with a null value — only returns the default when the key is
absent. An explicit `if branch_type == null: branch_type = ""` check
prevents assigning `null` to a `String`-typed variable, which would crash
`_inject_trackers` for all files.

**Autoload-based instrumentation (Track 24.5, 2026-07-15):**

- `_GDTCoverage` is registered as the **first** autoload (position 0) via
  `register_coverage_autoload()` in `init.py`, which uses PREPEND instead of
  APPEND. This ensures `_ready()` runs before any other autoload creates
  instances, so instrumentation completes before autoload scripts are loaded
  by user code.
- If `_GDTCoverage` already exists but is not at position 0, `init.py`
  auto-fixes by moving it to position 0 with a stderr warning.
- `_instrument_file()` in `coverage.gd` captures original source **before**
  mutation. On `reload()` returning `ERR_ALREADY_IN_USE`, the original source
  is restored and the file is skipped with a warning.
- On other `reload()` failures, the original source is restored and a
  best-effort `reload()` is attempted to get back to the original state.
- Autoloads are now **included** in the coverage plan (Track 24.5 removed the
  old `resolve_autoload_paths()` exclusion from `plan_generator.py`).
  Because instrumentation runs in `_ready()` before autoloads create
  instances, the `ERR_ALREADY_IN_USE` issue is eliminated.
- 38 GUT tests moved from `test_pre_run_hook.gd` to
  `test_coverage_instrumentation.gd`. `pre_run_hook.gd` now has 2 GUT tests.

**Branch injection fix (Track 21, 2026-07-14):**

- `_inject_trackers` updated to inject `if_false` (`else:`) and `elif_true`
  (`elif:`) trackers **after** the keyword line (inside the body) rather
  than before it. Previously, injecting before `else:` or `elif:` inserted
  a statement between the `if` body and the keyword, producing an orphaned
  `else`/`elif` — a GDScript syntax error. `reload()` silently failed
  (error routed to stderr via `push_error()`), and the error handler
  restored the original source, so tests ran against uninstrumented code
  with 0 coverage hits.
- `match_case` injection (Track 19) was already correct. The fix extends
  the same after-keyword-line strategy to `if_false` and `elif_true`.
- Null guard for `branch_type` added: `Dictionary.get("branch_type", "")`
  returns `null` when the key exists with a null value (plan JSON uses
  `null` for non-branch entries). Explicit `if branch_type == null` check
  prevents a `String`-typed variable from receiving `null`.
- `_detect_body_indent()` helper added (Track 19): scans forward from the
  keyword/pattern line to find the first non-empty body line and returns
  its indentation.
- 2 new GUT tests in `test_pre_run_hook.gd`
  (`test_inject_trackers_if_false_injects_after_else`,
  `test_inject_trackers_elif_true_injects_after_elif`). Expected GUT test
  count updated from 41 to 43 in `test_coverage_hooks.py`.

---

### 4.3 `post_run_hook.gd` — GUT Post-Run Hook

> **Spike-validated:** GUT hooks must `extends GutHookScript` (not `RefCounted`)
> and use `run()` method (not `_init()`).
>
> **Implemented:** Track 11 (`coverage_hooks_20260711`, archived). See
> `src/gd_tools/addons/gd-tools-coverage/post_run_hook.gd` (113 lines). All 12
> acceptance criteria passed. Key deviations from spec below:
> - `run()` checks `tracker.is_active()` before collecting data (no output if
>   tracker was never activated)
> - `_log_error()` uses Cause/Fix format (product-guidelines)
> - `_log_summary(hits, output_path)` prints file/line counts + output path,
>   also returns summary string
> - `_write_json()` returns `bool`; `TRACKER_NAME` constant added
> - 13 GUT tests in `test_post_run_hook.gd`, 11 integration tests in
>   `test_coverage_hooks.py`. Overall coverage 98.65%.

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
| `GD_TOOLS_COVERAGE_PLAN`       | Python  | coverage.gd | Path to plan.json (triggers instrumentation in `_ready()`) |
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
│     GD_TOOLS_COVERAGE_PLAN=<abs_path>/plan.json
│     GD_TOOLS_COVERAGE_OUTPUT=<abs_path>/coverage.json
│
├─ 5. Run Godot with GUT:
│     godot --headless -s addons/gut/gut_cmdln.gd --path <project> -gexit
│       -gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd
│       -gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd
│       -gjunit_xml_file=.gd-tools/results.xml
│
│  ┌─────────────────────────────────────────────────────────┐
│  │ Godot + GUT                                             │
│  │                                                         │
│  │  6. Godot loads autoloads (Track 24.5)                 │
│  │     └─ _GDTCoverage._ready() runs first (position 0)   │
│  │        ├─ Read plan.json from GD_TOOLS_COVERAGE_PLAN   │
│  │        ├─ For each file in plan:                       │
│  │        │   ├─ load(res_path) → GDScript object        │
│  │        │   ├─ Insert _GDTCoverage.hit(file_id, line_id)│
│  │        │   │   before each instrumented line (bottom-up)│
│  │        │   ├─ Set script.source_code = instrumented    │
│  │        │   └─ script.reload()                          │
│  │        └─ _active stays false (tracker not yet active) │
│  │                                                         │
│  │  6b. GUT loads, calls pre_run_hook.run()               │
│  │      └─ _GDTCoverage.set_active(true)                  │
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
├─ 13. Generate report (coverage/reporter.py) ✅ Track 12
│      ├─ HTML: Jinja2 template → .gd-tools/coverage/html/index.html
│      ├─ LCOV: .gd-tools/coverage/lcov.info
│      ├─ Cobertura: .gd-tools/coverage/cobertura.xml
│      └─ Terminal: Rich table → stdout
│
├─ 14. Apply --min threshold (inside generate_report)
│      if overall_coverage < 80% → CoverageThresholdError (with ReportResult)
│
├─ 15. Print coverage summary table (Rich): Lines/Branches Found/Hit/Rate
│      ✅ Track: coverage_success_display_20260714
│      (on success: after generate_report() returns;
│       on threshold failure: BEFORE re-raising CoverageThresholdError)
│
└─ 16. Return TestResult (or re-raise TestFailureError first if both occurred)
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
