# Implementation Plan: Coverage Diff

- **Track ID:** coverage_diff_20260928
- **Type:** Feature
- **Status:** In Progress
- **Specification:** [`spec.md`](./spec.md)

**Design resolutions (from spec open items):**

- Baseline file is a single self-contained JSON document nesting the two
  existing coverage formats verbatim — `plan` (the `plan.json` payload) and
  `data` (the `coverage.json` payload) — plus an advisory `baseline_meta` block
  (`saved_at`, `git_branch`, `git_commit`). No new coverage schema is
  introduced; the nested payloads are consumed by the existing loaders.
- The baseline is self-sufficient across branches: the diff never assumes the
  head plan equals the baseline plan. Files are matched by path (not
  `file_id`); head-only files are `new`, baseline-only files are `removed`.
- Flag names: `--base` (required), `--show-lines`, `--report-format json`,
  `--fail-on-regression`.
- New module: `src/gd_tools/coverage/diff_reporter.py` (roadmap-mandated).
  `save-baseline`/`diff` orchestration functions live there or in the existing
  coverage orchestrator per surgical judgment; `cli.py` only wires commands.

## Phase 1 — Baseline snapshot and `save-baseline` [checkpoint: `4037956`]

**Purpose:** Establish the baseline file contract (self-contained plan+data
snapshot with advisory metadata) and expose `gd-tools coverage save-baseline`
with correct exit codes before any diff logic exists.

- [x] Task: Add failing baseline-snapshot unit tests [commit: `5d80d7c`]
  - [ ] Test saving a baseline from fixture `plan.json` + `coverage.json`
    produces a self-contained document with `plan`, `data`, and `baseline_meta`.
  - [ ] Test `baseline_meta.saved_at` is a valid UTC timestamp.
  - [ ] Test `baseline_meta.git_branch` / `git_commit` are stamped when inside
    a git repository and omitted (or null) when detection fails.
  - [ ] Test saving with no current coverage data raises the project's
    configuration-error path (exit-code `2` equivalent) and writes no file.
  - [ ] Test re-saving overwrites the previous baseline.
  - [ ] Test loading a baseline validates nested `plan`/`data` payloads via the
    existing loaders and rejects malformed/missing payloads with actionable
    errors.
  - [ ] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Implement baseline save/load in `diff_reporter.py` [commit: `a1a614c`]
  - [ ] Add the baseline document model and `save_baseline(...)` reusing
    `plan_generator.read_plan_json` / `reporter.read_coverage_json` for input.
  - [ ] Add `load_baseline(path)` returning plan + data + advisory metadata.
  - [ ] Best-effort git metadata stamping (no hard dependency, never fatal).
  - [ ] Convert missing/malformed inputs to exit-code `2` diagnostics with
    actionable messages.
  - [ ] Run the targeted tests to Green.
- [x] Task: Add failing CLI tests for `coverage save-baseline` [commit: `d793ecc`]
  - [ ] Verify the command is registered in the `coverage` group and delegates
    to the orchestrator function (no business logic in `cli.py`).
  - [ ] Verify success output names the written baseline path (exit `0`).
  - [ ] Verify missing current coverage data produces an actionable exit `2`.
  - [ ] Confirm the expected Red phase.
- [x] Task: Wire the `coverage save-baseline` command [commit: `2d85c20`]
  - [ ] Add the Click command to the existing `coverage` group.
  - [ ] Run CLI tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `4037956`]
  - [x] Run targeted unit and CLI tests plus static checks (`ruff`, `black`).
  - [x] Verify the baseline document round-trips through `load_baseline`.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 2 — Diff computation engine [checkpoint: `36a5eda`]

**Purpose:** Implement the pure diff core (`compute_diff`) with line and
branch deltas, file classification, newly-uncovered line extraction, and
totals — independent of CLI and rendering.

- [x] Task: Add failing `compute_diff` unit tests [commit: `d0a9dc3`]
  - [ ] Cover improvements (rate and covered-count increases) and regressions
    (rate decreases) for both line and branch metrics.
  - [ ] Cover `unchanged` files and exact zero-delta rounding behavior.
  - [ ] Cover `new` files (head only) and `removed` files (baseline only).
  - [ ] Cover path-based matching when plans differ between base and head.
  - [ ] Cover newly-uncovered line extraction for regressed files (covered in
    baseline, uncovered in head) and absence for improved/unchanged files.
  - [ ] Cover total-row aggregation across all files.
  - [ ] Cover degenerate cases: empty file sets, files with zero executable
    lines/branches (no division by zero).
  - [ ] Confirm the expected Red phase.
- [x] Task: Implement `compute_diff(base, head) -> DiffResult` [commit: `50f1b4b`]
  - [x] Compute per-file base/head covered and executable counts and rates for
    lines and branches, plus deltas in counts and rate points.
  - [x] Classify each file: `unchanged`, `improved`, `regressed`, `new`,
    `removed`.
  - [x] Extract newly-uncovered line numbers for regressed files.
  - [x] Aggregate total metrics and overall classification.
  - [x] Reuse existing summary computation where practical; keep the module
    self-contained otherwise (surgical, no refactor of existing reporters).
  - [x] Run the targeted tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `36a5eda`]
  - [x] Run the diff-engine unit tests plus static checks.
  - [x] Verify determinism (same inputs → same outputs) and stable ordering.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 3 — `coverage diff` CLI, rendering, and gating [checkpoint: `c6ccb2d`]

**Purpose:** Expose `gd-tools coverage diff` with the terminal table, line
detail, JSON report format, and `--fail-on-regression` gating.

- [x] Task: Add failing CLI tests for `coverage diff` [commit: `e729c09`]
  - [x] Verify `--base` is required and a missing file exits `2`.
  - [x] Verify a malformed baseline and missing/malformed current coverage data
    exit `2` with actionable messages.
  - [x] Verify the default terminal table lists per-file rows (path, base and
    head line/branch counts and rates, change) plus a total row, using shared
    `output.py` helpers and project color semantics.
  - [x] Verify baseline metadata renders as a one-line context header when
    present.
  - [x] Verify `--show-lines` lists newly-uncovered line numbers for regressed
    files only.
  - [x] Verify `--report-format json` emits valid, deterministic JSON covering
    per-file metrics, classifications, newly-uncovered lines, and totals.
  - [x] Verify `--fail-on-regression` exits `1` when any file regressed and `0`
    otherwise (including regressions without the flag).
  - [x] Confirm the expected Red phase.
- [x] Task: Implement the `coverage diff` command and rendering [commit: `15e5a3a`]
  - [x] Add the Click command to the existing `coverage` group, delegating to
    an orchestration function.
  - [x] Render the Rich summary table and detail lines per project output
    conventions (ASCII-only markers, color semantics).
  - [x] Implement the JSON report structure deterministically.
  - [x] Wire exit codes `0` / `1` / `2` per the specification.
  - [x] Run CLI tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `c6ccb2d`]
  - [x] Run all coverage-module tests plus static checks.
  - [x] Verify no new dependencies were added and `cli.py` holds no diff logic.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 4 — Documentation and full verification [checkpoint: `c70343e`]

**Purpose:** Document both subcommands for users and CI, and verify the whole
track against the specification's acceptance criteria.

- [x] Task: Update documentation [commit: `be3c4c7`]
  - [x] Document `coverage save-baseline` and `coverage diff` in
    `docs/USER_GUIDE.md` (options, exit codes, output examples).
  - [x] Document the JSON diff output shape.
  - [x] Add a CI usage snippet: `save-baseline` on main pushes,
    `diff --fail-on-regression` on PRs.
  - [x] Update `CHANGELOG.md` for the new subcommands.
  - [x] Cross-check `docs/ARCHITECTURE.md` for any needed pointer to the diff
    feature (surgical addition only).
- [x] Task: Full-suite verification
  - [x] Run `CI=true pytest` and confirm all tests pass.
  - [x] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
    and confirm >80% line / >70% branch for new source code.
  - [x] Run `ruff check src/ tests/` and `black --check src/ tests/`.
  - [ ] Walk the specification's acceptance criteria 1–11 and record results in
    `plan.md` implementation notes.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `c70343e`]
  - [x] Perform the workflow's manual verification (CLI feature steps:
    `pip install -e .`, run `save-baseline` and `diff` on a real coverage
    fixture, confirm table/JSON/exit codes).
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Implementation Notes

### Full-suite verification (2026-09-28)

- `CI=true pytest` (full suite, Godot 4.7.1 via `GODOT_BIN=C:\Godot\godot.exe`,
  worktree-local venv with `pip install -e ".[dev]"`): **1235 passed,
  2 skipped**. The 18 initial e2e failures were environmental
  (`FileNotFoundError: [WinError 2]` launching the `gd-tools` console script
  that resolves to the user's main-clone editable install); they all passed
  after the worktree venv was created. No product change was involved.
- Coverage: **95.40%** total (gates: >80% line, >70% branch);
  `coverage/diff_reporter.py` at **96%** (only defensive branches uncovered).
- `ruff check src/ tests/`: clean. `black --check src/ tests/`: clean.

### Acceptance criteria walk (spec, 1–11)

1. **save-baseline writes baseline.json + metadata** — PASS. Unit:
   `save_baseline_writes_self_contained_document`, `stamps_utc_saved_at`,
   `stamps_git_metadata` (tests/unit/test_diff_reporter.py). Manual: file
   written with `version`/`baseline_meta`/`plan`/`data` keys (Phase 1
   verification transcript).
2. **save without data exits 2, no file** — PASS. Unit:
   `missing_coverage_data_raises`, `missing_plan_raises`; CLI:
   `test_coverage_save_baseline_missing_data_exit_2`; orchestrator:
   `test_save_coverage_baseline_missing_data_raises`. Manual: exit 2 with
   `[Error] Coverage data file not found` + Cause/Fix after deleting
   coverage.json.
3. **diff table with base/head counts, rates, deltas + TOTAL row** — PASS.
   Unit: `test_coverage_diff_is_registered`, table builder tests
   (`build_diff_table...` asserts in test_diff_reporter.py). Manual: full
   table rendered with per-file rows and TOTAL (Phase 3 transcript).
4. **improvements/regressions visually distinct** — PASS. Change cells use
   green for improved, red for regressed (style applied in
   `build_diff_table`); asserted in rendering tests via `Text.style`.
5. **new/removed files shown and classified** — PASS. Unit:
   `test_compute_diff_new_and_removed_files_sorted`; JSON/ table rows carry
   `new`/`removed` with one-sided metrics (base/head `null` in JSON).
   Manual: `brand_new.gd` shown as `new (2/3 = 67%)` in the Phase 2 scenario.
6. **--show-lines lists newly-uncovered lines for regressed files** — PASS.
   Unit: `build_diff_detail` tests + CLI flag-passing test. Manual:
   `res://enemy.gd: newly uncovered lines 3, 5, 8`.
7. **--report-format json valid + deterministic** — PASS. Unit:
   `build_diff_json` structure test and `json.dumps` twice-identical
   determinism test. Manual: JSON rendered in Phase 3 transcript.
8. **--fail-on-regression exit semantics** — PASS. Unit:
   `test_coverage_diff_regression_gate_exit_1` (exit 1 with flag),
   `test_compute_diff_has_regression_false_without_regression`. Manual:
   exit 1 with the regression table shown first; exit 0 without the flag.
9. **missing/malformed baseline or current data exit 2** — PASS. Unit:
   `missing_file_raises`, `invalid_json_raises`,
   `rejects_missing_plan_payload`, `rejects_missing_data_payload`,
   `rejects_malformed_nested_data`, `test_coverage_diff_plan_error_exit_2`
   (all `CoveragePlanError` → exit 2 at the CLI boundary).
10. **all tests pass; coverage gates; ruff/black** — PASS (see full-suite
    verification above: 1235 passed / 2 skipped, 95.40%, clean).
11. **USER_GUIDE documents subcommands, JSON shape, CI snippet** — PASS
    (§3.7.4/§3.7.5 added in commit be3c4c7; also CHANGELOG entry and
    ARCHITECTURE §5.6 pointer).
