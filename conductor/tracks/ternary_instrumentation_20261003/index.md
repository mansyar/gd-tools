# Track: Ternary Branch Instrumentation Correctness (`ternary_instrumentation_20261003`)

- **Type:** Bug fix
- **Status:** new
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
instrumentable when it already begins on its statement's line — which is true
for every other tracked node, since they all begin with a keyword. A ternary
whose line is a continuation line or a class-body line produces GDScript that
Godot cannot parse, so the file fails to instrument, is recorded as an omission,
and silently drops out of coverage.

Fixes three confirmed failure modes (multi-line parenthesized expression inside
a statement; class-level `const` and `@export` initializers; default parameter
values), anchors ternary branches to the nearest enclosing statement using a
real parse-tree ancestry walk, drops ternaries that have no statement to anchor
to, and bumps `PLAN_VERSION` to 3 so cached plans holding stale line numbers
are invalidated rather than silently reused.