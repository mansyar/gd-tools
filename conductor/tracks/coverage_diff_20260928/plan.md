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

## Phase 2 — Diff computation engine

**Purpose:** Implement the pure diff core (`compute_diff`) with line and
branch deltas, file classification, newly-uncovered line extraction, and
totals — independent of CLI and rendering.

- [ ] Task: Add failing `compute_diff` unit tests
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
- [ ] Task: Implement `compute_diff(base, head) -> DiffResult`
  - [ ] Compute per-file base/head covered and executable counts and rates for
    lines and branches, plus deltas in counts and rate points.
  - [ ] Classify each file: `unchanged`, `improved`, `regressed`, `new`,
    `removed`.
  - [ ] Extract newly-uncovered line numbers for regressed files.
  - [ ] Aggregate total metrics and overall classification.
  - [ ] Reuse existing summary computation where practical; keep the module
    self-contained otherwise (surgical, no refactor of existing reporters).
  - [ ] Run the targeted tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run the diff-engine unit tests plus static checks.
  - [ ] Verify determinism (same inputs → same outputs) and stable ordering.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 3 — `coverage diff` CLI, rendering, and gating

**Purpose:** Expose `gd-tools coverage diff` with the terminal table, line
detail, JSON report format, and `--fail-on-regression` gating.

- [ ] Task: Add failing CLI tests for `coverage diff`
  - [ ] Verify `--base` is required and a missing file exits `2`.
  - [ ] Verify a malformed baseline and missing/malformed current coverage data
    exit `2` with actionable messages.
  - [ ] Verify the default terminal table lists per-file rows (path, base and
    head line/branch counts and rates, change) plus a total row, using shared
    `output.py` helpers and project color semantics.
  - [ ] Verify baseline metadata renders as a one-line context header when
    present.
  - [ ] Verify `--show-lines` lists newly-uncovered line numbers for regressed
    files only.
  - [ ] Verify `--report-format json` emits valid, deterministic JSON covering
    per-file metrics, classifications, newly-uncovered lines, and totals.
  - [ ] Verify `--fail-on-regression` exits `1` when any file regressed and `0`
    otherwise (including regressions without the flag).
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement the `coverage diff` command and rendering
  - [ ] Add the Click command to the existing `coverage` group, delegating to
    an orchestration function.
  - [ ] Render the Rich summary table and detail lines per project output
    conventions (ASCII-only markers, color semantics).
  - [ ] Implement the JSON report structure deterministically.
  - [ ] Wire exit codes `0` / `1` / `2` per the specification.
  - [ ] Run CLI tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run all coverage-module tests plus static checks.
  - [ ] Verify no new dependencies were added and `cli.py` holds no diff logic.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 4 — Documentation and full verification

**Purpose:** Document both subcommands for users and CI, and verify the whole
track against the specification's acceptance criteria.

- [ ] Task: Update documentation
  - [ ] Document `coverage save-baseline` and `coverage diff` in
    `docs/USER_GUIDE.md` (options, exit codes, output examples).
  - [ ] Document the JSON diff output shape.
  - [ ] Add a CI usage snippet: `save-baseline` on main pushes,
    `diff --fail-on-regression` on PRs.
  - [ ] Update `CHANGELOG.md` for the new subcommands.
  - [ ] Cross-check `docs/ARCHITECTURE.md` for any needed pointer to the diff
    feature (surgical addition only).
- [ ] Task: Full-suite verification
  - [ ] Run `CI=true pytest` and confirm all tests pass.
  - [ ] Run `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`
    and confirm >80% line / >70% branch for new source code.
  - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/`.
  - [ ] Walk the specification's acceptance criteria 1–11 and record results in
    `plan.md` implementation notes.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Perform the workflow's manual verification (CLI feature steps:
    `pip install -e .`, run `save-baseline` and `diff` on a real coverage
    fixture, confirm table/JSON/exit codes).
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.
