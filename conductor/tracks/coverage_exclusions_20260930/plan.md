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

## Phase 1 — Annotation detection in the plan generator [checkpoint: 209271c]

Covers spec FR1–FR3.

- [x] Task 1.1: Write failing unit tests for annotation parsing and exclusion (Red) [0ffc869]
  - Fixture `.gd` files: line exclusion, block `start`/`end`, func-line exclusion
  - Assert excluded lines are absent from the plan's instrumented lines and present in the new excluded-lines field
- [x] Task 1.2: Write failing unit tests for edge cases (Red) [0ffc869]
  - Nested `start` ignored with warning; unterminated `start` → to-EOF; stray `end` ignored with warning
  - Annotation text inside string literals/docstrings is inert; annotation on blank/comment-only line excludes that line only
  - Malformed-annotation warnings go to stderr; generation does not fail
- [x] Task 1.3: Implement the annotation scanner in `plan_generator.py` (Green) [0ffc869]
  - Single-pass comment scan integrated with the existing Lark traversal; func-body spans derived from the AST

  > **Deviation (2026-09-30):** func-body spans are derived by an
  > indentation-based line scan instead of AST metadata — Lark
  > `end_line` in gdtoolkit is unreliable (a `func_def`'s reported
  > `end_line` overlaps the *next* function's def line), so text-based
  > spans are strictly more correct here. Scanner cost measured at
  > ~3ms per 100 files (NFR2 satisfied). Also discovered: gdtoolkit's
  > lexer fails on over-indented comment-only lines (pre-existing
  > parser quirk, unrelated to annotations) — test fixtures keep
  > annotations at statement indent.
- [x] Task 1.4: Phase Verification & Checkpoint (Refer to workflow.md) [209271c]

## Phase 2 — Plan version bump and cache invalidation [checkpoint: 6268894]

Covers spec FR4.

> **Deviation (2026-09-30):** the version bump required a one-line change
> in the GDScript addon (`gd_tools_native_coverage.gd`): its hard
> `version == 1` check was relaxed to `version >= 1`, because the
> instrumentation contract is unchanged and v2 plans only add the
> `excluded_lines` field. The plan originally assumed the addon would not
> need changes.

- [x] Task 2.1: Write failing tests for plan v2 acceptance, v1 rejection (with actionable regeneration message), and cache miss after bump (Red) [f2c2b15]
- [x] Task 2.2: Bump `PLAN_VERSION` to 2; update loader and cache key; add optional `excluded_lines` to the plan model/dataclass (Green) [f2c2b15]
- [x] Task 2.3: Verify files without annotations produce identical results to before (regression tests pinning success criterion 6) [f2c2b15]
- [ ] Task 2.4: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Reporting surface [checkpoint: f1ea59c]

Covers spec FR5.

- [x] Task 3.1: Write failing tests: HTML renders excluded lines in a distinct style; terminal report shows a compact excluded count only when exclusions exist; `--min` evaluates against the post-exclusion denominator (Red) [9786eab]
- [x] Task 3.2: Implement HTML + terminal changes reading `excluded_lines` from the plan (Green) [9786eab]
- [x] Task 3.3: Confirm LCOV/Cobertura/diff outputs are unchanged for annotated files (they simply never see the excluded lines) [9786eab]
- [ ] Task 3.4: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Documentation [checkpoint: ff99d74]

Covers spec AC8.

- [x] Task 4.1: USER_GUIDE section documenting all three forms, edge-case semantics, and the warn-and-continue behavior [9f39cfb]
- [x] Task 4.2: README one-liner under coverage features [9f39cfb]
- [x] Task 4.3: Phase Verification & Checkpoint (Refer to workflow.md) [ff99d74]

## Phase: Review Fixes

- [x] Task: Apply review suggestions [7611f2b]
