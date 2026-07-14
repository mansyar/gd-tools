# ROADMAP: gd-tools Development Plan

**Version:** 0.2.0 (draft)
**Date:** 2026-07-14
**Status:** Post-v1.0 -- Planning v0.4.0+ improvements
**Related docs:** [PRD.md](./PRD.md), [ROADMAP_v1.md](./ROADMAP_v1.md) (archived v1 roadmap, Tracks 0-22), [AUDIT_REPORT.md](./AUDIT_REPORT.md), [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 1. Overview

This document defines the post-v1.0 development roadmap for `gd-tools`,
organized as a sequence of **Conductor Tracks**. Each track is a
self-contained unit of work with a clear goal, bounded scope, verifiable
success criteria, and explicit dependencies on other tracks.

The v1.0 roadmap (Tracks 0-22) delivered the core product: CLI commands
(init, doctor, test, lint, format, coverage), the hybrid coverage system,
CI/CD pipeline, documentation, and PyPI release. See
[ROADMAP_v1.md](./ROADMAP_v1.md) for the complete v1 history.

This roadmap focuses on **incremental improvements** that increase the
tool's day-to-day value, close UX gaps, and expand the feature set into
new differentiating territory. The phasing is designed so that:

- **Quick wins ship first** -- low-effort, high-impact improvements that
  users feel immediately.
- **Strategic features follow** -- medium-effort features that integrate
  gd-tools deeper into existing workflows (pre-commit, CI annotations).
- **Differentiators come last** -- high-effort features that no other
  GDScript tool offers (coverage diff, playtesting coverage, editor plugin).
- **Robustness work runs throughout** -- technical debt and edge-case
  hardening that can be picked up between feature tracks.

---

## 2. Phasing Strategy

```
Phase 6: Quick Wins                        ──┐
  Track 23: Stale Addon Detection             │  ~2-3 days
  Track 24: Version Command                    │  Risk: LOW
  Track 25: Config Show/Validate              │
  Track 26: Shell Completion                   │
  Track 27: Verbose/Quiet Flags               │
  ──────────────────────────────────────────────┘

Phase 7: Strategic Features                ──┐
  Track 28: Watch Mode                        │  ~5-7 days
  Track 29: Pre-commit Hooks                  │  Risk: LOW-MEDIUM
  Track 30: Coverage Exclusion Annotations    │
  Track 31: GitHub Actions Annotations        │
  Track 32: Configurable Version Mapping      │
  ──────────────────────────────────────────────┘

Phase 8: Differentiators                   ──┐
  Track 33: Coverage Diff                     │  ~7-10 days
  Track 34: Coverage During Playtesting       │  Risk: MEDIUM-HIGH
  Track 35: Editor Plugin                     │
  ──────────────────────────────────────────────┘

Phase 9: Robustness & Quality              ──┐
  Track 36: macOS CI Matrix                   │  ~2-3 days
  Track 37: Plan Generator Caching            │  Risk: LOW-MEDIUM
  Track 38: GDScript AST Edge Cases           │
  Track 39: Clean Command                     │
  ──────────────────────────────────────────────┘

Total estimated effort: ~17-23 days
```

### Milestones

| Milestone | Phase Complete | What You Can Do |
|-----------|---------------|-----------------|
| **M5: Quick Wins** | Phase 6 | Users get version-aware addon warnings, `gd-tools version`, `gd-tools config show/validate`, shell completion, and `--verbose`/`--quiet` flags. |
| **M6: Workflow Integration** | Phase 7 | Watch mode for live test re-runs, pre-commit hooks, coverage exclusion annotations, GitHub Actions annotations, data-driven Godot/GUT version mapping. |
| **M7: Differentiators** | Phase 8 | Coverage diff between branches, coverage during manual playtesting, Godot editor plugin with inline coverage. |
| **M8: Hardened** | Phase 9 | macOS CI, plan caching for large projects, comprehensive AST edge-case coverage, `gd-tools clean` command. |

---

## 3. Dependency Graph

```
Phase 6: Quick Wins (all independent, can be parallelized)

  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Track 23: │  │Track 24: │  │Track 25: │  │Track 26: │  │Track 27: │
  │Stale     │  │Version   │  │Config    │  │Shell     │  │Verbose/  │
  │Addon     │  │Cmd       │  │Show/Val  │  │Completion│  │Quiet     │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘

Phase 7: Strategic Features

  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │Track 28: │     │Track 29: │     │Track 30: │
  │Watch Mode│     │Pre-commit│     │Coverage  │
  │          │     │Hooks     │     │Exclusions│
  └──────────┘     └──────────┘     └────┬─────┘
                                        │
                   ┌──────────┐         │ (exclusion
                   │Track 31: │         │  annotations
                   │GH Actions│         │  consumed by
                   │Annotate  │         │  plan gen)
                   └──────────┘         │
                                        ▼
                                  ┌──────────┐
                                  │Track 32: │
                                  │Version   │
                                  │Mapping   │
                                  └──────────┘

Phase 8: Differentiators

  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │Track 33: │     │Track 34: │     │Track 35: │
  │Cov Diff │     │Playtest  │     │Editor    │
  │          │     │Coverage  │     │Plugin    │
  └──────────┘     └──────────┘     └──────────┘

Phase 9: Robustness (all independent)

  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Track 36: │  │Track 37: │  │Track 38: │  │Track 39: │
  │macOS CI  │  │Plan      │  │AST Edge  │  │Clean     │
  │          │  │Caching   │  │Cases     │  │Cmd       │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Parallelization Opportunities

| Tracks | Can Run In Parallel? | Why |
|--------|---------------------|-----|
| 23-27 (Quick Wins) | Yes | All independent, touch different modules |
| 28 (Watch) + 29 (Pre-commit) | Yes | Different subsystems, no shared code |
| 30 (Exclusions) + 31 (GH Annotations) | Yes | Different modules (plan_generator vs reporter) |
| 36-39 (Robustness) | Yes | All independent, different concerns |

---

## 4. Track Specifications

### Track 23: Stale Addon Detection

| Field | Value |
|-------|-------|
| **Phase** | 6 -- Quick Wins |
| **Goal** | Detect when deployed coverage addon files are older than the installed gd-tools package version, and warn the user to re-run `gd-tools init` |
| **Dependencies** | Track 7 (init command), Track 18 (versioning) |
| **Modules** | `src/gd_tools/init.py`, `src/gd_tools/addons/gd-tools-coverage/` (version file), `src/gd_tools/cli.py` |
| **Effort** | 0.5 day |
| **Risk** | LOW |
| **Status** | Delivered — archived `stale_addon_detection_20260714` |

**Problem:**

When a user upgrades `gd-tools-cli` via pip, the deployed GDScript addons
(`coverage.gd`, `pre_run_hook.gd`, `post_run_hook.gd`) in their project
are **not** updated. They must remember to re-run `gd-tools init`. This
is a silent version-skew bug -- the Python package and GDScript addons
can drift, causing subtle coverage instrumentation failures.

**Scope:**
- Write a `_version.txt` file (or `plugin.cfg` with version field) to
  `addons/gd-tools-coverage/` during `gd-tools init`, containing the
  gd-tools package version
- On any CLI command invocation, check if the addon version file exists
  and compare its version against the installed package version
- If addon version < package version, print a warning to stderr:
  ```
  WARNING: Coverage addon is outdated (v0.2.0 deployed, v0.3.0 available).
  Run `gd-tools init` to update.
  ```
- If addon version file is missing, treat as stale (warn to run init)
- Warning is non-blocking (command still executes)
- `GD_TOOLS_NO_UPDATE_CHECK=1` also suppresses this check (reuse existing
  env var pattern)

**Deliverables:**
- Version file written during `init`
- Version comparison logic in `cli.py` (or a new `addon_check.py` module)
- Unit tests for version comparison, missing file, equal versions

**Success Criteria:**
1. `gd-tools init` writes a version file to `addons/gd-tools-coverage/`
2. When addon version < package version, a warning is printed to stderr
3. When versions match, no warning is printed
4. When version file is missing, a warning is printed
5. Warning does not block command execution (exit code unchanged)
6. `GD_TOOLS_NO_UPDATE_CHECK=1` suppresses the check

---

### Track 24: Version Command

| Field | Value |
|-------|-------|
| **Phase** | 6 -- Quick Wins |
| **Goal** | Add `gd-tools version` command that prints all component versions in a table |
| **Dependencies** | Track 1 (CLI skeleton), Track 3 (Godot detection) |
| **Modules** | `src/gd_tools/cli.py`, `src/gd_tools/version.py` |
| **Effort** | 0.5 day |
| **Risk** | LOW |
| **Status** | Done |

**Problem:**

`--version` only shows the gd-tools package version. Users troubleshooting
environment issues have no single command to see all component versions
(Godot, GUT, gdtoolkit, Python). This information is critical for bug
reports and environment diagnostics.

**Scope:**
- Add `gd-tools version` command (not a flag -- a subcommand)
- Detect and print versions in a Rich table:
  - `gd-tools` -- package version (`__version__`)
  - `Godot` -- detected Godot version (via `find_godot()`, if available)
  - `GUT` -- installed GUT version (read from `addons/gut/plugin.cfg`)
  - `gdtoolkit` -- installed gdtoolkit version (via `importlib.metadata`)
  - `Python` -- `sys.version`
- If a component is not found, show "not installed" or "not detected"
- Exit code 0 always (informational command)
- `--json` flag for machine-readable output

**Deliverables:**
- `version` command in `cli.py`
- Unit tests with mocked version detection

**Success Criteria:**
1. `gd-tools version` prints a table with all 5 component versions
2. Missing components show "not installed" / "not detected"
3. `--json` flag produces valid JSON output
4. Exit code is always 0
5. Command completes in <2 seconds (no slow network calls)

---

### Track 24.5: Autoload-Based Coverage Instrumentation (Urgent Bug Fix)

| Field | Value |
|-------|-------|
| **Phase** | Hotfix -- Urgent Bug Fix |
| **Goal** | Move coverage instrumentation from GUT's pre-run hook to `_GDTCoverage._ready()` (first autoload), eliminating `ERR_ALREADY_IN_USE` for scripts instantiated by autoloads. Tracker activation stays in the pre-run hook to preserve current coverage semantics (test execution only, not autoload init). |
| **Dependencies** | Track 7 (init), Track 9 (plan generator), Track 10 (coverage tracker), Track 11 (hooks) |
| **Modules** | `src/gd_tools/addons/gd-tools-coverage/coverage.gd`, `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`, `src/gd_tools/init.py`, `src/gd_tools/coverage/plan_generator.py`, `src/gd_tools/test_runner.py` |
| **Effort** | 1-2 days |
| **Risk** | MEDIUM -- Godot `reload()` in-place behavior needs empirical verification |
| **Status** | Planned |

**Problem:**

When an autoload's `_ready()` creates instances of other scripts (e.g.,
`GameState._ready()` calls `_init_new_game()` which loads `ChimeraData`
instances from `.tres` files), the GUT pre-run hook cannot instrument
those scripts via `load()` + `reload()`. `reload()` fails with
`ERR_ALREADY_IN_USE` because active instances already exist. The
instrumented file is skipped, showing 0% coverage despite being exercised
by tests. This dropped a real project's coverage from 93.8% to 75.3%.

The current workaround requires users to pollute production code with
env-var checks:

```gdscript
func _ready() -> void:
    if OS.get_environment("GD_TOOLS_COVERAGE_ACTIVE") in ["1", "true"]:
        return  # ← user shouldn't have to do this
    if not SaveManager.load_game():
        _init_new_game()
```

**Root Cause:**

Instrumentation happens too late. The pre-run hook runs AFTER all
autoloads have initialized. By that point, autoload-created instances
exist, and `reload()` refuses to recompile scripts with active instances.

**Solution: Autoload-Based Instrumentation with Deferred Activation**

Move instrumentation to `_GDTCoverage._ready()`, which runs as the
**first** autoload (before any other autoload creates instances). At
that point, no instances exist, so `reload()` succeeds.

Instrumentation and tracker activation are **separated**:
- **Instrumentation** happens in `_GDTCoverage._ready()` (first autoload)
- **Activation** happens in the GUT pre-run hook (after autoloads, before
  tests) via `set_active(true)`

This preserves the current coverage semantics: only test execution is
recorded, not autoload initialization.

**Why this works (Godot internals):**

- `class_name` registration maps a class name to a **file path** (not a
  Script object). Lookups call `load(path)` which returns the cached
  `GDScript` resource.
- `preload()` calls `ResourceLoader::load()` at compile time, returning
  a `Ref<GDScript>` pointing to the **same cached resource object**.
- `reload()` recompiles the `GDScript` resource **in-place** (same
  object identity, new bytecode). It does NOT create a new object.
- Therefore, ALL references -- `class_name`, `load()`, and `preload()`
  -- point to the same `GDScript` object, which `reload()` updates
  in-place. All references see the instrumented code.

Sources: Godot source code (`gdscript.h`, `script_language.h`), GitHub
issues #107869 (reload in-place behavior), #98985 (class_name
registration via file path), #55615 (preload returns cached resource).

**Scope:**

1. **`register_coverage_autoload()` in `init.py`:** Change from APPEND
   to PREPEND. `_GDTCoverage` must be the first entry in `[autoload]`
   so its `_ready()` runs before any other autoload.

2. **`coverage.gd`:** Move instrumentation logic from `pre_run_hook.gd`
   into `_GDTCoverage._ready()`. Check `GD_TOOLS_COVERAGE_PLAN` env var
   (not `GD_TOOLS_COVERAGE_ACTIVE`) to determine if this is a coverage
   run. If plan path is set, instrument all files: `load(path)` → modify
   `source_code` → `reload()`. Leave `_active = false` -- the pre-run
   hook will activate the tracker later. If `reload()` returns
   `ERR_ALREADY_IN_USE`, skip with a warning (shouldn't happen if
   `_GDTCoverage` is first, but defensive).

3. **`pre_run_hook.gd`:** Remove instrumentation logic (moved to
   `coverage.gd`). Simplify to a single line: `_GDTCoverage.set_active(true)`.
   The tracker activates here, after all autoloads have initialized, so
   only test execution is recorded.

4. **`plan_generator.py`:** Remove the autoload exclusion (lines
   395-405). Autoloads can now be instrumented because `_GDTCoverage`
   runs first and instruments before instances are created.

5. **`test_runner.py`:** Keep `-gpre_run_script` in `build_gut_args()`
   (still needed for `set_active(true)`). Stop setting
   `GD_TOOLS_COVERAGE_ACTIVE` env var -- the pre-run hook handles
   activation. Keep `GD_TOOLS_COVERAGE_PLAN` and `GD_TOOLS_COVERAGE_OUTPUT`.

6. **Empirical verification:** Before implementation, verify that
   `reload()` updates the `GDScript` resource in-place (same object
   identity). Quick test:
   ```gdscript
   var script = load("res://some_script.gd")
   var id_before = script.get_instance_id()
   script.source_code = script.source_code  # no-op modification
   script.reload()
   var id_after = script.get_instance_id()
   print("Same object: ", id_before == id_after)
   ```
   If `false`, the approach needs reconsideration.

**Deliverables:**
- Updated `coverage.gd` with instrumentation logic in `_ready()` (reads
  `GD_TOOLS_COVERAGE_PLAN`, instruments scripts, leaves `_active = false`)
- Updated `init.py` with prepend logic for autoload registration
- Updated `plan_generator.py` with autoload exclusion removed
- Updated `test_runner.py` to stop setting `GD_TOOLS_COVERAGE_ACTIVE`
- Simplified `pre_run_hook.gd` (single line: `set_active(true)`)
- Unit tests for prepend logic, instrumentation in `_ready()`, activation
- Integration test verifying autoload scripts get coverage
- E2E test on chimera-gladiator-manager project (or equivalent fixture)

**Success Criteria:**
1. `_GDTCoverage` is registered as the first autoload in `project.godot`
2. Autoload scripts (e.g., `game_state.gd`) appear in the coverage plan
3. Scripts instantiated by autoloads (e.g., `chimera_data.gd`) show
   non-zero coverage when exercised by tests
4. `reload()` never returns `ERR_ALREADY_IN_USE` during coverage runs
5. Users no longer need env-var checks in their `_ready()` methods
6. Autoload initialization code is NOT recorded as coverage (tracker
   activates via pre-run hook, after autoloads init)
7. Existing coverage results for non-autoload scripts are unchanged
8. All existing tests pass
9. The `reload()` in-place behavior is empirically verified

**Risks:**
- **`reload()` creates new object (not in-place):** If `reload()` creates
  a new `GDScript` object instead of updating in-place, `class_name` and
  `preload()` references would point to the old (un-instrumented) object.
  Mitigation: empirical test (step 6 above). If confirmed, fall back to
  file-based pre-instrumentation (Approach B).
- **`reload()` bug in pre-4.6 Godot (Issue #107869):** If `reload()`
  fails, the `reloading` flag stays `true`, permanently breaking the
  script. Mitigation: since `_GDTCoverage` is first, no instances exist,
  `reload()` should never fail. Add defensive error handling.
- **Autoload ordering dependency:** Users who manually reorder autoloads
  in `project.godot` could break instrumentation. Mitigation:
  `register_coverage_autoload()` should detect if `_GDTCoverage` is not
  first and move it.
- **Env var change for existing users:** `GD_TOOLS_COVERAGE_ACTIVE` is no
  longer set by `test_runner.py`. Users who relied on this env var in
  their production code (the workaround this track eliminates) will see
  it return empty. This is expected -- the workaround is no longer
  needed. Document in release notes.

---

### Track 25: Config Show/Validate

| Field | Value |
|-------|-------|
| **Phase** | 6 -- Quick Wins |
| **Goal** | Add `gd-tools config show` and `gd-tools config validate` subcommands |
| **Dependencies** | Track 2 (config system) |
| **Modules** | `src/gd_tools/cli.py`, `src/gd_tools/config.py` |
| **Effort** | 0.5 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

Users must manually open and read `gd-tools.toml` to see what's
configured. There's no way to validate config without running a command
that uses it. Unknown keys are silently rejected by Pydantic's
`extra='forbid'`, but users get no upfront feedback.

**Scope:**
- `gd-tools config show` -- Print the resolved config (including defaults
  applied) as a Rich table or formatted TOML
- `gd-tools config validate` -- Check config validity:
  - Schema validity (Pydantic validation)
  - Warn on unknown keys (already caught by `extra='forbid'`, but provide
    a friendlier message)
  - Warn on invalid paths (e.g., `[test].dirs` pointing to nonexistent
    directories)
  - Warn on deprecated settings (future-proofing)
- Both subcommands exit 0 on success, 1 on validation errors
- `--json` flag on `show` for machine-readable output

**Deliverables:**
- `config` command group in `cli.py` with `show` and `validate` subcommands
- Path validation logic in `config.py`
- Unit tests for show, validate, missing config, invalid config

**Success Criteria:**
1. `gd-tools config show` prints resolved config with defaults applied
2. `gd-tools config validate` exits 0 on valid config, 1 on invalid
3. Invalid paths are detected and reported
4. `--json` flag produces valid JSON output
5. Command works with no config file (shows all defaults)

---

### Track 26: Shell Completion

| Field | Value |
|-------|-------|
| **Phase** | 6 -- Quick Wins |
| **Goal** | Enable shell completion for bash, zsh, fish, and PowerShell |
| **Dependencies** | Track 1 (CLI skeleton) |
| **Modules** | `src/gd_tools/cli.py`, documentation |
| **Effort** | 0.25 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

Click supports shell completion natively, but gd-tools doesn't document or
expose it. Users on bash/zsh/fish/PowerShell get no tab completion for
commands, flags, or file paths.

**Scope:**
- Add `gd-tools completion [shell]` command that prints the completion
  script for the specified shell (bash, zsh, fish, powershell)
- Alternatively, document the Click built-in environment variable approach
  (`_GD_TOOLS_COMPLETE=bash_source gd-tools`)
- Add a "Shell Completion" section to README and USER_GUIDE with setup
  instructions for each shell
- Test that completion script generation works for all 4 shells

**Deliverables:**
- `completion` command in `cli.py` (or documentation of Click's built-in)
- README and USER_GUIDE sections
- Unit test verifying completion script output

**Success Criteria:**
1. `gd-tools completion bash` prints a valid bash completion script
2. `gd-tools completion zsh` prints a valid zsh completion script
3. `gd-tools completion fish` prints a valid fish completion script
4. `gd-tools completion powershell` prints a valid PowerShell completion script
5. Documentation includes setup instructions for each shell

---

### Track 27: Verbose/Quiet Global Flags

| Field | Value |
|-------|-------|
| **Phase** | 6 -- Quick Wins |
| **Goal** | Add `--verbose` and `--quiet` global flags to control output verbosity |
| **Dependencies** | Track 1 (CLI skeleton) |
| **Modules** | `src/gd_tools/cli.py`, all runner modules |
| **Effort** | 0.5-1 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

Output verbosity isn't controllable. In CI, users may want minimal output.
For debugging, they may want to see the underlying GUT/gdlint/gdformat
commands being run. Currently, there's no way to control this.

**Scope:**
- Add `--verbose` / `-v` global flag (before subcommand):
  - Shows underlying commands being run (e.g., the full `godot --headless
    -s addons/gut/gut_cmdln.gd ...` command)
  - Shows internal state (config file path, plan path, coverage output path)
  - Shows timing information
- Add `--quiet` / `-q` global flag:
  - Suppresses non-essential output (only show results and errors)
  - Still shows test pass/fail summary
  - Still shows lint violations
  - Suppresses update check notification, init summary, doctor details
- Implement a verbosity context (e.g., a `Verbosity` enum or logging level)
  that runners check before printing
- `--verbose` and `--quiet` are mutually exclusive

**Deliverables:**
- Global flags in `cli.py`
- Verbosity context passed to runner modules
- Updated runner modules to respect verbosity
- Unit tests for verbose output, quiet output, mutual exclusion

**Success Criteria:**
1. `gd-tools --verbose test` shows the underlying Godot/GUT command
2. `gd-tools --quiet test` shows only test results summary
3. `--verbose` and `--quiet` together produce an error
4. Default verbosity (no flag) matches current behavior
5. All existing tests still pass

---

### Track 28: Watch Mode

| Field | Value |
|-------|-------|
| **Phase** | 7 -- Strategic Features |
| **Goal** | Add `gd-tools test --watch` that monitors `.gd` files and re-runs affected tests on save |
| **Dependencies** | Track 6 (test runner) |
| **Modules** | `src/gd_tools/cli.py`, `src/gd_tools/watch.py` (new) |
| **Effort** | 2-3 days |
| **Risk** | MEDIUM -- file watching, debouncing, terminal management |
| **Status** | Planned |

**Problem:**

Developers working on GDScript code must manually re-run `gd-tools test`
after every change. This breaks flow and slows the feedback loop.

**Scope:**
- `gd-tools test --watch` enters watch mode:
  - Monitors `.gd` files in the project for changes
  - On file change, re-runs affected tests
  - Clears terminal between runs for a "live test" feel
  - Debounces rapid changes (500ms) to avoid multiple runs
- File-to-test mapping:
  - Convention: `foo.gd` -> `test_foo.gd` or `foo_test.gd`
  - If no matching test file found, re-run all tests
  - `--watch-all` flag: always re-run all tests on any change
- Uses `watchdog` library for cross-platform file system monitoring
- Shows a summary line: "Watching N files. Press Ctrl+C to stop."
- On Ctrl+C, exits cleanly with exit code 0
- Works with `--coverage` flag (re-generates coverage each run)

**Deliverables:**
- `watch.py` with `watch_and_run(config, paths, coverage, min_percent)` function
- `watchdog` added to dependencies
- Updated `cli.py` with `--watch` flag on `test` command
- Unit tests with mocked file system events
- Integration test (if possible with watchdog's test utilities)

**Success Criteria:**
1. `gd-tools test --watch` monitors `.gd` files and re-runs tests on change
2. File-to-test mapping works (changing `foo.gd` runs `test_foo.gd`)
3. Debouncing prevents multiple rapid runs
4. Ctrl+C exits cleanly with exit code 0
5. `--watch` works with `--coverage` flag
6. Terminal is cleared between runs
7. `watchdog` dependency doesn't break existing installs

---

### Track 29: Pre-commit Hook Integration

| Field | Value |
|-------|-------|
| **Phase** | 7 -- Strategic Features |
| **Goal** | Add `gd-tools install-hooks` command for pre-commit framework integration |
| **Dependencies** | Track 4 (lint), Track 5 (format) |
| **Modules** | `src/gd_tools/cli.py`, `src/gd_tools/hooks.py` (new) |
| **Effort** | 1 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

There's no integration with the popular [pre-commit](https://pre-commit.com/)
framework. Developers who use pre-commit for Git hook management can't
easily add gd-tools to their workflow.

**Scope:**
- `gd-tools install-hooks` command:
  - Generates a `.pre-commit-hooks.yaml` file in the project root
  - Registers gd-tools as a local hook repository
  - Hooks: `gd-tools format --check`, `gd-tools lint`, optionally
    `gd-tools test --min N`
  - Prompts user which hooks to enable (or `--all` for all)
  - Idempotent: re-running updates the file
- Document a `.pre-commit-config.yaml` snippet in README and USER_GUIDE:
  ```yaml
  repos:
    - repo: local
      hooks:
        - id: gd-tools-format
          name: gd-tools format
          entry: gd-tools format --check
          language: system
          files: \.gd$
        - id: gd-tools-lint
          name: gd-tools lint
          entry: gd-tools lint
          language: system
          files: \.gd$
  ```
- `--non-interactive` flag for CI/scripted use

**Deliverables:**
- `hooks.py` with `install_hooks(non_interactive, all_hooks)` function
- `install-hooks` command in `cli.py`
- Documentation in README and USER_GUIDE
- Unit tests for hook file generation, idempotency

**Success Criteria:**
1. `gd-tools install-hooks` generates a valid `.pre-commit-hooks.yaml`
2. Generated hooks work with `pre-commit run --all-files`
3. Re-running `install-hooks` is idempotent (no duplicates)
4. `--non-interactive` mode works without prompts
5. Documentation includes copy-pasteable `.pre-commit-config.yaml` example

---

### Track 30: Coverage Exclusion Annotations

| Field | Value |
|-------|-------|
| **Phase** | 7 -- Strategic Features |
| **Goal** | Support `# gd-tools: no cover` annotations to exclude specific lines/blocks from coverage |
| **Dependencies** | Track 9 (plan generator) |
| **Modules** | `src/gd_tools/coverage/plan_generator.py` |
| **Effort** | 1-1.5 days |
| **Risk** | MEDIUM -- AST annotation parsing, block detection |
| **Status** | Planned |

**Problem:**

There's no way to exclude specific lines or blocks from coverage. Debug-
only code, platform-specific branches, and `@onready` variable
declarations all show as uncovered, artificially lowering coverage
percentages and creating noise.

**Scope:**
- Support a GDScript comment annotation:
  ```gdscript
  # Single line exclusion
  func _ready():
      if OS.is_debug_build():  # gd-tools: no cover
          print("debug info")

  # Block exclusion (until end of function or next annotation)
  func _platform_specific():  # gd-tools: no cover start
      if OS.has_feature("windows"):
          do_windows_thing()
      elif OS.has_feature("linux"):
          do_linux_thing()
      # gd-tools: no cover end
  ```
- The plan generator detects these annotations during AST traversal and
  skips instrumenting the annotated lines/blocks
- `# gd-tools: no cover` on a line excludes that line only
- `# gd-tools: no cover start` ... `# gd-tools: no cover end` excludes
  a block of lines
- Excluded lines are noted in the plan JSON (for transparency in reports)
- HTML report shows excluded lines in a distinct color (gray/strikethrough)

**Deliverables:**
- Updated `plan_generator.py` with annotation detection
- Updated HTML reporter to show excluded lines distinctly
- Unit tests with fixture `.gd` files using all annotation forms
- Documentation in USER_GUIDE

**Success Criteria:**
1. `# gd-tools: no cover` excludes a single line from instrumentation
2. `# gd-tools: no cover start` / `end` excludes a block of lines
3. Excluded lines are not counted in coverage percentage
4. Excluded lines are noted in plan JSON
5. HTML report shows excluded lines in a distinct style
6. Existing coverage results are unchanged for files without annotations

---

### Track 31: GitHub Actions Annotations

| Field | Value |
|-------|-------|
| **Phase** | 7 -- Strategic Features |
| **Goal** | Add `--report-format github-actions` to lint and coverage for native GitHub PR annotations |
| **Dependencies** | Track 4 (lint), Track 12 (reporter) |
| **Modules** | `src/gd_tools/lint_runner.py`, `src/gd_tools/coverage/reporter.py` |
| **Effort** | 0.5 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

In CI, lint errors and coverage failures are just text in the log.
GitHub's native annotation UI (the "Files changed" diff view in PRs)
isn't used, making it harder for developers to spot issues.

**Scope:**
- Add `github-actions` as a valid `--report-format` option for `lint`:
  - Lint violations output as GitHub Actions log commands:
    ```
    ::error file=src/player.gd,line=42::GD3000 unused variable 'x'
    ```
  - These appear as annotations in the PR diff view
- Add `github-actions` as a valid `--report-format` option for `coverage report`:
  - Coverage threshold failures output as warnings:
    ```
    ::warning file=src/player.gd::Coverage 78% below minimum 80%
    ```
  - Uncovered files with <50% coverage get warning annotations
- Document CI usage in USER_GUIDE with a GitHub Actions workflow snippet

**Deliverables:**
- `format_lint_github_actions()` function in `lint_runner.py`
- `GitHubActionsReporter` class or function in `coverage/reporter.py`
- Updated CLI to accept `github-actions` format
- Unit tests for annotation format output
- Documentation in USER_GUIDE

**Success Criteria:**
1. `gd-tools lint --report-format github-actions` outputs valid GH Actions annotations
2. `gd-tools coverage report --report-format github-actions` outputs valid annotations
3. Annotations appear in GitHub PR diff view
4. Format follows GitHub Actions log command specification
5. Existing `text` and `json` formats are unchanged

---

### Track 32: Configurable Version Mapping

| Field | Value |
|-------|-------|
| **Phase** | 7 -- Strategic Features |
| **Goal** | Move the Godot-to-GUT version mapping out of hardcoded Python and into a data-driven config |
| **Dependencies** | Track 3 (Godot detection), Track 7 (init) |
| **Modules** | `src/gd_tools/godot.py`, `src/gd_tools/init.py`, `src/gd_tools/data/gut_versions.json` (new) |
| **Effort** | 0.5-1 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

The Godot version to GUT version mapping is hardcoded in `godot.py`
(`GUT_VERSION_MAP`). When Godot 4.8 or GUT 9.4 releases, gd-tools needs
a code change and new release. Users can't add support for new versions
themselves.

**Scope:**
- Move `GUT_VERSION_MAP` to a bundled JSON data file
  (`src/gd_tools/data/gut_versions.json`)
- Allow users to override or extend the mapping in `gd-tools.toml`:
  ```toml
  [godot_versions]
  "4.8" = { gut_version = "9.4.0", download_url = "https://github.com/..." }
  ```
- `get_gut_version_for_godot()` checks user config first, then bundled
  data file, then raises `ConfigError` if not found
- `gd-tools doctor` reports the mapping in use
- Document how to add custom version mappings in USER_GUIDE

**Deliverables:**
- `gut_versions.json` data file
- Updated `godot.py` to load from data file + user config
- Updated `init.py` to use the resolved mapping
- Unit tests for config override, data file loading, fallback behavior
- Documentation in USER_GUIDE

**Success Criteria:**
1. Default version mapping works without any config changes
2. User can override existing mappings in `gd-tools.toml`
3. User can add new Godot/GUT version mappings in `gd-tools.toml`
4. Bundled data file is included in pip package (package-data)
5. `gd-tools doctor` shows the active version mapping

---

### Track 33: Coverage Diff

| Field | Value |
|-------|-------|
| **Phase** | 8 -- Differentiators |
| **Goal** | Show coverage changes between current branch and a base branch (like codecov) |
| **Dependencies** | Track 12 (reporter), Track 13 (coverage CLI) |
| **Modules** | `src/gd_tools/coverage/diff_reporter.py` (new), `src/gd_tools/cli.py` |
| **Effort** | 2-3 days |
| **Risk** | MEDIUM -- baseline storage, diff computation |
| **Status** | Planned |

**Problem:**

Coverage is a single snapshot. There's no way to see what coverage
changed between the current branch and `main`. This makes it hard to
review coverage impact in PRs -- a developer can't tell if their change
added or removed coverage.

**Scope:**
- `gd-tools coverage diff --base main`:
  - Reads coverage data from current branch (`.gd-tools/coverage/`)
  - Reads baseline coverage data (stored from CI run on main)
  - Computes diff: new covered lines, newly uncovered lines, files with
    coverage regression
  - Outputs a diff table:
    ```
    File              Lines (base)  Lines (head)  Change
    src/player.gd     45/50 (90%)   48/50 (96%)   +3 covered
    src/enemy.gd      30/40 (75%)   28/40 (70%)   -2 covered
    ─────────────────────────────────────────────────────────
    Total             75/90 (83%)   76/90 (84%)   +1 covered
    ```
- Baseline storage:
  - `gd-tools coverage save-baseline` saves current coverage as baseline
  - Stored in `.gd-tools/coverage/baseline.json`
  - CI can save baseline on main branch pushes
- `--report-format json` for machine-readable diff output
- Exit code 1 if any file has coverage regression (configurable via
  `--fail-on-regression`)

**Deliverables:**
- `diff_reporter.py` with `compute_diff(base_data, head_data) -> DiffResult`
- `diff` and `save-baseline` subcommands in `coverage` command group
- Unit tests with mock coverage data (improvements, regressions, new files)
- Documentation in USER_GUIDE

**Success Criteria:**
1. `gd-tools coverage diff --base baseline.json` shows coverage changes
2. New covered lines are highlighted
3. Newly uncovered lines are highlighted
4. New files in head branch are shown
5. `--fail-on-regression` exits 1 if any file regressed
6. `--report-format json` produces valid JSON diff output
7. Baseline can be saved and loaded correctly

---

### Track 34: Coverage During Playtesting

| Field | Value |
|-------|-------|
| **Phase** | 8 -- Differentiators |
| **Goal** | Add `gd-tools coverage run` to collect coverage during manual playtesting |
| **Dependencies** | Track 9 (plan generator), Track 11 (hooks), Track 12 (reporter) |
| **Modules** | `src/gd_tools/coverage/playtest.py` (new), `src/gd_tools/cli.py`, GDScript addon updates |
| **Effort** | 3-4 days |
| **Risk** | HIGH -- game launch, signal handling, coverage collection on exit |
| **Status** | Planned |

**Problem:**

Coverage only works during automated test runs. There's no way to
collect coverage during manual playtesting, which is where much of the
game logic actually executes. This is a feature no other GDScript tool
offers.

**Scope:**
- `gd-tools coverage run --scene res://main.tscn`:
  1. Generates coverage plan (same as test coverage)
  2. Sets env vars for coverage activation
  3. Launches Godot with the specified scene (non-headless, windowed)
  4. Player plays the game normally
  5. On game exit (Godot process ends), post-run hook writes coverage data
  6. Python reporter generates reports (HTML, terminal, etc.)
- GDScript addon changes:
  - Coverage tracker must work outside GUT context (autoload-based, not
    hook-based)
  - Need a `NOTIFICATION_WM_CLOSE_REQUEST` handler or
    `Tree.exited` signal to flush coverage data on game exit
  - Alternative: write coverage data periodically to a temp file, final
    flush on exit
- `--scene` flag specifies the entry scene (default: `res://main.tscn`)
- `--timeout N` flag auto-closes after N seconds (for automated playtesting)
- Works with `--min N` threshold check

**Deliverables:**
- `playtest.py` with `run_playtest_coverage(config, scene, timeout) -> ReportResult`
- Updated GDScript addon for non-GUT coverage collection
- `run` subcommand in `coverage` command group
- Unit tests with mocked Godot process
- Integration test (requires Godot, may be CI-skipped)
- Documentation in USER_GUIDE

**Success Criteria:**
1. `gd-tools coverage run` launches the game with coverage instrumentation
2. Coverage data is collected during gameplay
3. On game exit, coverage reports are generated
4. `--scene` flag selects the entry scene
5. `--timeout` flag auto-closes the game after N seconds
6. `--min N` threshold check works
7. Coverage data from playtesting is compatible with existing reporters

---

### Track 35: Editor Plugin

| Field | Value |
|-------|-------|
| **Phase** | 8 -- Differentiators |
| **Goal** | Create a Godot editor plugin that provides a dock for running tests and viewing coverage inline |
| **Dependencies** | Track 6 (test runner), Track 12 (reporter) |
| **Modules** | `src/gd_tools/addons/gd-tools-editor/` (new GDScript plugin) |
| **Effort** | 3-5 days |
| **Risk** | MEDIUM-HIGH -- Godot editor API, GDScript UI, plugin distribution |
| **Status** | Planned |

**Problem:**

Developers must switch between the Godot editor and terminal to run
tests and check coverage. An editor plugin would eliminate this context
switch and provide inline coverage visualization.

**Scope:**
- Godot editor plugin (deployed via `gd-tools init`):
  - Adds a "gd-tools" dock panel with:
    - "Run Tests" button -> calls `gd-tools test` via `OS.execute()`
    - Test results displayed in the dock (pass/fail count, per-test details)
    - "Run Coverage" button -> calls `gd-tools test --coverage`
    - Coverage summary displayed in the dock
  - Coverage heatmap overlay in the script editor:
    - Covered lines: green background
    - Uncovered lines: red background
    - Partial branches: yellow background
    - Uses Godot's `CodeEdit` line background color API
  - Lint warnings in the editor margin (if feasible with Godot API)
- Plugin configuration in `project.godot`:
  - `[editor_plugins]` enabled entry
  - Dock visibility toggle
- `gd-tools init` deploys the editor plugin alongside the coverage addon

**Deliverables:**
- `addons/gd-tools-editor/` plugin directory with:
  - `plugin.cfg`
  - `plugin.gd` (main plugin script)
  - `dock.gd` (dock panel UI)
  - `coverage_overlay.gd` (script editor overlay)
- Updated `init.py` to deploy editor plugin
- Documentation in USER_GUIDE
- Manual testing checklist (editor plugin can't be unit tested easily)

**Success Criteria:**
1. Plugin appears in Godot editor after `gd-tools init`
2. Dock panel shows "Run Tests" and "Run Coverage" buttons
3. Clicking "Run Tests" executes tests and shows results in dock
4. Coverage heatmap overlay appears in script editor after coverage run
5. Covered/uncovered lines are visually distinct
6. Plugin can be toggled on/off in Godot's Plugin settings
7. Plugin works on Godot 4.5+

---

### Track 36: macOS CI Matrix

| Field | Value |
|-------|-------|
| **Phase** | 9 -- Robustness & Quality |
| **Goal** | Add macOS to the CI test matrix |
| **Dependencies** | Track 15 (CI/CD pipeline) |
| **Modules** | `.github/workflows/ci.yml` |
| **Effort** | 0.25 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

CI runs on Ubuntu and Windows but not macOS. Godot is cross-platform;
macOS users are a significant portion of the Godot community. Path
handling and Godot binary detection may have macOS-specific edge cases
that go untested.

**Scope:**
- Add `macos-latest` to the OS matrix in `.github/workflows/ci.yml`
- Ensure Godot binary download works on macOS in CI
- Verify all integration and E2E tests pass on macOS
- Fix any macOS-specific path or binary detection issues that surface

**Deliverables:**
- Updated `ci.yml` with macOS in matrix
- Any necessary fixes to `godot.py` for macOS path detection
- Verification that all CI stages pass on macOS

**Success Criteria:**
1. macOS appears in CI matrix and runs all 3 stages
2. All unit tests pass on macOS
3. All integration tests pass on macOS (with Godot installed)
4. All E2E tests pass on macOS
5. CI pipeline completes in <15 minutes total (macOS runners are slower)

---

### Track 37: Plan Generator Caching

| Field | Value |
|-------|-------|
| **Phase** | 9 -- Robustness & Quality |
| **Goal** | Cache the coverage plan to avoid regeneration when source files haven't changed |
| **Dependencies** | Track 9 (plan generator) |
| **Modules** | `src/gd_tools/coverage/plan_generator.py`, `src/gd_tools/coverage/orchestrator.py` |
| **Effort** | 1 day |
| **Risk** | LOW-MEDIUM -- cache invalidation, staleness detection |
| **Status** | Planned |

**Problem:**

The coverage plan is regenerated on every `gd-tools test --coverage` run,
even if no source files changed. For large projects (100+ files), this
adds noticeable latency to every test run.

**Scope:**
- Cache the plan based on source file hashes (already computed in plan
  generation as `source_hash`)
- Store cached plan in `.gd-tools/coverage/plan.json` (already the output
  path)
- On plan generation:
  1. Check if `plan.json` exists
  2. Read it and extract source hashes for each file
  3. Compare against current source file hashes
  4. If all hashes match, reuse the cached plan (skip regeneration)
  5. If any hash differs or new files exist, regenerate the full plan
- `--no-cache` flag to force plan regeneration
- Log whether plan was cached or regenerated (visible with `--verbose`)

**Deliverables:**
- Updated `plan_generator.py` with cache check logic
- Updated `orchestrator.py` to pass cache flag through
- `--no-cache` flag on `test --coverage` command
- Unit tests for cache hit, cache miss, partial cache, `--no-cache`
- Performance test: verify caching saves time on 100+ file project

**Success Criteria:**
1. When no source files changed, plan is loaded from cache (no regeneration)
2. When a source file changes, plan is regenerated
3. When a new file is added, plan is regenerated
4. `--no-cache` forces regeneration
5. Cached plan produces identical coverage results to fresh plan
6. Performance improvement is measurable on 50+ file project

---

### Track 38: GDScript AST Edge Cases

| Field | Value |
|-------|-------|
| **Phase** | 9 -- Robustness & Quality |
| **Goal** | Audit and fix the plan generator for complex GDScript syntax patterns |
| **Dependencies** | Track 9 (plan generator) |
| **Modules** | `src/gd_tools/coverage/plan_generator.py`, `tests/fixtures/gdscript/` |
| **Effort** | 1-2 days |
| **Risk** | MEDIUM -- Lark AST traversal complexity |
| **Status** | Planned |

**Problem:**

The plan generator uses Lark AST traversal. Complex GDScript patterns may
not be fully covered by the current statement classification:
- Ternary expressions (`var x = a if cond else b`)
- Lambda functions (`var f = func(): ...`)
- Setter/getter blocks (`var x: set(v): ...`, `get(): ...`)
- Match statements with bind patterns (`match x: 1 as a: ...`)
- `@onready` and `@export` annotations
- Static function calls (`ClassName.static_method()`)
- `await` expressions
- `super()` calls

**Scope:**
- Create a comprehensive GDScript fixture file (`edge_cases_advanced.gd`)
  that exercises all of the above patterns
- Run the plan generator against it and audit the output
- Fix any instrumentation gaps (lines not tracked, branches not detected)
- Add the fixture to the expected plan generation test suite
- Document any patterns that cannot be instrumented (with rationale)

**Deliverables:**
- `edge_cases_advanced.gd` fixture file
- Expected plan JSON for the fixture
- Fixes to `plan_generator.py` for any gaps found
- New unit tests for each pattern
- Documentation of any limitations

**Success Criteria:**
1. Ternary expressions are correctly tracked (both branches)
2. Lambda function bodies are tracked
3. Setter/getter blocks are tracked
4. Match bind patterns are tracked
5. `@onready`/`@export` annotations don't cause false positives
6. `await` expressions are tracked
7. `super()` calls are tracked
8. All new fixtures pass plan generation tests

---

### Track 39: Clean Command

| Field | Value |
|-------|-------|
| **Phase** | 9 -- Robustness & Quality |
| **Goal** | Add `gd-tools clean` command to remove generated artifacts |
| **Dependencies** | Track 1 (CLI skeleton) |
| **Modules** | `src/gd_tools/cli.py`, `src/gd_tools/clean.py` (new) |
| **Effort** | 0.25 day |
| **Risk** | LOW |
| **Status** | Planned |

**Problem:**

No way to clean up generated artifacts (`.gd-tools/`, coverage reports,
cached data) without manually deleting directories. Users may not know
what's safe to delete.

**Scope:**
- `gd-tools clean` command with optional flags:
  - `--coverage` -- Remove `.gd-tools/coverage/` (plan, data, reports)
  - `--cache` -- Remove `.gd-tools/cache/` (if plan caching exists)
  - `--all` -- Remove entire `.gd-tools/` directory
  - No flags -- prompt interactively (or remove coverage artifacts by default)
- `--dry-run` flag to show what would be deleted without deleting
- Prints a summary of what was removed
- Does NOT remove `addons/` (those are project files, not generated)
- Does NOT remove `gd-tools.toml` or `.gutconfig.json` (user config)

**Deliverables:**
- `clean.py` with `run_clean(coverage, cache, all, dry_run) -> CleanResult`
- `clean` command in `cli.py`
- Unit tests with temp directories
- Documentation in USER_GUIDE

**Success Criteria:**
1. `gd-tools clean --coverage` removes `.gd-tools/coverage/`
2. `gd-tools clean --all` removes entire `.gd-tools/`
3. `--dry-run` shows what would be deleted without deleting
4. `addons/` directory is never touched
5. `gd-tools.toml` and `.gutconfig.json` are never touched
6. Summary of removed files/dirs is printed

---

## 5. Risk Register

| Risk | Affected Tracks | Mitigation |
|------|-----------------|------------|
| **Watch mode file watching unreliable on some platforms** | 28 | Use `watchdog` (cross-platform). Fallback: polling-based watcher. Test on all OSes. |
| **Coverage exclusion annotations break AST parsing** | 30 | Comprehensive fixture tests. Fallback: only support single-line exclusions initially. |
| **Editor plugin API changes between Godot versions** | 35 | Target Godot 4.5+ only. Test on 4.5, 4.6, 4.7. Document version compatibility. |
| **Playtesting coverage: game crash loses data** | 34 | Write coverage data periodically (every N seconds) to temp file. Final flush on exit. |
| **Plan cache produces stale results** | 37 | Hash-based invalidation. `--no-cache` escape hatch. Log cache hit/miss. |
| **macOS CI runners are slower / more expensive** | 36 | Only run integration/E2E on macOS (unit tests are OS-agnostic). Consider running macOS CI on schedule, not every PR. |
| **Pre-commit framework version changes** | 29 | Generate standard `.pre-commit-hooks.yaml` format. Pin no framework version. |
| **GitHub Actions annotation format changes** | 31 | Follow [official spec](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions). Test with real PRs. |

---

## 6. Conductor Track Creation Guide

To create a track using the Conductor methodology:

```
conductor_new_track
  -> Provide the track ID and name from this document
  -> Copy the "Scope" section as the spec basis
  -> Use "Success Criteria" as verification gates
  -> Reference related PRD/ARCHITECTURE sections for implementation details
```

### Track Creation Order (Recommended)

1. **Tracks 23-27 (Quick Wins)** -- Can be created in any order. All
   independent. Start with Track 23 (Stale Addon Detection) as it prevents
   real user-facing bugs.

2. **Tracks 28-32 (Strategic Features)** -- Track 28 (Watch Mode) is the
   highest-impact feature, start there. Track 30 (Exclusions) should be
   done before Track 37 (Caching) since both touch `plan_generator.py`.

3. **Tracks 33-35 (Differentiators)** -- Track 33 (Coverage Diff) is the
   lowest-risk of the three. Track 34 (Playtesting) and Track 35 (Editor
   Plugin) are the most complex and can be done in parallel.

4. **Tracks 36-39 (Robustness)** -- Can be picked up between feature
   tracks as time allows. Track 36 (macOS CI) is quickest and should be
   done early to catch platform issues.

### Spec/Plan Template Per Track

Each Conductor track should produce:
- **`spec.md`** -- Track scope, goals, success criteria (from this
  document's track section)
- **`plan.md`** -- Implementation plan: file-by-file changes, function
  signatures, task breakdown, testing approach
- **`metadata.json`** -- Track metadata (status, assignee, dates)

---

## 7. Success Metrics (Post-v1)

| Metric | Target | Measured By |
|--------|--------|-------------|
| Quick win adoption | All 5 quick win tracks shipped in v0.4.0 | Release notes |
| Watch mode usage | Users report using `--watch` daily | User feedback / GitHub issues |
| Pre-commit integration | 10+ projects use gd-tools pre-commit hooks | Community survey |
| Coverage exclusion adoption | Users report cleaner coverage reports | User feedback |
| Editor plugin installs | 50+ projects with editor plugin | GitHub stars / feedback |
| macOS CI | All tests pass on macOS | CI pipeline |
| Plan cache speedup | 50%+ faster `test --coverage` on 50+ file projects | Benchmark |
| AST edge case coverage | 0 known untracked GDScript patterns | Fixture tests |
| PyPI download growth | 2x monthly downloads vs v1.0 | PyPI stats |
| Community contributions | 5+ external PRs | GitHub metrics |
