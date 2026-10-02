# Specification: Coverage Format Bugfix + CLI Unification

## Overview

`gd-tools coverage run --report-format json` is advertised by the CLI
(`cli.py`, `coverage run` choices) but always fails with
`CoveragePlanError` in `generate_report()` (`coverage/reporter.py`,
`_SUPPORTED_FORMATS` lacks `json`) **after** the playtest session has
completed — wasting minutes of test execution. Additionally, format
flags are inconsistent across coverage subcommands (`--format` on
`coverage report` with no validation, `--report-format` with
`click.Choice` on `run`/`diff`), and the `[coverage].format` config
validator (`config.py`) cannot accept `json`. This track fixes the bug
and unifies the format contract.

## Functional Requirements

- **FR-1 — JSON report format:** `generate_report()` in
  `src/gd_tools/coverage/reporter.py` supports `"json"` as a
  first-class format. The JSON structure mirrors the existing
  coverage-diff JSON shape (built by `build_diff_json` in
  `diff_reporter.py`): overall summary (line/branch rate, totals)
  plus per-file breakdown (line/branch rate, covered/uncovered
  lines). Output file follows existing per-format naming conventions
  (e.g. `coverage.json` alongside `index.html`/`lcov.info`/
  `cobertura.xml`); the path is returned in `ReportResult.output_path`.
- **FR-2 — End-to-end fix:** `gd-tools coverage run
  --report-format json` completes a full playtest session and writes
  the JSON report; exit code 0 on success. A regression test covers
  the run → report path (Godot mocked per the testing strategy).
- **FR-3 — Flag unification:** `coverage report` takes canonical
  `--report-format` with `click.Choice(["html", "lcov", "cobertura",
  "text", "json"])` validation (case-insensitive, matching
  `run`/`diff`). `--format` remains as a hidden backwards-compatible
  alias. If both are supplied, a usage error is raised.
- **FR-4 — Consistency:** `coverage run --report-format` choices gain
  `json`; `coverage diff` choices remain `text|json` (no expansion).
- **FR-5 — Config alignment:** the `[coverage].format` validator in
  `config.py` accepts the same set including `json`; the `ValueError`
  message lists all valid values.
- **FR-6 — Docs:** format tables/help strings in
  `docs/USER_GUIDE.md` (and any config-schema references,
  `docs/gd-tools.schema.json` if applicable) updated to include
  `json` and the canonical flag name; CHANGELOG updated.

## Non-Functional Requirements

- No new dependencies; ruff + black (line-length 80) clean; ≥80% line
  / ≥70% branch test coverage maintained for new source code.
- Exit-code protocol unchanged (report failure = exit 2); JSON output
  must be stable/deterministic for CI parsing.
- Follows the project TDD workflow (tests first per workflow.md).

## Acceptance Criteria

1. `coverage run --report-format json` succeeds end-to-end
   (automated regression test).
2. Invalid formats fail fast at CLI parse time on all three
   subcommands (`report`, `run`, `diff`).
3. `coverage report --format html` (alias) still works; supplying
   both `--format` and `--report-format` errors.
4. `json` accepted in `[coverage].format`; invalid config values
   rejected with a clear message listing valid values.
5. Docs updated; full pytest suite + ruff/black pass.

## Out of Scope

- GitHub Actions report format (Roadmap Track 31).
- Markdown/SARIF outputs (proposed Track 4).
- Expanding `coverage diff` formats beyond `text|json`.
- `.gd-tools/results.xml` documentation and `lint_runner.py`
  `report_format` parameter cleanup (F13 items).
- `doctor --json`, update-check offline stall, ROADMAP status sweep.
