# Track 38: GDScript AST Edge Cases — Specification

## Overview

This track audits and hardens the coverage plan generator (`src/gd_tools/coverage/plan_generator.py`) against complex GDScript syntax patterns. The plan generator uses a Lark AST visitor (`CoverageVisitor`) to identify trackable statements and branch points. The current visitor handles common patterns (if/elif/else, while/for loops, match cases, break/continue, return, variable assignments) but has not been validated against advanced GDScript 4.5+ syntax.

**Phase:** 9 — Robustness & Quality
**Track Type:** Chore (hardening/robustness)
**Dependencies:** Track 9 (plan generator) — already delivered
**Modules:** `src/gd_tools/coverage/plan_generator.py`, `tests/fixtures/gdscript/`, `tools/generate_expected_plans.py`
**Effort:** 1-2 days
**Risk:** MEDIUM — Lark AST traversal complexity

## Problem Statement

The `CoverageVisitor` class defines visitor methods for a fixed set of AST node types (e.g., `expr_stmt`, `if_branch`, `match_branch`). Complex GDScript patterns may either (a) not be tracked at all (instrumentation gaps → under-reported coverage) or (b) produce false positives (over-reported coverage). Neither failure has been tested because no fixture exercises these patterns.

**Current visitor coverage** (verified from `plan_generator.py:221-317`):
- Statements: `expr_stmt`, `return_stmt`, `func_var_assigned`, `func_var_typed_assgnd`, `func_var_inf`, `break_stmt`, `continue_stmt`
- Branches: `if_branch` (if_true), `elif_branch` (elif_true), `else_branch` (if_false), `while_stmt`, `for_stmt`, `for_stmt_typed` (loop_body), `match_branch` (match_case)

**Preliminary gap analysis** (to be confirmed during implementation):

| Pattern | Expected Gap | Rationale |
|---------|--------------|----------|
| Ternary (`a if cond else b`) | Both branches NOT tracked | Ternary is an expression; captured as single statement, branches invisible |
| Lambda (`var f = func(): ...`) | Body NOT tracked | No visitor method for lambda/func_def body |
| Setter/getter blocks | NOT tracked | No visitor method for property accessor blocks |
| Match bind patterns (`1 as a:`) | Verify | `match_branch` may already handle; needs confirmation |
| `@onready`/`@export` | Verify no false positives | Annotations are not statements; confirm visitor ignores them |
| Static calls (`Class.method()`) | Probably OK | Handled via `expr_stmt`; verify |
| `await` expressions | Verify | May need explicit handling depending on Lark grammar node type |
| `super()` calls | Probably OK | Handled via `expr_stmt`; verify |

## Functional Requirements

### FR-1: Comprehensive Fixture
Create a single GDScript fixture file `tests/fixtures/gdscript/edge_cases_advanced.gd` that exercises all 8 advanced patterns:
1. Ternary expressions (`var x = a if cond else b`)
2. Lambda functions (`var f = func(): ...`)
3. Setter/getter blocks (`var x: set(v): ...`, `get(): ...`)
4. Match statements with bind patterns (`match x: 1 as a: ...`)
5. `@onready` and `@export` annotations
6. Static function calls (`ClassName.static_method()`)
7. `await` expressions
8. `super()` calls

The fixture must be valid GDScript 4.5+ that parses without errors via `gdtoolkit.parser`.

### FR-2: Expected Plan Generation
Add `"edge_cases_advanced"` to the `_FIXTURE_NAMES` list in `tools/generate_expected_plans.py`. Regenerate the expected plan JSON to `tests/fixtures/plans/edge_cases_advanced.expected.json`. Manually verify the generated JSON reflects the expected trackable points before committing.

### FR-3: Audit
Run the plan generator against the fixture and audit the output:
- Confirm which patterns are already correctly tracked (static calls, super, etc.)
- Identify genuine gaps (ternary branches, lambda bodies, setter/getter blocks, etc.)
- Identify any false positives (e.g., annotations producing spurious points)

### FR-4: Fix Gaps
Add visitor methods to `CoverageVisitor` for any confirmed gaps so that trackable points are correctly identified. Fixes must not alter the tracking behavior for existing fixtures (regression-safe).

### FR-5: Unit Tests
Add unit tests in `tests/unit/` (following existing test naming conventions) that verify each pattern produces the expected trackable points. Tests must assert both presence of expected points and absence of false positives.

## Non-Functional Requirements

- **Regression safety:** Existing expected plan JSON fixtures (`simple`, `branches`, `loops`, `match_stmt`, `nested`, `edge_cases`) must remain unchanged after the fixes.
- **Coverage:** `plan_generator.py` must maintain ≥80% line coverage and ≥70% branch coverage.
- **Style:** Code must pass `ruff check` and `black --check`.
- **Documentation:** Any patterns that genuinely cannot be instrumented must be documented in the `## Known Limitations` section of this `spec.md` with rationale (see below).

## Acceptance Criteria

1. Ternary expressions are correctly tracked (both true and false branches)
2. Lambda function bodies are tracked
3. Setter/getter blocks are tracked
4. Match bind patterns are tracked
5. `@onready`/`@export` annotations do not cause false positives
6. `await` expressions are tracked
7. `super()` calls are tracked
8. All new fixtures pass plan generation tests
9. All existing expected plan JSON fixtures remain unchanged (no regressions)
10. `plan_generator.py` coverage ≥80% line, ≥70% branch
11. `ruff check` and `black --check` pass

## Known Limitations

_To be populated during implementation. Any pattern from the audit (FR-3) that cannot be instrumented will be documented here with rationale. Initially none are anticipated — all 8 patterns are expected to be trackable — but the audit phase will confirm._

## Out of Scope

- Changes to the GDScript runtime tracker (`coverage.gd`) or pre/post-run hooks — this track is Python-side (plan generation) only
- Changes to the HTML reporter
- Coverage exclusion annotations (`# gd-tools: no cover`) — that is Track 30 (separate)
- Changes to plan caching (Track 37 — already delivered)
- User-facing documentation changes (USER_GUIDE) — limitations stay in this spec.md only
