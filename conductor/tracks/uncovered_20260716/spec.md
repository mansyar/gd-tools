# Track: Show Uncovered Lines and Branches in Coverage Output

## Overview

Currently, `gd-tools test --coverage` prints only an aggregate one-line summary (e.g., `Coverage: 85.0% lines, 60.0% branches`), and `gd-tools coverage show` prints a summary table with hit/miss counts. Neither output surfaces *which* specific lines or branches are uncovered. This track adds uncovered line and branch detail to both outputs so developers can immediately see where coverage gaps exist.

## Functional Requirements

### FR-1: `--show-uncovered` Flag on `test` Command
Add a `--show-uncovered` boolean flag to the `test` CLI command. When `--coverage` and `--show-uncovered` are both passed, the one-line summary is followed by a per-file breakdown of uncovered lines and branches.

- When `--show-uncovered` is NOT passed (or coverage is 100%): only the one-line summary is printed (current behavior).
- When `--show-uncovered` IS passed and coverage < 100%: per-file panels are printed below the summary.
- When `--show-uncovered` IS passed but coverage is 100%: only the one-line summary is printed (nothing to show).

### FR-2: Uncovered Detail in `coverage show` Command
After the existing Rich summary table, always display per-file uncovered detail — no flag needed. The `coverage show` command is a dedicated inspection command where detailed output is expected.

- Same format and detail level as FR-1.
- If coverage is 100%, no uncovered panels are printed (nothing to show).

### FR-3: Per-File Panel Content
Both FR-1 and FR-2 use the same rendering. For each file with at least one uncovered line or branch, a Rich panel/group is shown:

- **Panel title**: file path.
- **Uncovered lines**: line numbers with zero hits, displayed as ranges where consecutive (e.g., `15, 23, 31-35`).
- **Uncovered branches**: line numbers of branch points with zero hits, annotated with branch type (e.g., `42 (if), 57 (match)`).
- No truncation — all uncovered items are shown regardless of count.
- Files with full coverage are omitted from the panels.

### FR-4: Branch Type Annotation
Uncovered branches must be annotated with their branch type. The branch type is derived from the instrumentation plan (`LinePlan.branch_type`). Supported branch types include `if`, `elif`, `else`, `for`, `while`, `match`, and `and`/`or` operators (as defined in `plan_generator.py`).

### FR-5: Data Model Enhancement
Add an `uncovered_branches: list[int]` field to the `FileSummary` dataclass in `reporter.py`. The `compute_file_summary()` function must compute this list by identifying branch-type lines (from the plan) that have zero coverage hits.

### FR-6: Documentation and Help Text Updates
The `--show-uncovered` flag and the enhanced `coverage show` output must be documented across all user-facing documentation:

- **`--help` output**: The Click `--show-uncovered` option must include a descriptive `help` string so `gd-tools test --help` automatically displays it.
- **README.md**: Update the test command usage examples to mention `--show-uncovered`.
- **docs/PRD.md**: Add `--show-uncovered` to the command reference flags table.
- **docs/USER_GUIDE.md**: Add a section or example showing `--show-uncovered` usage and the uncovered panel output.
- **skills/gd-tools/SKILL.md**: Add `--show-uncovered` to the CLI flag documentation.
- **CHANGELOG.md**: Add a feature entry for uncovered lines/branches display.

## Non-Functional Requirements

### NFR-1: Performance
The additional computation and rendering must not noticeably slow down the coverage workflow. Computing uncovered branches is a lightweight set operation.

### NFR-2: Backward Compatibility
The existing one-line summary and summary table outputs remain unchanged. The uncovered detail is purely additive — appended below existing output when triggered. The `--show-uncovered` flag defaults to off, so `test --coverage` behavior is unchanged unless the flag is passed.

## Acceptance Criteria

1. Running `gd-tools test --coverage --show-uncovered` on a project with <100% coverage prints the one-line summary followed by per-file panels showing uncovered lines (as ranges) and uncovered branches (with type annotations).
2. Running `gd-tools test --coverage` (without `--show-uncovered`) prints only the one-line summary — unchanged from current behavior.
3. Running `gd-tools test --coverage --show-uncovered` on a project with 100% coverage prints only the one-line summary.
4. Running `gd-tools coverage show` prints the existing summary table followed by per-file panels showing uncovered lines and branches.
5. Running `gd-tools coverage show` on a project with 100% coverage prints only the summary table.
6. Branch types are correctly annotated (e.g., `42 (if)`, `57 (match)`).
7. Consecutive uncovered line numbers are displayed as ranges (e.g., `31-35` not `31, 32, 33, 34, 35`).
8. No uncovered items are truncated or omitted regardless of count.
9. Unit tests cover: `--show-uncovered` CLI flag, line range formatting, branch type annotation, `uncovered_branches` computation in `compute_file_summary()`, and the inline/show output formatting.
10. Existing tests continue to pass without modification (additive change only).
11. `gd-tools test --help` displays the `--show-uncovered` flag with a descriptive help string.
12. README.md, docs/PRD.md, docs/USER_GUIDE.md, skills/gd-tools/SKILL.md, and CHANGELOG.md are updated to document the new `--show-uncovered` flag and enhanced `coverage show` output.

## Out of Scope

- Source code snippets/context display (only line numbers and branch types are shown).
- Uncovered detail in the text-format report file (terminal_reporter.py table) — only `test --coverage` inline and `coverage show` outputs are enhanced.
- HTML or other report format enhancements.
- A `--hide-uncovered` flag for `coverage show` (it always shows detail).
