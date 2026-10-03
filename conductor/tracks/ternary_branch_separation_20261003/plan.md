# Implementation Plan — Ternary Branch Separation

**Track ID:** `ternary_branch_separation_20261003`
**Branch:** `feature/ternary-branch-separation-20261003`
**Workflow:** TDD (red → green per task), per-task commits with git notes,
phase checkpoints per `conductor/workflow.md`.

## Phase 1 — Plan Model & Generator (operand spans) [checkpoint: 30e5a17]

- [x] Task: Write failing tests for ternary operand span extraction (Red) [cba5d24]
  - [x] Tests asserting each ternary branch point carries an operand source span (line/col offsets) sufficient for textual location
  - [x] Tests for nested and multi-line ternaries (correct spans on both arms)
  - [x] Tests that untracked contexts (const initializer, default parameter) emit no ternary points, unchanged
  - [x] Test that `PLAN_VERSION` is bumped 3 → 4
- [x] Task: Implement operand span capture in `CoverageVisitor` (Green) [cba5d24]
  - [x] Extend `LinePlan`/plan JSON with arm operand span fields; capture from lark `meta` in `test_expr`
  - [x] Bump `PLAN_VERSION` to 4
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Per-Arm Instrumentation (coverage.gd) [checkpoint: 8cd0d30]

- [x] Task: Write failing tests for operand wrapping injection (Red) [ce41436]
  - [x] Tests asserting ternary arms inject `_gdtools_coverage_hit_ret(<id>, <operand>)` wrapping the operand text (not a line-inserted `hit()` before the anchor)
  - [x] Tests for both arms on the same statement; nested/multi-line operand replacement at exact spans
  - [x] Tests that const/default-parameter ternaries produce no instrumentation
- [x] Task: Implement `hit_ret` tracker API and span-based operand replacement (Green) [ce41436]
  - [x] Add `hit_ret(id, value)` to the coverage tracker: record hit, return value unchanged
  - [x] Span-based text replacement in `_inject_trackers` (or sibling) for ternary branch points; remove the dual anchor-line `hit()` insertion
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Independent Measurement & Gating [checkpoint: 6f49632]

- [x] Task: Write failing end-to-end tests for per-arm measurement (Red) [11409d0]
  - [x] E2E: suite exercising only the true arm → `ternary_true` covered, `ternary_false` uncovered (and reverse; and both-covered)
  - [x] E2E: uncovered ternary arm fails `--min-branch` gate
  - [x] Test: stale cached plan (version 3) is rejected and regenerated (version 4) — covered by `test_cache_v3_plan_is_regenerated_with_outdated_reason` (Phase 1)
  - [x] Test: human/JSON report display remains combined under the anchor line (schema unchanged)
- [x] Task: Implement reporter/gate adjustments for per-arm evaluation (Green) [11409d0]
  - [x] Branch hit-join and gate evaluation by arm point id; line-coverage aggregation for anchor lines verified correct; new `--min-branch` CLI gate on `test` and `coverage show`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Edge Cases & Behavioral Equivalence [checkpoint: 6f49632]

- [x] Task: Write failing tests for semantic transparency (Red) [5ec7b48]
  - [x] Side-effect fixture: each operand evaluated exactly once, condition not re-evaluated; returned values identical to uninstrumented run (ran as verification gate — wrapping landed in Phase 2, so Red could not be demonstrated; test adds permanent regression protection)
- [x] Task: Implement/resolve edge cases (Green) [5ec7b48]
  - [x] `await` inside a ternary operand: verified sound — wrapped form `hit_ret(id, await f())` compiles (Godot 4.7.2 parse check) and preserves resolution order; no exclusion needed
  - [x] `@export var` initializer: parse check proves a hand-instrumented export ternary compiles; stays untracked as a conservative design choice (no anchor mapping), like const/default-parameter ternaries
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Documentation & Final Verification [checkpoint: d26031d]

- [x] Task: Update documentation
  - [x] CHANGELOG: replace the known-limitation note with the fix entry (Unreleased)
  - [x] ARCHITECTURE: ternary instrumentation sections (anchor → operand wrapping, PLAN_VERSION 4)
  - [x] ROADMAP: no ternary limitation references found (Track 38 section is historical narrative) — no changes needed
  - [x] TDD.md + USER_GUIDE.md truth pass: visitor snippet/LinePlan fields updated; `--min-branch` rows added to `test` and `coverage show` flag tables
- [x] Task: Final quality gates
  - [x] `ruff check`, `black --check`, full `CI=true pytest` with coverage gates (>80% line / >70% branch on new code)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [checkpoint: d26031d]
