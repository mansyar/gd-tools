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
