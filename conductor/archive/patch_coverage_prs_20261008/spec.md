# Track Spec: Patch Coverage for PRs

## Overview

PR review needs a coverage signal scoped to *what the PR changed*, not the whole project. Today `gd-tools coverage diff` compares full-file coverage between two snapshots, and GitHub annotations only cover lint findings. This track adds **patch coverage**: coverage computed over only the executable lines changed relative to a git base ref, reported in the terminal and JSON, gateable in CI with exit 1, and surfaced as inline `::warning` annotations on uncovered changed lines — completing the "production-quality GDScript coverage" differentiator for the pull-request workflow.

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | `coverage diff --patch` enables patch-coverage mode. Changed lines are determined by `git diff` between HEAD and the merge-base of `--base <ref>` and HEAD, using the same contract as `test --changed --base`. `--base` is **required** when `--patch` is set; a missing/unresolvable ref is a config error (exit 2). |
| FR-2 | Patch coverage = (covered changed executable lines) / (total changed executable lines) × 100, where executable lines come from the coverage instrumentation plan (line points) and hit data comes from the **current** run's coverage JSON. No baseline snapshot is required. |
| FR-3 | Edge-case semantics (strict set): (a) a changed `.gd` file absent from the coverage data has all its changed executable lines counted as **uncovered**; (b) brand-new files are fully included in the patch; (c) deleted files are ignored entirely; (d) only `.gd` files contribute; (e) changed files with zero executable plan lines are skipped and never fail the gate. |
| FR-4 | Gate: `--patch-fail-under <N>` (0–100). When the patch coverage is below `N`, the command exits **1**. Without the flag, the patch report is informational only. When combined with `--fail-on-regression`, either failure produces exit 1. |
| FR-5 | Terminal report (rich): per-file table (path, changed lines, covered, uncovered, file patch %), total patch coverage, and an explicit gate verdict line. |
| FR-6 | JSON report (`--json`): a `patch` section with per-file detail and totals (changed/covered/uncovered/percentage, threshold, gate verdict) for machine consumption. |
| FR-7 | GitHub Actions: when `GITHUB_ACTIONS=true`, emit (a) `::warning file=<path>,line=<n>,end_line=<m>,title=Uncovered in patch` annotations for each uncovered changed line (coalesced into contiguous runs) and (b) a markdown job summary with the patch table. An explicit `--patch-annotations {true,false}` flag overrides auto-detection. |
| FR-8 | Empty patch (no changed `.gd` executable lines): print a "no changed lines" notice, skip the gate vacuously, exit 0. |
| FR-9 | Reuses existing infrastructure: plan cache, coverage data loading, diff reporter plumbing, and the shared `gh_annotations` emission module. Git is invoked via subprocess with no shell interpolation. |

## Non-Functional Requirements

- **NFR-1** No new runtime dependencies (git via existing subprocess patterns).
- **NFR-2** Type hints + docstrings on all new public functions; follows `code_styleguides/python.md`; passes `ruff` and `black`.
- **NFR-3** New source modules ≥80% line / ≥70% branch coverage (project workflow standard).
- **NFR-4** Exit code convention preserved: 0 pass / 1 failure / 2 config error.
- **NFR-5** Performance: single `git diff` invocation; plan cache reuse; suitable for a CI PR job (<2s Python-side overhead on typical PRs).
- **NFR-6** Cross-platform path handling (Windows/macOS/Linux) consistent with existing diff logic.

## Acceptance Criteria

1. `gd-tools coverage diff --patch --base main --report <current.json>` prints a per-file patch coverage table and total, exit 0 when no gate is set.
2. With `--patch-fail-under 80` and 70% patch coverage → exit 1 and the terminal verdict states the failure; at/above the threshold → exit 0.
3. A changed `.gd` file with no coverage data contributes 100% uncovered lines (verifiable via test fixture).
4. New file in the PR → all its lines counted; deleted file → ignored; comments-only change → skipped.
5. With `GITHUB_ACTIONS=true` and uncovered changed lines, output contains `::warning` annotations with correct `file/line/end_line`; with the flag false, none are emitted.
6. `--json` output includes the `patch` section with totals and per-file entries matching the terminal table.
7. `--patch` without `--base` → exit 2 with an actionable error message.
8. Combined `--patch-fail-under` + `--fail-on-regression`: either failure → exit 1.
9. Existing `coverage diff` behavior without `--patch` is unchanged (no regressions in existing test suite).

## Out of Scope

- Branch-point-aware patch coverage (patch metric is line-based in v1; branch points remain a full-coverage concern).
- HTML report patch view/tab.
- Config-file keys (`[coverage] patch_min`, `patch_base`) — CLI flags only in this track.
- Auto-detecting the base from `GITHUB_BASE_REF`.
- Requiring or consuming a baseline/base-side coverage snapshot.
- Codecov/third-party uploader integration.
