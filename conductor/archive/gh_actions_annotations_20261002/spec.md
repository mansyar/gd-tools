# Specification: GitHub Actions Annotations

## Overview

Roadmap Track 31 (Phase 7 Strategic, LOW risk). In CI, `gd-tools lint`
violations and coverage threshold failures render as plain log text —
the GitHub annotation UI is unused, so issues don't surface inline in
PR diffs. This track adds a `github-actions` report format to `lint`,
`coverage report`, and `coverage run`, emitting official GitHub Actions
workflow log commands (`::error` / `::warning`) so violations and
coverage failures appear as native PR annotations. It builds directly
on the `--report-format` unification delivered by the previous track
(`coverage_format_unification_20261002`).

## Functional Requirements

- **FR-1 — Lint annotations:** a `format_lint_github_actions()` in
  `src/gd_tools/lint_runner.py` renders each violation as a log command
  per the official spec:
  `::error file=<path>,line=<line>,col=<col>::<message>` with `title`
  carrying the gdlint rule (e.g. `GD3000 unused variable`). Fields in
  canonical order, all values percent-escaped (`%`, `\r`, `\n`);
  paths relative with POSIX separators.
- **FR-2 — Lint CLI:** `gd-tools lint --report-format` choices gain
  `github-actions`; annotations go to stdout; exit codes unchanged
  (1 = violations, 2 = config error).
- **FR-3 — Coverage annotations:** a reporter in
  `src/gd_tools/coverage/reporter.py` renders: a summary `::error`
  (`title=Coverage gate`) when total coverage is below the configured
  minimum, plus one
  `::warning file=<path>::Coverage <N>% below minimum <M>%` per file
  below threshold — deterministic ordering (file path, then line).
- **FR-4 — Coverage CLI:** `coverage report` and `coverage run` accept
  `github-actions` in their `--report-format` choices
  (case-insensitive, matching the unified contract).
- **FR-5 — Config alignment:** the `[coverage].format` validator in
  `config.py` accepts `github-actions`; the `ValueError` message lists
  all valid values. (Lint has no config format field — flag-only.)
- **FR-6 — Docs:** `docs/USER_GUIDE.md` gains a GitHub Actions workflow
  snippet and format-table entries; CHANGELOG updated.

## Non-Functional Requirements

- No new dependencies; ruff + black (line-length 80) clean; ≥80% line
  / ≥70% branch test coverage for new source code.
- Exit-code protocol unchanged; output deterministic for CI parsing.
- Existing `text` / `json` outputs byte-for-byte unchanged.
- Follows the project TDD workflow (tests first per workflow.md).

## Acceptance Criteria

1. Lint annotations are valid per the official log-command spec
   (unit-tested, including escaping and field ordering).
2. Coverage annotations: summary `::error` on gate failure + per-file
   `::warning`s, verified by unit tests.
3. Annotation format follows the official spec such that annotations
   surface in the PR diff view.
4. Existing `text`/`json` formats unchanged (regression tests).
5. `[coverage].format` accepts `github-actions`; invalid values
   rejected with a clear message.
6. Docs updated; full pytest suite + ruff/black pass.

## Out of Scope

- SARIF output / GitHub code scanning (deferred — candidate future
  track).
- Test-runner failure annotations (native test output path).
- Coverage-diff annotations vs. baseline.
- Log formats for other CI systems (GitLab/Jenkins).
