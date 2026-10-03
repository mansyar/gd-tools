# Implementation Plan: GitHub Actions Annotations

## Phase 1: Lint Annotations [checkpoint: 1b8b142]

- [x] **Task 1.1 — Write failing tests (Red):** unit tests for
  `format_lint_github_actions()` in `tests/test_lint_runner.py` — exact
  `::error file=,line=,col=,title=::message` shape, canonical field
  order, percent-escaping of `%`/`\r`/`\n` in message and fields,
  POSIX relative paths, multiple violations ordering.
- [x] **Task 1.2 — Implement (Green):** add `format_lint_github_actions()`
  to `src/gd_tools/lint_runner.py`; extend `lint --report-format`
  `click.Choice` with `github-actions` in `cli.py` and route output to
  stdout; exit codes unchanged.
- [x] **Task 1.3 — Verify quality gates + commit:** `CI=true pytest
  tests/test_lint_runner.py` green; ruff + black clean; coverage ≥80%
  line / ≥70% branch for new code; commit
  `feat(lint): add github-actions annotation format` + git note; update
  plan.md. *(feat commit `08c60a5`, wiring tests `cfb579f`; full suite
  1582 passed / 95.48% coverage)*
- [ ] **Task: Phase Verification & Checkpoint (Refer to workflow.md)**

## Phase 2: Coverage Annotations [checkpoint: 439bd3a]

- [x] **Task 2.1 — Write failing tests (Red):** unit tests for the
  GitHub Actions coverage reporter — summary `::error`
  (`title=Coverage gate`) when total below minimum, one
  `::warning file=…::Coverage N% below minimum M%` per file below
  threshold, deterministic ordering, escaping, threshold-passed → no
  annotations.
- [x] **Task 2.2 — Implement (Green):** add the reporter to
  `src/gd_tools/coverage/reporter.py`; extend `--report-format` choices
  on `coverage report` and `coverage run` in `cli.py`.
  *(commit `c5cadd0`; shared escape helpers extracted to
  `gh_annotations.py`)*
- [x] **Task 2.3 — Config alignment (TDD):** failing test that
  `[coverage].format` validator accepts `github-actions` and that the
  rejection message lists all valid values; implement in `config.py`.
  *(red `b802122`, green `478e287`; schema snapshot regenerated and
  sync test green)*
- [x] **Task 2.4 — Verify quality gates + commit:** full coverage test
  suite green; gates pass; commit
  `feat(coverage): add github-actions annotation format` + git note;
  update plan.md. *(feat `c5cadd0`; full suite 1592 passed / 95.24%;
  manual-verification remediation `7507f23`)*
- [x] **Task: Phase Verification & Checkpoint (Refer to workflow.md)**
  *(checkpoint `439bd3a`)*

## Phase 3: Docs + Final Verification

- [x] **Task 3.1 — USER_GUIDE:** add GitHub Actions workflow snippet
  (lint + coverage steps using the new format) and update the format
  tables in `docs/USER_GUIDE.md`. *(new section 4.5 + 4 format tables
  updated)*
- [x] **Task 3.2 — CHANGELOG:** add Unreleased entry describing the new
  format for lint, coverage, and config. *(new `### Added` section with
  lint/coverage/config bullets)*
- [x] **Task 3.3 — Regression:** verify `text`/`json` outputs unchanged
  (existing tests pass untouched); full quality gates:
  `CI=true pytest`, `ruff check`, `black --check`. *(full suite 1592
  passed / 95.24% after final source change `7507f23`; docs-only edits
  since; ruff + black clean)*
- [x] **Task 3.4 — Commit docs:**
  `docs(user-guide): document github-actions report format` + git note;
  update plan.md. *(commit `d192400`)*
- [ ] **Task: Phase Verification & Checkpoint (Refer to workflow.md)**
