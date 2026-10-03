# Implementation Plan: Min-Branch Gate on `coverage run`

## Phase 1 — Zero-Branch Exemption in the Gate Logic
- [ ] Task: Write failing unit tests for zero-branch exemption (Red)
  - [ ] `generate_report` with `total_branches == 0` + positive threshold: no raise, note surfaced
  - [ ] Populated-branch failure still raises `CoverageThresholdError`; populated pass unaffected
  - [ ] `show_coverage_summary` + `print_threshold_footer` zero-branch note path
- [ ] Task: Implement exemption (Green)
  - [ ] `reporter.generate_report`: skip branch gate + set note when `total_branches == 0`
  - [ ] `orchestrator.print_threshold_footer` / `_print_coverage_inline` / `show_coverage_summary`: print note instead of pass/fail line
  - [ ] Verify `test` command path picks up the consistent rule automatically
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — CLI Parity: `coverage run --min-branch`
- [ ] Task: Write failing tests for CLI wiring (Red)
  - [ ] `--min-branch` accepted on `coverage run` and validated (int 0-100)
  - [ ] Native command/orchestrator forward `min_branch_percent` to the report generator
- [ ] Task: Wire the option (Green)
  - [ ] cli.py `coverage run` option + parameter
  - [ ] run_playtest_coverage/native command `min_branch_percent` passthrough
  - [ ] `_generate_native_report` passes `min_branch_threshold`
- [ ] Task: End-to-end gate tests (Red→Green)
  - [ ] Fixture with uncovered ternary arm: `coverage run --min-branch 100` exit 1
  - [ ] Zero-branch project: `coverage run --min-branch 100` exit 0 with note
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Documentation & Final Verification
- [ ] Task: Docs truth pass
  - [ ] USER_GUIDE: `--min-branch` row on `coverage run` + zero-branch exemption note
  - [ ] ARCHITECTURE: threshold section note (consistent rule)
  - [ ] CHANGELOG: Fix entry under Unreleased
- [ ] Task: Final quality gates
  - [ ] `ruff check src/ tests/` + `black --check` clean
  - [ ] Full `CI=true pytest` passes (unit + integration + e2e)
