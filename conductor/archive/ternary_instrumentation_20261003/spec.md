# Track Specification: Ternary Branch Instrumentation Correctness

- **Track ID:** `ternary_instrumentation_20261003`
- **Type:** Bug fix
- **Branch:** `fix/ternary-multiline-instrumentation-20261003`
- **Created:** 2026-10-03

## Overview

The coverage plan generator misplaces branch points for ternary expressions
(`value_if_true if condition else value_if_false`). A tracker call is inserted
*before* the planned line, so a ternary is only instrumentable when it begins
on the line of an enclosing tracked statement. Every other tracked AST node
begins with a keyword (`var`, `return`, `if`, `elif`, `else`, `while`, `for`,
`break`, `continue`) and therefore can only ever be reported at a statement
boundary. `test_expr` is the single exception: its first token is an arbitrary
operand expression.

When a ternary lands on a line that is not a statement boundary, the injected
tracker is written into the middle of an expression or into the class body, the
script fails to parse, and `_instrument_file` silently records an **omission**.
Affected files drop out of coverage entirely, and with `--min` the omission
gate escalates to exit 2.

## Root Cause

`CoverageVisitor.test_expr` places both ternary branch points at
`tree.meta.line`, which for `test_expr` resolves to the line of the
**value-if-true operand**, not the enclosing statement.

Three distinct failure modes were confirmed against Godot 4.7.2:

| # | Construct | Godot error |
|---|-----------|-------------|
| 1 | Ternary nested in a multi-line parenthesized expression inside a statement | `Expected closing ")" after grouping expression.` |
| 2 | Ternary in a class-level `const` / `@export` initializer, or in a default parameter value (single line) | `Unexpected identifier "GdToolsNativeCoverage" in class body.` |
| 3 | Same as #2 but spanning multiple lines | `Expected closing ")" after grouping expression.` |

Mode 1 is the reported symptom. Modes 2 and 3 share the identical root cause
and were already broken before the bug was reported.

Not affected (verified instrumentable): multi-line `if` / `elif` / `else` /
`while` / `for` conditions, multi-line array and dictionary literals, multi-line
string concatenation, lambdas, and backslash line continuations.

## Functional Requirements

- **FR-1 — Anchor ternary branches to the enclosing statement.** When a
  `test_expr` node is nested inside a tracked statement, both ternary branch
  points must be recorded at the line of that nearest enclosing statement, not
  at the ternary's own line.
- **FR-2 — Drop orphaned ternary branches.** When a `test_expr` node has no
  enclosing tracked statement (class-level `const`, `@export`, default parameter
  value, signal argument), no branch points may be emitted for it. There is no
  statement boundary at which a tracker could be legally inserted, so the
  expression is not instrumentable and must be excluded from the plan.
- **FR-3 — Anchor resolution must respect true ancestry.** The enclosing
  statement must be found by walking the parse tree, not by observing the next
  statement visited in bottom-up order. A ternary inside a `const` initializer
  must not be attributed to a later, unrelated statement.
- **FR-4 — Preserve existing behaviour for every other node type.** Statement,
  `if_true`, `elif_true`, `if_false`, `loop_body`, and `match_case` points must
  continue to be recorded at `tree.meta.line` exactly as today.
- **FR-5 — Preserve `# gd-tools: no cover` semantics.** Exclusion checks must
  evaluate against the line the point is finally recorded at, so an excluded
  statement line excludes its ternary branches too.
- **FR-6 — Bump `PLAN_VERSION` from 2 to 3.** The coverage plan cache keys on
  `{res_path: sha256}` plus plan version. Without a version bump, an existing
  project would keep serving stale, broken line numbers from its cached plan
   after upgrading, turning a loud failure into a silent one.
- **FR-7 — Both coverage runtimes benefit.** The fix lives entirely in the
  Python plan generator, which is shared by the native runtime
  (`gd-tools-test/gd_tools_native_coverage.gd`) and the legacy playtest
  collector (`gd-tools-coverage/coverage.gd`). Neither addon requires a change.

## Non-Functional Requirements

- **NFR-1 — No injected GDScript may fail to parse.** For any fixture the plan
  generator accepts, the instrumented output must compile. This is the
  invariant the track exists to restore, and it must be enforced by a test that
  runs a real Godot parse, not only by unit assertions on line numbers.
- **NFR-2 — Determinism.** Planning the same source twice must produce an
  identical plan. `id(tree)`-keyed maps must be built and consumed within a
  single `visit()` call so object identity never leaks into the output.
- **NFR-3 — Cost.** Anchor resolution is a single extra O(n) pass over the
  parse tree, negligible relative to parsing itself.
- **NFR-4 — Coverage.** New source code must meet >80% line and >70% branch
  coverage per the workflow quality gates.

## Acceptance Criteria

1. `generate_plan` records ternary branch points at the enclosing statement's
   line for a ternary inside a multi-line parenthesized expression.
2. `generate_plan` emits **no** branch points for a ternary in a class-level
   `const`, an `@export` initializer, or a default parameter value.
3. A ternary in a `const` initializer is not attributed to any later statement.
4. Every fixture exercised by the new real-Godot integration test produces
   source that Godot parses without error.
5. Unchanged sources that were previously correct — single-line ternary in a
   statement, nested ternaries, ternary in an array literal, ternary inside a
   lambda, multi-line `if` — keep their existing plan lines and ids.
6. `PLAN_VERSION` is `3`, and a plan file written at version 2 is rejected with
   a cache-miss reason naming the expected version.
7. The full existing test suite passes with no regressions.

## Out of Scope

- **Ternary arms remain indistinguishable.** `ternary_true` and
  `ternary_false` are still recorded at the same line and therefore always
  report covered-or-not together. This is a pre-existing metric limitation, not
  a defect introduced or worsened here; anchoring to the statement line loses no
  information that exists today. Making the arms genuinely distinguishable
  requires new injector syntax and a further plan version bump, and should be
  tracked separately.
- **Hardening `_inject_trackers` with a bracket-depth clamp.** Rejected in
  favour of fixing the plan, since the plan is the source of truth. Could be
  reconsidered as defence in depth once the plan is known correct.
- **`# gd-tools: no cover` on an anchored statement.** Per FR-5 the exclusion is
  evaluated against the anchor line, so marking a statement excluded does
  exclude its ternary branches. Whether a no-cover annotation should also
  propagate into a multi-line expression is a separate design question.
- **Multi-line `match` patterns.** gdtoolkit's Lark grammar cannot parse them
  at all (`UnexpectedToken`), so they never reach instrumentation. This is a
  parser limitation, not an instrumentation defect.

## Verification Evidence

The design in this spec was prototyped and validated before drafting. Twelve
fixtures were planned with the current generator and with a prototype of this
fix, instrumented, and compiled by Godot 4.7.2:

| Fixture | Before | After |
|---------|--------|-------|
| ternary in multi-line parens (statement) | BROKEN | ok |
| ternary in multi-line call args | BROKEN | ok |
| class-level `const` ternary | BROKEN | ok |
| `@export` ternary | BROKEN | ok |
| default parameter ternary | BROKEN | ok |
| multi-line class-level `const` ternary | BROKEN | ok |
| single-line ternary in statement | ok | ok |
| nested ternary | ok | ok |
| ternary in lambda | ok | ok |
| ternary in array literal | ok | ok |
| multi-line `if` condition | ok | ok |
| no ternary | ok | ok |

Zero regressions; all orphaned ternaries correctly reduced to zero branch
points.

Note on method: an earlier verification pass produced false negatives because
Godot's `.godot` import cache was reused across checks. The authoritative
harness clears `.godot`, runs `--import` to rebuild the global class cache, and
registers a `GdToolsNativeCoverage` stub via `class_name` so instrumented
fixtures compile for the right reason. The regression test must use an
equivalent harness.