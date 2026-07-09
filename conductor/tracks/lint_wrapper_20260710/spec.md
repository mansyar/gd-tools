# Track 4: Lint Wrapper — Specification

## Overview

Wrap `gdlint` (via the gdtoolkit Python API) with config-driven excludes and clean, formatted output. The lint runner discovers `.gd` files, invokes gdlint programmatically, collects issues into structured dataclasses, and renders results as either a rich terminal table or JSON. Exit codes follow convention: 0 for clean, 1 for lint errors, 2 for config/environment errors.

This track also fixes the existing `generate_gdlintrc()` function in `config.py`, which currently writes plain text instead of the YAML set format that gdtoolkit expects.

## Functional Requirements

### FR-1: gdlint Invocation via Python API

The lint runner must import and call gdtoolkit's lint functions directly from Python (not via subprocess). This matches the ROADMAP directive and avoids shell overhead.

**Signature (per TDD.md §3.8):**
```python
def run_lint(config: GdToolsConfig, path: str = ".", report_format: str = "text") -> LintResult:
    """Run gdlint on path, respecting excludes."""
```

### FR-2: File Discovery

The lint runner must discover `.gd` files by recursively walking the given path:
- Collect all files with `.gd` extension (case-insensitive: `.gd`, `.GD`, `.Gd`)
- Skip directories whose names appear in the config's exclude list (matched by directory name, not full path)
- Default excludes: `addons`, `.godot`, `.gd-tools`, `.git` (from `DEFAULT_EXCLUDES` in `config.py`)

File discovery is implemented in Python within `lint_runner.py` (not delegated to gdlint's built-in exclude mechanism).

### FR-3a: Terminal Output (Rich Table)

When `report_format="text"`, results are rendered using `rich.table.Table`:
- **Columns:** File, Line, Column, Rule, Severity, Message
- **Color coding:** Red for errors, yellow for warnings
- **Summary line:** "X errors, Y warnings, Z files checked"
- **Clean files:** Success message (e.g., "[OK] No lint issues found.")
- **No .gd files:** Informational message "No GDScript files found."

### FR-3b: JSON Output

When `report_format="json"`, results are serialized to a JSON string mirroring the `LintResult` dataclass:
```json
{
  "files_checked": 5,
  "errors": [
    {"file": "res://foo.gd", "line": 10, "column": 1, "rule": "SOME_RULE", "message": "...", "severity": "error"}
  ],
  "warnings": []
}
```
Empty arrays are `[]`, not `null`.

### FR-4: Exit Codes

| Condition | Exit Code |
|-----------|-----------|
| Clean (no errors, no warnings, or no .gd files) | 0 |
| One or more lint errors (severity=error) | 1 |
| Config/environment error (e.g., project root not found) | 2 |

Warnings alone do NOT cause a non-zero exit code.

### FR-5: Syntax Error Handling

If a `.gd` file has a syntax error that prevents gdlint from parsing it:
- Catch the parse error per-file (must NOT crash the runner)
- Report it as a `LintIssue` with `rule="SYNTAX_ERROR"`, `severity="error"`
- Continue linting remaining files
- Exit code 1 (syntax errors count as errors)

### FR-6: CLI Alignment

The `lint` command in `cli.py` must be updated to match the PRD interface:
- `path` argument: `required=False, default="."`
- `--report-format` option: `click.Choice(["text", "json"])`, `default="text"`
- `--fix` flag: no-op boolean flag that prints a warning ("gdlint is read-only; --fix has no effect")
- Command wired end-to-end: loads config, calls `run_lint()`, formats output, sets exit code

### FR-7: Fix `generate_gdlintrc()` to YAML Set Format

The existing `generate_gdlintrc()` in `config.py` currently writes plain text (one path per line). It must output the YAML set format that gdtoolkit expects:
```yaml
excluded_directories: !!set { .git: null, addons: null, .godot: null, .gd-tools: null }
```

## Data Models

```python
@dataclass
class LintIssue:
    file: str
    line: int
    column: int
    rule: str
    message: str
    severity: str  # "error" | "warning"

@dataclass
class LintResult:
    files_checked: int
    errors: list[LintIssue]
    warnings: list[LintIssue]
```

## Acceptance Criteria

1. **AC-1:** Running `gd-tools lint` on a project with clean `.gd` files exits 0 and displays a success message.
2. **AC-2:** Running `gd-tools lint` on a project with lint violations exits 1 and displays a rich table with file, line, column, rule, severity, and message for each violation.
3. **AC-3:** Files in excluded directories (e.g., `addons/`, `.godot/`) are NOT linted, even if they contain `.gd` files.
4. **AC-4:** Running `gd-tools lint --report-format json` produces valid JSON with `files_checked`, `errors`, and `warnings` keys.
5. **AC-5:** A `.gd` file with syntax errors is reported (rule=SYNTAX_ERROR, severity=error) without crashing the runner; other files are still linted.
6. **AC-6:** Running `gd-tools lint` in a directory with no `.gd` files exits 0 with the message "No GDScript files found."
7. **AC-7:** `generate_gdlintrc()` produces a YAML file with `excluded_directories: !!set { ... }` format that is valid and parseable.
8. **AC-8:** The `--fix` flag is accepted but prints a warning that gdlint is read-only and does not modify files.
9. **AC-9:** Config/environment errors (e.g., no `project.godot` found) exit with code 2.

## Out of Scope

- `init` command (gdlintrc generation via CLI is a separate track)
- Shared `file_discovery.py` module (discovery is local to `lint_runner.py` for this track)
- Actual `--fix` implementation (gdlint is read-only; flag is a no-op placeholder)
- End-to-end (E2E) tests
- Rule configuration/overrides (custom rule enabling/disabling)
- `generate_gdformatrc()` fix (same pattern but out of scope for this track)
