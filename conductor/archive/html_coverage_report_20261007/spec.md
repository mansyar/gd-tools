# Track: HTML Coverage Report Overhaul

## Overview

Overhaul the HTML coverage reporter (`src/gd_tools/coverage/html_reporter.py`
plus its Jinja2 templates in `src/gd_tools/coverage/templates/`) from its
current minimal line-coloring output into a self-contained, navigable report
that surfaces the branch engine's full detail (PLAN_VERSION 7 arms), the
`# gd-tools: no cover` exclusion annotations, and a summary dashboard — with
zero CLI-pipeline changes beyond two small convenience flags.

The HTML report is the showcase surface of the product's differentiator
(coverage). A richer report makes the branch engine's work (short-circuit
`and`/`or` arms, ternary arms, `assert` arms, exclusion annotations) visible
to users in a way the terminal and machine formats cannot.

## Goals

- Make the differentiating coverage data (branch arms, exclusions) visible in
  HTML, matching the fidelity of the terminal reporter.
- Keep output fully offline-capable: single-file pages, all CSS/JS inlined,
  no CDN or network requests.
- Preserve all existing exit codes, report content semantics, and output
  location (`.gd-tools/coverage/html/`).

## Functional Requirements

- **FR-1 Summary dashboard (index.html):** sortable/filterable file table
  (path, statements, line %, branch %, missed lines/branches); project-level
  totals header; zero-branch files labeled with the same "no branch points"
  semantics as the terminal reporter; omitted targets listed with
  reason/fix.
- **FR-2 Navigation:** each index row links to its per-file page
  (`file_<id>.html`); per-file pages link back to index; anchor links jump
  to uncovered lines/branches.
- **FR-3 Branch-arm detail:** per-file pages list uncovered branches with
  their arm-type labels (`if`, `elif`, `else`, ternary true/false,
  `and`/`or` site/right-operand/arm, `assert_true`/`assert_false`) using the
  same labels as the terminal reporter's uncovered-branch panels.
- **FR-4 Inline branch markers:** source lines hosting branch points get an
  inline per-branch badge/marker showing covered vs uncovered arms at that
  line (not just line-level yellow).
- **FR-5 Exclusion styling:** `# gd-tools: no cover` lines render in a
  distinct "excluded" style with a visible annotation chip and tooltip
  explaining the annotation; excluded lines remain out of coverage totals.
- **FR-6 Convenience flag:** `coverage report --html-open` opens the
  generated `index.html` in the default browser after writing; suppressed
  when stdout is not a TTY (CI-safe); exit code unaffected.
- **FR-7 Source rendering:** escaped source with syntax-safe rendering (no
  external highlighter dependency required); unreadable/missing source files
  degrade gracefully (as today).

## Non-Functional Requirements

- Self-contained: no external asset requests; total page weight reasonable
  for a few hundred files (no pagination — the index lists all files).
- All reporter logic unit-tested (TDD); HTML generation deterministic for
  identical inputs.
- `ruff`/`black` clean; ≥80% line / ≥70% branch coverage on new Python code.

## Acceptance Criteria

1. `gd-tools test --coverage --report-format html` produces index + per-file
   pages with FR-1…FR-5 behaviors; terminal exit codes unchanged.
2. A plan with short-circuit/ternary/assert arms shows each uncovered arm
   with its correct label in HTML.
3. A file containing `# gd-tools: no cover` shows the excluded style/chip
   and those lines stay out of totals.
4. `--html-open` opens the browser interactively and is a safe no-op in CI;
   the absent flag behaves exactly as today.
5. The report contains no external network references (verifiable by
   grepping generated HTML for `http://`/`https://` script/style tags).
6. Docs (coverage section of the user guide) and `CHANGELOG.md` updated.

## Out of Scope

- No pagination, no server mode, no diff/trend views.
- No changes to JSON/LCOV/Cobertura/github-actions report formats.
- No plan-schema changes (PLAN_VERSION stays 7) and no new config keys.
- No editor-plugin work (separate track).
