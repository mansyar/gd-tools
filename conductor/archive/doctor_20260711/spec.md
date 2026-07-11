<protect>
# Track 8: Doctor Command

## Overview

Implement `gd-tools doctor` — a diagnostic command that runs a series of environment and configuration checks and reports the health of a gd-tools project setup. The command produces a rich table with per-check status (pass/fail), severity classification, and actionable fix hints for failures.

**Phase:** 2 — MVP1 (Tool Wrappers)
**Track Type:** Feature
**Dependencies:** Track 2 (config), Track 3 (Godot detection), Track 7 (init — for project structure conventions)
**Module:** `src/gd_tools/doctor.py`
**Key References:** TDD §3.6, PRD §8, ROADMAP Track 8, TESTING_STRATEGY §4.8

---

## Functional Requirements

### FR-1: Nine Diagnostic Checks

The `run_doctor()` function must execute the following 9 checks in order. Each check returns a `CheckResult` dataclass with `name`, `passed`, `message`, `fix_hint`, and `severity`.

| # | Check | Pass Condition | Severity |
|---|-------|---------------|----------|
| 1 | `check_godot_binary` | Godot binary found via detection chain and runs without error | Critical |
| 2 | `check_godot_version` | Godot version >= 4.5.0 | Critical |
| 3 | `check_gut_installed` | `addons/gut/gut.gd` exists in project root | Critical |
| 4 | `check_gut_version` | Installed GUT version matches expected version per `GUT_VERSION_MAP` | Warning |
| 5 | `check_coverage_addon` | All `addons/gd-tools-coverage/*.gd` files present | Warning |
| 6 | `check_gutconfig` | `.gutconfig.json` is valid JSON and contains `pre_run_script` + `post_run_script` keys | Warning |
| 7 | `check_gd_tools_toml` | `gd-tools.toml` exists in project root and is parseable TOML | Critical |
| 8 | `check_gdtoolkit` | `gdlint --version` and `gdformat --version` both succeed | Critical |
| 9 | `check_autoload` | `_GDTCoverage` autoload registered in `project.godot` `[autoload]` section | Critical |

### FR-2: CheckResult Dataclass

```python
@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    fix_hint: str = ""
    severity: str = "critical"  # "critical" or "warning"
```

### FR-3: DoctorResult Dataclass

```python
@dataclass
class DoctorResult:
    checks: list[CheckResult]
    all_passed: bool
```

`run_doctor()` returns a `DoctorResult`. The CLI layer handles table rendering and exit code determination.

### FR-4: Rich Table Output

Output is a `rich.table.Table` with columns:
- **Check** — check name
- **Status** — green ✓ (pass) or red ✗ (critical fail) or yellow ⚠ (warning fail)
- **Message** — what was found (e.g., "Godot 4.6.2 at /usr/bin/godot")
- **Fix Hint** — actionable suggestion for failures (e.g., "Run `gd-tools init` to install GUT")

Color coding follows product-guidelines §2.1:
- Green = pass
- Red = critical failure
- Yellow = warning failure
- Cyan = section header

### FR-5: Actionable Fix Hints

Each failing check must include a concrete fix hint per product-guidelines §4.1. Examples:
- Godot not found → "Install Godot 4.5+ from https://godotengine.org and set GODOT_BIN or add to PATH."
- GUT not installed → "Run `gd-tools init` to install GUT, or see https://github.com/bitwes/Gut."
- gdtoolkit missing → "Run `pip install gdtoolkit` to install gdlint and gdformat."
- Autoload missing → "Run `gd-tools init` to deploy coverage addon (autoload registration in Phase 3)."

### FR-6: Exit Code (Hybrid Model)

- **Exit 0** — all checks pass
- **Exit 1** — any check fails (critical or warning)

Severity (critical/warning) is for display purposes only — it does not affect the exit code. Both critical and warning failures result in exit 1.

### FR-7: No Arguments, No Flags

The `doctor` command takes no arguments and no flags. It is a simple diagnostic command. No `--non-interactive` flag (doctor has no prompts). No `--report-format json` (rich table output only).

---

## Non-Functional Requirements

### NFR-1: Code Quality
- Type hints on all function signatures (Python 3.10+)
- Docstrings on all public functions and classes (Google style, consistent with init.py)
- Module-level docstring referencing TDD §3.6 and PRD §8
- Follows `code_styleguides/python.md` (ruff + black compliant)

### NFR-2: Testing
- Unit tests in `tests/unit/test_doctor.py` covering all 9 checks (pass and fail scenarios)
- Each check tested independently with mocked dependencies
- Integration tests in `tests/integration/test_doctor_integration.py` (if applicable, require real Godot)
- CLI tests in `tests/unit/test_cli.py` for the `doctor` command
- Target: >80% line coverage, >70% branch coverage for `doctor.py`

### NFR-3: Error Handling
- Checks must not raise exceptions — failures are captured as `CheckResult(passed=False, ...)`
- Unexpected exceptions during a check are caught and reported as a failed check with the exception message
- `run_doctor()` never raises — always returns `DoctorResult`

### NFR-4: ASCII-Only Terminal Output
- Use ✓/✗ symbols per PRD §8 and product-guidelines §7
- No emoji in terminal output

---

## Acceptance Criteria

1. **AC-1:** All 9 checks pass on a properly initialized project (post `gd-tools init`)
2. **AC-2:** Missing GUT is detected (check 3 fails) and fix suggestion includes "run `gd-tools init`"
3. **AC-3:** Incompatible GUT version is detected (check 4 fails as warning) and correct version is suggested
4. **AC-4:** Missing coverage addon files are detected (check 5 fails as warning)
5. **AC-5:** Invalid `.gutconfig.json` is detected (check 6 fails as warning)
6. **AC-6:** Missing `gdtoolkit` is detected (check 8 fails as critical)
7. **AC-7:** Output is readable — rich table with ✓/✗ per check, color-coded, with fix hints
8. **AC-8:** Exit code is 0 when all pass, 1 when any check fails
9. **AC-9:** `check_autoload` detects missing `_GDTCoverage` autoload registration in `project.godot`
10. **AC-10:** `run_doctor()` never raises exceptions — all failures are returned as `CheckResult`

---

## Out of Scope

- `--non-interactive` flag (doctor has no prompts)
- `--report-format json` or machine-readable output (rich table only)
- Auto-fixing detected issues (doctor is diagnostic only, not remediation)
- Coverage system checks beyond file/autoload presence (coverage functionality is Phase 3)
- Network connectivity checks
- Performance benchmarks
</protect>
