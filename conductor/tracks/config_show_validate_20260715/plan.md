# Track 25: Config Show/Validate — Implementation Plan

## Phase 1: Config Module Extensions (`config.py`)

This phase adds the backend logic to `config.py`: the deprecation registry, deprecation detection, path validation, and config formatting helpers. These are pure functions that the CLI layer (Phase 2) will call.

- [ ] Task: Deprecation Infrastructure
    - [ ] Write unit tests in `tests/unit/test_config.py` for the `DeprecatedField` dataclass, `_DEPRECATED_FIELDS` registry, and `check_deprecated_settings()` function. Test cases: empty registry (no warnings), registry with a deprecated key present in raw TOML, deprecated key absent, multiple deprecated keys, `replacement` is None (no replacement). Use a temporary deprecated field in tests via monkeypatching `_DEPRECATED_FIELDS`.
    - [ ] Implement `DeprecatedField` dataclass (fields: `field_path`, `since_version`, `replacement`, `migration_message`), `_DEPRECATED_FIELDS` dict (empty), and `check_deprecated_settings(raw_toml_data: dict) -> list[DeprecatedField]` in `config.py`. The function traverses the raw TOML dict and checks for any key paths matching entries in `_DEPRECATED_FIELDS`.
    - [ ] Verify: `CI=true pytest tests/unit/test_config.py -k deprecation` passes. `ruff check src/gd_tools/config.py` and `black --check src/gd_tools/config.py` pass.

- [ ] Task: Path Validation
    - [ ] Write unit tests in `tests/unit/test_config.py` for `validate_paths()` function. Test cases: all paths valid (no warnings), `test.test_dirs` with nonexistent dir, `godot.binary` set but missing (and None case — skip), `coverage.output_dir` parent missing, `lint.exclude` / `format.exclude` / `coverage.exclude` with nonexistent dirs. Use `tmp_path` fixtures for real filesystem checks. Paths resolved relative to project root.
    - [ ] Implement `validate_paths(config: GdToolsConfig, project_root: Path) -> list[str]` in `config.py`. Checks: `test.test_dirs` (each dir must exist), `godot.binary` (if not None, file must exist), `coverage.output_dir` (parent dir must exist), `lint.exclude` / `format.exclude` / `coverage.exclude` (each dir must exist). Returns a list of warning message strings.
    - [ ] Verify: `CI=true pytest tests/unit/test_config.py -k path` passes. `ruff check` and `black --check` pass.

- [ ] Task: Config Formatting Helpers
    - [ ] Write unit tests in `tests/unit/test_config.py` for `format_config_table()`, `format_config_toml()`, and `format_config_json()`. Test cases: table contains all 5 sections (godot, test, lint, format, coverage) with key/value pairs, defaults shown when no config file, TOML output is valid TOML (parseable by `tomllib`), JSON output is valid JSON (parseable by `json.loads`), round-trip: `format_config_toml()` → `tomllib.loads()` → `GdToolsConfig()` matches original.
    - [ ] Implement `format_config_table(config: GdToolsConfig) -> Table` (returns Rich `Table` with Section/Key/Value columns), `format_config_toml(config: GdToolsConfig) -> str` (uses `tomli_w.dumps`), and `format_config_json(config: GdToolsConfig) -> str` (uses `json.dumps(config.model_dump())`) in `config.py`.
    - [ ] Verify: `CI=true pytest tests/unit/test_config.py -k format` passes. `ruff check` and `black --check` pass.

- [ ] Task: Conductor - User Manual Verification 'Config Module Extensions' (Protocol in workflow.md)

## Phase 2: CLI Commands (`cli.py`)

This phase adds the `config` command group with `show` and `validate` subcommands, wiring the Phase 1 functions into Click commands.

- [ ] Task: `config` Command Group + `show` Subcommand
    - [ ] Write unit tests in `tests/unit/test_cli_config.py` (new file) using Click's `CliRunner`. Test cases: `config show` prints Rich table with all sections, `config show --format toml` prints valid TOML, `config show --json` prints valid JSON, `config show` with no config file shows defaults, `config show --format toml --json` produces error and exit code 2, exit code 0 on success, exit code 2 on config load error.
    - [ ] Implement `config` command group and `show` subcommand in `cli.py`. The `show` command: loads config via `load_config()`, calls the appropriate formatting helper based on flags (`--format toml` → `format_config_toml()`, `--json` → `format_config_json()`, default → `format_config_table()` printed via Rich `Console`). Enforce mutual exclusion of `--format` and `--json` (Click constraint or manual check → exit 2). Catch `ConfigError` → print error to stderr, exit 2.
    - [ ] Verify: `CI=true pytest tests/unit/test_cli_config.py -k show` passes. `ruff check src/gd_tools/cli.py` and `black --check src/gd_tools/cli.py` pass.

- [ ] Task: `config validate` Subcommand
    - [ ] Write unit tests in `tests/unit/test_cli_config.py` for `config validate`. Test cases: valid config → exit 0, prints summary with config file path and "✓ Configuration is valid"; invalid TOML → exit 1, reports schema error; unknown key → exit 1, reports unknown key with friendly message; nonexistent `test.test_dirs` path → exit 0, prints path warning; nonexistent `godot.binary` → exit 0, prints path warning; nonexistent exclude dir → exit 0, prints path warning; deprecated setting present → exit 1, prints deprecation warning with migration message; no config file → exit 0, prints "using defaults" summary.
    - [ ] Implement `validate` subcommand in `cli.py`. The `validate` command: resolves project root and config file path, reads raw TOML (if file exists) for deprecation check via `check_deprecated_settings()`, attempts `load_config()` for schema validation (catch `ConfigError` → collect schema errors, friendly unknown-key message), if schema valid → call `validate_paths()` for path warnings, prints grouped findings (schema errors, path warnings, deprecation warnings) + summary, exit 0 if no schema errors or deprecated settings (path warnings are non-fatal), exit 1 if schema errors or deprecated settings present.
    - [ ] Verify: `CI=true pytest tests/unit/test_cli_config.py -k validate` passes. `ruff check src/gd_tools/cli.py` and `black --check src/gd_tools/cli.py` pass.

- [ ] Task: Conductor - User Manual Verification 'CLI Commands' (Protocol in workflow.md)
