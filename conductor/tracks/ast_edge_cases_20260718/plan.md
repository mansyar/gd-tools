<protect>
# Track 38: GDScript AST Edge Cases — Implementation Plan

## Phase 1: Fixture & Baseline Audit

- [x] Task: Read spec.md and workflow.md to refresh context (no commit — read-only)
    - [x] Read `./spec.md` for the track requirements and acceptance criteria
    - [x] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [x] Task: Create `edge_cases_advanced.gd` fixture [d2e0991]
    - [x] Write `tests/fixtures/gdscript/edge_cases_advanced.gd` exercising all 8 patterns (ternary, lambda, setter/getter, match bind, @onready/@export, static calls, await, super)
    - [x] Verify the fixture parses without errors via `gdtoolkit.parser` (no `LarkError`)
    - [x] Verify the fixture is valid Godot 4.5+ GDScript
- [x] Task: Wire fixture into the expected-plan generation tool [d2e0991]
    - [x] Add `"edge_cases_advanced"` to `_FIXTURE_NAMES` in `tools/generate_expected_plans.py`
    - [x] Run `python tools/generate_expected_plans.py` to generate `tests/fixtures/plans/edge_cases_advanced.expected.json`
    - [x] Commit the baseline expected JSON (pre-fix state)
- [x] Task: Audit the baseline plan output against the fixture [d2e0991]
    - [x] Run `generate_plan` against the fixture and inspect the emitted `LinePlan` entries
    - [x] For each of the 8 patterns, record: tracked correctly / gap (missing points) / false positive (spurious points)
    - [x] Confirm or reject each preliminary gap hypothesis from the spec's gap-analysis table
    - [x] Record the confirmed gap list (this drives Phase 2 test-writing)
    - **AUDIT RESULT:** Only ternary is a gap (tracked as single statement, missing `ternary_true`/`ternary_false` branch points). All other 7 patterns already tracked via existing visitor methods. `@onready`/`@export` produce zero false positives. Spec's match-bind example `1 as a:` was invalid GDScript; correct `var y:` syntax used in fixture.
- [x] Task: Conductor - User Manual Verification 'Fixture & Baseline Audit' (Protocol in workflow.md) — approved

## Phase 2: TDD — Failing Tests & Implementation

- [x] Task: Read spec.md and workflow.md to refresh context (no commit — read-only)
    - [x] Read `./spec.md` for the track requirements and acceptance criteria
    - [x] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [x] Task: Write unit tests for ternary gap + verification tests for already-tracked patterns (Red phase) — SHA: c867f90
    - [x] Create `tests/unit/test_plan_generator_edge_cases.py`
    - [x] Write test asserting ternary true AND false branches are both tracked (FAILS: only single statement tracked — the sole genuine gap)
    - [x] Write verification tests asserting lambda body statements are tracked (PASSES immediately — audit confirmed already tracked via existing visitors)
    - [x] Write verification tests asserting setter/getter block bodies are tracked (PASSES immediately — audit confirmed already tracked via existing visitors)
    - [x] Write verification tests for match bind, await, super, static/builtin calls (PASSES immediately — audit confirmed all tracked)
    - [x] Write test asserting `@onready`/`@export` annotations produce NO false-positive points (PASSES immediately — audit confirmed zero points)
    - [x] Run `$env:CI='true'; pytest tests/unit/test_plan_generator_edge_cases.py` and confirm only ternary test fails as expected
- [x] Task: Implement visitor fix to make ternary test pass (Green phase) — SHA: c867f90
    - [x] Add `test_expr` visitor method to `CoverageVisitor` in `plan_generator.py` (after `match_branch`) that adds two branch points: `ternary_true` + `ternary_false` on `tree.meta.line`
    - [x] Regenerate expected JSON: `python tools/generate_expected_plans.py` (now reflects fixed ternary tracking)
    - [x] Manually verify the regenerated JSON: `edge_cases_advanced` gains 2 ternary branch points; `edge_cases` gains 2 ternary branch points (line 24); all other existing JSONs byte-identical
    - [x] Run `$env:CI='true'; pytest tests/unit/test_plan_generator_edge_cases.py` and confirm all tests pass
- [x] Task: Conductor - User Manual Verification 'TDD Tests & Implementation' (Protocol in workflow.md) — approved

## Phase 3: Regression Safety, Quality Gates & Finalization

- [x] Task: Read spec.md and workflow.md to refresh context (no commit — read-only)
    - [x] Read `./spec.md` for the track requirements and acceptance criteria
    - [x] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [x] Task: Verify no unintended regressions in existing fixtures [c867f90]
    - [x] Run `git diff --stat tests/fixtures/plans/` and confirm only `edge_cases.expected.json` (intentional ternary fix) and `edge_cases_advanced.expected.json` (new) differ
    - [x] Confirm `simple`, `branches`, `loops`, `match_stmt`, `nested` expected JSON files are byte-identical to pre-track state
    - [x] Confirm `edge_cases.expected.json` changes are ONLY the 2 new ternary branch points (line 24); no other points altered
    - [x] Run `$env:CI='true'; pytest tests/unit/test_plan_generator.py` (existing plan-generator tests) and confirm all pass (61 passed)
- [x] Task: Verify coverage thresholds [c867f90]
    - [x] Run `$env:CI='true'; pytest --cov=gd_tools.coverage.plan_generator --cov-branch --cov-report=term-missing`
    - [x] Confirm `plan_generator.py` line coverage ≥80% and branch coverage ≥70% (actual: 98% line, 179 stmts / 2 missed)
- [x] Task: Verify style gates [c867f90]
    - [x] Run `ruff check src/ tests/ tools/` and confirm no errors (exit 0)
    - [x] Run `black --check src/ tests/ tools/` and confirm no reformatting needed (exit 0)
- [x] Task: Finalize `spec.md` Known Limitations section [c135e69]
    - [x] If the audit (Phase 1) found any pattern that cannot be instrumented, document it with rationale in the spec's `## Known Limitations` section
    - [x] If no limitations were found, replace the placeholder text with "None — all 8 patterns are fully tracked."
- [x] Task: Conductor - User Manual Verification 'Regression Safety, Quality Gates & Finalization' (Protocol in workflow.md) — approved

## Phase: Review Fixes

- [x] Task: Apply review suggestions [5a9b5cf]
</protect>
