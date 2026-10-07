# Implementation Plan: HTML Coverage Report Overhaul

Branch: `feature/html-coverage-report-20261007`
Spec: [spec.md](spec.md)

Workflow reference: TDD (red → green → refactor) per task; quality gates
(`ruff check`, `black --check`, `CI=true pytest`, ≥80% line / ≥70% branch on
new source); commit + git-note + plan-update per task; phase checkpoints per
`conductor/workflow.md`.

---

## Phase 1 — Report data model (TDD) [checkpoint: d73a86e]

- [x] Task: Write failing unit tests for the enriched per-line/per-branch view model (`8567428`)
  - [x] Branch-point lines expose their arm entries with terminal-parity labels (`if`/`elif`/`else`, ternary true/false, `and`/`or` site/right-operand/arm, `assert_true`/`assert_false`) and covered/uncovered state per arm
  - [x] Excluded lines carry an `excluded` flag plus the annotation text context
  - [x] Zero-branch files are flagged for the "no branch points" note
- [x] Task: Implement view-model builders in `html_reporter.py` reusing `FileSummary` + plan data (no `reporter.py` changes) (`8567428`)
- [x] Task: Commit (`feat(coverage): add branch-arm and exclusion view model for HTML report`) + git note + plan update (`8567428`)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Templates: dashboard + per-file pages (TDD) [checkpoint: e136598]

- [x] Task: Write failing tests for index.html dashboard
  - [x] Sortable/filterable file table (path, statements, line %, branch %, missed) with project totals header
  - [x] Zero-branch files show the "no branch points" note; omitted targets listed with reason/fix
  - [x] Rows link to `file_<id>.html`
- [x] Task: Write failing tests for per-file pages
  - [x] Uncovered-branch panel with arm-type labels matching the terminal reporter wording
  - [x] Inline branch markers/badges on source lines hosting branch points
  - [x] Exclusion chip + tooltip on `# gd-tools: no cover` lines; excluded lines out of totals
  - [x] Back-link to index; anchor jumps to uncovered lines/branches
  - [x] Test-side corrections during red: panel assertion updated to an actually-uncovered arm (`and short-circuit arm` instead of covered `and site`); generate tests switched from `FileCoverage` to a `CoverageData` helper
- [x] Task: Rewrite `templates/index.html` + `templates/file.html` with inlined CSS/JS (no external requests)
  - [x] Index: Missed Lines/Missed Branches columns, filter input + `filterTable()` JS, zero-branch note, omitted-targets section, `branch_flags` in context
  - [x] Per-file: lines from `build_line_views` with `id="line-N"` anchors, per-arm badges, exclusion chip, uncovered panel with anchor links
- [x] Task: Add generated-output test asserting no `http(s)://` asset references in any produced page (`test_html_has_no_external_references`)
- [x] Task: Commit (`feat(coverage): overhaul HTML report dashboard and per-file pages`) + git note + plan update (`6282295`)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) (approved; suite 1896 passed / 95.87%)

## Phase 3 — `--html-open` convenience flag (TDD)

- [ ] Task: Write failing tests for `coverage report --html-open`
  - [ ] Opens `index.html` via `webbrowser` when TTY; suppressed when not a TTY (CI-safe); open failure degrades gracefully (no crash, unchanged exit code)
  - [ ] Flag only affects the `html` report format
- [ ] Task: Add the `--html-open` click option and wire it in `report()` (`src/gd_tools/cli.py`), gated on TTY
- [ ] Task: Commit (`feat(coverage): add --html-open to coverage report`) + git note + plan update
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Docs, CHANGELOG, and release polish

- [ ] Task: Update coverage docs (HTML report section: dashboard, arm detail, exclusions, `--html-open`)
- [ ] Task: Update `CHANGELOG.md` (Unreleased → Added/Changed entries)
- [ ] Task: Run quality gates: `ruff check`, `black --check`, `CI=true pytest`, coverage ≥80%/≥70%
- [ ] Task: Commit (`docs(coverage): document HTML report overhaul`) + git note + plan update
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
