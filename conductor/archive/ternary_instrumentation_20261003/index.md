# Track: Ternary Branch Instrumentation Correctness (`ternary_instrumentation_20261003`)

- **Type:** Bug fix
- **Status:** completed
- **Branch:** `fix/ternary-multiline-instrumentation-20261003`
- **Created:** 2026-10-03

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

The coverage plan generator records ternary (`test_expr`) branch points at the
line of the ternary's first operand rather than at its enclosing statement.
Because a tracker call is inserted *before* the planned line, a ternary is only
instrumentable when it already begins on its statement's line - which is true
for every other tracked node, since they all begin with a keyword. A ternary
whose line is a continuation line or a class-body line produces GDScript that
Godot cannot parse, so the file fails to instrument, is recorded as an omission,
and silently drops out of coverage.

Fixes the confirmed failure modes (multi-line parenthesized expression inside a
statement; multi-line call arguments; class-level `const`/`var`/`static var` and
`@export` initializers; default parameter values), anchors ternary branches to
the nearest enclosing node whose line is a legal insertion point (`ANCHOR_NODES`:
the tracked statements plus the control-flow statement headers), drops ternaries
that have no anchor at all, and bumps `PLAN_VERSION` to 3 so cached plans holding
stale line numbers are invalidated rather than silently reused.

A formal review (`conductor-review`, 2026-10-03) found the original anchor set
silently dropped ternaries in `if`/`while`/`for`/`match` headers, which had been
tracked correctly before - a regression, since branch totals shrank without
warning. The anchor set was widened with the statement-header nodes, the Godot
parse suite was made to assert each case's planned points rather than only that
the output compiles, the injection port gained a drift guard against the real
collector, and a `ternary_anchors.gd` golden fixture covers all the anchor
positions. Known remaining defects are recorded in the track plan: a class-level
lambda body still records a statement on the class-body line and produces
uncompilable output (pre-existing, no ternary involved), ternary arms remain
co-anchored so ternary branch coverage cannot fail, and multi-line `match`
patterns are unparseable by gdtoolkit.