# ROADMAP: gd-tools Development Plan

**Version:** 0.1.0 (draft)
**Date:** 2026-07-09
**Status:** Phase 4 In Progress — CI/CD Pipeline delivered (Track 15)
**Related docs:** [PRD.md](./PRD.md), [TDD.md](./TDD.md), [TESTING_STRATEGY.md](./TESTING_STRATEGY.md), [SPIKE_coverage_instrumentation.md](./SPIKE_coverage_instrumentation.md)

---

## 1. Overview

This document defines the development roadmap for `gd-tools`, organized as a
sequence of **Conductor Tracks**. Each track is a self-contained unit of work
with a clear goal, bounded scope, verifiable success criteria, and explicit
dependencies on other tracks.

The roadmap is divided into **5 phases**, each delivering an incrementally
more useful product. The phasing is designed so that:

- **The riskiest work happens first** (coverage spike validates the core
  assumption before any coverage code is built).
- **MVP1 (tool wrappers) ships before coverage** — the tool is useful even
  without its differentiating feature.
- **Coverage is built bottom-up** — plan generator → tracker → hooks →
  reporter → CLI integration, with each layer testable in isolation.

---

## 2. Phasing Strategy

```
Phase 0: Spike (Validate)          ──┐
  Track 0: Coverage Spike             │  ~1-2 days
                                      │  Risk: HIGH (make-or-break)
──────────────────────────────────────┘
                                     
Phase 1: Foundation                   ──┐
  Track 1: Project Scaffolding           │  ~2.5 days
  Track 2: Configuration System          │  Risk: LOW-MEDIUM
  Track 3: Godot Binary Detection        │
──────────────────────────────────────────┘
                                     
Phase 2: MVP1 — Tool Wrappers         ──┐
  Track 4: Lint Wrapper                   │  ~7-8 days
  Track 5: Format Wrapper                 │  Risk: LOW-MEDIUM
  Track 6: Test Runner (GUT)             │  ← FIRST USABLE RELEASE
  Track 7: Init Command                  │
  Track 8: Doctor Command                 │
──────────────────────────────────────────┘
                                     
Phase 3: MVP2 — Coverage System       ──┐
  Track 9:  Plan Generator               │  ~10-14 days
  Track 10: Tracker Addon (GDScript)     │  Risk: HIGH (core innovation)
  Track 11: Coverage Hooks (inject)      │  ← THE DIFFERENTIATOR
  Track 12: Reporter                      │
  Track 13: Coverage CLI Integration     │
──────────────────────────────────────────┘
                                     
Phase 4: Polish & Release              ──┐
  Track 14: Test Suite ✅                  │  ~ongoing + 3 days
  Track 15: CI/CD Pipeline ✅              │  Risk: LOW
  Track 16: Documentation                 │
  Track 17: PyPI Release                  │
──────────────────────────────────────────┘

Total estimated effort: ~25-30 days
```

### Milestones

| Milestone | Phase Complete | What You Can Do |
|-----------|---------------|-----------------|
| **M0: Spike Pass** ✅ | Phase 0 | ✅ ACHIEVED — Runtime GDScript instrumentation validated (2026-07-09). All 6 success criteria passed. Architecture C confirmed. |
| **M1: Foundation** ✅ | Phase 1 | ✅ ACHIEVED — Config loads, Godot binary detected, CLI skeleton runs (2026-07-10). Tracks 1-3 all complete. |
| **M2: First Usable** ✅ | Phase 2 | ✅ ACHIEVED — `gd-tools lint`, `format`, `test`, `init`, `doctor` all work (2026-07-11). Tracks 4-8 all complete. |
| **M3: Coverage Alpha** ✅ | Phase 3 | ✅ ACHIEVED — `gd-tools test --coverage` produces line+branch reports; all Phase 3 tracks (9-13) complete (2026-07-12) |
| **M4: v1.0 Release** | Phase 4 | PyPI package, CI/CD, docs, test suite at 80%+ coverage (Track 14 ✅: 99.49% line, 98% branch; Track 15 ✅: CI/CD pipeline with staged gating) |

---

## 3. Dependency Graph

```
                    ┌──────────────┐
                    │  Track 0:    │
                    │  Spike       │
                    └──────┬───────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐         ┌─────────────┐         ┌───────────┐
│Track 9: │         │ Track 10:   │         │ Track 11: │
│Plan Gen │         │ Tracker     │         │ Hooks     │
└────┬────┘         └──────┬──────┘         └─────┬─────┘
     │                     │                      │
     │              ┌──────┘                      │
     │              │                             │
     ▼              ▼                             │
┌──────────┐  ┌──────────┐                        │
│Track 12: │  │ (tracker │                        │
│Reporter  │  │  used by)│                        │
└────┬─────┘  └──────────┘                        │
     │                                            │
     │                      ┌─────────────────────┘
     │                      │
     ▼                      ▼
┌───────────────────────────────────┐
│  Track 13: Coverage CLI          │
│  Integration                     │
└───────────────────────────────────┘


Phase 1 Foundation (parallel to spike for non-coverage tracks):

┌──────────┐     ┌──────────┐     ┌──────────┐
│ Track 1: │────►│ Track 2: │────►│ Track 3: │
│ Scaffold │     │ Config   │     │ Godot    │
└──────────┘     └────┬─────┘     └────┬─────┘
                      │                │
          ┌───────────┼────────┬───────┼────────┐
          │           │        │       │        │
          ▼           ▼        ▼       ▼        ▼
     ┌────────┐  ┌────────┐ ┌──────┐ ┌──────┐ ┌────────┐
     │Track 4:│  │Track 5:│ │Track │ │Track │ │Track 8:│
     │ Lint   │  │ Format│ │ 6:   │ │ 7:   │ │ Doctor │
     │        │  │        │ │ Test │ │ Init │ │        │
     └────────┘  └────────┘ └──────┘ └──────┘ └────────┘
```

### Parallelization Opportunities

| Tracks | Can Run In Parallel? | Why |
|--------|---------------------|-----|
| 0 (Spike) + 1 (Scaffold) | ✅ Yes | No dependency between them |
| 4 (Lint) + 5 (Format) | ✅ Yes | Both depend only on Track 2 |
| 9 (Plan Gen) + 10 (Tracker) | ✅ Yes | Python vs GDScript, no shared code |
| 12 (Reporter) starts early | ✅ Yes | Can begin once plan JSON format is defined (Track 9 design, not implementation) |

---

## 4. Track Specifications

### Track 0: Coverage Instrumentation Spike ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 0 — Validation |
| **Goal** | Prove that GDScript can be instrumented at runtime via source modification + `Script.reload()`, and that tracker calls fire during test execution |
| **Dependencies** | None |
| **Modules** | None (standalone POC) |
| **Effort** | 1-2 days |
| **Risk** | HIGH — make-or-break for Architecture C |
| **Status** | ✅ **COMPLETED** (2026-07-09) — All 6 success criteria passed |
| **Spec doc** | [SPIKE_coverage_instrumentation.md](./SPIKE_coverage_instrumentation.md) |
| **Conductor track** | `spike_coverage_20260709` (archived to `conductor/archive/`) |
| **Commits** | `1cd1e13`..`f717a16` (47 commits, 16 source files, 651 insertions) |

**Scope:**
- Build a minimal Godot project with one source file (`calculator.gd`) and one GUT test file
- Write a simple `pre_run_hook.gd` that modifies `calculator.gd`'s source code (inject `_GDTCoverage.hit(id)` calls) and calls `reload()`
- Write a `tracker.gd` autoload that records hits
- Write a `post_run_hook.gd` that dumps hit data to JSON
- Run GUT and verify trackers fire

**Deliverables:**
- Working POC project (disposable, not part of final codebase)
- Spike results document: what worked, what didn't, lessons learned
- Go/no-go decision for Architecture C

**Success Criteria:**
1. `calculator.gd` is instrumented at runtime (source modified + reloaded)
2. Tracker calls fire during test execution (hit counts > 0)
3. Post-run JSON contains correct hit data
4. Original source file on disk is NOT modified
5. GUT tests pass on instrumented code (no false failures)
6. Reload works without manual editor intervention (headless CLI mode)

**Fallback (if spike fails):**
- Fall back to Architecture B (fork jamie-pate/godot-code-coverage, update for Godot 4.5)
- Or Architecture A (pure Python, accept Reconstructor limitations)

**Spike Results (2026-07-09):**
- ✅ All 6 success criteria PASSED
- ✅ Architecture C (Hybrid) CONFIRMED — proceeding with full implementation
- **Key learnings** (see [SPIKE_coverage_instrumentation.md](./SPIKE_coverage_instrumentation.md) §13):
  1. GUT hooks must `extends GutHookScript` (not `RefCounted`) and use `run()` method (not `_init()`)
  2. `.gutconfig.json` uses `should_exit` (not `exit`)
  3. Godot 4.6.2 used (spec said 4.5) — works correctly
  4. `tracker.gd` needs `set_active(bool)` method for testability (env var alone is insufficient)
  5. Env var activation should check value, not just existence (`=0` or `=false` should deactivate)
  6. Source restoration after instrumentation is not needed (process exits after tests)
  7. Instrumentation must work bottom-to-top to preserve line numbers

---

### Track 1: Project Scaffolding ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 1 — Foundation |
| **Goal** | Create the Python package structure, build system, and CLI skeleton |
| **Dependencies** | None |
| **Modules** | `pyproject.toml`, `src/gd_tools/__init__.py`, `src/gd_tools/__main__.py`, `src/gd_tools/cli.py` (skeleton) |
| **Effort** | 0.5 day |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-09) — All 4 success criteria passed |
| **Conductor track** | `scaffolding_20260709` (archived to `conductor/archive/`) |
| **Commits** | `d0cc81a`..`f882b6e` (6 commits) + review fix `39ae6d9` |

**Scope:**
- `pyproject.toml` with all dependencies from TDD §12
- Package structure (`src/gd_tools/` layout)
- Click CLI skeleton with `--version` and empty command groups (`test`, `lint`, `format`, `coverage`, `init`, `doctor`)
- `__main__.py` entry point (`python -m gd_tools`)
- Console script entry point (`gd-tools` command)
- `.gitignore` (Python, `.gd-tools/`, `.godot/`)
- Basic `README.md` placeholder

**Deliverables:**
- `pip install -e .` works
- `gd-tools --version` prints version
- `gd-tools --help` shows command structure
- `python -m gd_tools` works as alias

**Success Criteria:**
1. `pip install -e .` succeeds without errors
2. `gd-tools --version` outputs `gd-tools 0.1.0`
3. All command groups appear in `--help` output (even if they error "not implemented")
4. Package imports cleanly: `from gd_tools import cli`

**Track 1 Results (2026-07-09):**
- ✅ All 4 success criteria PASSED
- ✅ 39 unit tests, 98.85% coverage (cli.py at 100%)
- ✅ ruff check + black --check pass
- **Review fixes applied:**
  1. Added return type annotations on `main()` and `GdToolsGroup.invoke()`
  2. Added stub tests for `coverage merge` and `coverage show` commands
- **Key implementation notes:**
  - `errors.py` implements full exception hierarchy with `exit_code` attribute and keyword-only override
  - `cli.py` uses custom `GdToolsGroup` class that catches `NotImplementedError` → exit code 2
  - `__main__.py` catches `GdToolsError` → prints to stderr → `sys.exit(e.exit_code)`
  - All command stubs raise `NotImplementedError` (full implementation in Tracks 4-8, 13)

---

### Track 2: Configuration System

| Field | Value |
|-------|-------|
| **Phase** | 1 — Foundation |
| **Goal** | Implement `gd-tools.toml` loading, validation, and default resolution |
| **Dependencies** | Track 1 (package structure) |
| **Modules** | `src/gd_tools/config.py` |
| **Effort** | 1 day |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-10) — All 5 success criteria passed |
| **Conductor track** | `config_20260710` (archived to `conductor/archive/`) |
| **Commits** | `bd09525`..`e41e953` (18 commits) + review fix `d7b0ebe` |

**Scope:**
- Pydantic models for all config sections: `[godot]`, `[test]`, `[lint]`, `[format]`, `[coverage]`
- TOML loading (use `tomllib` on Python 3.11+, `tomli` backport for older)
- Config file discovery: walk up from CWD to nearest `project.godot`, then look for `gd-tools.toml` in same directory
- Default values per PRD §6
- CLI flag override mechanism (config → defaults, CLI flags override)
- Config validation with clear error messages
- `Config` dataclass/object passed to all other modules

**Deliverables:**
- `config.py` with full Pydantic model hierarchy
- Unit tests for config loading, defaults, overrides, error cases

**Success Criteria:**
1. Loading a valid `gd-tools.toml` returns a typed `Config` object
2. Missing config file falls back to defaults (no error)
3. Invalid TOML / invalid values produce clear error messages with file path + line
4. CLI flags override config values (e.g., `--min 90` overrides `min_percent = 80`)
5. Exclude lists use TOML value when present, defaults when absent (replace semantics)

**Key TDD references:** §3 (Module: config.py), §7 (Data Contracts)

**Track 2 Results (2026-07-10):**
- ✅ All 5 success criteria PASSED
- ✅ 51 unit tests (config.py at 100% coverage), 90 tests total at 99.42% coverage
- ✅ ruff check + black --check pass
- **Review fixes applied:**
  1. Added `encoding="utf-8"` to `write_text()` in `generate_gdlintrc` and `generate_gdformatrc` (prevents `UnicodeEncodeError` on Windows with non-ASCII paths)
  2. Collapsed unnecessary split f-string in `validate_coverage` error message
- **Key implementation notes:**
  - Pydantic v2 models with `extra='forbid'` on all sections — catches typo'd config keys (e.g., `[covrage]`)
  - `ConfigDict(extra="forbid")` used instead of inner `Config` class (Pydantic v2 pattern)
  - `__test__ = False` on `TestConfig` prevents pytest from collecting it as a test class
  - Exclude lists use **replace** semantics (not merge): if `exclude` key present in TOML, it replaces `DEFAULT_EXCLUDES`; if absent, `DEFAULT_EXCLUDES` from code is used
  - `save_config` uses `model_dump(exclude_none=True)` — omits `binary=None` from written TOML
  - `find_project_root` uses `Path.resolve()` to handle symlinks correctly
  - TOML parsing uses conditional import: `tomllib` on Python 3.11+, `tomli` backport on 3.10

---

### Track 3: Godot Binary Detection ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 1 — Foundation |
| **Goal** | Implement the 5-level Godot binary resolution chain |
| **Dependencies** | Track 2 (uses config for `[godot].binary`) |
| **Modules** | `src/gd_tools/godot.py` |
| **Effort** | 1 day |
| **Risk** | MEDIUM — platform-specific edge cases |
| **Status** | ✅ **COMPLETED** (2026-07-10) — All 6 success criteria passed |
| **Conductor track** | `godot-detection_20260710` (archived to `conductor/archive/`) |
| **Commits** | `50e5d50`..`3ce2f06` (15 commits) + review fix `f189c80` |

**Scope:**
- Resolution chain: config → env vars (`GODOT_BIN`, `GODOT4_BIN`, `GODOT_PATH`) → PATH (`which`) → common locations → error
- Platform-specific common locations (Windows, macOS, Linux)
- Version detection: run `godot --version`, parse output (e.g., `4.5.1-stable`)
- Version validation: require 4.5+
- `GodotNotFoundError` exception with actionable message
- `find_godot()` → `GodotInfo` (path, version, is_valid)
- `run_godot(args)` → `subprocess.CompletedProcess` (wrapper for consistent invocation)

**Deliverables:**
- `godot.py` with detection + invocation logic
- Unit tests with mocked `shutil.which`, env vars, and platform checks

**Success Criteria:**
1. `find_godot()` returns correct binary when `GODOT_BIN` is set
2. PATH lookup finds `godot` or `godot4` when available
3. Platform-specific locations checked on respective OS
4. `GodotNotFoundError` raised with install instructions when nothing found
5. Version parsing handles `4.5.1-stable`, `4.6-dev`, `4.7` formats
6. Version < 4.5 raises clear error

**Key TDD references:** §3 (Module: godot.py), PRD §9

**Track 3 Results (2026-07-10):**
- ✅ All 6 success criteria PASSED
- ✅ 51 unit tests (godot.py at 99% coverage), 142 tests total at 99.30% coverage
- ✅ ruff check + black --check pass
- **Review fixes applied:**
  1. Added `test_get_godot_version_unparseable_output_raises` (regex-no-match path)
  2. Added `test_get_godot_version_oserror_raises` (OSError exception path)
  3. Added parametrized cases for invalid version format in `check_version_compatible`
  4. Added macOS/Linux not-found message tests
  5. Guarded `LOCALAPPDATA` edge case (unset → relative path bug)
- **Key implementation notes:**
  - `find_godot_binary()` renamed to `find_godot()` returning `GodotInfo` dataclass (path, version, is_valid)
  - `GodotInfo.is_valid` is `False` (not an exception) when version < 4.5 — callers can decide whether to error
  - `get_godot_version()` raises `GodotNotFoundError` on both subprocess failure AND unparseable output
  - `GUT_VERSION_MAP` maps major.minor prefix → GUT version; `get_gut_version_for_godot()` raises `ConfigError` on unmapped versions
  - `run_godot()` merges caller env with `os.environ` (caller takes precedence) and sets `--path` to project_path
  - `_build_not_found_message()` generates platform-specific install instructions

---

### Track 4: Lint Wrapper ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Wrap `gdlint` with config-driven excludes and clean output |
| **Dependencies** | Track 2 (config for exclude list) |
| **Modules** | `src/gd_tools/lint_runner.py` |
| **Effort** | 1 day |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-10) — All 6 success criteria passed |
| **Conductor track** | `lint_wrapper_20260710` (archived to `conductor/archive/`) |
| **Commits** | `062d74e`..`cb14c35` (11 commits) + review fixes `f60bb71`, `45e8bd1`, `4d072ed` |

**Scope:**
- Discover `.gd` files in target path (respecting excludes)
- Invoke `gdlint` via `gdtoolkit` Python API (not subprocess — import directly)
- Parse lint output (violations with file, line, rule, message)
- Format output: terminal (rich tables), JSON (`--report-format json`)
- Exit codes: 0 = clean, 1 = lint errors found, 2 = config/environment error
- `gdlintrc` generation (from config exclude list)

**Deliverables:**
- `lint_runner.py` with `run_lint(path, config) -> LintResult`
- Unit tests with fixture `.gd` files (clean + various violations)

**Success Criteria:**
1. Clean files exit 0
2. Files with violations exit 1 and show readable output
3. `addons/` directory excluded by default
4. JSON output is valid JSON with expected schema
5. Custom exclude dirs from config are respected
6. `gdlintrc` generated by `init` makes `gdlint` work standalone

**Key TDD references:** §3 (Module: lint_runner.py)

**Track 4 Results (2026-07-10):**
- ✅ All 6 success criteria PASSED
- ✅ 190 tests total (99.47% coverage, lint_runner.py at 100%)
- ✅ ruff check + black --check pass
- **Test breakdown:** 33 unit tests in `test_lint_runner.py`, 9 CLI tests in `test_cli.py`, 5 config tests in `test_config.py`, 4 integration tests in `test_lint_integration.py`
- **Review fixes applied:**
  1. Added `pyyaml` to `pyproject.toml` dependencies (was transitive via gdtoolkit, now explicit)
  2. Narrowed `except Exception` to `except LarkError` in `run_lint()` (prevents non-parse errors from being masked as SYNTAX_ERROR)
  3. Updated all plan.md sub-tasks from `[ ]` to `[x]` (tests existed but checkboxes were unchecked)
- **Key implementation notes:**
  - `LintIssue` and `LintResult` dataclasses match TDD §3.8 spec exactly
  - `discover_gd_files()` handles exclude patterns and `.gd` extension filtering
  - `run_lint()` uses `gdtoolkit.linter.lint_code()` Python API (not subprocess) for direct integration
  - Syntax errors (Lark parse failures) are caught and reported as `SYNTAX_ERROR` issues, not crashes
  - `format_lint_text()` uses rich `Table` with `force_terminal=True` for testable ANSI output
  - `format_lint_json()` produces structured JSON with `files_checked`, `error_count`, `issues` fields
  - `generate_gdlintrc()` in `config.py` writes YAML `!!set` format for `excluded_directories`
  - CLI `lint` command: `path` defaults to `.`, `--report-format` (text/json), `--fix` no-op flag, exit codes 0/1/2

---

### Track 5: Format Wrapper ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Wrap `gdformat` with `--check` and `--diff` modes |
| **Dependencies** | Track 2 (config for exclude list) |
| **Modules** | `src/gd_tools/format_runner.py` |
| **Effort** | 1 day |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-10) — All 6 success criteria passed |
| **Conductor track** | `format_wrapper_20260710` (archived to `conductor/archive/`) |
| **Commits** | `d51db2b`..`a0a11d2` (4 commits) + review fix `38f1b25` |

**Scope:**
- Discover `.gd` files (same logic as lint, refactor to shared `file_discovery.py`)
- Invoke `gdformat` via `gdtoolkit` Python API
- `--check` mode: report which files need formatting, don't modify, exit 1 if any
- `--diff` mode: show unified diff of changes (does not modify)
- Default mode: format in place
- `gdformatrc` generation (from config exclude list)

**Deliverables:**
- `format_runner.py` with `run_format(path, config, check=False, diff=False) -> FormatResult`
- Shared `file_discovery.py` (extracted from lint/format common logic)
- Unit tests with fixture files (already formatted, needs formatting, syntax error)

**Success Criteria:**
1. Already-formatted files: exit 0, no changes
2. Unformatted files: `--check` exits 1, lists files; default mode formats them
3. `--diff` shows correct unified diff
4. `addons/` excluded by default
5. Syntax-error files produce clear error, don't crash the tool
6. `gdformatrc` generated by `init` makes `gdformat` work standalone

**Key TDD references:** §3 (Module: format_runner.py)

**Track 5 Results (2026-07-10):**
- ✅ All 6 success criteria PASSED
- ✅ 225 tests total (99.57% coverage; format_runner.py, file_discovery.py,
  cli.py, lint_runner.py all at 100%)
- ✅ ruff check + black --check pass
- **Test breakdown:** 15 unit tests in `test_format_runner.py`, 6 unit tests
  in `test_file_discovery.py`, ~10 CLI tests in `test_cli.py`, 10 integration
  tests in `test_format_integration.py`
- **Review fixes applied:**
  1. Added syntax error reporting to `run_format()` — `except LarkError as e`
     now prints `"Warning: Skipping {file_path}: {e}"` to stderr instead of
     silently swallowing the error (violated AC-6)
  2. Collapsed unnecessary implicit string concatenation in `cli.py` to a
     single f-string
  3. Updated tests to assert syntax error warnings are reported in both unit
     and integration tests
- **Key implementation notes:**
  - `FormatResult` dataclass includes `files_needing_format_paths` field
    (deviation from spec) to list specific files needing formatting in
    `--check` mode
  - `run_format()` uses `gdtoolkit.formatter.format_code()` Python API (not
    subprocess) with `max_line_length=100`
  - `--check` mode returns data; CLI decides exit code (consistent with
    `run_lint` pattern)
  - `--diff` mode uses `difflib.unified_diff` and renders via `rich.Console`
    + `rich.syntax.Syntax`
  - `file_discovery.py` extracted from `lint_runner.py` as shared module —
    `discover_gd_files(path, excludes)` handles recursive `.gd` discovery
    with case-insensitive matching and exclude patterns
  - Syntax errors (Lark parse failures) are caught and reported as warnings
    to stderr, then the file is skipped — does not crash the tool
  - Mutual exclusion of `--check` and `--diff` raises `FormatError(exit_code=2)`
  - `gdformatrc` generation verified in integration tests — `gdformat` works
    standalone after `gd-tools init`

---

### Track 6: Test Runner (GUT Wrapper) ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Orchestrate GUT via Godot CLI, parse JUnit XML, return structured results |
| **Dependencies** | Track 2 (config), Track 3 (Godot binary) |
| **Modules** | `src/gd_tools/test_runner.py` |
| **Effort** | 2 days |
| **Risk** | MEDIUM — GUT CLI interaction, path handling |
| **Status** | ✅ **COMPLETED** (2026-07-10) — All 8 success criteria passed |
| **Conductor track** | `test_runner_20260710` (archived to `conductor/archive/`) |
| **Commits** | `5987228`..`a094ba0` (26 commits) + review fix `e487b9a` |

**Scope:**
- Build GUT command line: `godot --headless -s addons/gut/gut_cmdln.gd --path "$PWD" -gexit`
- Pass test dirs, prefix, suffix from config
- Support `--suite` and `--test` filter flags
- Set JUnit XML output path (absolute, not `user://`)
- Run Godot as subprocess, capture stdout/stderr
- Parse JUnit XML with `junitparser`
- Return structured `TestResult` (total, passed, failed, skipped, duration, per-test details)
- Exit codes: 0 = all pass, 1 = failures, 2 = environment error
- Coverage hook integration points (env vars set here, but actual coverage logic is Phase 3)

**Deliverables:**
- `test_runner.py` with `run_tests(config, suite=None, test=None, coverage=False) -> TestResult`
- Unit tests with mocked Godot subprocess + fixture JUnit XML
- Integration test with real Godot + GUT + sample project

**Success Criteria:**
1. Tests run via GUT and produce JUnit XML
2. JUnit XML parsed into structured results
3. `--suite` filter works (only named suite runs)
4. `--test` filter works (only matching tests run)
5. Exit code reflects pass/fail correctly
6. GUT stdout/stderr captured and surfaced on failure
7. `--coverage` flag sets env vars (no-op until Phase 3, but infrastructure in place)
8. Works on Windows, macOS, Linux (path handling)

**Key TDD references:** §3 (Module: test_runner.py), §5 (End-to-end flow), §7 (Data Contracts)

**Track 6 Results (2026-07-10):**
- ✅ All 8 success criteria PASSED
- ✅ 282 tests total (99.52% coverage; test_runner.py at 99%, cli.py at 100%)
- ✅ ruff check + black --check pass
- **Test breakdown:** 52 unit tests in `test_test_runner.py`, ~10 CLI tests in
  `test_cli.py`, 7 integration tests in `test_test_runner_integration.py`
- **Review fixes applied:**
  1. Removed hardcoded `force_terminal=True` in `format_test_results()` — added
     optional `console` parameter (auto-detect by default, injectable for tests)
  2. Fixed GUT CLI flag names in spec.md and TDD.md: `-gdirs` → `-gdir`,
     `-gname` → `-gunit_test_name` (verified against GUT 9.x source)
  3. Replaced non-idiomatic `del min_percent` with a comment for API
     compatibility documentation
- **Key implementation notes:**
  - `TestDetail` and `TestResult` dataclasses with `__test__ = False` to
    prevent pytest collection
  - `build_gut_args()` uses GUT 9.x CLI flags: `-gdir` (comma-separated test
    dirs), `-gselect` (suite filter), `-gunit_test_name` (test name filter),
    `-gjunit_xml_file`, `-gpre_run_script`, `-gpost_run_script`
  - `check_gut_installed()` verifies `addons/gut/gut_cmdln.gd` exists
  - `parse_junit_xml()` uses `junitparser`, handles missing/malformed XML
  - `run_tests()` orchestrates: `find_project_root()` →
    `check_gut_installed()` → `find_godot()` → `build_gut_args()` →
    `run_godot()` → `parse_junit_xml()` → `format_test_results()`
  - `run_godot()` merges env with `os.environ` (caller takes precedence) —
    coverage env vars passed safely without clobbering existing environment
  - `TestFailureError` (exit 1) caught before `GdToolsError` (exit 2) in CLI
  - Integration tests use `@skip_if_no_godot` marker (7 skipped in CI)
  - `--coverage` flag sets `GD_TOOLS_COVERAGE_*` env vars (no-op until
    Phase 3, but infrastructure in place)

---

### Track 7: Init Command ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Bootstrap a Godot project: install GUT, deploy coverage addon, generate configs |
| **Dependencies** | Track 2 (config), Track 3 (Godot version detection) |
| **Modules** | `src/gd_tools/init.py` |
| **Effort** | 2-3 days |
| **Risk** | MEDIUM — `project.godot` editing, zip download/extract, idempotency |
| **Status** | ✅ **COMPLETED** (2026-07-11) — All 10 success criteria passed |
| **Conductor track** | `init_20260710` (archived to `conductor/archive/`) |
| **Commits** | `1af60d5`..`1f542a2` (42 commits) + review fix `ca5e743` |

**Scope:**
- Detect project root (find `project.godot`)
- Detect Godot version (Track 3)
- GUT version mapping table (Godot 4.5→GUT 9.5.0, 4.6→9.6.0, 4.7→9.7.0)
- Check if GUT installed (`addons/gut/gut.gd` exists?)
  - If yes: verify version, warn if mismatch
  - If no: prompt user (interactive Y/n, or `--non-interactive` for CI)
    - Y: download from GitHub releases, extract zip, copy `addons/gut/`
    - n: print manual instructions
- Enable GUT plugin in `project.godot` (add to `[editor_plugins]`, idempotent)
- Deploy coverage addon (copy bundled GDScript files to `addons/gd-tools-coverage/`)
  - Note: files are placeholders until Phase 3 implements real functionality
- Create/update `.gutconfig.json` (merge coverage hook paths)
- Create `gd-tools.toml` (with defaults, preserve existing if present)
- Generate `gdlintrc` and `gdformatrc` from config
- Create `.gd-tools/` directory, add to `.gitignore`
- Print summary of actions taken
- `--non-interactive` flag for CI (assume defaults, don't prompt)

**Deliverables:**
- `init.py` with `run_init(non_interactive=False) -> InitResult`
- Bundled addon files (placeholder GDScript until Phase 3)
- Unit tests with temp project directories

**Success Criteria:**
1. Running `init` in a Godot project installs GUT correctly
2. `project.godot` has GUT plugin enabled (idempotent — running twice doesn't duplicate)
3. Coverage addon files copied to `addons/gd-tools-coverage/`
4. `.gutconfig.json` created with correct hook paths
5. `gd-tools.toml` created with defaults
6. `gdlintrc` and `gdformatrc` generated
7. `.gd-tools/` created and in `.gitignore`
8. `--non-interactive` mode works without prompts
9. Re-running `init` is idempotent (no duplicates, updates stale files)
10. GUT download fails gracefully (network error → instructions for manual install)

**Key TDD references:** §3 (Module: init.py), PRD §7

**Track 7 Results (2026-07-11):**
- ✅ All 10 success criteria PASSED
- ✅ 329 tests total (41 unit tests in `test_init.py`, 3 CLI tests in
  `test_cli.py`, 3 integration tests in `test_init_integration.py`), 7
  skipped (require Godot), 0 failed
- ✅ 98.30% overall coverage; `init.py` at 96%
- ✅ ruff check + black --check pass
- **Review fixes applied:**
  1. Changed `install_gut()` return type from `None` → `bool`. Returns
     `True` when GUT installed/already present, `False` when user declines.
     `run_init()` now calls `sys.exit(0)` when user declines (spec FR-3:
     "Exit 0") — prevents enabling a non-existent plugin downstream
  2. Replaced non-ASCII bullet `•` (U+2022) with `-` in `print_summary`
     (product-guidelines §7: ASCII-only terminal output)
  3. Removed unused imports from `init.py` (`generate_gdformatrc`,
     `generate_gdlintrc`, `ConfigError`, `GodotNotFoundError`, `GodotInfo`)
     and the `# ruff: noqa: F401` directive
  4. Updated `plan.md` sub-task checkboxes from `[ ]` to `[x]`
- **Key implementation notes:**
  - 14 functions in `init.py` (561 lines): `run_init`, `find_project_root`,
    `detect_godot_version`, `check_gut_installed`, `install_gut`,
    `download_gut`, `extract_gut`, `enable_gut_plugin`,
    `install_coverage_addon`, `update_gutconfig`, `create_config_file`,
    `create_data_dir`, `generate_lint_format_rcs`, `print_summary`
  - GUT download from GitHub releases (`bitwes/Gut`), zip extraction to
    temp dir, copy `addons/gut/` to project
  - `project.godot` editing: `[editor_plugins]` enabled entry (idempotent)
  - Coverage addon stubs deployed as package data via
    `[tool.setuptools.package-data]` in `pyproject.toml`
  - `.gutconfig.json` merge: preserves user keys (`dirs`, `prefix`, `suffix`,
    `include_subdirs`), always overwrites hook paths + `should_exit` +
    `junit_xml_file`
  - `gdlintrc`/`gdformatrc` generation policy: generate-if-missing,
    warn-if-differs (PRD §16 Open Question 1 resolved)
  - `.gd-tools/` data directory created, added to `.gitignore` if not present
  - `--non-interactive` flag: assumes yes for GUT install, skips all prompts
  - `print_summary()` prints ASCII-only summary of actions taken

---

### Track 8: Doctor Command ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Run diagnostic checks and report environment health |
| **Dependencies** | Track 2 (config), Track 3 (Godot detection) |
| **Modules** | `src/gd_tools/doctor.py` |
| **Effort** | 1 day |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-11) — All 8 success criteria passed |
| **Conductor track** | `doctor_20260711` (archived to `conductor/archive/`) |
| **Commits** | `e0c5ad3`..`f29253f` (37 commits) + review fix `ffe3124` |

**Scope:**
- Run all checks from PRD §8:
  1. Godot binary accessible
  2. Godot version 4.5+
  3. GUT installed
  4. GUT version compatible
  5. Coverage addon files present
  6. `.gutconfig.json` valid + has hook paths
  7. `gd-tools.toml` exists and valid
  8. `gdtoolkit` installed (`gdlint --version` succeeds)
  9. `_GDTCoverage` autoload registered in `project.godot`
- Output: rich table with ✓/✗ per check + actionable fix suggestions
- Exit code: 0 = all pass, 1 = any check fails (critical or warning)

**Deliverables:**
- `doctor.py` with `run_doctor() -> DoctorResult` and `format_doctor_table()`
- Unit tests with mocked environment states

**Success Criteria:**
1. All checks pass on a properly initialized project
2. Missing GUT is detected and fix suggestion is shown
3. Incompatible GUT version is detected
4. Missing coverage addon files are detected
5. Invalid `.gutconfig.json` is detected
6. Missing `gdtoolkit` is detected
7. Output is readable (table format with colors)
8. Exit code reflects overall health

**Key TDD references:** §3 (Module: doctor.py), PRD §8

**Track 8 Results (2026-07-11):**
- ✅ All 8 success criteria PASSED
- ✅ 388 tests total (55 unit tests in `test_doctor.py`, 4 CLI tests in
  `test_cli.py`, 2 integration tests in `test_doctor_integration.py`), 7
  skipped (require Godot), 0 failed
- ✅ 97.80% overall coverage; `doctor.py` at 100% (line + branch)
- ✅ ruff check + black --check pass
- **Review fixes applied:**
  1. Added `tomllib`/`tomli` compatibility shim for Python 3.10 (matching
     `config.py` pattern: `sys.version_info >= (3, 11)` check)
  2. Added `timeout=10` to `check_gdtoolkit` subprocess call
  3. Simplified `check_gutconfig` exception handling: `(json.JSONDecodeError,
     ValueError)` → `ValueError` (JSONDecodeError is subclass)
  4. Changed `check_autoload` autoload match from `startswith("_GDTCoverage")`
     to `startswith("_GDTCoverage=")` to avoid false positives
- **Key implementation notes:**
  - 9 diagnostic checks, each returning `CheckResult` dataclass with
    `name`, `passed`, `message`, `fix_hint`, `severity` ("critical"/"warning")
  - `run_doctor()` orchestrates: resolves project root → loads config →
    detects Godot version → runs all 9 checks → returns `DoctorResult`
  - `run_doctor()` never raises — all exceptions caught and converted to
    failed `CheckResult` with severity "critical"
  - `format_doctor_table()` builds rich `Table` with color-coded status:
    green ✓ (pass), red ✗ (critical fail), yellow ⚠ (warning fail)
  - Python 3.10 compatibility: `tomllib`/`tomli` shim, `list[CheckResult]`
    type hint (requires `from __future__ import annotations` on 3.9)

---

### Track 9: Coverage Plan Generator ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Parse GDScript with gdtoolkit/Lark, identify executable lines + branch points, generate instrumentation plan JSON |
| **Dependencies** | Track 0 (spike validated approach), Track 2 (config for excludes) |
| **Modules** | `src/gd_tools/coverage/plan_generator.py` |
| **Effort** | 3-4 days |
| **Risk** | MEDIUM-HIGH — Lark AST traversal, statement classification |
| **Status** | ✅ **COMPLETED** (2026-07-11) — All 12 acceptance criteria passed |
| **Conductor track** | `coverage-plan-generator_20260711` (archived to `conductor/archive/`) |
| **Commits** | `baa3890`..`06978b7` (20 commits) + review fixes `d822a5b`, `a36d966` |

**Scope:**
- Use `gdtoolkit.parser.parse(code, gather_metadata=True)` to get Lark AST
- Implement Lark `Visitor` pattern to walk AST bottom-up
- Statement classification:
  - **Executable (track):** `expr_stmt`, `return_stmt`, `func_var_assigned`, `func_var_typed_assgnd`, `func_var_inf`, `break_stmt`, `continue_stmt`
  - **Branch points:** `if_stmt` (if_true, elif_true, if_false), `while_stmt` (loop_body), `for_stmt`/`for_stmt_typed` (loop_body), `match_stmt` (match_case per branch)
  - **Skip:** `pass_stmt`, `breakpoint_stmt`
  - **Declarative (not tracked):** `const_stmt`, `class_var_stmt`, `signal_stmt`, `enum_stmt`, `func_def`, `static_func_def`, `extends_stmt`, `classname_stmt`
- Extract `meta.line` for each tracked node
- Assign unique IDs to each trackable point
- Generate plan JSON per TDD §7 data contract
- File discovery (respect excludes, skip test dirs as coverage targets)
- Source hash for staleness detection

**Deliverables:**
- `plan_generator.py` with `generate_plan(config) -> CoveragePlan`
- Unit tests with all 6 GDScript fixtures from TESTING_STRATEGY §7
- Expected plan JSON fixtures for each test file

**Success Criteria:**
1. `simple.gd` → correct line IDs, no branches
2. `branches.gd` → correct if_true/if_false branch IDs
3. `loops.gd` → correct loop_body branch IDs
4. `match_stmt.gd` → correct match_case branch IDs
5. `nested.gd` → correct nested branch IDs
6. `edge_cases.gd` → empty functions, single-line functions, etc. handled
7. Plan JSON matches schema in TDD §7
8. `addons/` excluded by default
9. Source hash included for staleness detection
10. Performance: <1s for a 100-file project

**Key TDD references:** §3 (Module: coverage/plan_generator.py), §7 (Data Contracts), §10 (Coverage Architecture)

**Reference:** b4 compressed section contains the full Lark grammar research and statement classification details.

**Track 9 Results (2026-07-11):**
- ✅ All 12 acceptance criteria PASSED
- ✅ 437 tests total (49 unit tests in `test_plan_generator.py`, 2 in
  `test_generate_expected_plans.py`), 7 skipped (require Godot), 0 failed
- ✅ 98.03% overall coverage; `plan_generator.py` at 100% (116 statements,
  0 missed, 26 branches, 0 partial)
- ✅ ruff check + black --check pass
- **Test breakdown:** 49 unit tests in `test_plan_generator.py` (data
  structures, JSON I/O, parsing, classification, plan generation, fixtures,
  performance, error handling), 2 tests in `test_generate_expected_plans.py`
  (regenerates fixtures, checks no drift)
- **Review fixes applied:**
  1. Added schema validation to `read_plan_json` — validates `files` is a
     list, each file entry is a dict, and required fields (`file_id`, `path`,
     `source_hash`) are present. All failures raise `CoveragePlanError`
     instead of raw `KeyError`
  2. Added 7 new tests: `test_read_plan_json_missing_files_field`,
     `test_read_plan_json_data_not_dict`, `test_read_plan_json_files_not_list`,
     `test_read_plan_json_file_entry_missing_field`,
     `test_read_plan_json_file_entry_not_dict`,
     `test_generate_plan_with_custom_exclude_dirs`,
     `test_generate_plan_with_custom_test_dirs`
  3. Fixed imprecise test assertions in
     `test_generate_plan_excludes_addons` and
     `test_generate_plan_excludes_test_dirs` — exact path checks instead of
     substring matching
  4. Cleaned up stream-of-consciousness comments in
     `test_declarations_not_tracked`
  5. Fixed plan.md tracking checkboxes (Phase 2 `[~]`→`[x]`, Phase 5 & 6
     `[ ]`→`[x]`)
- **Key implementation notes:**
  - `CoveragePlan`, `FilePlan`, `LinePlan` dataclasses with `to_dict()`/
    `from_dict()` serialization methods
  - `CoverageVisitor` is a Lark `Visitor` subclass — visits nodes by method
    name matching (e.g., `expr_stmt()`, `if_stmt()`, `match_stmt()`)
  - `parse_gdscript()` uses `gdtoolkit.parser.parse(source,
    gather_metadata=True)`
  - `generate_plan()` reuses `discover_gd_files()` from `file_discovery.py`,
    filters test_dirs from coverage targets
  - Source hash: SHA-256 with `sha256:` prefix for staleness detection
  - JSON I/O: `write_plan_json` / `read_plan_json` with `CoveragePlanError`
    on invalid input (missing file, invalid JSON, schema mismatch)
  - `tools/generate_expected_plans.py` — CLI script to regenerate all 6
    expected plan JSON fixtures from GDScript fixture files
  - 6 GDScript fixtures: `simple.gd`, `branches.gd`, `loops.gd`,
    `match_stmt.gd`, `nested.gd`, `edge_cases.gd`
  - 6 expected JSON plans verified correct against fixtures

---

### Track 10: Coverage Tracker Addon (GDScript) ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Implement the GDScript autoload singleton that tracks hit counts |
| **Dependencies** | Track 0 (spike validated approach) |
| **Modules** | `src/gd_tools/addons/gd-tools-coverage/coverage.gd` (bundled) |
| **Effort** | 1 day |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-11) — All 7 success criteria passed |
| **Conductor track** | `coverage_tracker_20260711` (archived to `conductor/archive/`) |
| **Commits** | `995405c`..`cba89f5` (7 commits) + review fix `a207175` |

**Scope:**
- Autoload singleton (`_GDTCoverage` / `GDTTracker`)
- `hit(file_id: int, line_id: int)` — record a hit (increment counter)
- Internal data structure: `Dictionary` keyed by `file_id`, value is `Dictionary` of `line_id → count`
- `reset()` — clear all hit data
- `get_data() -> Dictionary` — serialize hit data for JSON output
- `set_active(active: bool)` — enable/disable tracking
- `_ready()` — check `GD_TOOLS_COVERAGE_ACTIVE` env var, set active flag
- When inactive, `hit()` is a no-op (single bool check, minimal overhead)
- Thread-safe (GUT tests may use coroutines/await)

**Deliverables:**
- `coverage.gd` (final version, replaces placeholder from Track 7)
- Updated `init.py` to deploy the real file
- Manual test: load in Godot editor, verify autoload works

**Success Criteria:**
1. Autoload registers correctly in `project.godot`
2. `hit(0, 5)` records correctly, `get_data()` returns `{"0": {"5": 1}}`
3. Multiple hits to same line increment correctly
4. `reset()` clears all data
5. When `GD_TOOLS_COVERAGE_ACTIVE` not set, `hit()` is a no-op
6. When active flag is false, overhead is minimal (single bool check)
7. Works with coroutines (no threading issues with `await`)

**Key TDD references:** §4.1 (GDScript Addon: coverage.gd)

**Track 10 Results (2026-07-11):**
- ✅ All 7 success criteria PASSED
- ✅ 442 tests total (3 new unit tests in `test_init.py` for
  `register_coverage_autoload`, 6 GUT tests in
  `test_coverage_tracker.gd`, 1 integration test in
  `test_coverage_tracker_integration.py`), 8 skipped (require Godot), 0
  failed
- ✅ 98.74% overall coverage; `init.py` at 97%
- ✅ ruff check + black --check pass
- ✅ gdlint + gdformat pass on GDScript files
- **Review fixes applied:**
  1. Fixed `test_doctor_after_init` regression — Track 10 added
     `register_coverage_autoload()` to `run_init()`, causing the
     autoload check to pass after init (previously asserted failure).
     Updated test to assert `all_passed` and `check_map["Autoload"].passed`
  2. Replaced manual autoload string construction in integration test
     with `register_coverage_autoload(tmp_path)` call
  3. Removed duplicate unchecked task in `plan.md`
  4. Added `test_register_coverage_autoload_handles_no_trailing_newline`
     for uncovered branch
- **Key implementation notes:**
  - `coverage.gd` extends `Node`, registered as autoload `_GDTCoverage`
  - `_hits: Dictionary` keyed by `file_id`, value is `Dictionary` of
    `line_id → count`
  - `_ready()` checks `GD_TOOLS_COVERAGE_ACTIVE` env var (value-aware:
    `0`/`false`/empty deactivates)
  - `hit(file_id, line_id)` is no-op when inactive (single bool check)
  - `register_coverage_autoload()` in `init.py` adds autoload entry to
    `project.godot` `[autoload]` section (idempotent, handles trailing
    newline)
  - `COVERAGE_AUTOLOAD_PATH` constant in `init.py` points to bundled
    `coverage.gd`

**GUT Integration Bug Fixes (post-Track 10, commits `67c9aa3`, `6d48a05`):**

After Track 10, integration tests were found to be always skipped due to a
skip condition bug. Once fixed, four pre-existing bugs in
`test_runner.py` surfaced:

1. **Skip condition ignored `GODOT_BIN` env var** — Integration tests used
   `shutil.which("godot") is None` as sole skip condition, ignoring the
   `GODOT_BIN` env var. Added `.env` file loading via `conftest.py` and
   updated skip condition to `not (os.environ.get("GODOT_BIN") or
   shutil.which("godot"))` (commit `67c9aa3`)

2. **Missing `--import` step** — `run_tests()` didn't run
   `godot --headless --import` before GUT. On fresh projects without
   `.godot/` cache, GUT class names aren't registered, causing silent
   failure (exit 0, no JUnit XML). Added import step after `find_godot()`,
   before `.gd-tools/` dir creation. Does not check returncode (benign
   import warnings may produce non-zero exit)

3. **`-gselect` with `res://` prefix doesn't match** — GUT's `-gselect`
   matches against filename only, not `res://`-prefixed paths. Fixed
   `build_gut_args()` to strip `res://` prefix and extract filename via
   `Path(select_name).name`

4. **GUT exit code 1 treated as crash** — GUT exits 0 (all pass) or 1
   (some fail). Code checked `returncode != 0`, treating test failures as
   crashes and preventing `TestFailureError`. Changed to
   `returncode > 1` (crash codes only)

5. **Missing `--headless` flag** — Godot window opened during test runs.
   Added `--headless` as first element in GUT base args

**Final test results after all fixes:** 452 passed, 0 failed, 0 skipped
(425 unit + 27 integration). 98.65% overall coverage. These were the
FIRST integration tests to ever actually run.

---

### Track 11: Coverage Hooks (Instrumentation Engine) ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Implement GUT pre-run and post-run hooks that instrument GDScript at runtime and collect coverage data |
| **Dependencies** | Track 0 (spike), Track 9 (plan format), Track 10 (tracker) |
| **Modules** | `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`, `post_run_hook.gd` |
| **Effort** | 3-4 days |
| **Risk** | HIGH — core innovation, source injection + reload |
| **Status** | ✅ **COMPLETED** (2026-07-11) — All 12 acceptance criteria passed |
| **Conductor track** | `coverage_hooks_20260711` (archived to `conductor/archive/`) |
| **Commits** | `d1d0668`..`ed65874` (11 commits) + review fixes `47ed18a`, `431eafd`, `a4f139b` |

**Scope:**
- **`pre_run_hook.gd`:**
  - Read `GD_TOOLS_COVERAGE_PLAN` env var → load plan JSON
  - For each file in plan:
    - Load script via `ResourceLoader` or `load()`
    - Get `source_code` from script
    - Inject `_GDTCoverage.hit(file_id, line_id)` calls before each tracked line
    - Injection strategy: split source into lines, work bottom-to-top, insert tracker with matching indentation
    - Set `script.source_code = injected_source`
    - Call `script.reload()` to recompile
  - Set tracker active via `_GDTCoverage.set_active(true)`
  - Handle errors gracefully (compile error in instrumented code → clear error, skip file)
- **`post_run_hook.gd`:**
  - Get coverage data from `_GDTCoverage.get_data()`
  - Serialize to JSON
  - Write to path from `GD_TOOLS_COVERAGE_OUTPUT` env var
  - Restore original source code (set `source_code` back, `reload()`)
  - Log summary (files instrumented, total hits)

**Deliverables:**
- `pre_run_hook.gd` and `post_run_hook.gd` (final versions)
- Updated `init.py` to deploy real files
- Integration test: full coverage run on sample project

**Success Criteria:**
1. Plan JSON is read and parsed correctly
2. Each file in plan is instrumented (source modified + reloaded)
3. Tracker calls fire during test execution (verified by hit data)
4. Coverage JSON written to correct path
5. Original source restored after run (no side effects on project files)
6. Instrumentation preserves code semantics (tests pass on instrumented code)
7. Indentation of injected code matches surrounding context
8. Compile errors in instrumented code are caught and reported clearly
9. Works in headless mode (`godot -s ... -gexit`)
10. Performance: instrumentation of 50 files < 5 seconds

**Key TDD references:** §6 (GDScript Addon: hooks), §5 (End-to-end flow)

**Reference:** SPIKE_coverage_instrumentation.md contains the POC implementation. This track productionizes it.

**Track 11 Results (2026-07-11):**
- ✅ All 12 acceptance criteria PASSED
- ✅ 452 unit tests passed (98.65% overall coverage), 11 integration tests
  passed (all GUT suites pass inside them), 0 failed
- ✅ ruff check + black --check pass
- ✅ gdlint + gdformat pass on GDScript files
- **Test breakdown:** 28 GUT tests in `test_pre_run_hook.gd` (plan loading,
  validation, instrumentation, indentation, tracker activation), 13 GUT tests
  in `test_post_run_hook.gd` (tracker retrieval, JSON building, file writing,
  summary logging, run flow), 11 integration tests in
  `test_coverage_hooks.py` (GUT suite pass-through, end-to-end flow, missing
  env vars, malformed plan, nonexistent script, headless mode, performance
  50 files <60s, empty plan, unloadable script)
- **Review fixes applied:**
  1. Added line entry validation in `_validate_file_entry` — each line_entry
     must be a Dictionary with `line` and `id` keys (prevents unhandled
     runtime crash on malformed plans)
  2. Fixed `_log_error` in both hooks — changed `\n` to `\n\n` before
     Cause/Fix section per product-guidelines (blank line between error
     description and Cause/Fix)
- **Key implementation notes (pre_run_hook.gd, 228 lines):**
  - `run()` reads `GD_TOOLS_COVERAGE_PLAN` env var, calls `_load_plan()`,
    `_validate_plan()`, `_instrument_files()`, `_activate_tracker()`
  - `_validate_plan()` validates version, files list; `_validate_file_entry()`
    validates file_id, path, lines, and each line entry's `line`/`id` keys
  - `_instrument_file()` loads script via `load()`, gets `source_code`, calls
    `_inject_trackers()`, sets `source_code`, calls `reload()`
  - `_inject_trackers()` is `static`, sorts lines descending (bottom-to-top),
    inserts `_GDTCoverage.hit(file_id, line_id)` before each tracked line
    with matching indentation via `_extract_indent()`
  - `_activate_tracker()` finds `_GDTCoverage` autoload via `SceneTree.root`,
    calls `set_active(true)`
  - `_log_error(what, cause, fix)` uses Cause/Fix format per product-guidelines
  - `TRACKER_NAME` constant = `"_GDTCoverage"`
- **Key implementation notes (post_run_hook.gd, 113 lines):**
  - `run()` gets tracker, checks `is_active()`, collects `get_hits()`,
    builds JSON, writes to `GD_TOOLS_COVERAGE_OUTPUT` env var path
  - `is_active()` guard prevents output if tracker was never activated
  - `_build_coverage_json()` produces `{version:1, generated_at, files:[{file_id, hits:{line_id:count}}]}`
  - `_write_json()` creates parent dirs, writes with 2-space indent
  - `_log_summary()` prints file count, line count, output path; returns
    summary string

---

### Track 12: Coverage Reporter ✅

**Status:** ✅ COMPLETED (2026-07-11)
**Conductor track:** `coverage_reporter_20260711` (archived to `conductor/archive/`)
**Commits:** `36c648f`..`6aff1d0` (33 commits) + review fixes `e9457ec`

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Read coverage data + plan, compute metrics, generate reports (HTML, LCOV, Cobertura, terminal) |
| **Dependencies** | Track 9 (plan format for cross-reference) |
| **Modules** | `src/gd_tools/coverage/reporter.py`, `html_reporter.py`, `lcov_reporter.py`, `cobertura_reporter.py`, `terminal_reporter.py` |
| **Effort** | 2-3 days |
| **Risk** | LOW |

**Scope:**
- Read plan JSON (all trackable points) + coverage JSON (hit data)
- Compute metrics:
  - Line coverage: (executed lines / total executable lines) × 100
  - Branch coverage: (taken branches / total branch points) × 100
  - Per-file and overall
- Identify uncovered lines/branches (in plan but not in hit data)
- **HTML reporter** (Jinja2):
  - Index page: summary table (file → line %, branch %, color-coded)
  - Per-file page: syntax-highlighted source with covered/uncovered lines
  - Color coding: green = covered, red = uncovered, yellow = partial branch
- **LCOV reporter:**
  - Standard LCOV `.info` format for codecov.io / coveralls
  - `SF:`, `DA:` (line data), `BRDA:` (branch data) records
- **Cobertura reporter:**
  - XML format for Jenkins / GitLab CI
  - `<coverage>`, `<package>`, `<class>`, `<line>` elements
- **Terminal reporter:**
  - Rich table: file, lines (found/hit/%), branches (found/hit/%)
  - Overall summary at bottom
- `--min N` threshold check (exit 1 if below)

**Deliverables:**
- `reporter.py` with `generate_report(plan_path, data_path, format, output_dir) -> ReportResult`
- `html_reporter.py`, `lcov_reporter.py`, `cobertura_reporter.py`
- Jinja2 HTML templates
- Unit tests with mock plan + coverage data (full/partial/zero coverage scenarios)

**Success Criteria:**
1. HTML report shows correct coverage percentages
2. Source view highlights covered/uncovered lines correctly
3. LCOV output is valid (passes `lcov --summary` if available)
4. Cobertura XML is valid (passes schema validation)
5. Terminal output is readable and color-coded
6. `--min 80` exits 1 when coverage is 79%, exits 0 when 80%+
7. Zero-coverage files appear in report (not silently omitted)
8. Branch coverage computed correctly (true/false, loop body, match cases)

**Key TDD references:** §3 (Modules: coverage/reporter.py + sub-reporters), §10 (Coverage metrics)

**Results:**
- All 8 success criteria passed.
- `reporter.py` (~510 lines): orchestrator with `read_coverage_json()`,
  `merge_coverage_data()`, `compute_file_summary()`, `compute_summary()`,
  `generate_report(plan, data, output_dir, format, min_threshold)`.
- 4 format reporters: `html_reporter.py` (Jinja2, index + per-file pages),
  `lcov_reporter.py` (TN/SF/DA/BRDA/BRF/BRH/LF/LH records),
  `cobertura_reporter.py` (XML with line-rate/branch-rate),
  `terminal_reporter.py` (Rich table, color-coded: green >=80%, yellow 50-79%,
  red <50%).
- HTML templates: `templates/index.html`, `templates/file.html`.
- 73 unit tests across 5 test files. Coverage: reporter 96%, cobertura 98%,
  html/lcov/terminal 100%.
- `generate_report()` writes report THEN raises `CoverageThresholdError` if
  below threshold — by design (report exists even on failure).
- `read_coverage_json()` normalizes hits keys to strings, validates version==1.
- `merge_coverage_data()` sums hit counts per file_id/line_id across shards.
- Errors use Cause/Fix format. `CoveragePlanError` (exit_code=2),
  `CoverageThresholdError` (exit_code=1).

**Review fixes (commit `e9457ec`):**
1. HIGH — `pyproject.toml`: Added `"gd_tools.coverage" = ["templates/*.html"]`
   to package-data (templates weren't shipping with pip install).
2. HIGH — `reporter.py`: All 12 error messages updated to Cause/Fix format
   per product-guidelines §4.
3. MEDIUM — `html_reporter.py`: Added TODO for deferred source code display
   (spec FR-4.3 partially met — line numbers shown, source not populated).
4. LOW — `cobertura_reporter.py`: Removed dead `or "0"` from `_format_rate()`.
5. LOW — `plan.md`: Checked all Phase 1 sub-task checkboxes.

**Known limitation:** HTML reporter does not display source code content
(line numbers shown but `source` field is empty string). Spec FR-4.3
partially met — deferred to future track.

---

### Track 13: Coverage CLI Integration ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Wire coverage components into the CLI — `test --coverage`, `coverage report/merge/show` |
| **Dependencies** | Track 6 (test runner), Track 9 (plan gen), Track 11 (hooks), Track 12 (reporter) |
| **Modules** | `src/gd_tools/cli.py` (update), `src/gd_tools/coverage/orchestrator.py` (new), `src/gd_tools/coverage/__init__.py` |
| **Effort** | 1-2 days |
| **Risk** | LOW — wiring, no new complex logic |
| **Status** | ✅ **COMPLETED** (2026-07-12) — All 12 acceptance criteria passed |
| **Conductor track** | `coverage_cli_20260711` (archived to `conductor/archive/`) |
| **Commits** | `9317351`..`2266d07` + review fixes `1f69f12` |

**Scope:**
- `gd-tools test --coverage`:
  1. Generate plan (Track 9)
  2. Write plan to `.gd-tools/coverage/plan.json`
  3. Set env vars (`GD_TOOLS_COVERAGE_ACTIVE`, `GD_TOOLS_COVERAGE_PLAN`, `GD_TOOLS_COVERAGE_OUTPUT`)
  4. Run tests with hooks (Track 6 + Track 11)
  5. Read coverage JSON + plan
  6. Generate reports (Track 12)
  7. Apply `--min` threshold
  8. Print terminal summary
- `gd-tools coverage report`:
  - Read existing `.gd-tools/coverage/coverage.json` + `plan.json`
  - Regenerate reports (HTML/LCOV/Cobertura) without re-running tests
- `gd-tools coverage merge`:
  - Read multiple coverage JSON files
  - Merge hit counts (sum per file/line)
  - Write merged JSON to output path
- `gd-tools coverage show`:
  - Read existing coverage data
  - Print terminal summary table
  - Support `--min` for threshold check

**Deliverables:**
- Updated `cli.py` with coverage command wiring
- `coverage/orchestrator.py` with orchestration logic (new module)
- `coverage/__init__.py` re-exporting orchestrator functions
- Unit tests: `test_orchestrator.py` (25+ tests), updated `test_cli.py`, `test_test_runner.py`
- Integration tests: `test_coverage_cli_integration.py` (6 tests, skipif no Godot)
- E2E tests: `test_coverage_e2e.py` (8 tests, skipif no Godot)

**Success Criteria:**
1. `gd-tools test --coverage` runs tests, collects coverage, generates HTML report
2. `--min 80` fails the command when coverage is below 80%
3. `gd-tools coverage report` regenerates reports without re-running tests
4. `gd-tools coverage merge` correctly combines two coverage data files
5. `gd-tools coverage show` prints a readable summary table
6. Coverage data saved to `.gd-tools/coverage/` as expected
7. JUnit XML still produced alongside coverage (both available)
8. Full end-to-end works on Windows, macOS, Linux

**Key TDD references:** §5 (End-to-end flow), §3 (Module: cli.py + coverage/orchestrator.py)

**Track 13 Results (2026-07-12):**
- ✅ All 12 acceptance criteria PASSED
- ✅ 547 unit tests passed; overall coverage maintained at ~98%
- ✅ `ruff check` + `black --check` pass
- **Key implementation:**
  - `orchestrator.py` (275 lines): 4 functions — `run_coverage_test()`,
    `generate_coverage_report()`, `merge_coverage_files()`,
    `show_coverage_summary()`. CLI commands are thin wrappers (NFR-1).
  - Error precedence (NFR-2): `TestFailureError` reported first, then
    `CoverageThresholdError`. `run_coverage_test()` catches test errors,
    still generates reports, then re-raises in correct priority order.
  - `test_runner.py`: `coverage=True` sets `GD_TOOLS_COVERAGE_ACTIVE=1`,
    `GD_TOOLS_COVERAGE_PLAN`, `GD_TOOLS_COVERAGE_OUTPUT` env vars.
    `min_percent` accepted but enforcement deferred to orchestrator
    (no double-checking).
  - `post_run_hook.gd`: Converted flat hits dict to per-file format
    (`{files:[{file_id, hits:{line_id:count}}]}`) to match reporter's
    `CoverageData` model. Added `_hits_to_files()` helper.
  - Deviations documented in plan.md: `--timeout` added, `--min` changed
    `float`→`int`, added `_GDTCoverage` autoload to fixture project.
  - Phase 5 bug fixes: `post_run_hook.gd` format mismatch, missing
    `_GDTCoverage` autoload, `pre_run_hook` `else:` injection workaround.
- **Review fixes (commit `1f69f12`):**
  1. MEDIUM — Fixed docstring format name mismatch: `"terminal"` → `"text"`
     in `orchestrator.py` and `reporter.py` docstrings
  2. MEDIUM — `merge_coverage_files()` now accepts optional `config` param;
     default output path respects `config.coverage.output_dir` instead of
     hardcoded `Path.cwd()`
  3. LOW — Added `write_coverage_json()` to `reporter.py`;
     `merge_coverage_files()` uses it instead of manual JSON dict construction
  4. LOW — Renamed `format` → `report_format` parameter in
     `generate_coverage_report()` (shadows builtin)
  5. LOW — `CoverageThresholdError` message in `show_coverage_summary()`
     updated to Cause/Fix format per product-guidelines §4

---

### Track 14: Test Suite Implementation ✅ COMPLETED

| Field | Value |
|-------|-------|
| **Phase** | 4 — Polish |
| **Goal** | Implement the test suite described in TESTING_STRATEGY.md |
| **Dependencies** | All MVP1 tracks (4-8) for unit tests, all MVP2 tracks (9-13) for coverage tests |
| **Modules** | `tests/` (all test files) |
| **Effort** | Ongoing (parallel to development, formalized here) |
| **Risk** | LOW |
| **Status** | ✅ **COMPLETED** (2026-07-12) — All 5 success criteria passed |
| **Conductor track** | `test_suite_20260712` (archived to `conductor/archive/`) |
| **Commits** | `ef95a1d`..`2f666a2` (44 commits, 31 files, 1055 insertions) + review fix `9851f1a` |

**Scope:**
- Implement unit tests for all Python modules per TESTING_STRATEGY §3
- Implement integration tests per TESTING_STRATEGY §4
- Implement E2E tests per TESTING_STRATEGY §5
- Create GDScript fixtures per TESTING_STRATEGY §7
- Create mock coverage data per TESTING_STRATEGY §8
- Create sample integration project per TESTING_STRATEGY §9
- Achieve 80% line coverage / 70% branch coverage on gd-tools itself

**Deliverables:**
- Full `tests/` directory per TESTING_STRATEGY structure
- `pytest` runs all tests green
- `pytest --cov=gd_tools` shows ≥80% line coverage

**Success Criteria:**
1. All unit tests pass (<5s)
2. All integration tests pass (<60s)
3. All E2E tests pass (<120s)
4. `pytest --cov=gd_tools --cov-branch --cov-fail-under=80` passes
5. No flaky tests (run 10×, all pass)

**Key reference:** [TESTING_STRATEGY.md](./TESTING_STRATEGY.md) — full specification

**Track 14 Results (2026-07-12):**
- ✅ All 5 success criteria PASSED
- ✅ 630 tests total: 572 unit tests pass (9.94s), 50 integration tests
  (skip without Godot), 8 E2E tests (skip without Godot)
- ✅ Coverage: 99.49% line, 98% branch (exceeds 80%/70% gates)
- ✅ ruff check + black --check pass
- ✅ `.env.example` created, `.env` in `.gitignore`
- **Key implementation:**
  - Root `conftest.py` with `find_godot_binary()` helper (checks
    `GODOT_BIN` env var + `shutil.which("godot")` + `shutil.which("godot4")`)
  - `.env` loading via `python-dotenv` for local dev convenience
  - `tests/unit/conftest.py` with `mock_godot_on_path` fixture (context
    manager factory for `shutil.which` mocking)
  - `tests/integration/conftest.py` and `tests/e2e/conftest.py` with
    `godot_bin` and `sample_project_path` fixtures
  - `pytest.ini` config in `pyproject.toml`: `--strict-markers`,
    `--strict-config`, coverage with `--cov=gd_tools`,
    `--cov-branch`, `--cov-fail-under=80`
  - E2E test (`test_full_workflow.py`) uses `skip_if_no_godot` marker
    with `find_godot_binary()` for consistent Godot detection
- **Review fixes applied (commit `9851f1a`):**
  1. Fixed broken `mock_godot_on_path` fixture — removed incorrect
     `@contextmanager` decorator stacked over `@pytest.fixture`
  2. Fixed import ordering in 9 test files — `import pytest` moved to
     third-party group (before `from gd_tools...`) per Google Python
     Style Guide §2
  3. Fixed Godot detection inconsistency in E2E test —
     `skip_if_no_godot` now uses `find_godot_binary()` from root
     conftest instead of ad-hoc `shutil.which("godot")` check

---

### Track 15: CI/CD Pipeline ✅

> **Status: ✅ Complete** (2026-07-12). See `.github/workflows/ci.yml` and
> `.github/workflows/release.yml` for the implementation.

| Field | Value |
|-------|-------|
| **Phase** | 4 — Polish |
| **Goal** | Set up GitHub Actions CI/CD with staged gating |
| **Dependencies** | Track 14 (test suite must exist) |
| **Modules** | `.github/workflows/ci.yml` |
| **Effort** | 1 day |
| **Risk** | LOW |

**Scope:**
- GitHub Actions workflow per TESTING_STRATEGY §11:
  - **Stage 1 (fast):** lint (ruff), format check (black --check), unit tests (<5s)
  - **Stage 2 (medium):** integration tests (<60s, depends on Stage 1)
  - **Stage 3 (slow):** E2E tests with Godot (<120s, depends on Stage 2)
- OS matrix: Ubuntu (primary), Windows (secondary), macOS (if budget allows)
- Python matrix: 3.10, 3.11, 3.12
- Godot installation in CI (download binary)
- Coverage upload to codecov.io
- JUnit XML test results upload to GitHub Actions

**Deliverables:**
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml` (on tag push → PyPI publish)

**Success Criteria:**
1. PR triggers CI pipeline
2. All 3 stages run in order with correct dependencies
3. Failing stage blocks merge (branch protection)
4. Coverage report uploaded to codecov.io
5. Tag push triggers PyPI publish
6. Pipeline completes in <10 minutes total

**Implementation Notes:**
- CI workflow (`.github/workflows/ci.yml`) implements 3-stage gating:
  `lint-format-unit` → `integration` → `e2e`, plus a cross-platform
  matrix (Ubuntu + Windows, Python 3.10/3.11/3.12).
- Release skeleton (`.github/workflows/release.yml`) triggers on tag
  push (`v*`), builds package, uploads to TestPyPI (production PyPI
  deferred to Track 17).
- Godot 4.6.1 installed in CI for integration and E2E stages.
- Coverage uploaded to codecov.io via `codecov-action@v4`.
- JUnit XML results uploaded as GitHub Actions artifacts.
- Secrets documented in `.github/SECRETS.md`.
- Review fixes applied: `permissions: contents: read` added to both
  workflows for least-privilege security.

---

### Track 16: Documentation

| Field | Value |
|-------|-------|
| **Phase** | 4 — Polish |
| **Goal** | Write user-facing documentation: README, user guide, contributing guide |
| **Dependencies** | All tracks (document the final product) |
| **Modules** | `README.md`, `docs/USAGE.md`, `docs/CONTRIBUTING.md` |
| **Effort** | 1-2 days |
| **Risk** | LOW |

**Scope:**
- **README.md:**
  - What is gd-tools (elevator pitch)
  - Quick start (install, init, first run)
  - Feature overview with examples
  - Requirements (Python 3.10+, Godot 4.5+)
  - Installation (`pip install gd-tools`)
  - Links to detailed docs
- **USAGE.md:**
  - Full command reference
  - Configuration guide (`gd-tools.toml` all sections)
  - Coverage guide (how to read reports, set thresholds)
  - CI/CD integration guide (GitHub Actions, GitLab CI examples)
  - Troubleshooting / FAQ
- **CONTRIBUTING.md:**
  - Development setup
  - Code style (ruff, black)
  - Testing requirements
  - PR process
  - Architecture overview (link to TDD)

**Deliverables:**
- `README.md` (complete, replaces placeholder from Track 1)
- `docs/USAGE.md`
- `docs/CONTRIBUTING.md`

**Success Criteria:**
1. New user can install and use gd-tools following README alone
2. All commands documented with examples
3. Configuration options fully documented
4. CI/CD examples work when copied
5. Contributor can set up dev environment following CONTRIBUTING.md

---

### Track 17: PyPI Release

| Field | Value |
|-------|-------|
| **Phase** | 4 — Polish |
| **Goal** | Package and publish gd-tools to PyPI |
| **Dependencies** | Track 14 (tests), Track 15 (CI/CD), Track 16 (docs) |
| **Modules** | `pyproject.toml` (finalize), release workflow |
| **Effort** | 0.5 day |
| **Risk** | LOW |

**Scope:**
- Finalize `pyproject.toml` (metadata, classifiers, long_description)
- Verify package builds: `python -m build`
- Verify `twine check` passes
- Test on TestPyPI first
- Publish to PyPI
- Tag release in git
- Create GitHub release with release notes

**Deliverables:**
- Built sdist + wheel
- Published PyPI package
- Git tag `v0.1.0`
- GitHub release

**Success Criteria:**
1. `pip install gd-tools` works on clean environment
2. `gd-tools --version` prints `0.1.0`
3. All commands work after pip install (not just editable install)
4. Package metadata correct on PyPI
5. README renders correctly on PyPI

---

## 5. Risk Summary

| Risk | Track(s) | Mitigation |
|------|----------|------------|
| **Runtime instrumentation doesn't work** (Script.reload fails, tracker doesn't fire) | 0, 11 | Spike first. Fallback: Architecture B (fork jamie-pate) or Architecture A (pure Python) |
| **Lark AST traversal misses edge cases** (complex GDScript patterns) | 9 | Comprehensive fixtures (6 test files). Fallback: iterative improvement, report as "partial coverage" |
| **Instrumented code behaves differently** (side effects from tracker calls) | 0, 11 | Tracker is pure (no side effects, just counter). Spike verifies this. |
| **GUT CLI changes between versions** | 6, 7 | Pin GUT version per Godot version. Version mapping table in init. |
| **Platform-specific Godot path issues** | 3 | Test on all 3 OSes in CI. Comprehensive common-locations list. |
| **project.godot editing corrupts file** | 7 | Use TOML/INI parser, not regex. Idempotent operations. Backup before modify. |
| **Performance: large projects slow** | 9, 11 | Benchmark on 100+ file project. Optimize plan generation (Lark is fast). Instrumentation is O(lines). |

---

## 6. Conductor Track Creation Guide

To create a track using the Conductor methodology:

```
conductor_new_track
  → Provide the track ID and name from this document
  → Copy the "Scope" section as the spec basis
  → Use "Success Criteria" as verification gates
  → Reference related TDD/PRD sections for implementation details
```

### Track Creation Order (Recommended)

1. **Track 0 (Spike)** — Create and execute FIRST. The result determines whether subsequent coverage tracks use Architecture C or fall back to B/A.

2. **Tracks 1-3 (Foundation)** — Can be created in sequence. These are prerequisites for all MVP1 work.

3. **Tracks 4-8 (MVP1)** — Can be created in any order after foundation, but 4+5 (lint/format) are quickest wins. Track 6 (test runner) and Track 7 (init) are the most complex.

4. **Tracks 9-13 (MVP2)** — Must follow spike result. Create Track 9 (plan gen) and Track 10 (tracker) first (parallel). Track 11 (hooks) is the riskiest — create after 9+10. Track 12 (reporter) can start once 9's plan format is stable. Track 13 (CLI) wires everything up last.

5. **Tracks 14-17 (Polish)** — Create after MVP2 is functionally complete. Track 14 (tests) runs parallel to all development. Tracks 15-17 are sequential at the end.

### Spec/Plan Template Per Track

Each Conductor track should produce:
- **`spec.md`** — Track scope, goals, success criteria (from this document's track section)
- **`plan.md`** — Implementation plan: file-by-file changes, function signatures (from TDD), task breakdown, testing approach
- **`metadata.json`** — Track metadata (status, assignee, dates)

---

## 7. Success Metrics (Project-Level)

| Metric | Target | Measured By |
|--------|--------|-------------|
| Spike pass rate | 100% success criteria | Manual verification |
| MVP1 command coverage | All 5 commands work | E2E tests |
| MVP2 coverage accuracy | ±1 line vs. manual audit | Fixture-based tests |
| Test coverage (gd-tools itself) | ≥80% line, ≥70% branch | pytest-cov |
| CI pipeline runtime | <10 min total | GitHub Actions |
| Install-to-first-run time | <2 min | `gd-tools init` + first `gd-tools lint` |
| PyPI package size | <500KB | `twine check` |
