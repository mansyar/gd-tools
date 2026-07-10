<protect>
# Track 8: Doctor Command — Implementation Plan

## Phase 1: Module Skeleton and Data Structures [checkpoint: c5fc9c2]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/doctor_20260711/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Set up `doctor.py` module skeleton with imports and data structures [e0c5ad3]
    - [ ] Create `src/gd_tools/doctor.py` with module docstring referencing TDD §3.6 and PRD §8
    - [ ] Import `find_godot`, `check_version_compatible`, `get_gut_version_for_godot`, `GodotInfo`, `GodotNotFoundError` from `godot`
    - [ ] Import `find_project_root`, `load_config`, `GdToolsConfig`, `ConfigError` from `config`
    - [ ] Import `get_installed_gut_version` from `init` (reuse, no new implementation)
    - [ ] Import `Console`, `Table` from `rich`
    - [ ] Define `CheckResult` dataclass: `name`, `passed`, `message`, `fix_hint`, `severity`
    - [ ] Define `DoctorResult` dataclass: `checks: list[CheckResult]`, `all_passed: bool`
    - [ ] Write tests for `CheckResult` and `DoctorResult` dataclasses
    - [ ] Run `ruff check src/gd_tools/doctor.py` — verify no import errors

- [x] Task: Conductor - User Manual Verification 'Phase 1: Module Skeleton and Data Structures' (Protocol in workflow.md)

## Phase 2: Godot and External Tool Checks [checkpoint: 56a1b4a]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/doctor_20260711/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Implement `check_godot_binary(config: GdToolsConfig) -> CheckResult` [2e76a09]
    - [ ] Write failing tests: `test_check_godot_binary_passes_when_found`, `test_check_godot_binary_fails_when_not_found`, `test_check_godot_binary_critical_severity`
    - [ ] Implement `check_godot_binary()` — call `find_godot(config.godot)`, return `CheckResult(passed=True, message="Godot <version> at <path>")` or `CheckResult(passed=False, fix_hint="Install Godot 4.5+ from https://godotengine.org and set GODOT_BIN or add to PATH.", severity="critical")`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check` on modified files

- [x] Task: Implement `check_godot_version(config: GdToolsConfig) -> CheckResult` [5668dab]
    - [ ] Write failing tests: `test_check_godot_version_passes_when_45_plus`, `test_check_godot_version_fails_when_below_45`, `test_check_godot_version_critical_severity`
    - [ ] Implement `check_godot_version()` — call `find_godot(config.godot)`, use `check_version_compatible(info.version)`, return pass/fail `CheckResult` with actionable fix hint
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `check_gdtoolkit() -> CheckResult` [c387804]
    - [ ] Write failing tests: `test_check_gdtoolkit_passes_when_installed`, `test_check_gdtoolkit_fails_when_gdlint_missing`, `test_check_gdtoolkit_fails_when_gdformat_missing`, `test_check_gdtoolkit_critical_severity`
    - [ ] Implement `check_gdtoolkit()` — run `subprocess.run(["gdlint", "--version"])` and `subprocess.run(["gdformat", "--version"])`, return pass/fail `CheckResult` with fix hint "Run `pip install gdtoolkit`"
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Conductor - User Manual Verification 'Phase 2: Godot and External Tool Checks' (Protocol in workflow.md)

## Phase 3: GUT and Project Configuration Checks [checkpoint: ab93fcc]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/doctor_20260711/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Implement `check_gut_installed(project_root: Path) -> CheckResult` [98e4386]
    - [ ] Write failing tests: `test_check_gut_installed_passes_when_present`, `test_check_gut_installed_fails_when_absent`, `test_check_gut_installed_critical_severity`
    - [ ] Implement `check_gut_installed()` — check if `project_root/addons/gut/gut.gd` exists, return `CheckResult` with fix hint "Run `gd-tools init` to install GUT, or see https://github.com/bitwes/Gut."
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `check_gut_version(project_root: Path, godot_version: str) -> CheckResult` (cf54a81)
    - [ ] Write failing tests: `test_check_gut_version_passes_when_matches`, `test_check_gut_version_fails_as_warning_when_mismatch`, `test_check_gut_version_warning_severity`, `test_check_gut_version_passes_when_version_unknown`
    - [ ] Implement `check_gut_version()` — call `get_installed_gut_version(project_root)` and `get_gut_version_for_godot(godot_version)`, compare, return `CheckResult(severity="warning")` with correct version suggestion on mismatch
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `check_coverage_addon(project_root: Path) -> CheckResult` (420674b)
    - [ ] Write failing tests: `test_check_coverage_addon_passes_when_all_files_present`, `test_check_coverage_addon_fails_when_missing_files`, `test_check_coverage_addon_warning_severity`
    - [ ] Implement `check_coverage_addon()` — check all `addons/gd-tools-coverage/*.gd` files exist (coverage.gd, pre_run_hook.gd, post_run_hook.gd), return `CheckResult(severity="warning")` with fix hint "Run `gd-tools init` to deploy coverage addon."
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `check_gutconfig(project_root: Path) -> CheckResult` [91530fe]
    - [ ] Write failing tests: `test_check_gutconfig_passes_when_valid_with_hooks`, `test_check_gutconfig_fails_when_missing`, `test_check_gutconfig_fails_when_invalid_json`, `test_check_gutconfig_fails_when_no_hook_paths`, `test_check_gutconfig_warning_severity`
    - [ ] Implement `check_gutconfig()` — read `.gutconfig.json`, parse JSON, check for `pre_run_script` and `post_run_script` keys, return `CheckResult(severity="warning")` with fix hint
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `check_gd_tools_toml(project_root: Path) -> CheckResult` [1ffc0b1]
    - [ ] Write failing tests: `test_check_gd_tools_toml_passes_when_valid`, `test_check_gd_tools_toml_fails_when_missing`, `test_check_gd_tools_toml_fails_when_invalid_toml`, `test_check_gd_tools_toml_critical_severity`
    - [ ] Implement `check_gd_tools_toml()` — check if `gd-tools.toml` exists and is parseable TOML (use `load_config` or `tomllib`/`tomli`), return `CheckResult(severity="critical")` with fix hint
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `check_autoload(project_root: Path) -> CheckResult` [a475208]
    - [ ] Write failing tests: `test_check_autoload_passes_when_registered`, `test_check_autoload_fails_when_not_registered`, `test_check_autoload_fails_when_no_project_godot`, `test_check_autoload_critical_severity`
    - [ ] Implement `check_autoload()` — read `project.godot`, parse `[autoload]` section, check for `_GDTCoverage` entry, return `CheckResult(severity="critical")` with fix hint "Run `gd-tools init` to deploy coverage addon (autoload registration in Phase 3)."
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Conductor - User Manual Verification 'Phase 3: GUT and Project Configuration Checks' (Protocol in workflow.md)

## Phase 4: Orchestration, Output, and CLI Integration

- [ ] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [ ] Read `conductor/tracks/doctor_20260711/spec.md` for functional requirements, acceptance criteria, and constraints
    - [ ] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [ ] Task: Implement `run_doctor() -> DoctorResult`
    - [ ] Write failing tests: `test_run_doctor_returns_doctor_result`, `test_run_doctor_runs_all_9_checks`, `test_run_doctor_all_passed_when_no_failures`, `test_run_doctor_all_passed_false_when_any_fails`, `test_run_doctor_never_raises_on_check_exception`
    - [ ] Implement `run_doctor()` — resolve project root via `find_project_root()`, load config, run all 9 checks in order, catch exceptions per check and convert to failed `CheckResult`, return `DoctorResult`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [ ] Task: Implement `format_doctor_table(result: DoctorResult) -> Table`
    - [ ] Write failing tests: `test_format_doctor_table_has_4_columns`, `test_format_doctor_table_shows_checkmark_for_pass`, `test_format_doctor_table_shows_x_for_critical_fail`, `test_format_doctor_table_shows_warning_for_warning_fail`, `test_format_doctor_table_includes_fix_hints`, `test_format_doctor_table_shows_summary_line`
    - [ ] Implement `format_doctor_table()` — build `rich.table.Table` with Check/Status/Message/Fix Hint columns, color-code rows (green=pass, red=critical fail, yellow=warning fail), add summary line (X/9 checks passed)
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [ ] Task: Wire CLI `doctor` command to `run_doctor()` and `format_doctor_table()`
    - [ ] Write failing tests: `test_cli_doctor_calls_run_doctor`, `test_cli_doctor_prints_table`, `test_cli_doctor_exits_zero_when_all_pass`, `test_cli_doctor_exits_one_when_any_fails`
    - [ ] Implement — replace `raise NotImplementedError` in `cli.py` doctor command with call to `run_doctor()`, print table via `format_doctor_table()`, set exit code based on `result.all_passed`
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [ ] Task: Conductor - User Manual Verification 'Phase 4: Orchestration, Output, and CLI Integration' (Protocol in workflow.md)

## Phase 5: Integration Tests and Coverage

- [ ] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [ ] Read `conductor/tracks/doctor_20260711/spec.md` for functional requirements, acceptance criteria, and constraints
    - [ ] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [ ] Task: Write integration tests for doctor command
    - [ ] Write `test_doctor_on_fresh_project` — run `gd-tools doctor` before `gd-tools init`, verify checks report missing components
    - [ ] Write `test_doctor_after_init` — run `gd-tools init` then `gd-tools doctor`, verify all checks pass (except autoload, which is Phase 3)
    - [ ] Run full test suite (`CI=true pytest`), verify all pass and overall coverage thresholds still met
    - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/`

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Integration Tests and Coverage' (Protocol in workflow.md)
</protect>
