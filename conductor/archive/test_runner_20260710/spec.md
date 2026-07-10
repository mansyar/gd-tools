<protect>

# Track 6: Test Runner (GUT Wrapper)

## Track ID
`test_runner_20260710`

## Type
Feature

## Overview

Implement `src/gd_tools/test_runner.py` — the module that orchestrates GUT (Godot Unit Test) via the Godot CLI. The test runner builds the GUT command line from config, invokes Godot as a subprocess, captures stdout/stderr, parses JUnit XML output into structured results, and returns a `TestResult` dataclass. It supports `--suite` and `--test` filter flags, `--no-exit-code` for CI flexibility, and `--coverage` flag infrastructure (env vars + hook args only; full coverage logic deferred to Phase 3).

This is Track 6 in the project roadmap (Phase 2 — MVP1), delivering the first usable test runner for `gd-tools`.

## Dependencies

- **Track 2** (Config System) — for `GdToolsConfig`, `TestConfig` (test_dirs, prefix, suffix, gutconfig)
- **Track 3** (Godot Binary Detection) — for `find_godot()`, `GodotInfo`, `run_godot()`
- **`errors.py`** (Track 1) — for `GUTNotInstalledError`, `TestFailureError`, `GodotNotFoundError`

## Functional Requirements

### FR-1: GUT CLI Argument Construction

The module must build GUT CLI arguments from config:

- **Base command:** `godot -s addons/gut/gut_cmdln.gd -d --path <project_root> -gexit`
- **Test dirs:** Pass test directories via `-gdir=res://<dir1>/,res://<dir2>/` (comma-separated, verified against GUT 9.x source)
- **Prefix/suffix:** Pass via `-gprefix=<prefix>` and `-gsuffix=<suffix>` (from `TestConfig`)
- **Suite filter:** When `--suite NAME` is provided, pass `-gselect=<NAME>`
- **Test name filter:** When `--test NAME` is provided, pass `-gunit_test_name=<NAME>`
- **JUnit XML output:** Pass `-gjunit_xml_file=<absolute_path>` (default: `<project_root>/.gd-tools/results.xml`)
- **Config source:** All test configuration passed via CLI flags. `.gutconfig.json` is NOT used for test execution (it is managed by `gd-tools init` for coverage hooks only).

### FR-2: GUT Installation Check

Before invoking Godot, the module must proactively verify that GUT is installed:

- Check that `<project_root>/addons/gut/gut_cmdln.gd` exists on disk.
- If missing, raise `GUTNotInstalledError` (exit code 2) with an actionable message: "GUT is not installed. Run `gd-tools init` to install it."
- This check runs before any subprocess invocation for fast, clear failure feedback.

### FR-3: Godot Subprocess Invocation

- Use `run_godot()` from `godot.py` (Track 3) to invoke Godot with the built GUT args.
- Capture both `stdout` and `stderr` from the subprocess.
- Support an optional `timeout` parameter (default: None = no timeout).
- Handle `subprocess.TimeoutExpired` → raise `GdToolsError` (exit code 2) with message indicating timeout.
- Handle non-zero Godot exit codes (crash) → raise `GdToolsError` (exit code 2) with captured stderr.

### FR-4: JUnit XML Parsing

- Parse the JUnit XML file produced by GUT using `junitparser`.
- Extract: total tests, passed, failed, skipped, duration (from timestamps).
- Extract per-test details: test name, class/suite name, status (pass/fail/skip), failure message (if any), duration.
- Handle missing JUnit XML file → raise `GdToolsError` (exit code 2) with message "GUT did not produce JUnit XML output. Check GUT stderr for errors."
- Handle malformed/unparseable JUnit XML → raise `GdToolsError` (exit code 2).

### FR-5: Structured TestResult

Return a `TestResult` dataclass with:

```python
@dataclass
class TestResult:
    total: int
    passed: int
    failed: int
    skipped: int
    duration: float
    junit_xml_path: Path | None
    coverage_data_path: Path | None  # None when --coverage not used
    stdout: str  # GUT stdout (for debugging/surfacing on failure)
    stderr: str  # GUT stderr (for debugging/surfacing on failure)
    test_details: list[TestDetail]  # Per-test breakdown
```

```python
@dataclass
class TestDetail:
    name: str
    suite: str
    status: str  # "pass" | "fail" | "skip"
    message: str  # Failure message or empty
    duration: float  # Seconds
```

### FR-6: Exit Code Logic

- `no_exit_code=False` (default): Exit code reflects test results — 0 if all pass, 1 if any fail.
- `no_exit_code=True`: Always exit 0 regardless of test failures (for CI pipelines that want to collect results without failing the build).
- Environment/config errors (Godot not found, GUT not installed, timeout) always exit 2 regardless of `no_exit_code`.
- The `TestFailureError` is raised when tests fail and `no_exit_code=False`. The CLI catches it and exits 1.

### FR-7: Rich Terminal Output

- Always print a Rich table summarizing test results: total, passed, failed, skipped, duration.
- On failure (failed > 0), also print GUT's stdout/stderr for debugging context (truncated if extremely long).
- The `TestResult` dataclass is returned for programmatic use (CLI layer, future coverage integration).
- Output is produced by the test_runner module (not deferred to CLI layer) for self-contained behavior.

### FR-8: Coverage Flag Infrastructure (Phase 2 Stub)

When `--coverage` is passed:

- Set environment variable `GD_TOOLS_COVERAGE_ACTIVE=1` for the Godot subprocess.
- Add `-gpre_run_script=res://addons/gd-tools-coverage/pre_run_hook.gd` to GUT args.
- Add `-gpost_run_script=res://addons/gd-tools-coverage/post_run_hook.gd` to GUT args.
- Do NOT generate instrumentation plan (Track 9, Phase 3).
- Do NOT generate coverage reports (Track 12, Phase 3).
- Do NOT apply `--min` threshold (Track 13, Phase 3).
- If coverage addon files don't exist, GUT may warn but tests should still run (hooks are optional).
- The `coverage_data_path` field in `TestResult` is set to the expected output path (`.gd-tools/coverage/coverage.json`) but may not exist after the run (Phase 3 will make it functional).

### FR-9: CLI Integration

Wire the `test` command in `cli.py` to call `run_tests()`:

- `--coverage` flag → passes `coverage=True`
- `--min N` → passes `min_percent=N` (stored but not enforced in Track 6; enforcement deferred to Phase 3)
- `--suite NAME` → passes `suite=NAME`
- `--test NAME` → passes `test_name=NAME`
- `--junit-xml PATH` → passes `junit_xml=PATH`
- `--no-exit-code` → passes `no_exit_code=True`
- Config loaded via `load_config()` from `config.py`.

## Non-Functional Requirements

### NFR-1: Cross-Platform Path Handling
- All file paths must use `pathlib.Path` for OS-agnostic handling.
- JUnit XML path must be absolute (GUT may interpret relative paths as `user://`-relative).
- Test dirs must be converted from config values to `res://` paths for GUT args.

### NFR-2: Performance
- Test runner overhead (argument building, result parsing, output formatting) must be negligible compared to Godot startup (~1-3s).
- JUnit XML parsing must handle large test suites (1000+ tests) without noticeable delay.

### NFR-3: Error Messages
- All errors must include actionable fix hints (e.g., "Run `gd-tools init` to install GUT").
- Errors must follow the existing `GdToolsError` pattern (message + exit_code attribute).

## Acceptance Criteria

1. **AC-1:** `run_tests()` invokes GUT via Godot CLI and tests execute successfully.
2. **AC-2:** JUnit XML is produced by GUT and parsed into a structured `TestResult` with correct totals (total/passed/failed/skipped).
3. **AC-3:** `--suite NAME` filter works — only tests in the named suite run.
4. **AC-4:** `--test NAME` filter works — only tests matching the name substring run.
5. **AC-5:** Exit code 0 when all tests pass; exit code 1 when any tests fail (and `--no-exit-code` not set).
6. **AC-6:** `--no-exit-code` flag always returns exit 0 regardless of test failures.
7. **AC-7:** GUT stdout/stderr captured and displayed on test failure.
8. **AC-8:** `--coverage` flag sets `GD_TOOLS_COVERAGE_ACTIVE=1` env var and adds pre/post run script args to GUT command (infrastructure only, no plan/report generation).
9. **AC-9:** Missing GUT installation (`addons/gut/gut_cmdln.gd`) detected proactively → `GUTNotInstalledError` (exit code 2) with actionable message.
10. **AC-10:** Missing JUnit XML file after GUT run → clear error message (exit code 2).
11. **AC-11:** Rich summary table printed on every test run showing total/passed/failed/skipped/duration.
12. **AC-12:** Per-test details (name, suite, status, message, duration) available in `TestResult.test_details`.
13. **AC-13:** Works on Windows, macOS, Linux (path handling via `pathlib.Path`).

## Out of Scope

- **Instrumentation plan generation** — Track 9 (Phase 3) implements `coverage/plan_generator.py`.
- **Coverage report generation** — Track 12 (Phase 3) implements HTML/LCOV/Cobertura reporters.
- **Coverage threshold enforcement** — Track 13 (Phase 3) implements `--min` threshold checking.
- **GUT installation/download** — Track 7 (Init Command) handles GUT bootstrap.
- **Coverage addon file creation** — Track 7 (Init) deploys `addons/gd-tools-coverage/` files.
- **Watch mode** — `gd-tools test --watch` is a future roadmap item (post-v1).
- **GdUnit4 support** — Only GUT is supported in v1.

## Key References

- **ROADMAP.md** §4 Track 6 (lines 489-527): Scope, deliverables, success criteria
- **TDD.md** §3.7 (lines 527-600): `test_runner.py` module spec, `build_gut_args()`, `TestResult`, GUT CLI invocation
- **PRD.md** §5: `gd-tools test` command surface, flags, exit codes
- **TESTING_STRATEGY.md** §5.2: Integration test cases for `test_test_runner.py`
- **TDD.md** §5.4: `.gutconfig.json` format (managed by init, not by test_runner)

</protect>
