# Implementation Plan: Fix Match Statement Instrumentation (Option A+)

## Phase 1: Fix Match Statement Instrumentation

- [ ] Task: Write failing tests for _inject_trackers match case injection
    - [ ] Write GUT unit tests in `tests/fixtures/gdscript/test_pre_run_hook.gd` for each match pattern type:
        - Literal/enum pattern: `0:`, `GameEnums.PartSlot.HEAD:`
        - Wildcard: `_:`
        - Variable binding: `var x:`
        - Array pattern: `[0, 1]:`
        - Dictionary pattern: `{0: 1}:`
        - Multiple patterns: `0, 1, 2:`
        - Guarded pattern (`when` clause): `0 when x > 5:`
    - [ ] Each GUT test must verify: (a) no `_GDTCoverage.hit()` call appears before the pattern line, (b) `_GDTCoverage.hit()` appears as the first statement inside the match case body, (c) correct file_id and line_id in the injected call
    - [ ] Write GUT test verifying a full match statement with multiple cases instruments correctly (no tracker between `match <expr>:` and first pattern)
    - [ ] Write GUT test verifying non-match_case entries (regular statements) still inject BEFORE the tracked line (no regression)
    - [ ] Write Python integration test extending `tests/integration/test_coverage_hooks.py` (or new file) that: generates a coverage plan for a match fixture, simulates hits for match_case branches, and verifies the reporter correctly marks match_case branches as covered
    - [ ] Run GUT tests and confirm they fail as expected (Red phase — _inject_trackers currently injects before pattern lines)
    - [ ] Run Python integration test and confirm plan generation + reporter produce correct results for match statements
- [ ] Task: Implement match_case body injection in _inject_trackers
    - [ ] Read and understand the current `_inject_trackers` implementation in `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd` (lines 115-129)
    - [ ] Add a conditional check in `_inject_trackers`: if the entry has `branch_type == "match_case"`, use injection-after-pattern logic instead of injection-before-line
    - [ ] Implement body indent detection: scan lines after the pattern line to find the next non-empty line and copy its indentation for the injected tracker
    - [ ] Set injection point to `line_idx + 1` (after pattern line) for match_case entries; keep `line_idx` (before line) for all other entries
    - [ ] Ensure descending-order processing remains correct — entries with higher line numbers are processed first, so insertions after pattern lines do not affect already-processed entries
    - [ ] Run GUT tests and confirm all pattern type tests pass (Green phase)
    - [ ] Run full test suite: `CI=true pytest` — confirm all existing tests pass with no regressions
    - [ ] Verify coverage thresholds: `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing` — confirm >80% line, >70% branch
- [ ] Task: Conductor - User Manual Verification 'Fix Match Statement Instrumentation' (Protocol in workflow.md)
