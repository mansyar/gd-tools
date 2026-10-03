# Specification — Ternary Branch Separation

**Track ID:** `ternary_branch_separation_20261003`
**Type:** Bug (coverage correctness)
**Branch:** `feature/ternary-branch-separation-20261003`

## Overview

Ternary branch coverage can never fail: both arms (`ternary_true`, `ternary_false`)
are anchored to the same statement line, and the line-based injector places both
tracker calls before that statement, so they fire in lockstep regardless of which
arm evaluates. The fix instruments each ternary arm **at the point its operand
expression evaluates**, using a value-preserving wrapper call, so arms are
measured and gated independently.

This closes the known limitation documented by the
`ternary_instrumentation_20261003` track ("ternary_true/ternary_false share one
recorded line so ternary branch coverage can never fail").

## Root Cause (verified)

- `coverage/plan_generator.py::test_expr` adds both arm points with
  `line=anchor` (the enclosing statement's line).
- `coverage.gd::_inject_trackers` is line-based: it inserts
  `TRACKER_NAME.hit(file_id, <point_id>)` statements before the anchor line.
  Both arm calls therefore execute together whenever the statement runs.
- Distinct point ids exist but cannot help while both trackers sit at the same
  insertion point — the gate can never observe an uncovered arm.

## Functional Requirements

- **FR-1 — Operand positions in the plan.** The plan generator records, for each
  ternary branch point, the source span (line/column offsets) of its operand
  expression, sufficient for the injector to locate the operand textually.
  `PLAN_VERSION` bumps 3 → 4 (cached plans invalidate and regenerate; fail-open
  semantics preserved).
- **FR-2 — Value-preserving per-arm instrumentation.** The coverage addon
  replaces each ternary operand with a wrapper call,
  `_gdtools_coverage_hit_ret(<plan_id>, <operand>)`, which records that arm's
  hit and **returns the operand value unchanged**. This replaces the current
  dual anchor-line `hit()` insertion for ternary points.
- **FR-3 — Semantic transparency.** Instrumented code must be behaviorally
  identical to the original: same operand values, same evaluation order, each
  operand evaluated exactly once. The condition must not be re-evaluated.
- **FR-4 — Conservative applicability.** Operand wrapping is applied only where
  a runtime call expression is legal. Ternaries in `const` initializers and
  default parameter values (currently untracked) remain untracked. The
  `@export var` initializer case is evaluated during implementation with
  explicit tests; if a runtime call is illegal there, it stays untracked.
- **FR-5 — Independent measurement, combined display.** Each arm records under
  its own plan-point id, so branch coverage and the `--min-branch` gate evaluate
  arms independently. Human/JSON report display stays combined under the anchor
  line as today (JSON report schema unchanged).
- **FR-6 — Docs truth pass.** Remove/update the "known limitation" notes in
  CHANGELOG, ARCHITECTURE, and any ROADMAP references.

## Non-Functional Requirements

- No regression in line-coverage semantics; statement instrumentation untouched.
- Existing `--no-cache`, `clean --cache`, and cache fail-open behavior unaffected.
- gd-tools' own test suite coverage must not degrade.

## Acceptance Criteria

1. A suite executing only the true arm yields `ternary_true` covered /
   `ternary_false` uncovered; the reverse also holds.
2. An uncovered ternary arm fails the `--min-branch` gate (end-to-end CLI test).
3. Both arms executing reports both covered.
4. Nested and multi-line ternaries instrument correctly (operands located at
   correct spans).
5. `const` initializer / default-parameter ternaries remain untracked with no
   compile errors.
6. Behavioral equivalence verified for instrumented fixtures (values, side
   effects, evaluation count).
7. PLAN_VERSION bump verified: stale cached plans regenerate.
8. Full test suite passes; docs updated per FR-6.

## Out of Scope

- Per-arm display in reports.
- Instrumenting ternaries in const/default-parameter contexts.
- Other expression-level coverage (short-circuit `and`/`or`, lambdas).
- Report format changes.

## Open Implementation Questions

- `@export var` initializer legality (FR-4 — resolved by test during
  implementation).
- `await` appearing inside a ternary operand (verify parse + instrumented
  behavior, or explicitly exclude with a documented reason).
