<protect>
# Track 27: Verbose/Quiet Global Flags — Implementation Plan

## Phase 1: Verbosity Core Infrastructure

- [x] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocols
- [x] Task: Create Verbosity enum and context module (8e4caa2)
    - [x] Write failing tests for `Verbosity` enum (QUIET, DEFAULT, VERBOSE values) and a verbosity context object that stores and retrieves the active level (`tests/unit/test_verbosity.py`)
    - [x] Implement `Verbosity` enum and context in a new `src/gd_tools/verbosity.py` module — context stores active level, provides `get_verbosity()` / `set_verbosity()` accessors
    - [x] Run tests, confirm Green phase
    - [x] Verify >80% line / >70% branch coverage for `verbosity.py`
    - [x] Commit: `feat(verbosity): Add Verbosity enum and context module`
    - [x] Attach git note with task summary to commit
    - [x] Mark task complete in `plan.md` with commit SHA
- [x] Task: Extend output.py to respect verbosity level (ff4c9ca)
    - [x] Write failing tests verifying that `print_info` and `print_warning` are suppressed when verbosity is QUIET, and that `print_success`, `print_error`, `print_summary`, and `print_table` always render regardless of verbosity (`tests/unit/test_output.py`)
    - [x] Implement verbosity checks in `output.py` — `print_info` and `print_warning` check `get_verbosity()` and skip output when QUIET; add a new `print_verbose()` helper that only renders when VERBOSE
    - [x] Run tests, confirm Green phase
    - [x] Verify >80% line / >70% branch coverage for `output.py`
    - [x] Commit: `feat(output): Integrate verbosity checks into output module`
    - [x] Attach git note with task summary to commit
    - [x] Mark task complete in `plan.md` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Verbosity Core Infrastructure' (Protocol in workflow.md)

## Phase 2: Global CLI Flags

- [x] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocols
- [x] Task: Add --verbose/-v and --quiet/-q global flags to CLI group (a58e1e6)
    - [x] Write failing tests for flag parsing (`gd-tools --verbose test`, `gd-tools -v test`, `gd-tools --quiet test`, `gd-tools -q test`), mutual exclusion error (`gd-tools --verbose --quiet test` exits 2), and default behavior (no flag = DEFAULT verbosity) (`tests/unit/test_cli.py`)
    - [x] Implement `--verbose`/`-v` and `--quiet`/`-q` flags on the `@click.group(cls=GdToolsGroup)` decorator in `cli.py`; add mutual exclusion check in the group callback; call `set_verbosity()` based on flags; store verbosity in `ctx.obj` for subcommand access
    - [x] Run tests, confirm Green phase
    - [x] Verify >80% line / >70% branch coverage for modified `cli.py` sections
    - [x] Commit: `feat(cli): Add --verbose and --quiet global flags with mutual exclusion`
    - [x] Attach git note with task summary to commit
    - [x] Mark task complete in `plan.md` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Global CLI Flags' (Protocol in workflow.md)

## Phase 3: Verbose Mode Implementation

- [x] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocols
- [x] Task: Display underlying commands in verbose mode (eaddb11)
    - [ ] Write failing tests verifying that when verbosity is VERBOSE, the full Godot/GUT command is printed before execution in `run_tests()`, the gdlint invocation is shown in `run_lint()`, and the gdformat invocation is shown in `run_format()` (`tests/unit/test_test_runner.py`, `tests/unit/test_lint_runner.py`, `tests/unit/test_format_runner.py`)
    - [ ] Implement command display logic — add a `print_verbose()` call in `test_runner.py` (before `run_godot()` showing `[binary, --path, project_root, *args]`), in `lint_runner.py` (before `lint_code()` showing the file being linted), and in `format_runner.py` (before `format_code()` showing the file being formatted)
    - [ ] Run tests, confirm Green phase
    - [ ] Verify >80% line / >70% branch coverage for modified runner sections
    - [ ] Commit: `feat(verbose): Display underlying commands in verbose mode`
    - [ ] Attach git note with task summary to commit
    - [ ] Mark task complete in `plan.md` with commit SHA
- [x] Task: Display timing information in verbose mode (b356eb3)
    - [ ] Write failing tests verifying that when verbosity is VERBOSE, elapsed time is printed after each major operation (test run, lint scan, format pass) (`tests/unit/test_test_runner.py`, `tests/unit/test_lint_runner.py`, `tests/unit/test_format_runner.py`)
    - [ ] Implement timing logic — wrap each major operation in `time.perf_counter()` start/end calls and print elapsed time via `print_verbose()` in `test_runner.py`, `lint_runner.py`, and `format_runner.py`
    - [ ] Run tests, confirm Green phase
    - [ ] Verify >80% line / >70% branch coverage for modified runner sections
    - [ ] Commit: `feat(verbose): Display timing information in verbose mode`
    - [ ] Attach git note with task summary to commit
    - [ ] Mark task complete in `plan.md` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Verbose Mode Implementation' (Protocol in workflow.md) [checkpoint: a7ff3f2]

## Phase 4: Quiet Mode Implementation

- [x] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocols
- [x] Task: Suppress update check and addon version check in quiet mode (473c687)
    - [x] Write failing tests verifying that when verbosity is QUIET, `check_for_update()` and `check_addon_version()` are skipped (no update notification printed) (`tests/unit/test_cli.py`)
    - [x] Implement suppression in `GdToolsGroup.invoke()` — check `get_verbosity()` before calling `check_for_update()` and `check_addon_version()`; skip both when QUIET
    - [x] Run tests, confirm Green phase
    - [x] Verify >80% line / >70% branch coverage for modified `cli.py` sections
    - [x] Commit: `feat(quiet): Suppress update and addon version checks in quiet mode`
    - [x] Attach git note with task summary to commit
    - [x] Mark task complete in `plan.md` with commit SHA
- [x] Task: Suppress progress/info messages in quiet mode (4282872)
    - [x] Write failing tests verifying that when verbosity is QUIET, `print_info()` calls in runner modules produce no output, but `print_success()`, `print_error()`, and `print_summary()` still render (`tests/unit/test_output.py`, `tests/unit/test_test_runner.py`, `tests/unit/test_lint_runner.py`)
    - [x] Verify that the `output.py` changes from Phase 1 already handle this (print_info checks verbosity); if any runner modules use `click.echo` or direct `Console` calls for non-essential output, route them through `print_info()` or add explicit verbosity checks
    - [x] Run tests, confirm Green phase
    - [x] Verify >80% line / >70% branch coverage
    - [x] Commit: `feat(quiet): Suppress progress and info messages in quiet mode`
    - [x] Attach git note with task summary to commit
    - [x] Mark task complete in `plan.md` with commit SHA
- [x] Task: Suppress init/doctor details in quiet mode (953303d)
    - [x] Write failing tests verifying that when verbosity is QUIET, `gd-tools init` shows only a success/failure status (no summary table), and `gd-tools doctor` shows only pass/fail status (no detailed table) (`tests/unit/test_cli.py` or `tests/integration/test_init_integration.py`)
    - [x] Implement quiet mode in `init` and `doctor` commands — check `get_verbosity()` before printing detailed output; in QUIET mode, print only a one-line status (`[OK] Initialized` or `[FAIL] Initialization failed`)
    - [x] Run tests, confirm Green phase
    - [x] Verify >80% line / >70% branch coverage
    - [x] Commit: `feat(quiet): Suppress init and doctor details in quiet mode`
    - [x] Attach git note with task summary to commit
    - [x] Mark task complete in `plan.md` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Quiet Mode Implementation' (Protocol in workflow.md)

## Phase 5: Integration Testing & Documentation

- [ ] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocols
- [ ] Task: Write integration tests for verbose/quiet across all commands
    - [ ] Write integration tests verifying end-to-end verbose output (commands shown, timing shown) and quiet output (minimal output, results only) for `test`, `lint`, `format`, `doctor`, and `init` commands (`tests/integration/test_verbosity_integration.py`)
    - [ ] Run integration tests, confirm all pass
    - [ ] Verify no regressions in existing integration tests
    - [ ] Commit: `test(verbosity): Add integration tests for verbose and quiet modes`
    - [ ] Attach git note with task summary to commit
    - [ ] Mark task complete in `plan.md` with commit SHA
- [ ] Task: Update documentation with --verbose/--quiet usage
    - [ ] Add a "Verbosity Control" section to README documenting `--verbose`/`-v` and `--quiet`/`-q` flags with examples
    - [ ] Add a "Verbosity Control" section to USER_GUIDE with detailed usage examples for CI (quiet) and debugging (verbose) scenarios
    - [ ] Commit: `docs(verbosity): Document --verbose and --quiet global flags`
    - [ ] Attach git note with task summary to commit
    - [ ] Mark task complete in `plan.md` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Integration Testing & Documentation' (Protocol in workflow.md)
</protect>
