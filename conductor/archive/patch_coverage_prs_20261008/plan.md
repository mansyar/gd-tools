# Plan: Patch Coverage for PRs (`patch_coverage_prs_20261008`)

## Phase 1 — Changed-line extraction [checkpoint: a58d3e5]

- [x] Task: Write failing unit tests for changed-line-range extraction (`tests/unit/test_patch_lines.py`)
  - [x] Test: parse `git diff -U0` output into per-file added-line ranges (added/modified hunks)
  - [x] Test: brand-new file → full-file range; deleted file → excluded; rename → handled as modified (rename-with-edits emits standard hunks; pure rename emits none — covered by modified-file + pure-deletion tests)
  - [x] Test: non-`.gd` files filtered out; merge-base resolution failure → config error
- [x] Task: Implement `changed_lines(base)` in `src/gd_tools/changes.py` (extend the existing merge-base module; single `git diff -U0 merge_base..HEAD` subprocess, no shell) — `8abf4e7`
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — [checkpoint: a58d3e5]

## Phase 2 — Patch coverage computation [checkpoint: 26e7eab]

- [x] Task: Write failing unit tests for patch metric computation (`tests/unit/test_patch_coverage.py`)
  - [x] Test: intersect changed line ranges with plan executable line points → covered/uncovered counts per file
  - [x] Test: changed file missing from coverage data → all changed executable lines uncovered
  - [x] Test: file with zero executable plan lines → excluded from metrics entirely (also covers changed-but-unplanned files)
  - [x] Test: totals + percentage math (0 lines edge case)
- [x] Task: Implement `compute_patch_coverage(...)` in new `src/gd_tools/coverage/patch.py` (loads current coverage JSON + plan, reuses plan cache) — `26e7eab` (pure function over loaded plan+data; cache/JSON loading deferred to Phase 4 CLI wiring)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — [checkpoint: 26e7eab]

## Phase 3 — Reporting (terminal + JSON) [checkpoint: c92a70e]

- [x] Task: Write failing tests for patch report rendering
  - [x] Test: rich terminal table — per-file (path, changed, covered, uncovered, %), total, gate verdict line
  - [x] Test: JSON `patch` section structure (per-file entries + totals + threshold + verdict)
  - [x] Test: empty patch → "no changed lines" notice in both formats
- [x] Task: Implement rendering in `coverage/patch.py` (or `diff_reporter.py` sibling functions, matching existing table builder style) — `c92a70e` (implemented in `patch.py` alongside the computation, matching `build_diff_table`/`build_diff_json` style)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — CLI integration + gate [checkpoint: db012bb]

- [x] Task: Write failing CLI tests (click runner, `tests/` diff command tests) — in `tests/unit/test_coverage_patch_cli.py`
  - [x] Test: `coverage diff --patch` without `--base` → exit 2 with actionable error (click `required=True` → usage exit 2)
  - [x] Test: `--patch-fail-under 80` below threshold → exit 1; at threshold → exit 0; without flag → exit 0 informational
  - [x] Test: combined `--patch-fail-under` + `--fail-on-regression` → exit 1 if either fails (regression loads canonical `<output_dir>/baseline.json`; missing baseline → exit 2)
  - [x] Test: `--patch-annotations` flag parsing/validation (plus `--show-lines` conflict → exit 2)
- [x] Task: Wire options onto the `coverage diff` command in `cli.py`; validate option combinations; keep non-patch behavior untouched — `db012bb` (orchestrator `diff_coverage_patch` + CLI options; `--base` help updated to cover both modes)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — [checkpoint: 16a5371]

## Phase 5 — GitHub Actions annotations + summary [checkpoint: 321684c]

- [x] Task: Write failing tests for annotation emission
  - [x] Test: uncovered changed lines coalesce into contiguous `::warning file=,line=,end_line=,title=` runs (using `gh_annotations` escaping helpers)
  - [x] Test: auto-emit when `GITHUB_ACTIONS=true`; suppressed when flag set to false; forced on with flag
  - [x] Test: markdown job summary content (patch table)
- [x] Task: Implement emission + summary write (`$GITHUB_STEP_SUMMARY`) in the diff/patch flow — `321684c` (JSON format keeps stdout pure: annotations suppressed there; additional test added for that invariant)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — [checkpoint: 8a8f86e]

## Phase 6 — Documentation & final verification [checkpoint: 695e20f]

- [x] Task: Update docs — README, `docs/USER_GUIDE.md` (patch coverage + CI recipe), `docs/ROADMAP.md`, `CHANGELOG.md` (Unreleased) — `695e20f`
- [x] Task: Full quality gate — `ruff check`, `black --check`, `CI=true pytest`, project coverage ≥80/70 on new modules — `695e20f` (1835 passed / 3 skipped, 95.45%)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — [checkpoint: 695e20f]

## Phase: Review Fixes

- [x] Task: Apply review suggestions — `ad5fc84` (JSON `uncovered_lines` field added to match USER_GUIDE contract; per-point counting for lines holding statement + branch points)
