# Implementation Plan: Coverage Format Bugfix + CLI Unification

> Follows the Standard Task Workflow and Phase Completion Verification
> and Checkpointing Protocol defined in `conductor/workflow.md`
> (TDD: Red → Green → Refactor, coverage ≥80% line / ≥70% branch,
> commit + git note per task, checkpoint commit per phase).

## Phase 1: JSON Report Format (F1 Fix)

- [ ] Task 1.1: Write failing tests for JSON report format (Red)
  - [ ] Add tests in the coverage reporter test suite (match existing
        naming/style, e.g. `tests/test_coverage_reporter.py`):
        `generate_report(..., format="json")` does not raise
        `CoveragePlanError`; JSON structure mirrors the
        coverage-diff JSON shape (overall summary + per-file
        line/branch breakdown); output file written (e.g.
        `coverage.json`) and path returned in
        `ReportResult.output_path`; threshold error still raised
        after the report is written; output is deterministic.
  - [ ] Add regression test at the `coverage run` orchestration
        level asserting `report_format="json"` completes the
        run → report path (Godot mocked per testing strategy).
  - [ ] Run tests, confirm Red.
- [ ] Task 1.2: Implement JSON reporter (Green)
  - [ ] Add `"json"` to `_SUPPORTED_FORMATS` in
        `coverage/reporter.py`; implement JSON serialization
        reusing the coverage-diff JSON structure from
        `diff_reporter.build_diff_json`.
  - [ ] Run tests, confirm Green; refactor if needed.
  - [ ] Verify coverage:
        `CI=true pytest --cov=gd_tools --cov-branch`
  - [ ] Commit (`fix(coverage): support json report format`) and
        attach task summary git note; update plan task statuses.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: CLI Flag Unification + Validation

- [ ] Task 2.1: Write failing CLI tests (Red)
  - [ ] Tests in the CLI test suite: `coverage report
        --report-format <invalid>` fails fast with a usage error
        (exit 2); `coverage report --report-format html` works;
        `coverage report --format html` (hidden alias) still works;
        supplying both `--format` and `--report-format` raises a
        usage error; `coverage run --report-format json` accepted
        at parse time.
  - [ ] Run tests, confirm Red.
- [ ] Task 2.2: Implement CLI changes (Green)
  - [ ] In `cli.py`: canonical `--report-format` with
        `click.Choice` on `coverage report` (case-insensitive,
        matching `run`/`diff`); keep `--format` as a hidden alias;
        mutual-exclusion error when both are supplied.
  - [ ] Run tests, confirm Green; full suite still green.
  - [ ] Commit (`refactor(coverage): unify report format flags with
        validation`) and attach git note; update plan task statuses.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Config Alignment + Docs + Final Verification

- [ ] Task 3.1: Write failing config tests (Red)
  - [ ] Tests in `tests/test_config.py` (or the coverage config test
        module if that is where the validator is tested):
        `[coverage].format = "json"` validates; invalid value error
        message lists all valid values.
  - [ ] Run tests, confirm Red.
- [ ] Task 3.2: Update config validator (Green)
  - [ ] Align the `[coverage].format` validation in `config.py` with
        the new format set; update docstring/error message.
  - [ ] Run tests, confirm Green.
  - [ ] Commit (`fix(config): accept json in coverage format
        validator`) and attach git note; update plan task statuses.
- [ ] Task 3.3: Update documentation
  - [ ] Update `docs/USER_GUIDE.md` format tables/help text (json
        format, canonical `--report-format`); check
        `docs/gd-tools.schema.json` for a format enum; update
        CHANGELOG under Unreleased.
  - [ ] Commit (`docs(coverage): document json report format and
        flag unification`).
- [ ] Task 3.4: Final quality gate
  - [ ] `ruff check src/ tests/ && black --check src/ tests/ &&
        CI=true pytest` all pass; coverage ≥80% line / ≥70% branch.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
