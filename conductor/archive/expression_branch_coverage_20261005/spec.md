# Track Specification: Expression-Level Branch Coverage

## Overview

Extend the hybrid branch coverage system beyond ternaries to measure
**boolean short-circuit operators (`and`/`or`)** and **`assert` conditions**
as first-class branch points. Each `and`/`or` operator becomes one branch
point with two measurable arms (right operand evaluated vs. short-circuited);
each `assert(cond)` becomes one branch point with pass/fail arms. This
completes the instrumentation-correctness arc begun with ternary
instrumentation and separation, and makes `--min-branch` meaningful for the
most common source of hidden branches in GDScript.

## Background

- Branch coverage currently covers `if`/`elif`/`while`/`match` and ternaries
  (`ternary_true`/`ternary_false`, plan format v1, `PLAN_VERSION` 6).
- `a and b` short-circuits: the right operand (and its side effects) may never
  evaluate. Untested short-circuit paths are invisible today, so
  `--min-branch` over-reports confidence.
- `assert(cond)` has a pass/fail branch that is currently invisible.
- Precedent machinery to reuse: value-preserving `hit_ret` operand wrappers,
  `operand_span` plan entries, `_collect_illegal_lines`, line-level
  exclusions, `generate_plan_cached()` + `CacheStatus`, zero-branch
  exemption, branch-aware reporters and the coverage-diff regression gate.

## Decisions (confirmed with the user)

- **Type:** Feature.
- **Scope:** `and`/`or` short-circuit operators plus `assert` conditions.
- **Gate semantics:** fully gated — new arms are ordinary branch points
  (in the `--min-branch` denominator, excludable, reported per-arm).
- **Counting:** per-arm counters; `and`/`or` arms named `and_right`/
  `and_short` (resp. `or_right`/`or_short`); assert arms named
  `assert_true`/`assert_false` (final ids consistent with plan format v1 and
  the ternary precedent).
- **Chain granularity:** per operator — `a and b and c` parses as
  `(a and b) and c` and yields two branch points.
- **Exclusions:** line-level `# gd-tools: no cover` only; no new syntax.
- **Assert mode:** always counted, regardless of export target
  (deterministic plans, consistent CI numbers). No config toggle.
- **Version:** `PLAN_VERSION` bumps 6 -> 7, invalidating cached plans.

## Functional Requirements

1. **Plan generation** — `CoverageVisitor` detects every `and`/`or` operator
   (per-operator granularity for chains and nesting) and every `assert` call
   in the Lark AST; emits one branch point per site with per-arm identifiers
   and source spans (right operand + whole-expression site span for
   `and`/`or`; condition span for `assert`).
2. **PLAN_VERSION 6 -> 7** — bump invalidates all cached plans (regeneration
   on next run via the existing `CacheStatus` path).
3. **Runtime instrumentation** — GDScript-side instrumentation in the
   coverage addons preserves expression semantics exactly: lazy evaluation of
   the right operand (side effects occur only when GDScript would evaluate
   it), value preservation (expression result unchanged), and per-arm hit
   recording via the collectors.
4. **Exclusions** — a line-level `# gd-tools: no cover` comment suppresses
   the expression branch points on that line, consistent with ternary
   behavior. No new exclusion syntax.
5. **Gate integration** — new branch points are ordinary branch points:
   included in the `--min-branch` denominator, enforced by the gate,
   reported per-arm in terminal/HTML reporters, and automatically covered by
   the `coverage diff` regression gate and lcov/cobertura branch data.
6. **Zero-branch exemption** — unchanged semantics; files whose only branch
   points come from expression arms participate normally in the gate.
7. **Addon deployment/versioning** — the coverage addons ship the new
   instrumentation; a loud-failure handshake ensures an old addon paired with
   a v7 plan fails loudly rather than silently mis-measuring.
8. **Documentation** — README coverage section, ARCHITECTURE, CHANGELOG, and
   ROADMAP updated; ternary and expression branch points documented together.

## Non-Functional Requirements

- Instrumentation must not alter program semantics (no eager evaluation of
  right operands; no changed return values; side-effect order preserved).
- Performance: plan generation and runtime overhead stay within existing
  perf-test budgets (`tests/performance/`).
- Python changes keep >80% line / >70% branch coverage; GDScript addon
  changes are tested via the native runtime e2e suite.

## Acceptance Criteria

1. `if a and b:` yields the existing line branch plus one `and` branch point
   with two arms; `a or b` behaves analogously.
2. `a and b and c` yields two operator branch points (per-operator), arms
   measured independently.
3. `assert(cond)` yields `assert_true`/`assert_false` arms; both reachable in
   tests.
4. Right-operand side effects occur **only** under original short-circuit
   semantics (regression-tested).
5. `# gd-tools: no cover` on the expression's line removes its branch points
   from reports and the gate.
6. `--min-branch` blocks when expression arms are unhit; passes when hit; old
   cached plans (v6) regenerate.
7. Existing ternary coverage, all reporters, `coverage diff`, and playtest
   coverage behave unchanged for files without expressions.
8. Full suite green: unit, integration, e2e, performance; pre-commit checks
   pass.

## Out of Scope

- Per-operand (flattened) chain measurement — per-operator only.
- `not`, `in`/`not in`, `is`, and truthiness of `if x:` as branch points.
- Config toggle for assert counting (always counted).
- Inline (non-line-level) exclusion directives.
- Untracked positions from the known-limitations list (class-level
  initializers, `@export` defaults, default parameters).
- GdUnit4 runtime adapter (reserved `runtime` field).
