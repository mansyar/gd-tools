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

## Phase 2: Pydantic Configuration Models — TDD

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
- [~] Task: Conductor - User Manual Verification 'Phase 2: Pydantic Configuration Models' (Protocol in workflow.md)

## Phase 3: Config Discovery & Loading — TDD

- [ ] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [ ] Task: Write unit tests for `find_project_root` (Red)
    - [ ] Test: finds `project.godot` in CWD
    - [ ] Test: walks up directory tree to find `project.godot` in parent
    - [ ] Test: raises `ConfigError` when `project.godot` not found
    - [ ] Test: uses custom start path when provided
- [ ] Task: Write unit tests for `load_config` (Red)
    - [ ] Test: loads valid `gd-tools.toml` with all sections → correct typed `GdToolsConfig`
    - [ ] Test: loads valid `gd-tools.toml` with partial sections → defaults for missing sections
    - [ ] Test: missing `gd-tools.toml` → returns `GdToolsConfig()` defaults (no error)
    - [ ] Test: invalid TOML syntax → raises `ConfigError` with file path
    - [ ] Test: invalid `min_percent` (negative) → raises `ConfigError`
    - [ ] Test: invalid `format` value → raises `ConfigError`
    - [ ] Test: unknown TOML key → raises `ConfigError` (extra='forbid')
    - [ ] Test: exclude list present in TOML → uses TOML value (replace semantics)
    - [ ] Test: exclude list absent in TOML → uses `DEFAULT_EXCLUDES`
- [ ] Task: Implement `find_project_root` (Green)
    - [ ] Implement walk-up logic from start path (default: `Path.cwd()`)
    - [ ] Check for `project.godot` at each directory level
    - [ ] Raise `ConfigError` if not found at filesystem root
- [ ] Task: Implement `load_config` (Green)
    - [ ] Implement TOML parsing with `tomllib`/`tomli` conditional import
    - [ ] Read `gd-tools.toml` from project root
    - [ ] Handle missing file → return `GdToolsConfig()` defaults
    - [ ] Catch TOML parse errors → raise `ConfigError` with file path
    - [ ] Catch Pydantic `ValidationError` → raise `ConfigError` with field details
- [ ] Task: Verify tests pass (Green check)
    - [ ] Run `CI=true pytest tests/unit/test_config.py -v`
    - [ ] Confirm all discovery and loading tests pass
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Config Discovery & Loading' (Protocol in workflow.md)

## Phase 4: Serialization & RC Generation — TDD

- [ ] Task: Read spec.md and workflow.md to review requirements and workflow rules
- [ ] Task: Write unit tests for `save_config` (Red)
    - [ ] Test: writes valid TOML file from `GdToolsConfig`
    - [ ] Test: round-trip — `save_config` then `load_config` returns equivalent config
    - [ ] Test: writes to specified `project_root` path
- [ ] Task: Write unit tests for `generate_gdlintrc` (Red)
    - [ ] Test: generates gdlintrc file from `[lint]` exclude list
    - [ ] Test: overwrites existing gdlintrc file
    - [ ] Test: writes to project root directory
- [ ] Task: Write unit tests for `generate_gdformatrc` (Red)
    - [ ] Test: generates gdformatrc file from `[format]` exclude list
    - [ ] Test: overwrites existing gdformatrc file
    - [ ] Test: writes to project root directory
- [ ] Task: Implement `save_config` (Green)
    - [ ] Convert `GdToolsConfig` to dict via `model_dump()`
    - [ ] Use `tomli_w` to write TOML to `gd-tools.toml` in project root
- [ ] Task: Implement `generate_gdlintrc` (Green)
    - [ ] Read `[lint]` exclude list from config
    - [ ] Write gdlintrc file to project root
- [ ] Task: Implement `generate_gdformatrc` (Green)
    - [ ] Read `[format]` exclude list from config
    - [ ] Write gdformatrc file to project root
- [ ] Task: Verify tests pass (Green check)
    - [ ] Run `CI=true pytest tests/unit/test_config.py -v`
    - [ ] Confirm all serialization and generation tests pass
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
