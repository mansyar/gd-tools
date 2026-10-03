# Implementation Plan — Ternary Branch Separation

**Track ID:** `ternary_branch_separation_20261003`
**Branch:** `feature/ternary-branch-separation-20261003`
**Workflow:** TDD (red → green per task), per-task commits with git notes,
phase checkpoints per `conductor/workflow.md`.

## Phase 1 — Plan Model & Generator (operand spans)

- [x] Task: Write failing tests for ternary operand span extraction (Red) [cba5d24]
  - [x] Tests asserting each ternary branch point carries an operand source span (line/col offsets) sufficient for textual location
  - [x] Tests for nested and multi-line ternaries (correct spans on both arms)
  - [x] Tests that untracked contexts (const initializer, default parameter) emit no ternary points, unchanged
  - [x] Test that `PLAN_VERSION` is bumped 3 → 4
- [x] Task: Implement operand span capture in `CoverageVisitor` (Green) [cba5d24]
  - [x] Extend `LinePlan`/plan JSON with arm operand span fields; capture from lark `meta` in `test_expr`
  - [x] Bump `PLAN_VERSION` to 4
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Per-Arm Instrumentation (coverage.gd)

- [ ] Task: Write failing tests for operand wrapping injection (Red)
  - [ ] Tests asserting ternary arms inject `_gdtools_coverage_hit_ret(<id>, <operand>)` wrapping the operand text (not a line-inserted `hit()` before the anchor)
  - [ ] Tests for both arms on the same statement; nested/multi-line operand replacement at exact spans
  - [ ] Tests that const/default-parameter ternaries produce no instrumentation
- [ ] Task: Implement `hit_ret` tracker API and span-based operand replacement (Green)
  - [ ] Add `hit_ret(id, value)` to the coverage tracker: record hit, return value unchanged
  - [ ] Span-based text replacement in `_inject_trackers` (or sibling) for ternary branch points; remove the dual anchor-line `hit()` insertion
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Independent Measurement & Gating

- [ ] Task: Write failing end-to-end tests for per-arm measurement (Red)
  - [ ] E2E: suite exercising only the true arm → `ternary_true` covered, `ternary_false` uncovered (and reverse; and both-covered)
  - [ ] E2E: uncovered ternary arm fails `--min-branch` gate
  - [ ] Test: stale cached plan (version 3) is rejected and regenerated (version 4)
  - [ ] Test: human/JSON report display remains combined under the anchor line (schema unchanged)
- [ ] Task: Implement reporter/gate adjustments for per-arm evaluation (Green)
  - [ ] Branch hit-join and gate evaluation by arm point id; line-coverage aggregation for anchor lines verified correct
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Edge Cases & Behavioral Equivalence

- [ ] Task: Write failing tests for semantic transparency (Red)
  - [ ] Side-effect fixture: each operand evaluated exactly once, condition not re-evaluated; returned values identical to uninstrumented run
- [ ] Task: Implement/resolve edge cases (Green)
  - [ ] `await` inside a ternary operand: verify behavior; explicitly exclude with a documented reason if unsound
  - [ ] `@export var` initializer: legality test; stay untracked if a runtime call is illegal
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Documentation & Final Verification

- [ ] Task: Update documentation
  - [ ] CHANGELOG: replace the known-limitation note with the fix entry (Unreleased)
  - [ ] ARCHITECTURE: ternary instrumentation sections (anchor → operand wrapping)
  - [ ] ROADMAP: retire ternary limitation references
- [ ] Task: Final quality gates
  - [ ] `ruff check`, `black --check`, full `CI=true pytest` with coverage gates (>80% line / >70% branch on new code)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
