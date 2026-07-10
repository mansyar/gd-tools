<protect>

# Track: Format Wrapper (format_wrapper_20260710)

## Overview

Implement the `gd-tools format` command, wrapping `gdformat` from the `gdtoolkit` library. The command supports three modes: default (format in place), `--check` (report unformatted files without modifying, exit 1 if any need formatting), and `--diff` (show unified diffs of what would change without modifying). This track also extracts shared file discovery logic from `lint_runner.py` into a reusable `file_discovery.py` module.

## Dependencies

- **Track 2 (Config)** — COMPLETED. Provides `FormatConfig` with `exclude` list, `generate_gdformatrc()`, and `GdToolsConfig` model.
- **Track 1 (Scaffolding)** — COMPLETED. Provides `FormatError` exception class and `format` CLI command stub (currently raises `NotImplementedError`).
- **Track 4 (Lint Wrapper)** — COMPLETED. Provides `discover_gd_files()` in `lint_runner.py` to be extracted into shared module.

## Functional Requirements

### FR-1: Shared File Discovery Module

1. Extract `discover_gd_files()` from `lint_runner.py` into a new `src/gd_tools/file_discovery.py` module.
2. The function discovers `.gd` files under a given path, applying exclude patterns from the config.
3. Update `lint_runner.py` to import `discover_gd_files` from `file_discovery.py` instead of defining it locally.
4. No behavioral changes to existing lint functionality — this is a pure refactor.

### FR-2: FormatResult Dataclass

1. Define `FormatResult` dataclass in `format_runner.py` with fields:
   - `files_checked: int` — total number of `.gd` files examined.
   - `files_formatted: int` — number of files actually formatted (default mode only).
   - `files_needing_format: int` — number of files that need formatting (set in `--check` mode).
   - `diffs: list[str]` — list of unified diff strings (set in `--diff` mode).

### FR-3: run_format Function

1. Signature: `run_format(config: GdToolsConfig, path: str = '.', check: bool = False, diff: bool = False) -> FormatResult`
2. Uses `discover_gd_files()` from `file_discovery.py` to enumerate `.gd` files, respecting exclude patterns.
3. Invokes `gdformat` via the `gdtoolkit` Python API (not subprocess), consistent with how `run_lint()` uses `gdtoolkit.linter.lint_code()`.
4. **Default mode** (check=False, diff=False): Format files in place. Return `FormatResult` with `files_formatted` count.
5. **--check mode** (check=True): Report which files need formatting without modifying. Return `FormatResult` with `files_needing_format` count. Raise `FormatError` (exit 1) if any files need formatting.
6. **--diff mode** (diff=True): Show unified diffs of what would change without modifying. Return `FormatResult` with `diffs` list populated.
7. **Mutual exclusion**: If both `check=True` and `diff=True`, raise `FormatError` with message "--check and --diff are mutually exclusive" and exit code 2.
8. **Syntax error handling**: If a `.gd` file has a syntax error (gdformat/gdtoolkit raises a parse exception), catch it and report a clear error message. Do not crash. Report the file path and error description.
9. **No files found**: If no `.gd` files are discovered, return `FormatResult` with all counts at 0 and empty diffs. Print a graceful message. Exit 0.

### FR-4: CLI Format Command

1. Implement the `format` command in `cli.py` (replacing the existing `NotImplementedError` stub).
2. Arguments: `path` (optional, default `'.'`).
3. Options: `--check` (is_flag, CI mode), `--diff` (is_flag, show diff).
4. If both `--check` and `--diff` are passed, print error message and exit with code 2.
5. Call `run_format(config, path, check, diff)` and render the result.
6. **Default mode output**: Print summary (e.g., "Formatted N file(s).").
7. **--check output**: Print list of files needing formatting. Exit 1 if any need formatting, exit 0 otherwise.
8. **--diff output**: Render unified diffs using rich Console with syntax highlighting (green for additions, red for deletions). Prefix each diff block with the file path.
9. **Exit codes**: 0 (success/no changes needed), 1 (files need formatting in --check mode), 2 (usage error).

### FR-5: gdformatrc Integration

1. `generate_gdformatrc()` (already implemented in Track 2) generates `gdformatrc` from `[format]` exclude list in `gd-tools.toml`.
2. `gd-tools init` already calls `generate_gdformatrc()` — verify it works correctly with the format runner.
3. No changes to `generate_gdformatrc()` are expected unless testing reveals issues.

## Non-Functional Requirements

1. **Test Coverage**: >80% line coverage, >70% branch coverage for `format_runner.py` and `file_discovery.py`.
2. **Code Quality**: Type hints on all functions, docstrings on all public functions/classes, ruff and black compliant.
3. **TDD**: All implementation follows Red-Green-Refactor. Tests written first.
4. **Consistency**: Code style and patterns consistent with `lint_runner.py` (Track 4).

## Acceptance Criteria

1. **AC-1**: Already-formatted files — `gd-tools format --check` exits 0, reports no files needing formatting.
2. **AC-2**: Unformatted files — `gd-tools format --check` exits 1, lists files needing formatting.
3. **AC-3**: Default mode — `gd-tools format` formats files in place, reports count of formatted files.
4. **AC-4**: `gd-tools format --diff` shows correct unified diffs with file path headers.
5. **AC-5**: `addons/` directory excluded by default (via config exclude list).
6. **AC-6**: Syntax-error files produce a clear error message with file path, do not crash the tool.
7. **AC-7**: `--check` and `--diff` simultaneously — error message printed, exit code 2.
8. **AC-8**: No `.gd` files found — graceful message, exit 0.
9. **AC-9**: `gdformatrc` generated by `gd-tools init` makes `gdformat` work standalone.
10. **AC-10**: `file_discovery.py` extracted, `lint_runner.py` updated to import from it, all existing lint tests still pass.

## Out of Scope

- Configuration of gdformat formatting rules (line length, indent style, etc.) — gdformat uses its own defaults.
- Recursive project-wide format-on-save hooks for editors.
- Integration with git pre-commit hooks.
- Changes to `generate_gdformatrc()` implementation (already done in Track 2).
- Watch mode or auto-format on file change.

</protect>
