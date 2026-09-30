## v0.5.0 (2026-09-30)

### Feat

- **native-test**: Add GUT-compatible parameterized tests to the native runtime. Suites declare value sets once in `before_all` with `parameterize(names, values)`, and every method whose arity matches expands into one first-class case per value set (own hooks, timeout, retry accounting, result entry, and artifacts) with pytest-style case names (`test_foo[3]`, `test_foo[3-admin]`, index fallback for unstable types). The GUT legacy `use_parameters(values)` inside a test body is also supported (array or dictionary form). Preflight statically resolves declarations and rejects malformed ones with exit 2; `--test "method[case]"` selects a single case. Bridge (`GutTest`) suites use the same machinery — parameterization is removed from the bridge scan's unsupported list. This closes the "no parameterized tests" known limitation in ARCHITECTURE.md.
- **native-test**: `skip_test()` in `before_all` now skips the whole suite: every test (and every expanded parameterized case) is reported `skipped` with the recorded reason, no test body or per-test hook runs, and the skip is terminal (never consumes a retry). Per-test `skip_test()` behavior is unchanged. This closes the "no suite-level skip" known limitation in ARCHITECTURE.md.
- **watch**: Add `gd-tools test --watch` — interactive watch mode for the native runtime. An initial full suite is followed by debounced re-runs mapped from changed `.gd` files by convention (`src/enemy.gd` → `test_enemy.gd`/`enemy_test.gd`, same-directory preferred), with an explicit full-suite fallback when nothing maps. Existing filters (`--suite`, `--test`, `--tag`) and `--coverage` apply to every run; rapid saves coalesce into one re-run and a save during a run queues exactly one follow-up. The screen is cleared between runs under a watching banner, `Ctrl+C` exits 0, and `--watch` rejects `--runtime gut` and `CI=true` with exit 2.
- **coverage**: Add `coverage save-baseline` and `coverage diff` subcommands (codecov-style). `save-baseline` persists the latest coverage run as a self-contained baseline document with advisory metadata; `diff --base` reports per-file line and branch deltas (improved/regressed/unchanged/new/removed) with newly-uncovered line detail (`--show-lines`), deterministic JSON output (`--report-format json`), and CI gating (`--fail-on-regression` exits 1 on any per-file regression).
- **native-test**: Deprecate the GUT compatibility bridge. Runs using `GutTest` suites print a one-time deprecation notice stating removal is planned for v0.6.0; the one-release migration window gives projects the full v0.5.0 cycle to move to `GdToolsTest`. Doctor and `init --with-gut` messaging now state the deprecation and the addon-vs-bridge conflict.
- **native-test**: Mark interrupted test runs. `Ctrl+C` (or `SIGTERM`) during a test run kills the in-flight Godot process, publishes an `incomplete` artifact index listing exactly the suites already attempted, prints a notice pointing at the run directory, and exits 130. Complete runs are never marked incomplete.

### Fix

- **native-test**: `GdToolsTest.wait_for_signal` is bounded and returns whether the signal was emitted. It was declared `-> bool` but could only ever return `true`, so a guard such as `if not wait_for_signal(sig): fail(...)` never reached the `fail` — the await blocked to the per-test timeout and the test was reported as `timeout` rather than `failed`, discarding the reason. A test waiting on a signal that never arrives now receives `false` at the wait budget (default `5.0`, matching the per-test default) instead of running to the per-test timeout, and the wait resolves as soon as the signal fires rather than when the budget runs out. The wait records no failure of its own.
- **native-test**: Infrastructure failures (exit 2) now carry structured diagnostics. Timeout, engine-crash, unparseable-result, and protocol-mismatch failures report `expected` / `found` / `kind` / `remedy` — e.g. a timeout names its budget and points at `--timeout` / `[test].timeout_seconds`; an engine crash points at the engine log directory; the aggregate error surfaces the first remedy.

### Known Limitations

- Suites run sequentially; optional parallel execution is deferred (roadmap Phase 5).
- The GUT compatibility bridge is deprecated in this release and planned for removal in v0.6.0. `GutTest` suites still run through it during the migration window; new suites should extend `GdToolsTest`.
- There is no editor plugin integration (roadmap Phase 5 candidates: coverage heatmap dock, playtest coverage).

## v0.4.0 (2026-07-16)

### Feat

- **coverage**: Show uncovered lines and branches in coverage output (`--show-uncovered` flag for `test`, automatic for `coverage show`)
- **coverage**: Standardize coverage output via shared output module
- **test**: Standardize test output via shared output module
- **format**: Standardize format output via shared output module
- **lint**: Standardize lint output via shared output module
- **output**: Add shared output module with rendering helpers
- **cli**: add config validate subcommand
- **cli**: add config command group with show subcommand
- **config**: add format_config_table, format_config_toml, format_config_json
- **config**: add validate_paths for filesystem path validation
- **config**: add deprecation infrastructure for config fields
- **version**: add version CLI command with Rich table and --json output
- **version**: add collect_versions() version detection module
- **doctor**: report addon version status in check_coverage_addon
- **addon-check**: add stale addon detection module and CLI integration
- **init**: write _version.txt during coverage addon deployment

### Fix

- **tests**: Fix CI failures — tomllib import for Python 3.10 and format summary assertion
- **conductor**: Apply review suggestions for track 'stdout_20260715'
- **conductor**: Apply review suggestions for track 'Config Show/Validate'
- **conductor**: Apply review suggestions for track 'lint_output_clipping_fix_20260715'
- **lint**: Replace Rich Table with flat line-based output format
- **coverage**: Use reload(true) for autoload instrumentation
- **coverage**: Remove GD_TOOLS_COVERAGE_ACTIVE env var from test_runner
- **coverage**: Prepend _GDTCoverage autoload and auto-fix ordering
- **coverage**: Remove autoload exclusion from plan generator
- **conductor**: Apply review suggestions for track 'Stale Addon Detection'

### Refactor

- **coverage**: Move instrumentation to _ready(), simplify pre_run_hook

## v0.3.0 (2026-07-14)

### Feat

- **coverage**: Display coverage summary table on test --coverage success

### Fix

- **conductor**: Apply review suggestions for track 'Show Coverage Summary on Success'
- **coverage**: Inject if_false and elif_true trackers after keyword line
- **conductor**: Apply review suggestions for track 'Fix Match Statement Instrumentation (Option A+)'
- **coverage**: Inject match_case trackers after pattern line, not before

## v0.2.0 (2026-07-14)

### Feat

- **cli**: Multi-path support for lint/format/test commands (FR-4, FR-5, FR-6)
- **coverage**: auto-exclude autoload scripts from coverage plan (FR-2)
- **update-check**: Integrate update notification into CLI invoke
- **update-check**: Implement PyPI update notification module
- **deps**: Add packaging dependency for version comparison

### Fix

- **conductor**: Apply review suggestions for track 'coverage_autoload_fix_20260714'
- **coverage**: Harden _instrument_file against autoload corruption (FR-3)
- **file_discovery**: Implement hybrid path-aware exclude matching
- **conductor**: Apply review suggestions for track 'PyPI update notification when running gd-tools commands'

## v0.1.4 (2026-07-14)

### Fix

- update version tests to assert against dynamic __version__

## v0.1.3 (2026-07-14)

### Fix

- read __version__ dynamically from package metadata

## v0.1.2 (2026-07-14)

### Fix

- reconfigure stdout/stderr to UTF-8 on Windows to prevent Rich crash
- revert L2 _log_summary return type and update format integration test
- remove source_dirs argument from generate_plan call in orchestrator
- remove unused is_gut_installed import in test_test_runner.py

## v0.1.1 (2026-07-13)

### Fix

- resolve 23 audit findings across all severity tiers

## v0.1.0 (2026-07-12)

### Feat

- **ci**: Add CI/CD pipeline with staged gating and release skeleton
- **ci**: Add release.yml skeleton with TestPyPI publish on tag push
- **ci**: Add Stage 2 integration and Stage 3 e2e jobs with Godot installation
- **ci**: Add ci.yml with Stage 1 lint-format-unit and cross-platform matrix
- **coverage**: add integration and E2E tests for coverage CLI
- **coverage**: wire coverage report/merge/show commands to orchestrator
- **coverage**: wire test --coverage to orchestrator
- **coverage**: add orchestrator re-exports to coverage __init__.py
- **coverage**: implement show_coverage_summary orchestrator function
- **coverage**: implement merge_coverage_files orchestrator function
- **coverage**: implement generate_coverage_report orchestrator function
- **coverage**: implement run_coverage_test orchestrator function
- **coverage**: complete coverage env vars in test_runner
- **coverage**: Implement terminal reporter with Rich table and color coding
- **coverage**: Implement HTML reporter with Jinja2 templates and coverage highlighting
- **coverage**: Implement Cobertura XML reporter with valid structure and metrics
- **coverage**: Implement LCOV reporter with valid .info format generation
- **coverage**: Implement report dispatch and threshold check
- **coverage**: Implement coverage metrics computation
- **coverage**: Implement reporter data models and JSON I/O
- **coverage-hooks**: Phase 6 - Performance and edge case tests
- **coverage-hooks**: Phase 5 - Python integration tests (end-to-end, error scenarios, headless)
- **coverage-hooks**: Phase 4 - post_run_hook.gd data collection and output (TDD)
- **coverage-hooks**: Phase 3 - Source instrumentation in pre_run_hook.gd (TDD)
- **coverage-hooks**: Phase 2 - Plan loading in pre_run_hook.gd (TDD)
- **coverage-hooks**: Phase 1 - Project setup (stubs, GUT test fixtures, integration skeleton)
- **coverage**: Add register_coverage_autoload to init.py (Phase 2)
- **coverage**: Implement coverage.gd tracker with GUT tests (Phase 1)
- **coverage**: add fixture generation script
- **coverage**: implement plan generator module
- **doctor**: Add integration tests for doctor command
- **doctor**: Wire CLI doctor command to run_doctor and format_doctor_table
- **doctor**: Add format_doctor_table function with rich table output
- **doctor**: Implement run_doctor() orchestration function
- **doctor**: Add check_autoload for _GDTCoverage autoload verification
- **doctor**: Add check_gd_tools_toml for gd-tools.toml validation
- **doctor**: Add check_gutconfig to validate .gutconfig.json structure
- **doctor**: Add check_coverage_addon diagnostic check
- **doctor**: Add check_gut_version to verify installed GUT version matches expected
- **doctor**: Add check_gut_installed diagnostic check
- **doctor**: Implement check_gdtoolkit check
- **doctor**: Implement check_godot_version check
- **doctor**: Implement check_godot_binary check
- **doctor**: Add doctor module skeleton with CheckResult and DoctorResult dataclasses
- **init**: Wire CLI init command to run_init with TDD
- **init**: Implement run_init with TDD
- **init**: Implement print_summary with TDD
- **init**: Implement create_data_dir with TDD
- **init**: Implement generate_lint_format_rcs with TDD
- **init**: Implement create_config_file with TDD
- **init**: Implement update_gutconfig with TDD
- **init**: Implement install_coverage_addon with TDD
- **init**: Create placeholder coverage addon GDScript files
- **init**: Implement enable_gut_plugin with TDD
- **init**: Implement install_gut with TDD
- **init**: Implement extract_gut with TDD
- **init**: Implement download_gut with TDD
- **init**: Implement get_installed_gut_version with TDD
- **init**: Implement check_gut_installed with TDD
- **init**: Implement detect_godot_version with TDD
- **init**: Create init.py module skeleton with imports and constants
- **cli**: Wire test command to run_tests with all flags
- **test_runner**: Implement Rich terminal output for test results
- **test_runner**: Implement coverage flag infrastructure with GUT hook scripts
- **test_runner**: Implement run_tests orchestration with exit code logic
- **test_runner**: Implement JUnit XML parsing with junitparser
- **test_runner**: Implement GUT installation check with GUTNotInstalledError
- **test_runner**: Implement build_gut_args for GUT CLI construction
- **test_runner**: Define TestResult and TestDetail dataclasses
- **format**: Implement CLI format command with --check and --diff modes
- **format**: Implement FormatResult and run_format function
- **cli**: Wire lint command to run_lint with formatters and exit codes
- **lint**: Implement format_lint_json JSON output
- **lint**: Implement format_lint_text rich table output
- **lint**: Add syntax error handling to run_lint()
- **lint**: Implement run_lint() core logic using gdtoolkit Python API
- **lint**: Implement discover_gd_files() for recursive .gd file discovery
- **lint**: Define LintIssue and LintResult dataclasses
- **godot**: Add run_godot subprocess wrapper
- **godot**: Add GUT version mapping and get_gut_version_for_godot
- **godot**: Add binary detection chain and version helpers
- **godot**: Add GodotInfo dataclass and module skeleton
- **config**: add save_config, generate_gdlintrc, and generate_gdformatrc
- **config**: add find_project_root and load_config
- **config**: Implement Pydantic v2 config models with validation
- **config**: Add pydantic and tomli_w dependencies for config system
- **main**: implement module entry point with GdToolsError handling
- **cli**: implement CLI skeleton with Click group and command stubs
- **errors**: implement exception hierarchy for gd-tools
- **scaffold**: Add package version string with TDD test
- **scaffold**: Create pyproject.toml build configuration
- **spike**: Implement post_run_hook.gd for coverage data serialization
- **spike**: Implement pre_run_hook.gd with _inject_trackers (Green Phase)
- **spike**: Implement tracker.gd with hit/get_hits/reset/is_active (Green Phase)
- **spike**: Implement calculator.gd divide function (Green Phase)

### Fix

- **e2e**: Use production coverage addon, add missing config files for doctor checks
- **test**: Remove untested line from end-to-end coverage plan
- **test**: Use production coverage addon, fix line numbers and env var tests
- **ci**: Correct autoload path from tracker.gd to coverage.gd
- **ci**: Remove -d debug flag, add JUnit XML diagnostics, default timeout
- **ci**: Rich markup error, coverage env var override, Python 3.10 tomllib
- **test**: Set executable bit in test_is_executable_existing_file for Linux CI
- **conductor**: Apply review suggestions for track 'CI/CD Pipeline'
- **conductor**: Apply review suggestions for track 'Test Suite Implementation'
- **conductor**: Apply review suggestions for track 'coverage_cli_20260711'
- **conductor**: Apply review suggestions for track 'coverage_reporter_20260711'
- **conductor**: Apply review suggestions for track 'coverage_hooks_20260711'
- **docs**: Restore deleted Track 11 heading in ROADMAP.md
- **test-runner**: Add --import step, --headless flag, fix GUT exit code handling
- **test**: Integration tests skip condition ignores GODOT_BIN env var
- **conductor**: Apply review suggestions for track 'Coverage Tracker Addon (GDScript)'
- **coverage**: Fix GUT integration test - use filename for -gselect filter
- **conductor**: Apply review suggestions for track 'coverage-plan-generator_20260711'
- **conductor**: Apply review suggestions for track 'doctor_20260711'
- **conductor**: Apply review suggestions for track 'init_20260710'
- **conductor**: Apply review suggestions for track 'test_runner_20260710'
- **conductor**: Apply review suggestions for track 'Format Wrapper'
- **conductor**: Apply review suggestions for track 'lint_wrapper_20260710'
- **config**: Generate gdlintrc in YAML !!set format
- **conductor**: Apply review suggestions for track 'Godot Binary Detection'
- **conductor**: Apply review suggestions for track 'Configuration System'
- **conductor**: Apply review suggestions for track 'Project Scaffolding'
- **conductor**: Apply review suggestions for track 'spike_coverage_20260709'
- **spike**: Hook scripts must extend GutHookScript and use run() method

### Refactor

- **format**: Extract shared file_discovery.py from lint_runner
- **spike**: Add docstrings to pre_run_hook.gd methods
- **spike**: Add docstrings to tracker.gd public methods
