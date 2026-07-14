<protect>
# Track: Fix Match Statement Instrumentation (Option A+)

## Overview

The coverage tool's `_inject_trackers` function in `pre_run_hook.gd` blindly inserts `_GDTCoverage.hit()` calls before ALL tracked lines, including `match` statement pattern lines (e.g., `0:`, `GameEnums.PartSlot.HEAD:`). Since match patterns are declarative labels — not executable statements — GDScript requires them to appear directly after `match <expr>:`. The injected tracker between `match state:` and the pattern `0:` produces a parse error, causing `reload()` to fail, source corruption, and cascading test failures (25 tests).

**Option A+** fixes this by modifying `_inject_trackers` to detect `match_case` branch entries (via the existing `branch_type` field in the plan JSON) and inject the tracker *inside the match body* (after the pattern line) rather than before it. This preserves match_case branch coverage reporting while producing valid GDScript.

## Root Cause

1. `CoverageVisitor.match_branch` (`plan_generator.py:301-303`) tracks match pattern lines as `type: "branch", branch_type: "match_case"` entries in the plan JSON.
2. `_inject_trackers` (`pre_run_hook.gd:115-129`) iterates all tracked lines in descending order and inserts `_GDTCoverage.hit(file_id, line_id)` BEFORE each tracked line — including pattern lines.
3. This produces invalid GDScript: a tracker statement between `match <expr>:` and the pattern, which GDScript cannot parse.

## Functional Requirements

### FR-1: Match Case Body Injection
`_inject_trackers` must detect plan entries with `branch_type == "match_case"` and inject the `_GDTCoverage.hit()` tracker AFTER the pattern line (inside the match case body), not before it.

### FR-2: Body Indent Detection
The injected tracker's indentation must match the body's indentation level. This is determined by scanning the next non-empty line after the pattern line and copying its indent.

### FR-3: All Pattern Types Supported
The fix must handle all GDScript 4.5 match pattern types:
- Literal/enum patterns: `0:`, `GameEnums.PartSlot.HEAD:`
- Wildcard: `_:`
- Variable bindings: `var x:`
- Array patterns: `[0, 1]:`
- Dictionary patterns: `{0: 1}:`
- Multiple patterns: `0, 1, 2:`
- Guarded patterns (`when` clause): `0 when x > 5:`

### FR-4: Existing Behavior Preserved
Non-match_case entries (statements, if branches, loop bodies, etc.) must continue to be injected BEFORE the tracked line, exactly as before. No regression in existing instrumentation behavior.

### FR-5: Descending-Order Processing Integrity
The descending-order line processing must remain correct. When inserting after a pattern line, subsequent (lower) lines shift down by one, but since entries with higher line numbers are processed first, the shift does not affect already-processed entries.

## Non-Functional Requirements

### NFR-1: No Plan Schema Changes
The plan JSON schema remains unchanged. `match_case` entries keep their existing `type: "branch", branch_type: "match_case"` format with the pattern line number. The fix is entirely in the Godot-side `_inject_trackers` logic.

### NFR-2: No Reporter Changes
The reporter (`reporter.py`) requires no changes. Match_case branches continue to be counted as both line and branch entries. With the fix, they will actually be "hit" when the tracker inside the body executes.

### NFR-3: No Plan Generator Changes
The plan generator (`plan_generator.py`) requires no changes. `CoverageVisitor.match_branch` continues to track pattern lines as `match_case` branches.

## Acceptance Criteria

1. **AC-1**: `_inject_trackers` produces valid GDScript when instrumenting files containing match statements with any pattern type (FR-3).
2. **AC-2**: The instrumented match body contains a `_GDTCoverage.hit()` call as the first statement inside each case body.
3. **AC-3**: No `_GDTCoverage.hit()` call appears between `match <expr>:` and the first pattern line.
4. **AC-4**: Match case branch coverage is correctly reported — match_case entries are marked as "hit" when their body executes (verified via integration test with simulated hits).
5. **AC-5**: All existing tests continue to pass — no regressions for non-match code instrumentation.
6. **AC-6**: New GUT unit tests cover all pattern types listed in FR-3.
7. **AC-7**: New Python integration test exercises match statement coverage end-to-end (plan generation + reporter with simulated hits).
8. **AC-8**: Code coverage thresholds maintained: >80% line, >70% branch for modified source files.

## Out of Scope

- Changes to the plan generator (`plan_generator.py`).
- Changes to the reporter (`reporter.py`).
- Changes to the plan JSON schema.
- Changes to `CoverageVisitor.match_branch` tracking logic.
- Inline match case bodies (e.g., `0: print("x")`) — GDScript 4.5 does not support this syntax; match case bodies must be on the next indented line.
</protect>
