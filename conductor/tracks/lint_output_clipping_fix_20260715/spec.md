# Track 24.6: Lint Output Clipping Fix

## Overview

Replace the Rich `Table` in `format_lint_text` with a flat, line-based `file:line:col: rule message [SEVERITY]` format to eliminate file path and rule name truncation. The current 6-column Rich Table, rendered with `Console(force_terminal=True)`, defaults to a 79-character width in non-interactive contexts (piped output, CI), causing silent truncation of long file paths and rule names with ellipsis (`…`).

**Track Type:** Bug Fix (UX)
**Phase:** Hotfix
**Effort:** 0.5 day
**Risk:** LOW
**Dependencies:** Track 4 (lint)

## Problem Statement

The `format_lint_text` function renders lint results as a Rich `Table` with 6 columns (File, Line, Column, Rule, Severity, Message). The `Console(force_terminal=True)` call defaults to a width of 79 characters when terminal width cannot be detected (piped output, CI, non-interactive contexts). With 6 columns competing for 79 characters, the File column receives only ~16 characters of usable width.

When file paths or rule names exceed the column width and cannot be wrapped (no spaces to break on), Rich truncates them with an ellipsis (`…`), causing **silent data loss**. The user cannot see the full file path or rule name, making it difficult to locate and fix lint issues.

Quantified clipping at default width 79:
- File path `src/very/deeply/nested/module/subsystem/components/PlayerCharacterController.gd` (76 chars) → truncated to ~20 chars visible
- Rule name `class-name-underscore-prefix-violation-detailed-check` (52 chars) → truncated to ~30 chars visible

The integration test at `tests/integration/test_lint_integration.py:53` already acknowledges this with a comment: `# Rich table may truncate long messages, so check a short fragment`.

## Root Cause

Tables are fundamentally unsuited for variable-length data like file paths and lint messages. No amount of column tuning (wider width, `overflow="fold"`, `ratio` weights, `no_wrap` settings) fully solves this — it only shifts where truncation occurs. A 76-character file path folded into a 16-character column produces unreadable output.

## Solution: Flat Line-Based Format

Replace the Rich `Table` with a flat `file:line:col: rule: message [SEVERITY]` format, matching the convention used by ESLint, Ruff, flake8, pylint, mypy, rust-clippy, golangci-lint, GCC, and Clang.

**Example output:**
```
src/player/PlayerCharacterController.gd:10:1: function-name: Function name BadFunctionName is not valid  [ERROR]
src/enemy.gd:5:3: some-rule: Warning message  [WARN]

1 errors, 1 warnings, 2 files checked
```

**Benefits:**
- Zero data loss at any terminal width — content wraps naturally at the terminal boundary, never truncated
- Editor/IDE clickable — `file:line:col:` format recognized by VS Code, JetBrains, Vim/Emacs, GitHub Actions annotations
- Simpler code — no Rich `Table`, `Console` width detection, or `console.capture()` block needed
- Colors preserved — severity tag colored red/yellow, summary colored by status

## Design Decisions (from clarifying questions)

1. **Issue Ordering:** Sort all issues by file path, then line number (ESLint/ruff convention). Groups issues by location, making navigation easier.
2. **Color Forcing:** Use plain `Console()` (no `force_terminal=True`). Colors appear only on a real TTY; piped/redirected output is clean plain text. Matches standard behavior of ruff/flake8/ESLint.
3. **Summary Coloring:** Summary line colored by severity: red if errors > 0, yellow if only warnings, green if clean. The `[OK] No lint issues found.` message is also colored green.

## Functional Requirements

### FR-1: Flat line format
Each lint issue rendered as a single line: `{file}:{line}:{col}: {rule}: {message}  [{SEVERITY}]`
- `SEVERITY` is uppercase: `ERROR` or `WARN`
- Two spaces before the `[SEVERITY]` tag (matching the example output convention)
- Errors are styled red, warnings styled yellow (via Rich markup on the severity tag)

### FR-2: Issue ordering
All issues (errors and warnings combined) sorted by file path, then line number, then column.

### FR-3: Color behavior
- Use `Console()` without `force_terminal=True` — colors appear only on a real TTY
- Severity tag: errors red `[ERROR]`, warnings yellow `[WARN]`
- Summary line: red if errors > 0, yellow if only warnings, green if clean
- `[OK] No lint issues found.` message colored green

### FR-4: Summary line
Format unchanged: `N errors, N warnings, N files checked` (but now colored per FR-3)

### FR-5: Empty / clean states
- No GDScript files found: return `"No GDScript files found."` (unchanged)
- No issues found: return green-colored `"[OK] No lint issues found."`

### FR-6: No changes to JSON output
`format_lint_json` output is unchanged.

### FR-7: No changes to CLI
The `lint` command in `cli.py` already calls `format_lint_text(result)`, so the new format flows through automatically. No CLI changes needed.

## Non-Functional Requirements

- **NFR-1:** Code coverage for `lint_runner.py` remains >80% line, >70% branch
- **NFR-2:** No new dependencies introduced
- **NFR-3:** Exit code behavior unchanged (1 on errors, 0 on clean)
- **NFR-4:** All existing tests pass after updating assertions for the new format

## Acceptance Criteria

1. File paths of any length appear in full in text output (no `…` truncation)
2. Rule names of any length appear in full in text output
3. Messages of any length appear in full (may wrap at terminal boundary, but content is never truncated)
4. Error severity is colored red, warning severity is colored yellow
5. Summary line is colored red (errors), yellow (warnings only), or green (clean)
6. Summary line text format is unchanged: `N errors, N warnings, N files checked`
7. `format_lint_json` output is unchanged
8. `file:line:col:` prefix format is present for IDE/editor click-to-navigate
9. Issues are sorted by file path, then line number
10. All existing tests pass (after updating assertions for new format)
11. Exit code behavior is unchanged (1 on errors, 0 on clean)

## Out of Scope

- Changes to `format_lint_json` (JSON output unchanged)
- Changes to CLI command structure or flags
- Changes to `run_lint` logic (issue collection unchanged)
- GitHub Actions annotation format (Track 31)
- Configurable output format selection
- Documentation changes (USER_GUIDE, README)
