# Track Implementation Plan: Ternary Branch Instrumentation Correctness

- **Track ID:** `ternary_instrumentation_20261003`
- **Spec:** [./spec.md](./spec.md)
- **Branch:** `fix/ternary-multiline-instrumentation-20261003`

## Phase 1: Anchor Resolution in the Plan Generator [complete: 39131e6]

- [x] Task: Write failing unit tests for anchor resolution (Red) [9e9c978]
  - [x] Add tests to `tests/unit/test_plan_generator.py` (or a new
        `test_plan_generator_ternary.py` if that file is already large) that
        assert, for a ternary inside a multi-line parenthesized expression, that
        both ternary branch points are recorded at the line of the enclosing
        statement and not at the operand's line.
  - [x] Add tests asserting that a ternary in a class-level `const`, an
        `@export` initializer, and a default parameter value produce **zero**
        branch points (FR-2).
  - [x] Add a test asserting a `const` initializer's ternary is **not**
        attributed to a later, unrelated statement (FR-3) — this is the case a
        naive bottom-up buffer gets wrong.
  - [x] Add tests pinning existing behaviour for single-line ternaries in a
        statement, nested ternaries, a ternary in an array literal, a ternary
        inside a lambda, and a multi-line `if` condition (FR-4).
  - [x] Add a test asserting `# gd-tools: no cover` on the anchor statement
        line excludes its ternary branches (FR-5).
  - [x] Run the new tests and confirm they fail for the expected reason — a
        ternary point recorded at the operand line rather than the statement
        line, and orphan ternaries still being emitted.

- [x] Task: Implement anchor resolution (Green) [9e9c978]
  - [x] Add a module-level frozenset of the tracked statement node names
        (`expr_stmt`, `return_stmt`, `func_var_assigned`,
        `func_var_typed_assgnd`, `func_var_inf`, `break_stmt`,
        `continue_stmt`).
  - [x] Add a helper that walks the parse tree recursively and returns a mapping
        from `id(test_expr node)` to the line of its nearest enclosing statement.
        It must be built and consumed inside a single `visit()` call so object
        identity never leaks into the plan (NFR-2).
  - [x] Extend `CoverageVisitor._add_point` with an optional `line` override,
        defaulting to `tree.meta.line`, so existing callers are unchanged and
        the exclusion check runs against the final line (FR-5).
  - [x] Override `CoverageVisitor.visit` to build the anchor map before
        delegating to `super().visit(tree)`. `lark.visitors.Visitor.visit` is
        eager in lark 1.2.2, so this hook cannot be bypassed by a caller that
        only calls `visit()`.
  - [x] Rewrite `CoverageVisitor.test_expr` to read its anchor from the map:
        anchor to that line when present, emit nothing when absent.
  - [x] Run the new tests and confirm they pass.

- [x] Task: Refactor [9e9c978]
  - [x] Confirm the recursive helper handles nesting depth and that repeated
        planning of the same source yields an identical plan (NFR-2).
  - [x] Keep the helper private and document why a recursive walk is required
        instead of the flat bottom-up visitor.

- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [39131e6]

## Phase 2: Plan Version Bump and Cache Invalidation

- [x] Task: Write failing test for cache invalidation (Red) [a220cac]
  - [x] Add a test asserting `PLAN_VERSION == 3`.
  - [x] Add a test asserting a cached plan at version 2 produces a cache miss
        whose reason names the expected version (FR-6), following the existing
        "cache plan version outdated" convention.

- [x] Task: Bump the plan version (Green) [a220cac]
  - [x] Change `PLAN_VERSION` from 2 to 3 in
        `src/gd_tools/coverage/plan_generator.py` and update its surrounding
        comment if it documents prior versions.
  - [x] Update any test or fixture that hard-codes version 2 as the current
        value. Fixtures that intentionally assert rejection of *older* versions
        must keep their intent.
  - [x] Run the tests and confirm they pass.

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Real-Godot Parse Regression Test

- [ ] Task: Build the Godot parse harness
  - [ ] Create a temporary Godot project containing a `GdToolsNativeCoverage`
        stub declared with `class_name` so instrumented fixtures compile for the
        correct reason. Do **not** register it as an autoload at the same time —
        `class_name` and an autoload of the same name collide with
        `Class "GdToolsNativeCoverage" hides an autoload singleton`.
  - [ ] Clear the `.godot` directory before each check and run `--import` to
        rebuild the global script class cache. Reusing a stale `.godot` produced
        false negatives during the investigation.
  - [ ] Invoke `godot --headless --path <project> --check-only --script
        res://<fixture>.gd` and treat any `Parse Error` / `Compile Error` in the
        output as a failure.

- [ ] Task: Write the regression test
  - [ ] Add an integration test that plans each fixture, applies the same
        bottom-up insertion the collector performs, writes the instrumented
        source, and asserts Godot parses it.
  - [ ] Cover all twelve fixtures listed in the spec's verification table so the
        previously broken cases can never regress silently.
  - [ ] Mark the test to skip when no Godot binary is available, consistent with
        the existing `conftest.py` conventions. It must not fail the suite on a
        machine without Godot.

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Documentation and Final Validation

- [ ] Task: Update documentation
  - [ ] Correct the `CoverageVisitor` node-to-type mapping in
        `docs/ARCHITECTURE.md` to state that `test_expr` points are anchored to
        the enclosing statement and that unanchored ternaries are not tracked.
  - [ ] Add a `CHANGELOG.md` entry under `## Unreleased` describing the fix and
        the plan version bump.

- [ ] Task: Full-suite validation
  - [ ] Run the full test suite and confirm no regressions.
  - [ ] Run coverage for the new source code and confirm >80% line and >70%
        branch coverage.
  - [ ] Run `ruff check` and `black --check`.

- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)