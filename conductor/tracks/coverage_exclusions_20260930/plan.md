# Implementation Plan — Coverage Exclusion Annotations

**Track ID:** `coverage_exclusions_20260930`
**Spec:** [`./spec.md`](./spec.md)
**Workflow:** [`../../workflow.md`](../../workflow.md)
**Branch:** `feat/coverage-exclusions-20260930`

## Guiding constraints for this plan

1. **Exclusion happens at plan generation, not in the reporter.** Excluded lines are omitted from the instrumented line set and recorded in a new plan field. This makes the denominator math in `compute_file_summary` (`reporter.py:423-470`) correct *for free* and keeps the GDScript side untouched (excluded lines never reach it). If a task appears to require per-reporter filtering logic instead, that is a design smell — revisit.
2. **Plan version bump is the only cache mechanism change.** `PLAN_VERSION` 1→2 (`plan_generator.py:405`); loader accepts 2 and rejects 1 with a regeneration-directed message. No content-hash keying (spec decision).
3. **Warn-and-continue.** Malformed annotations warn on stderr and never abort plan generation or change exit codes (0/1 by coverage outcome only).
4. **Follow existing test harnesses** in the plan-generator and reporter unit test modules; fixture `.gd` files follow the current fixture style.
5. **No ROADMAP edits** — docs scope is USER_GUIDE + README only (spec decision).

---

## Phase 1 — Annotation detection in the plan generator

Covers spec FR1–FR3.

- [ ] Task 1.1: Write failing unit tests for annotation parsing and exclusion (Red)
  - Fixture `.gd` files: line exclusion, block `start`/`end`, func-line exclusion
  - Assert excluded lines are absent from the plan's instrumented lines and present in the new excluded-lines field
- [ ] Task 1.2: Write failing unit tests for edge cases (Red)
  - Nested `start` ignored with warning; unterminated `start` → to-EOF; stray `end` ignored with warning
  - Annotation text inside string literals/docstrings is inert; annotation on blank/comment-only line excludes that line only
  - Malformed-annotation warnings go to stderr; generation does not fail
- [ ] Task 1.3: Implement the annotation scanner in `plan_generator.py` (Green)
  - Single-pass comment scan integrated with the existing Lark traversal; func-body spans derived from the AST
- [ ] Task 1.4: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Plan version bump and cache invalidation

Covers spec FR4.

- [ ] Task 2.1: Write failing tests for plan v2 acceptance, v1 rejection (with actionable regeneration message), and cache miss after bump (Red)
- [ ] Task 2.2: Bump `PLAN_VERSION` to 2; update loader and cache key; add optional `excluded_lines` to the plan model/dataclass (Green)
- [ ] Task 2.3: Verify files without annotations produce identical results to before (regression tests pinning success criterion 6)
- [ ] Task 2.4: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Reporting surface

Covers spec FR5.

- [ ] Task 3.1: Write failing tests: HTML renders excluded lines in a distinct style; terminal report shows a compact excluded count only when exclusions exist; `--min` evaluates against the post-exclusion denominator (Red)
- [ ] Task 3.2: Implement HTML + terminal changes reading `excluded_lines` from the plan (Green)
- [ ] Task 3.3: Confirm LCOV/Cobertura/diff outputs are unchanged for annotated files (they simply never see the excluded lines)
- [ ] Task 3.4: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Documentation

Covers spec AC8.

- [ ] Task 4.1: USER_GUIDE section documenting all three forms, edge-case semantics, and the warn-and-continue behavior
- [ ] Task 4.2: README one-liner under coverage features
- [ ] Task 4.3: Phase Verification & Checkpoint (Refer to workflow.md)
