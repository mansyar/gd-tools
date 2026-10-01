# Spec: `test --changed` — Affected-Suite Selection

- **Track ID:** `test_changed_20261001`
- **Type:** Feature
- **Branch:** `feature/test-changed-20261001`
- **Status:** Approved

## Overview

Add a `--changed` flag (with optional `--base <ref>`) to `gd-tools test` that
runs only the suites affected by a set of changed files, reusing the
file→suite mapping conventions already proven in watch mode
(`watch/mapping.py`). This brings watch mode's intelligence to CI pipelines
and large projects, where running the full suite on every push is the
dominant time cost.

## User Stories

- As a developer on a feature branch, I run `gd-tools test --changed --base main`
  in CI and only suites touched by my PR execute.
- As a developer before committing, I run `gd-tools test --changed` to test
  only what my uncommitted edits affect.

## Functional Requirements

1. **FR-1 — Flag surface:** `gd-tools test --changed` selects only suites
   mapped from changed files; `--base <ref>` switches the change source to
   `git diff --name-only <merge-base(ref, HEAD)>` (default: working tree via
   `git status --porcelain`, covering staged/unstaged/untracked/deleted).
2. **FR-2 — Mapping:** Changed `.gd` files map to suites via the existing
   `map_changed_file` conventions (`src/foo.gd` → `test_foo.gd` /
   `foo_test.gd`, sibling preferred, discovery-selected fallback); a changed
   file that *is* a selected suite maps to itself. The mapping logic is
   shared with watch mode (extracted, not duplicated) — watch behavior must
   not regress.
3. **FR-3 — Full-suite fallback:** Any changed file mapping to no selected
   suite runs the **full (filter-respecting) suite**, with a printed notice
   naming the unmapped file(s) — the same contract as `--watch`.
4. **FR-4 — Empty set:** No changed files → `--changed: no changes
   detected`, exit `0`, no Godot processes launched.
5. **FR-5 — Error semantics:** Not a git repository, or an invalid
   `--base` ref → exit `2` with an actionable message.
6. **FR-6 — Composition:** Works with `--parallel N`, `--coverage`, and
   `--suite/--test/--tag` filters (mapping respects the active selection;
   the fallback honors filters too).
7. **FR-7 — Reporting:** Always prints a one-line summary
   (`--changed: N of M suites selected by <working tree|base ref>`);
   `--verbose` prints the per-file mapping decisions.

## Non-Functional Requirements

- **NFR-1 — Performance:** Change detection adds negligible overhead
  (< 100 ms typical): at most two git subprocess calls, no indexing or cache.
- **NFR-2 — Portability:** Cross-platform path handling (Windows/macOS/Linux)
  via existing `pathlib` conventions; `res://` normalization reused from
  `watch/mapping.py`.
- **NFR-3 — Quality:** TDD per `workflow.md`; > 80% line / > 70% branch
  coverage on new modules; exit-code semantics (0/1/2) preserved.

## Acceptance Criteria

1. `gd-tools test --changed` with an edited `src/enemy.gd` runs only
   `test_enemy.gd` (or `enemy_test.gd`), exit 0 on pass.
2. `--base main` on a branch with 3 affected suites runs exactly those 3 suites.
3. A changed non-`.gd` file (e.g. `project.godot`) triggers full-suite
   fallback with a notice naming the file.
4. An untracked new test file is picked up in working-tree mode.
5. Deleted source files are handled gracefully (no crash; mapped or fallback).
6. Outside a git repository → exit `2`, actionable message.
7. Clean working tree → exit `0`, "no changes detected".
8. Summary line always shown; `--verbose` shows per-file mapping detail.
9. `--changed` + `--coverage` produces valid coverage scoped to executed suites.
10. Existing `--watch` behavior is unchanged (regression tests pass).

## Out of Scope

- `lint --changed` / `format --changed` (candidate separate track).
- Scene-file (`.tscn`) → suite heuristics.
- Persisted selection cache between runs.
- Changes to watch mode's interactive UX.
