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
- [ ] Task: Conductor - User Manual Verification 'Fixture & Baseline Audit' (Protocol in workflow.md)

## Phase 2: TDD — Failing Tests & Implementation

- [x] Task: Read spec.md and workflow.md to refresh context (no commit — read-only)
    - [x] Read `./spec.md` for the track requirements and acceptance criteria
    - [x] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [ ] Task: Write unit tests for ternary gap + verification tests for already-tracked patterns (Red phase)
    - [ ] Create `tests/unit/test_plan_generator_edge_cases.py`
    - [ ] Write test asserting ternary true AND false branches are both tracked (FAILS: only single statement tracked — the sole genuine gap)
    - [ ] Write verification tests asserting lambda body statements are tracked (PASSES immediately — audit confirmed already tracked via existing visitors)
    - [ ] Write verification tests asserting setter/getter block bodies are tracked (PASSES immediately — audit confirmed already tracked via existing visitors)
    - [ ] Write verification tests for match bind, await, super, static/builtin calls (PASSES immediately — audit confirmed all tracked)
    - [ ] Write test asserting `@onready`/`@export` annotations produce NO false-positive points (PASSES immediately — audit confirmed zero points)
    - [ ] Run `$env:CI='true'; pytest tests/unit/test_plan_generator_edge_cases.py` and confirm only ternary test fails as expected
- [ ] Task: Implement visitor fix to make ternary test pass (Green phase)
    - [ ] Add `test_expr` visitor method to `CoverageVisitor` in `plan_generator.py` (after `match_branch`) that adds two branch points: `ternary_true` + `ternary_false` on `tree.meta.line`
    - [ ] Regenerate expected JSON: `python tools/generate_expected_plans.py` (now reflects fixed ternary tracking)
    - [ ] Manually verify the regenerated JSON: `edge_cases_advanced` gains 2 ternary branch points; `edge_cases` gains 2 ternary branch points (line 24); all other existing JSONs byte-identical
    - [ ] Run `$env:CI='true'; pytest tests/unit/test_plan_generator_edge_cases.py` and confirm all tests pass
- [ ] Task: Conductor - User Manual Verification 'TDD Tests & Implementation' (Protocol in workflow.md)

## Phase 3: Regression Safety, Quality Gates & Finalization

- [x] Task: Read spec.md and workflow.md to refresh context (no commit — read-only)
    - [x] Read `./spec.md` for the track requirements and acceptance criteria
    - [x] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [ ] Task: Verify no unintended regressions in existing fixtures
    - [ ] Run `git diff --stat tests/fixtures/plans/` and confirm only `edge_cases.expected.json` (intentional ternary fix) and `edge_cases_advanced.expected.json` (new) differ
    - [ ] Confirm `simple`, `branches`, `loops`, `match_stmt`, `nested` expected JSON files are byte-identical to pre-track state
    - [ ] Confirm `edge_cases.expected.json` changes are ONLY the 2 new ternary branch points (line 24); no other points altered
    - [ ] Run `$env:CI='true'; pytest tests/unit/test_plan_generator.py` (existing plan-generator tests) and confirm all pass
- [ ] Task: Verify coverage thresholds
    - [ ] Run `$env:CI='true'; pytest --cov=gd_tools.coverage.plan_generator --cov-branch --cov-report=term-missing`
    - [ ] Confirm `plan_generator.py` line coverage ≥80% and branch coverage ≥70%
- [ ] Task: Verify style gates
    - [ ] Run `ruff check src/ tests/ tools/` and confirm no errors
    - [ ] Run `black --check src/ tests/ tools/` and confirm no reformatting needed
- [ ] Task: Finalize `spec.md` Known Limitations section
    - [ ] If the audit (Phase 1) found any pattern that cannot be instrumented, document it with rationale in the spec's `## Known Limitations` section
    - [ ] If no limitations were found, replace the placeholder text with "None — all 8 patterns are fully tracked."
- [ ] Task: Conductor - User Manual Verification 'Regression Safety, Quality Gates & Finalization' (Protocol in workflow.md)
</protect>
