# Track Plan: Expression-Level Branch Coverage

- **Track ID:** `expression_branch_coverage_20261005`
- **Branch:** `feature/expression-branch-coverage-20261005`
- **Workflow:** TDD mandatory (Red → Green → optional Refactor). Coverage
  targets for new source: >80% line, >70% branch. Conventional commits with
  git-note summaries; phase checkpoints per `conductor/workflow.md`.

## Phase 1 — Plan Generation (Python, `plan_generator.py`)

- [x] Task: Write failing tests for boolean-operator branch points (Red) (747968f)
  - Per-operator granularity: `a and b and c` → 2 branch points; nesting
    (`a and (b or c)`) → nested spans
  - Each operator point carries arm ids `and_right`/`and_short` (resp.
    `or_right`/`or_short`); right-operand `operand_span` plus
    whole-expression site span; multi-line and parenthesized conditions
  - No-anchor positions (class-level initializers, `@export` initializers,
    default parameter values) → not tracked (ternary precedent)
- [x] Task: Implement boolean-operator detection in `CoverageVisitor` (Green) (747968f)
- [x] Task: Write failing tests for `assert` branch points (Red) (747968f)
  - Both syntaxes: `assert cond` and `assert(cond, msg)`; arms
    `assert_true`/`assert_false`; condition span excludes the message
- [x] Task: Implement assert-call detection (Green) (747968f)
- [x] Task: Write failing tests for exclusion interaction (Red) (747968f)
  - Line-level `# gd-tools: no cover` suppresses expression points on that
    line; non-expression points unaffected
- [x] Task: Implement exclusion handling for expression points (Green) (747968f)
- [x] Task: Bump `PLAN_VERSION` 6→7, update version-history docstring, verify
  cached-plan invalidation (Red+Green) (747968f)
- [x] Task: Refactor pass — span helper reuse, style-guide conformance (747968f)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — GDScript Collector Instrumentation (both addons)

- [ ] Task: Write failing e2e tests for `and`/`or` arm measurement (Red)
  - Right operand wrapped value-preservingly: `and_right` records exactly
    when the right operand evaluates; side effects only under original
    short-circuit semantics; result value unchanged
  - Short-circuit arm derived from site vs. right counters (site wrap of the
    whole expression; derivation in collector aggregation, clamped ≥ 0)
- [ ] Task: Implement right-operand + site span wrapping in
  `gd_tools_native_coverage.gd` (Green) — generalize `_wrap_ternary_operands`
- [ ] Task: Write failing e2e tests for `assert` arm measurement (Red)
  - A single wrapper call records exactly one of `assert_true`/
    `assert_false` based on the evaluated condition value
- [ ] Task: Implement value-aware dual-arm helper (e.g. `hit_bool`) in the
  native collector (Green)
- [ ] Task: Mirror instrumentation in `coverage.gd` (`gd-tools-coverage`
  autoload / playtest path) (Green)
- [ ] Task: Write failing test + implement loud-failure handshake: collector
  rejects plans containing unknown/unimplemented branch types (old addon +
  v7 plan must fail loudly, not silently mis-measure)
- [ ] Task: Refactor pass — keep wrap/derivation logic consistent across the
  two collectors
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Gate, Reporters & Compatibility

- [ ] Task: Write failing tests for gate integration (Red)
  - Expression arms in the `--min-branch` denominator; zero-branch exemption
    unaffected; threshold blocking/passing scenarios
- [ ] Task: Implement gate integration (Green)
- [ ] Task: Write failing tests for reporter rendering (Red)
  - Terminal + HTML arm labels (ternary-style), `coverage diff` counts
    expression arms, lcov/cobertura branch data includes the new arms
- [ ] Task: Implement reporter updates (Green)
- [ ] Task: Write failing test + verify the playtest coverage path end-to-end
  with v7 plans (Red+Green)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Docs & Final Verification

- [ ] Task: README + ARCHITECTURE — expression branch points documented
  together with ternaries; coverage semantics updated
- [ ] Task: CHANGELOG + ROADMAP track entry
- [ ] Task: Full verification — `CI=true pytest`, `ruff check src/ tests/`,
  `black --check src/ tests/`, coverage targets, Definition-of-Done sweep
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
