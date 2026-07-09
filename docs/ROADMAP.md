# ROADMAP: gd-tools Development Plan

**Version:** 0.1.0 (draft)
**Date:** 2026-07-09
**Status:** Phase 0 Complete — Spike Validated, Architecture C Confirmed
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
  Track 14: Test Suite                    │  ~ongoing + 3 days
  Track 15: CI/CD Pipeline                │  Risk: LOW
  Track 16: Documentation                 │
  Track 17: PyPI Release                  │
──────────────────────────────────────────┘

Total estimated effort: ~25-30 days
```

### Milestones

| Milestone | Phase Complete | What You Can Do |
|-----------|---------------|-----------------|
| **M0: Spike Pass** ✅ | Phase 0 | ✅ ACHIEVED — Runtime GDScript instrumentation validated (2026-07-09). All 6 success criteria passed. Architecture C confirmed. |
| **M1: Foundation** | Phase 1 | Config loads, Godot binary detected, CLI skeleton runs |
| **M2: First Usable** | Phase 2 | `gd-tools lint`, `format`, `test`, `init`, `doctor` all work |
| **M3: Coverage Alpha** | Phase 3 | `gd-tools test --coverage` produces line+branch reports |
| **M4: v1.0 Release** | Phase 4 | PyPI package, CI/CD, docs, test suite at 80% coverage |

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

### Track 1: Project Scaffolding

| Field | Value |
|-------|-------|
| **Phase** | 1 — Foundation |
| **Goal** | Create the Python package structure, build system, and CLI skeleton |
| **Dependencies** | None |
| **Modules** | `pyproject.toml`, `src/gd_tools/__init__.py`, `src/gd_tools/__main__.py`, `src/gd_tools/cli.py` (skeleton) |
| **Effort** | 0.5 day |
| **Risk** | LOW |

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
5. Exclude lists merge correctly (config + defaults)

**Key TDD references:** §3 (Module: config.py), §7 (Data Contracts)

---

### Track 3: Godot Binary Detection

| Field | Value |
|-------|-------|
| **Phase** | 1 — Foundation |
| **Goal** | Implement the 5-level Godot binary resolution chain |
| **Dependencies** | Track 2 (uses config for `[godot].binary`) |
| **Modules** | `src/gd_tools/godot.py` |
| **Effort** | 1 day |
| **Risk** | MEDIUM — platform-specific edge cases |

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

---

### Track 4: Lint Wrapper

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Wrap `gdlint` with config-driven excludes and clean output |
| **Dependencies** | Track 2 (config for exclude list) |
| **Modules** | `src/gd_tools/lint_runner.py` |
| **Effort** | 1 day |
| **Risk** | LOW |

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

---

### Track 5: Format Wrapper

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Wrap `gdformat` with `--check` and `--diff` modes |
| **Dependencies** | Track 2 (config for exclude list) |
| **Modules** | `src/gd_tools/format_runner.py` |
| **Effort** | 1 day |
| **Risk** | LOW |

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

---

### Track 6: Test Runner (GUT Wrapper)

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Orchestrate GUT via Godot CLI, parse JUnit XML, return structured results |
| **Dependencies** | Track 2 (config), Track 3 (Godot binary) |
| **Modules** | `src/gd_tools/test_runner.py` |
| **Effort** | 2 days |
| **Risk** | MEDIUM — GUT CLI interaction, path handling |

**Scope:**
- Build GUT command line: `godot -s addons/gut/gut_cmdln.gd -d --path "$PWD" -gexit`
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

---

### Track 7: Init Command

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Bootstrap a Godot project: install GUT, deploy coverage addon, generate configs |
| **Dependencies** | Track 2 (config), Track 3 (Godot version detection) |
| **Modules** | `src/gd_tools/init.py` |
| **Effort** | 2-3 days |
| **Risk** | MEDIUM — `project.godot` editing, zip download/extract, idempotency |

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

---

### Track 8: Doctor Command

| Field | Value |
|-------|-------|
| **Phase** | 2 — MVP1 |
| **Goal** | Run diagnostic checks and report environment health |
| **Dependencies** | Track 2 (config), Track 3 (Godot detection) |
| **Modules** | `src/gd_tools/doctor.py` |
| **Effort** | 1 day |
| **Risk** | LOW |

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
- Output: rich table with ✓/✗ per check + actionable fix suggestions
- Exit code: 0 = all pass, 1 = warnings, 2 = critical failures

**Deliverables:**
- `doctor.py` with `run_doctor() -> DoctorResult`
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

---

### Track 9: Coverage Plan Generator

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Parse GDScript with gdtoolkit/Lark, identify executable lines + branch points, generate instrumentation plan JSON |
| **Dependencies** | Track 0 (spike validated approach), Track 2 (config for excludes) |
| **Modules** | `src/gd_tools/coverage/plan_generator.py` |
| **Effort** | 3-4 days |
| **Risk** | MEDIUM-HIGH — Lark AST traversal, statement classification |

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

---

### Track 10: Coverage Tracker Addon (GDScript)

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Implement the GDScript autoload singleton that tracks hit counts |
| **Dependencies** | Track 0 (spike validated approach) |
| **Modules** | `src/gd_tools/addons/gd-tools-coverage/tracker.gd` (bundled) |
| **Effort** | 1 day |
| **Risk** | LOW |

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
- `tracker.gd` (final version, replaces placeholder from Track 7)
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

**Key TDD references:** §6 (GDScript Addon: tracker.gd)

---

### Track 11: Coverage Hooks (Instrumentation Engine)

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Implement GUT pre-run and post-run hooks that instrument GDScript at runtime and collect coverage data |
| **Dependencies** | Track 0 (spike), Track 9 (plan format), Track 10 (tracker) |
| **Modules** | `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`, `post_run_hook.gd` |
| **Effort** | 3-4 days |
| **Risk** | HIGH — core innovation, source injection + reload |

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

---

### Track 12: Coverage Reporter

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Read coverage data + plan, compute metrics, generate reports (HTML, LCOV, Cobertura, terminal) |
| **Dependencies** | Track 9 (plan format for cross-reference) |
| **Modules** | `src/gd_tools/coverage/reporter.py`, `html_reporter.py`, `lcov_reporter.py`, `cobertura_reporter.py` |
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

---

### Track 13: Coverage CLI Integration

| Field | Value |
|-------|-------|
| **Phase** | 3 — MVP2 |
| **Goal** | Wire coverage components into the CLI — `test --coverage`, `coverage report/merge/show` |
| **Dependencies** | Track 6 (test runner), Track 9 (plan gen), Track 11 (hooks), Track 12 (reporter) |
| **Modules** | `src/gd_tools/cli.py` (update), `src/gd_tools/coverage/__init__.py` |
| **Effort** | 1-2 days |
| **Risk** | LOW — wiring, no new complex logic |

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
- `coverage/__init__.py` with orchestration logic
- E2E test: full `gd-tools test --coverage` on sample project

**Success Criteria:**
1. `gd-tools test --coverage` runs tests, collects coverage, generates HTML report
2. `--min 80` fails the command when coverage is below 80%
3. `gd-tools coverage report` regenerates reports without re-running tests
4. `gd-tools coverage merge` correctly combines two coverage data files
5. `gd-tools coverage show` prints a readable summary table
6. Coverage data saved to `.gd-tools/coverage/` as expected
7. JUnit XML still produced alongside coverage (both available)
8. Full end-to-end works on Windows, macOS, Linux

**Key TDD references:** §5 (End-to-end flow), §3 (Module: cli.py)

---

### Track 14: Test Suite Implementation

| Field | Value |
|-------|-------|
| **Phase** | 4 — Polish |
| **Goal** | Implement the test suite described in TESTING_STRATEGY.md |
| **Dependencies** | All MVP1 tracks (4-8) for unit tests, all MVP2 tracks (9-13) for coverage tests |
| **Modules** | `tests/` (all test files) |
| **Effort** | Ongoing (parallel to development, formalized here) |
| **Risk** | LOW |

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

---

### Track 15: CI/CD Pipeline

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
