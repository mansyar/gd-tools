<protect>
# Track 38: GDScript AST Edge Cases — Implementation Plan

## Phase 1: Fixture & Baseline Audit

- [ ] Task: Read spec.md and workflow.md to refresh context
    - [ ] Read `./spec.md` for the track requirements and acceptance criteria
    - [ ] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [ ] Task: Create `edge_cases_advanced.gd` fixture
    - [ ] Write `tests/fixtures/gdscript/edge_cases_advanced.gd` exercising all 8 patterns (ternary, lambda, setter/getter, match bind, @onready/@export, static calls, await, super)
    - [ ] Verify the fixture parses without errors via `gdtoolkit.parser` (no `LarkError`)
    - [ ] Verify the fixture is valid Godot 4.5+ GDScript
- [ ] Task: Wire fixture into the expected-plan generation tool
    - [ ] Add `"edge_cases_advanced"` to `_FIXTURE_NAMES` in `tools/generate_expected_plans.py`
    - [ ] Run `python tools/generate_expected_plans.py` to generate `tests/fixtures/plans/edge_cases_advanced.expected.json`
    - [ ] Commit the baseline expected JSON (pre-fix state)
- [ ] Task: Audit the baseline plan output against the fixture
    - [ ] Run `generate_plan` against the fixture and inspect the emitted `LinePlan` entries
    - [ ] For each of the 8 patterns, record: tracked correctly / gap (missing points) / false positive (spurious points)
    - [ ] Confirm or reject each preliminary gap hypothesis from the spec's gap-analysis table
    - [ ] Record the confirmed gap list (this drives Phase 2 test-writing)
- [ ] Task: Conductor - User Manual Verification 'Fixture & Baseline Audit' (Protocol in workflow.md)

## Phase 2: TDD — Failing Tests & Implementation

- [ ] Task: Read spec.md and workflow.md to refresh context
    - [ ] Read `./spec.md` for the track requirements and acceptance criteria
    - [ ] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [ ] Task: Write failing unit tests for each confirmed gap (Red phase)
    - [ ] Create `tests/unit/test_plan_generator_edge_cases.py` (or extend existing plan-generator test file per repo convention)
    - [ ] Write test asserting ternary true AND false branches are both tracked (fails: only single statement tracked)
    - [ ] Write test asserting lambda body statements are tracked (fails: no visitor method)
    - [ ] Write test asserting setter/getter block bodies are tracked (fails: no visitor method)
    - [ ] Write tests for any other confirmed gaps from the Phase 1 audit (e.g., await, match bind)
    - [ ] Write test asserting `@onready`/`@export` annotations produce NO false-positive points
    - [ ] Run `CI=true pytest tests/unit/test_plan_generator_edge_cases.py` and confirm all gap tests fail as expected
- [ ] Task: Implement visitor fixes to make tests pass (Green phase)
    - [ ] Add visitor method(s) to `CoverageVisitor` in `plan_generator.py` for ternary branch tracking (both branches)
    - [ ] Add visitor method(s) for lambda function body tracking
    - [ ] Add visitor method(s) for setter/getter block tracking
    - [ ] Add visitor method(s) for any other confirmed gaps
    - [ ] Regenerate expected JSON: `python tools/generate_expected_plans.py` (now reflects fixed tracking)
    - [ ] Manually verify the regenerated JSON matches the expected trackable points
    - [ ] Run `CI=true pytest tests/unit/test_plan_generator_edge_cases.py` and confirm all tests pass
- [ ] Task: Conductor - User Manual Verification 'TDD Tests & Implementation' (Protocol in workflow.md)

## Phase 3: Regression Safety, Quality Gates & Finalization

- [ ] Task: Read spec.md and workflow.md to refresh context
    - [ ] Read `./spec.md` for the track requirements and acceptance criteria
    - [ ] Read `../../workflow.md` for the TDD task lifecycle and phase completion protocol
- [ ] Task: Verify no regressions in existing fixtures
    - [ ] Run `git diff --stat tests/fixtures/plans/` and confirm only `edge_cases_advanced.expected.json` is new/changed
    - [ ] Confirm existing expected JSON files (`simple`, `branches`, `loops`, `match_stmt`, `nested`, `edge_cases`) are byte-identical to their pre-track state
    - [ ] Run `CI=true pytest tests/unit/test_plan_generator.py` (existing plan-generator tests) and confirm all pass
- [ ] Task: Verify coverage thresholds
    - [ ] Run `CI=true pytest --cov=gd_tools.coverage.plan_generator --cov-branch --cov-report=term-missing`
    - [ ] Confirm `plan_generator.py` line coverage ≥80% and branch coverage ≥70%
- [ ] Task: Verify style gates
    - [ ] Run `ruff check src/ tests/ tools/` and confirm no errors
    - [ ] Run `black --check src/ tests/ tools/` and confirm no reformatting needed
- [ ] Task: Finalize `spec.md` Known Limitations section
    - [ ] If the audit (Phase 1) found any pattern that cannot be instrumented, document it with rationale in the spec's `## Known Limitations` section
    - [ ] If no limitations were found, replace the placeholder text with "None — all 8 patterns are fully tracked."
- [ ] Task: Conductor - User Manual Verification 'Regression Safety, Quality Gates & Finalization' (Protocol in workflow.md)
</protect>
