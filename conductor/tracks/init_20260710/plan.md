<protect>
# Track 7: Init Command — Implementation Plan

## Phase 1: Project Detection and Godot Version Detection [checkpoint: c2718a2]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/init_20260710/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Set up `init.py` module skeleton and import reusable functions (1af60d5)
    - [x] Create `src/gd_tools/init.py` with module docstring
    - [x] Import `find_project_root` from `config` (reuse, no new implementation)
    - [x] Import `load_config`, `save_config`, `generate_gdlintrc`, `generate_gdformatrc` from `config`
    - [x] Import `find_godot`, `get_gut_version_for_godot`, `GodotInfo` from `godot`
    - [x] Import `ConfigError`, `GodotNotFoundError`, `GdToolsError` from `errors`
    - [x] Define `GUTCONFIG_TEMPLATE` constant and `GUT_DOWNLOAD_URL` constant
    - [x] Run `ruff check src/gd_tools/init.py` — verify no import errors

- [x] Task: Implement `detect_godot_version(config: GdToolsConfig) -> str` (26f30a7)
    - [x] Write failing tests: `test_detect_godot_version_returns_version`, `test_detect_godot_version_raises_godot_not_found`, `test_detect_godot_version_warns_if_invalid_version`
    - [x] Implement `detect_godot_version()` — call `find_godot(config.godot)`, return `GodotInfo.version`, warn if `is_valid` is False
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check` on modified files

- [x] Task: Conductor - User Manual Verification 'Phase 1: Project Detection and Godot Version Detection' (Protocol in workflow.md)

## Phase 2: GUT Installation [checkpoint: d239f38]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/init_20260710/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Implement `check_gut_installed(project_root: Path) -> bool` (714164c)
    - [ ] Write failing tests: `test_check_gut_installed_returns_true_when_present`, `test_check_gut_installed_returns_false_when_absent`
    - [ ] Implement `check_gut_installed()` — check if `project_root/addons/gut/gut.gd` exists
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `get_installed_gut_version(project_root: Path) -> str | None` (d31d908)
    - [ ] Write failing tests: `test_get_installed_gut_version_reads_plugin_cfg`, `test_get_installed_gut_version_returns_none_if_no_cfg`
    - [ ] Implement `get_installed_gut_version()` — parse `addons/gut/plugin.cfg` for `version` key
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `download_gut(version: str, dest: Path) -> Path` (6abbefc)
    - [x] Write failing tests: `test_download_gut_downloads_zip`, `test_download_gut_fails_with_instructions_on_network_error`
    - [x] Implement `download_gut()` — `requests.get(GUT_DOWNLOAD_URL.format(version=version))`, save to `dest`, raise actionable error on failure with manual install instructions
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check`

- [x] Task: Implement `extract_gut(zip_path: Path, project_root: Path) -> None`
    - [x] Write failing tests: `test_extract_gut_copies_addons_dir`, `test_extract_gut_cleans_up_temp_dir`
    - [x] Implement `extract_gut()` — `zipfile.ZipFile.extractall` to temp dir, copy `addons/gut/` to `project_root/addons/gut/`, clean up temp
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check`

- [x] Task: Implement `install_gut(project_root: Path, godot_version: str, non_interactive: bool) -> None`
    - [x] Write failing tests: `test_install_gut_prompts_interactive_yes`, `test_install_gut_non_interactive_assumes_yes`, `test_install_gut_user_declines_prints_manual_instructions`, `test_install_gut_version_mismatch_warning`
    - [x] Implement `install_gut()` — prompt logic (interactive Y/n), call `download_gut()` + `extract_gut()`, or print manual instructions. Check installed GUT version vs expected, warn if mismatch.
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check`

- [x] Task: Implement `enable_gut_plugin(project_root: Path) -> None`
    - [x] Write failing tests: `test_enable_gut_plugin_adds_section_to_empty_file`, `test_enable_gut_plugin_adds_entry_to_existing_section`, `test_enable_gut_plugin_idempotent_no_duplicate`, `test_enable_gut_plugin_preserves_existing_content`
    - [x] Implement `enable_gut_plugin()` — text-based parse of `project.godot`, add `[editor_plugins]` with `enabled=PackedStringArray("res://addons/gut/plugin.gd")` if not present. Idempotent.
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check`

- [x] Task: Conductor - User Manual Verification 'Phase 2: GUT Installation' (Protocol in workflow.md)

## Phase 3: Coverage Addon Deployment [checkpoint: e78d25c]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/init_20260710/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Create placeholder GDScript files as package data
    - [x] Create `src/gd_tools/addons/gd-tools-coverage/coverage.gd` — `extends Node`, TODO comment for Phase 3
    - [x] Create `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd` — `extends GutHookScript`, TODO comment
    - [x] Create `src/gd_tools/addons/gd-tools-coverage/post_run_hook.gd` — `extends GutHookScript`, TODO comment
    - [x] Update `pyproject.toml` to include addon `.gd` files as package data
    - [x] Verify `pip install -e .` includes the addon files

- [x] Task: Implement `install_coverage_addon(project_root: Path) -> None`
    - [x] Write failing tests: `test_install_coverage_addon_copies_all_files`, `test_install_coverage_addon_overwrites_stale_files`, `test_install_coverage_addon_creates_target_dir`
    - [x] Implement `install_coverage_addon()` — copy bundled `.gd` files from package data to `project_root/addons/gd-tools-coverage/`. Always overwrite.
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check`

- [x] Task: Conductor - User Manual Verification 'Phase 3: Coverage Addon Deployment' (Protocol in workflow.md)

## Phase 4: Configuration File Generation [checkpoint: 2627f98]

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/init_20260710/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Implement `update_gutconfig(project_root: Path, config: GdToolsConfig) -> None`
    - [ ] Write failing tests: `test_update_gutconfig_creates_new_with_template`, `test_update_gutconfig_merges_existing_preserves_user_keys`, `test_update_gutconfig_overwrites_hook_keys`, `test_update_gutconfig_preserves_custom_dirs`
    - [ ] Implement `update_gutconfig()` — if no `.gutconfig.json`, write `GUTCONFIG_TEMPLATE`. If exists, merge: preserve `dirs`, `prefix`, `suffix`, `include_subdirs`; always set `pre_run_script`, `post_run_script`, `junit_xml_file`, `should_exit`.
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement `create_config_file(project_root: Path, config: GdToolsConfig) -> None`
    - [ ] Write failing tests: `test_create_config_file_creates_defaults_if_missing`, `test_create_config_file_preserves_existing`
    - [ ] Implement `create_config_file()` — if `gd-tools.toml` exists, return (preserve). If not, call `save_config(config, project_root)`.
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Implement lint/format RC generation with "generate if missing, warn if differs" policy
    - [ ] Write failing tests: `test_generate_rcs_generates_if_missing`, `test_generate_rcs_warns_if_differs`, `test_generate_rcs_skips_if_matches`
    - [ ] Implement `generate_lint_format_rcs(project_root, config)` — for each of `gdlintrc` and `gdformatrc`: generate expected content, if file missing write it, if exists and differs print warning, if matches do nothing
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [x] Task: Conductor - User Manual Verification 'Phase 4: Configuration File Generation' (Protocol in workflow.md)

## Phase 5: Data Directory, Summary, and Orchestration

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/init_20260710/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [x] Task: Implement `create_data_dir(project_root: Path) -> None`
    - [x] Write failing tests: `test_create_data_dir_creates_directory`, `test_create_data_dir_adds_to_gitignore`, `test_create_data_dir_gitignore_idempotent`, `test_create_data_dir_creates_gitignore_if_missing`
    - [x] Implement `create_data_dir()` — `mkdir(exist_ok=True)` for `.gd-tools/`, append `.gd-tools/` to `.gitignore` if not present (create `.gitignore` if missing)
    - [x] Verify coverage >80% line, >70% branch
    - [x] Run `ruff check` and `black --check`

- [ ] Task: Implement `print_summary(project_root: Path, actions: list[str]) -> None`
    - [ ] Write failing tests: `test_print_summary_lists_actions`, `test_print_summary_prints_next_steps`
    - [ ] Implement `print_summary()` — Rich-formatted output, list all actions taken, print next steps (e.g., "Run `gd-tools test` to execute tests")
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [ ] Task: Implement `run_init(non_interactive: bool = False) -> None`
    - [ ] Write failing tests: `test_run_init_full_flow_with_mocks`, `test_run_init_non_interactive_skips_prompts`, `test_run_init_collects_actions_list`
    - [ ] Implement `run_init()` — orchestrate: find_project_root → load_config → detect_godot_version → get_gut_version → check_gut_installed → install_gut (if needed) → enable_gut_plugin → install_coverage_addon → update_gutconfig → create_config_file → generate_lint_format_rcs → create_data_dir → print_summary
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [ ] Task: Wire CLI `init` command to `run_init()`
    - [ ] Write failing tests: `test_cli_init_calls_run_init`, `test_cli_init_passes_non_interactive_flag`, `test_cli_init_exits_zero_on_success`
    - [ ] Implement — replace `raise NotImplementedError` with `run_init(non_interactive)`, add error handling (catch `GdToolsError`, exit with `e.exit_code`)
    - [ ] Verify coverage >80% line, >70% branch
    - [ ] Run `ruff check` and `black --check`

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Data Directory, Summary, and Orchestration' (Protocol in workflow.md)

## Phase 6: Integration Tests

- [x] Task: Read `spec.md` and `workflow.md` to align implementation with requirements and TDD protocol
    - [x] Read `conductor/tracks/init_20260710/spec.md` for functional requirements, acceptance criteria, and constraints
    - [x] Read `conductor/workflow.md` for TDD lifecycle (Red → Green → Refactor), coverage thresholds, and commit conventions

- [ ] Task: Write integration tests for full init flow
    - [ ] Write `test_init_fresh_project` — full flow on a clean `tmp_path` with mocked Godot/GUT download, verify all artifacts created
    - [ ] Write `test_init_project_with_existing_gut` — GUT already installed, verify no download attempt, plugin still enabled
    - [ ] Write `test_init_idempotent` — run init twice, verify no duplicate entries in any file
    - [ ] Run full test suite (`CI=true pytest`), verify all pass and overall coverage thresholds still met
    - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/`

- [ ] Task: Conductor - User Manual Verification 'Phase 6: Integration Tests' (Protocol in workflow.md)
</protect>
