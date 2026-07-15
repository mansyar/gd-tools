<protect>
# Specification: Standardize Terminal Output

## Overview

The lint, format, test, and coverage commands currently produce inconsistent terminal output. Lint uses `Console().capture()` with `Text` objects and flat line-based text. Format uses plain `click.echo()` with no Rich styling at all. Test uses a `rich.table.Table` directly. Coverage output varies between subcommands. This track standardizes all four commands' terminal output to match their respective ecosystem conventions (lint → ruff/flake8, format → black/prettier, test → pytest/Jest, coverage → `go test -cover`) while enforcing a unified visual language through a shared output module.

## Functional Requirements

### FR-1: Shared Output Module

Create `src/gd_tools/output.py` — a shared utility module providing consistent rendering helpers used by all commands:

- `print_summary(status, counts, files_checked, extra_info)` — renders a standardized summary footer line with color coding (green=pass, red=fail, yellow=warning).
- `print_success(message)` — renders a success message with `[OK]` marker in green.
- `print_error(message)` — renders an error message with `[FAIL]` marker in red.
- `print_warning(message)` — renders a warning message in yellow.
- `print_info(message)` — renders an informational message in cyan.
- `print_table(table)` — wrapper around `console.print(table)` for consistent table rendering.
- A shared `Console` instance (or factory) ensuring consistent terminal detection behavior across commands.

### FR-2: Lint Command Output

- **Detail format:** Keep the existing `file:line:col: rule: message  [ERROR/WARN]` convention (matches ruff/flake8/ESLint).
- **Summary footer:** Use the shared `print_summary()` helper instead of the current inline `Text()` construction.
- **Clean state:** Use shared `print_success()` for the `[OK] No lint issues found.` message.
- **Rich usage:** Replace `Console().capture()` pattern with direct `console.print()` calls via the shared module.
- **JSON mode:** Unchanged — `format_lint_json()` remains as-is.

### FR-3: Format Command Output

- **Detail format:** Minimal, matching black/prettier conventions — list files needing formatting (in `--check` mode), show diffs (in `--diff` mode).
- **Summary footer:** Use shared `print_summary()` for the counts line (e.g., `3 of 5 file(s) need formatting`).
- **Clean state:** Use shared `print_success()` for the "all files formatted" message.
- **Rich usage:** Replace all `click.echo()` calls with Rich-based output from the shared module. File paths in `--check` mode rendered with `dim` style.
- **Diff mode:** Already uses `Syntax` — keep, but route through shared console.

### FR-4: Test Command Output

- **Summary table:** Keep the existing Rich table (Total/Passed/Failed/Skipped/Duration) but render via shared `print_table()`.
- **Per-test details:** Show per-test failure details only when tests fail (pytest-style: quiet on pass, verbose on fail). Failed tests listed with test name, suite, status marker (✗), and failure message.
- **Summary footer:** Add a shared `print_summary()` footer line below the table with pass/fail status.
- **Clean state:** Use shared `print_success()` when all tests pass.
- **GUT stdout/stderr on failure:** Keep existing behavior (truncated to 5000 chars).

### FR-5: Coverage Command Output

- **`coverage show`:** Render as a Rich table with line coverage %, branch coverage %, and color-coded threshold status (green ≥ threshold, red < threshold). Use shared `print_summary()` for the threshold pass/fail footer.
- **`test --coverage` inline summary:** After the test summary table, print a coverage summary line (line %, branch %) using shared `print_info()` / `print_summary()`. Color-coded by threshold.
- **Report command:** Unchanged — just prints the output path.

### FR-6: Unified Color Semantics

All commands enforce the color rules from `product-guidelines.md` §2.1:
- Green = pass / covered / success
- Red = fail / uncovered / error
- Yellow = warning / partial coverage
- Cyan = info / headers
- Dim/gray = secondary info, file paths

### FR-7: Consistent Markers

- Success: `[OK]` in green (ASCII-only, per `product-guidelines.md` §7).
- Failure: `[FAIL]` in red.
- Per-test status: `✓` (pass) / `✗` (fail) / `-` (skip) — text symbols, not emoji.

## Non-Functional Requirements

### NFR-1: Rich Consistency
All user-facing terminal output uses the `rich` library via the shared output module. `click.echo()` is only used for error messages to stderr (config errors, unexpected failures) where Rich markup is unnecessary.

### NFR-2: Accessibility
Color is supplementary, not load-bearing. All information conveyed by color is also conveyed by text (status words, exit codes, markers). Compliant with `product-guidelines.md` §7.

### NFR-3: ASCII-Only
No emoji in CLI output. Use text symbols (`[OK]`, `[FAIL]`, `✓`, `✗`, `-`) per `product-guidelines.md` §7.

### NFR-4: Machine-Readable Output Unaffected
JSON output modes (`--report-format json`, `--junit-xml`) are unchanged. Only human-readable terminal output is standardized.

### NFR-5: No Behavior Changes
Command logic, exit codes, and return values remain unchanged. Only output rendering is modified.

## Acceptance Criteria

1. `src/gd_tools/output.py` exists with shared rendering helpers (`print_summary`, `print_success`, `print_error`, `print_warning`, `print_info`, `print_table`).
2. Lint command uses shared helpers for summary footer and clean-state message; detail format unchanged.
3. Format command uses Rich via shared helpers instead of `click.echo()` for all user-facing output.
4. Test command renders summary table via shared `print_table()`, shows per-test failure details on failure, and includes a summary footer.
5. `coverage show` renders a Rich table with line/branch percentages and threshold status.
6. `test --coverage` prints an inline coverage summary after the test summary.
7. All four commands use consistent color semantics (green/red/yellow/cyan/dim).
8. All four commands use consistent markers (`[OK]`, `[FAIL]`, `✓`, `✗`).
9. JSON output modes are unaffected.
10. All existing tests pass.
11. New unit tests cover the shared output module.
12. Code coverage ≥80% line, ≥70% branch for new/modified source code.

## Out of Scope

- Changes to JSON output format or structure.
- Changes to HTML, LCOV, or Cobertura report formats.
- New CLI flags or command options.
- Changes to command logic, exit codes, or return values.
- Changes to the `coverage report` or `coverage merge` subcommands (only `coverage show` and `test --coverage` inline summary are in scope).
- Changes to `init`, `doctor`, or `config` command output.
</protect>
