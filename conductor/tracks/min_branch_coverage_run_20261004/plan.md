# Implementation Plan: Min-Branch Gate on `coverage run`

## Phase 1 — Zero-Branch Exemption in the Gate Logic [checkpoint: ebc14e7]
- [x] Task: Write failing unit tests for zero-branch exemption (Red)
  - [x] `generate_report` with `total_branches == 0` + positive threshold: no raise, note surfaced
  - [x] Populated-branch failure still raises `CoverageThresholdError`; populated pass unaffected
  - [x] `show_coverage_summary` + `print_threshold_footer` zero-branch note path
- [x] Task: Implement exemption (Green)
  - [x] `reporter.generate_report`: skip branch gate when `total_branches == 0`
  - [x] `orchestrator.print_threshold_footer` / `_print_coverage_inline` / `show_coverage_summary`: print note instead of pass/fail line
  - [x] `test` command path picks up the consistent rule automatically
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — CLI Parity: `coverage run --min-branch` [checkpoint: pending]
- [x] Task: Write failing tests for CLI wiring (Red)
  - [x] `--min-branch` accepted on `coverage run` and validated (int 0-100)
  - [x] Native command/orchestrator: already forwards `min_branch_percent` (from ternary track); `test` path verified unchanged
- [x] Task: Wire the option (Green)
  - [x] cli.py `coverage run` option + parameter
  - [x] `run_playtest_coverage` / `_collect_and_report` `min_branch_percent` passthrough + branch gate
  - [x] `_generate_native_report` already passes `min_branch_threshold` (ternary track)
- [x] Task: Gate tests (Red→Green)
  - [x] Fixture with uncovered ternary arm: `coverage run --min-branch 100` raises branch gate error
  - [x] Zero-branch project: `coverage run --min-branch 100` passes with note
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Documentation & Final Verification
- [x] Task: Docs truth pass
  - [x] USER_GUIDE: `--min-branch` row on `coverage run` + zero-branch exemption note
  - [x] ARCHITECTURE: zero-branch exemption bullet in threshold section
  - [x] CHANGELOG: coverage bullet under Unreleased
- [x] Task: Final quality gates
  - [x] `ruff check src/ tests/` + `black --check` clean
  - [x] Full `CI=true pytest` passes (unit + integration + e2e) — 1720 passed / 7 skipped, 95.66%

- [x] Final commit artifacts: docs commit 5865031, checkpoint 964e787
