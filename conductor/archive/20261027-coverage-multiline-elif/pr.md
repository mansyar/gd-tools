# PR: Fix coverage injector on multi-line branch headers (Godot error 43)

- **Track:** `20261027-coverage-multiline-elif`
- **Branch:** `fix/20261027-coverage-multiline-elif` → `main`
- **Type:** bug fix (high priority)

## What

The native coverage injector inserted after-line branch trackers
(`elif_true`, `match_case`, `if_false`) on the line after the header
*start* line. For multi-line headers (parenthesized `elif ( ... )`,
multi-line match patterns) the tracker landed *inside* the condition →
Godot parse error 43 → file omitted → `test --coverage --min` failed even
when measured coverage cleared the gate.

## Changes

- `gd_tools_native_coverage.gd`: new `_find_header_end` scan (depth-aware
  colon, strings/comments, backslash continuation, EOF fail-open);
  after-line trackers insert after the header terminator.
- `plan_generator.py`: and/or + ternary points inside `elif_branch` /
  `match_branch` / `guarded_match_branch` guards anchor to their true
  header; guarded match cases now emit `match_case`; `PLAN_VERSION` 8 → 9.
- Tests: new `multiline_elif.gd` fixture through the batched Godot parse
  check; header-end port units (incl. string/comment/backslash/nested/EOF
  edges); anchor units (elif or-chain, match-`when` guard, elif ternary);
  `_short`-skip drift parity; stale-plan rejection; omission-gate
  message-level split. 8 expected-plan fixtures regenerated (version-only
  diffs).
- Docs: `conductor/tech-stack.md` schema note v7 → v9.

## Verification

- `CI=true pytest tests/unit`: 1842 passed, 3 skipped, 94.85% line (gate 80).
- Coverage integration (`parses` + `playtest_cli` + `playtest`): 54 passed,
  incl. batched Godot parse of all fixtures.
- `ruff check` / `black --check`: clean. `python -m build`: success.
- Track review: PASS (round 2, 4/4 findings fixed).
- Gap: full-suite `pytest` timed out at 10 min (Godot-heavy); scoped runs
  above are green.

## Follow-ups

- none
