<protect>
# Track 2: Configuration System — Implementation Plan

## Phase 1: Dependencies & Project Setup [checkpoint: c0e5752]

- [x] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [x] Task: Add pydantic and tomli_w to pyproject.toml [bd09525]
    - [x] Add `pydantic >= 2.0` to `[project] dependencies`
    - [x] Add `tomli_w` to `[project] dependencies`
    - [x] Verify pyproject.toml is valid
- [x] Task: Update conductor/tech-stack.md with new dependencies [bd09525]
    - [x] Document pydantic v2 addition and rationale (TDD §3.2 specifies Pydantic models)
    - [x] Document tomli_w addition (TOML writer for `save_config`)
- [x] Task: Install new dependencies [bd09525]
    - [x] Run `pip install -e ".[dev]"` to install pydantic and tomli_w
    - [x] Verify imports work (`python -c "import pydantic; import tomli_w"`)
- [x] Task: Conductor - User Manual Verification 'Phase 1: Dependencies & Project Setup' (Protocol in workflow.md) [c0e5752]

## Phase 2: Pydantic Configuration Models — TDD [checkpoint: ffb6404]

- [x] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [x] Task: Write unit tests for Pydantic models (Red)
    - [x] Test `GodotConfig` default (`binary=None`)
    - [x] Test `TestConfig` defaults (`test_dirs`, `prefix`, `suffix`, `gutconfig`)
    - [x] Test `LintConfig` defaults (`exclude=DEFAULT_EXCLUDES`)
    - [x] Test `FormatConfig` defaults (`exclude=DEFAULT_EXCLUDES`)
    - [x] Test `CoverageConfig` defaults (`enabled`, `min_percent`, `format`, `output_dir`, `exclude`, `test_dirs`)
    - [x] Test `GdToolsConfig` defaults (all sections present with defaults)
    - [x] Test `GdToolsConfig` coverage validator: valid format values (html, lcov, cobertura, text)
    - [x] Test `GdToolsConfig` coverage validator: invalid format raises `ValidationError`
    - [x] Test `GdToolsConfig` coverage validator: `min_percent` out of range raises `ValidationError`
    - [x] Test `extra='forbid'`: unknown key in any section raises `ValidationError`
    - [x] Test mutability: fields can be updated after creation (for CLI overrides)
- [x] Task: Implement Pydantic models (Green) [ff15c1a]
    - [x] Define `DEFAULT_EXCLUDES` constant
    - [x] Implement `GodotConfig(BaseModel)` with `extra='forbid'`
    - [x] Implement `TestConfig(BaseModel)` with `extra='forbid'`
    - [x] Implement `LintConfig(BaseModel)` with `extra='forbid'`
    - [x] Implement `FormatConfig(BaseModel)` with `extra='forbid'`
    - [x] Implement `CoverageConfig(BaseModel)` with `extra='forbid'`
    - [x] Implement `GdToolsConfig(BaseModel)` with `field_validator` on coverage and `extra='forbid'`
    - [x] Verify models are mutable (Pydantic v2 default)
- [x] Task: Verify tests pass (Green check) [ff15c1a]
    - [x] Run `CI=true pytest tests/unit/test_config.py -v`
    - [x] Confirm all model tests pass
- [x] Task: Conductor - User Manual Verification 'Phase 2: Pydantic Configuration Models' (Protocol in workflow.md) [ffb6404]

## Phase 3: Config Discovery & Loading — TDD [checkpoint: a5f65b7]

- [x] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [x] Task: Write unit tests for `find_project_root` (Red) [6c54a60]
    - [x] Test: finds `project.godot` in CWD
    - [x] Test: walks up directory tree to find `project.godot` in parent
    - [x] Test: raises `ConfigError` when `project.godot` not found
    - [x] Test: uses custom start path when provided
- [x] Task: Write unit tests for `load_config` (Red) [6c54a60]
    - [x] Test: loads valid `gd-tools.toml` with all sections → correct typed `GdToolsConfig`
    - [x] Test: loads valid `gd-tools.toml` with partial sections → defaults for missing sections
    - [x] Test: missing `gd-tools.toml` → returns `GdToolsConfig()` defaults (no error)
    - [x] Test: invalid TOML syntax → raises `ConfigError` with file path
    - [x] Test: invalid `min_percent` (negative) → raises `ConfigError`
    - [x] Test: invalid `format` value → raises `ConfigError`
    - [x] Test: unknown TOML key → raises `ConfigError` (extra='forbid')
    - [x] Test: exclude list present in TOML → uses TOML value (replace semantics)
    - [x] Test: exclude list absent in TOML → uses `DEFAULT_EXCLUDES`
- [x] Task: Implement `find_project_root` (Green) [6c54a60]
    - [x] Implement walk-up logic from start path (default: `Path.cwd()`)
    - [x] Check for `project.godot` at each directory level
    - [x] Raise `ConfigError` if not found at filesystem root
- [x] Task: Implement `load_config` (Green) [6c54a60]
    - [x] Implement TOML parsing with `tomllib`/`tomli` conditional import
    - [x] Read `gd-tools.toml` from project root
    - [x] Handle missing file → return `GdToolsConfig()` defaults
    - [x] Catch TOML parse errors → raise `ConfigError` with file path
    - [x] Catch Pydantic `ValidationError` → raise `ConfigError` with field details
- [x] Task: Verify tests pass (Green check) [6c54a60]
    - [x] Run `CI=true pytest tests/unit/test_config.py -v`
    - [x] Confirm all discovery and loading tests pass
- [x] Task: Conductor - User Manual Verification 'Phase 3: Config Discovery & Loading' (Protocol in workflow.md) [a5f65b7]

## Phase 4: Serialization & RC Generation — TDD

- [x] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [x] Task: Write unit tests for `save_config` (Red) [bef7cd5]
    - [x] Test: writes valid TOML file from `GdToolsConfig`
    - [x] Test: round-trip — `save_config` then `load_config` returns equivalent config
    - [x] Test: writes to specified `project_root` path
- [x] Task: Write unit tests for `generate_gdlintrc` (Red) [bef7cd5]
    - [x] Test: generates gdlintrc file from `[lint]` exclude list
    - [x] Test: overwrites existing gdlintrc file
    - [x] Test: writes to project root directory
- [x] Task: Write unit tests for `generate_gdformatrc` (Red) [bef7cd5]
    - [x] Test: generates gdformatrc file from `[format]` exclude list
    - [x] Test: overwrites existing gdformatrc file
    - [x] Test: writes to project root directory
- [x] Task: Implement `save_config` (Green) [bef7cd5]
    - [x] Convert `GdToolsConfig` to dict via `model_dump(exclude_none=True)`
    - [x] Use `tomli_w` to write TOML to `gd-tools.toml` in project root
- [x] Task: Implement `generate_gdlintrc` (Green) [bef7cd5]
    - [x] Read `[lint]` exclude list from config
    - [x] Write gdlintrc file to project root
- [x] Task: Implement `generate_gdformatrc` (Green) [bef7cd5]
    - [x] Read `[format]` exclude list from config
    - [x] Write gdformatrc file to project root
- [x] Task: Verify tests pass (Green check) [bef7cd5]
    - [x] Run `CI=true pytest tests/unit/test_config.py -v`
    - [x] Confirm all serialization and generation tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Serialization & RC Generation' (Protocol in workflow.md)

## Phase 5: Finalization & Quality Gates

- [ ] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [ ] Task: Verify test coverage
    - [ ] Run `CI=true pytest --cov=gd_tools.config --cov-report=term-missing tests/unit/test_config.py`
    - [ ] Confirm >80% line coverage for `config.py`
    - [ ] Confirm >70% branch coverage for `config.py`
- [ ] Task: Run code quality checks
    - [ ] Run `ruff check src/gd_tools/config.py tests/unit/test_config.py`
    - [ ] Run `black --check src/gd_tools/config.py tests/unit/test_config.py`
    - [ ] Fix any issues found
- [ ] Task: Run full test suite
    - [ ] Run `CI=true pytest` to ensure no regressions
    - [ ] Confirm all existing tests still pass
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Finalization & Quality Gates' (Protocol in workflow.md)
</protect>
