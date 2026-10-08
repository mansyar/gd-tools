# Plan: Patch Coverage for PRs (`patch_coverage_prs_20261008`)

## Phase 1 — Changed-line extraction [checkpoint: a58d3e5]

- [x] Task: Write failing unit tests for changed-line-range extraction (`tests/unit/test_patch_lines.py`)
  - [x] Test: parse `git diff -U0` output into per-file added-line ranges (added/modified hunks)
  - [x] Test: brand-new file → full-file range; deleted file → excluded; rename → handled as modified (rename-with-edits emits standard hunks; pure rename emits none — covered by modified-file + pure-deletion tests)
  - [x] Test: non-`.gd` files filtered out; merge-base resolution failure → config error
- [x] Task: Implement `changed_lines(base)` in `src/gd_tools/changes.py` (extend the existing merge-base module; single `git diff -U0 merge_base..HEAD` subprocess, no shell) — `8abf4e7`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Patch coverage computation

- [~] Task: Write failing unit tests for patch metric computation (`tests/unit/test_patch_coverage.py`)
  - [ ] Test: intersect changed line ranges with plan executable line points → covered/uncovered counts per file
  - [ ] Test: changed file missing from coverage data → all changed executable lines uncovered
  - [ ] Test: file with zero executable plan lines → excluded from metrics entirely
  - [ ] Test: totals + percentage math (0 lines edge case)
- [ ] Task: Implement `compute_patch_coverage(...)` in new `src/gd_tools/coverage/patch.py` (loads current coverage JSON + plan, reuses plan cache)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Reporting (terminal + JSON)

- [ ] Task: Write failing tests for patch report rendering
  - [ ] Test: rich terminal table — per-file (path, changed, covered, uncovered, %), total, gate verdict line
  - [ ] Test: JSON `patch` section structure (per-file entries + totals + threshold + verdict)
  - [ ] Test: empty patch → "no changed lines" notice in both formats
- [ ] Task: Implement rendering in `coverage/patch.py` (or `diff_reporter.py` sibling functions, matching existing table builder style)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — CLI integration + gate

- [ ] Task: Write failing CLI tests (click runner, `tests/` diff command tests)
  - [ ] Test: `coverage diff --patch` without `--base` → exit 2 with actionable error
  - [ ] Test: `--patch-fail-under 80` below threshold → exit 1; at threshold → exit 0; without flag → exit 0 informational
  - [ ] Test: combined `--patch-fail-under` + `--fail-on-regression` → exit 1 if either fails
  - [ ] Test: `--patch-annotations` flag parsing/validation
- [ ] Task: Wire options onto the `coverage diff` command in `cli.py`; validate option combinations; keep non-patch behavior untouched
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — GitHub Actions annotations + summary

- [ ] Task: Write failing tests for annotation emission
  - [ ] Test: uncovered changed lines coalesce into contiguous `::warning file=,line=,end_line=,title=` runs (using `gh_annotations` escaping helpers)
  - [ ] Test: auto-emit when `GITHUB_ACTIONS=true`; suppressed when flag set to false; forced on with flag
  - [ ] Test: markdown job summary content (patch table)
- [ ] Task: Implement emission + summary write (`$GITHUB_STEP_SUMMARY`) in the diff/patch flow
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 6 — Documentation & final verification

- [ ] Task: Update docs — README, `docs/USER_GUIDE.md` (patch coverage + CI recipe), `docs/ROADMAP.md`, `CHANGELOG.md` (Unreleased)
- [ ] Task: Full quality gate — `ruff check`, `black --check`, `CI=true pytest`, project coverage ≥80/70 on new modules
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
