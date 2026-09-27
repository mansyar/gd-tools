# Track: Coverage Diff

**ID:** `coverage_diff_20260928`
**Type:** Feature
**Roadmap reference:** docs/ROADMAP.md — Track 33, Phase 8 (Differentiators)
**Dependencies:** Coverage reporter/orchestrator (v1 Track 12/13), coverage CLI command group
**Status:** new

---

## Overview

Coverage today is a single snapshot: `gd-tools coverage` reports how much of the
code is covered right now, but there is no way to see what *changed* between a
base state and the current state. A developer reviewing a PR cannot tell whether
their change added or removed coverage.

This track adds two subcommands to the existing `coverage` command group:

- `gd-tools coverage save-baseline` — persists the current run's coverage data
  as a baseline file.
- `gd-tools coverage diff --base <baseline.json>` — compares the current run's
  coverage data against that baseline and reports per-file line and branch
  deltas, with optional regression gating for CI.

The feature is pure Python: it operates on coverage data files already produced
by the coverage system. No Godot process is involved.

## Confirmed Decisions

| Decision | Choice |
|---|---|
| Baseline location for `diff` | Explicit `--base <path>` argument only (no implicit default) |
| Baseline file format | Reuses the existing coverage-data JSON format verbatim (no new schema) |
| Baseline metadata | `save-baseline` stamps advisory metadata (saved-at timestamp, git branch and commit SHA when available); the diff computation never depends on it |
| Regression gate | `--fail-on-regression`: any per-file decrease in line OR branch rate exits 1 |
| Metrics | Line and branch deltas (both), mirroring the existing terminal/HTML reporters |
| Terminal output | Summary table by default; newly-uncovered line detail behind a flag |
| Error handling | Exit 2 for missing/malformed baseline, missing current coverage data, or malformed current data |
| HTML diff report | Out of scope (candidate follow-up) |

## Functional Requirements

### FR-1: `gd-tools coverage save-baseline`

- Reads the latest run's coverage data from the working tree (the location the
  coverage system already writes to under `.gd-tools/coverage/`).
- Writes it unchanged as the baseline to `.gd-tools/coverage/baseline.json`.
- Adds an advisory metadata block (e.g., `baseline_meta`) with:
  - `saved_at` — UTC timestamp of when the baseline was saved.
  - `git_branch` and `git_commit` — when the working tree is inside a git
    repository; omitted (or null) otherwise. Detection failure is not an error.
- Exits `2` with an actionable message when no current coverage data exists.
- Re-running overwrites the previous baseline (the baseline is single-valued).

### FR-2: `gd-tools coverage diff`

- `--base <path>` is **required**. The file must be a coverage-data JSON file
  (the same format `save-baseline` stores).
- Current coverage data is read from the same working-tree location as FR-1.
- Computes, per file:
  - Line metrics: executable/covered counts and rate for base and head, delta in
    covered-line count and in rate points.
  - Branch metrics: same shape as line metrics.
  - File classification: `unchanged`, `improved`, `regressed`, `new` (present
    only in head), `removed` (present only in baseline).
- Terminal output (default): a Rich summary table — one row per file plus a
  total row — using the shared `output.py` helpers and project color semantics
  (green = improvement, red = regression, dim = paths; ASCII-only markers).
  Baseline metadata, when present, is shown as a one-line context header.
- Line detail (behind a flag, e.g. `--show-lines`): for files with regressions,
  lists newly-uncovered line numbers (present in baseline's covered set but
  absent in head's). Suppressed for improved/unchanged files.
- `--report-format json`: machine-readable diff output containing per-file
  metrics, classifications, newly-uncovered lines, totals, and (when present)
  the baseline metadata. Structure is deterministic and documented.
- `--fail-on-regression`: exits `1` if any file's line rate or branch rate is
  lower in head than in baseline. Without the flag, a regression is reported
  but the exit code is `0`.

### FR-3: Exit codes (existing project semantics preserved)

| Code | Meaning for this track |
|---|---|
| `0` | Diff computed successfully (no regression, or gate not enabled) |
| `1` | Diff computed; `--fail-on-regression` enabled and at least one file regressed |
| `2` | Missing or malformed baseline file; missing or malformed current coverage data; invalid arguments |

## Non-Functional Requirements

- **No new runtime dependencies.** Everything is stdlib + existing deps (Rich,
  Pydantic where validation helps).
- **Pure Python.** No Godot subprocess, no plan generation, no instrumentation.
- **Consistency.** Reuses `output.py` helpers, existing exit-code conventions,
  and existing coverage-data parsing where a parser already exists; avoids
  duplicating load logic.
- **Code quality.** Type hints, docstrings on all public functions, `ruff` and
  `black` clean; new code meets >80% line and >70% branch coverage.
- **Cross-platform.** Paths handled portably (Windows/macOS/Linux).

## Acceptance Criteria

1. `gd-tools coverage save-baseline` writes `.gd-tools/coverage/baseline.json`
   containing the current coverage data plus advisory metadata.
2. Saving a baseline when no coverage data exists exits `2` with an actionable
   message and writes no file.
3. `gd-tools coverage diff --base <baseline.json>` prints a per-file table with
   base/head line and branch counts, rates, and deltas, plus a total row.
4. New covered lines are highlighted as improvements; newly uncovered lines as
   regressions; rate decreases are visually distinct in the table.
5. Files present only in head are shown and classified as `new`; files present
   only in the baseline are reported as `removed`.
6. `--show-lines` lists newly-uncovered line numbers for regressed files.
7. `--report-format json` emits valid, deterministic JSON covering per-file
   metrics, classifications, newly-uncovered lines, and totals.
8. `--fail-on-regression` exits `1` when any file's line or branch rate
   decreased; otherwise the diff exits `0` even when regressions are reported.
9. A missing or malformed baseline file exits `2`; a missing or malformed
   current coverage dataset exits `2`.
10. All existing tests pass; new modules meet the coverage gates (>80% line,
    >70% branch); `ruff check` and `black --check` pass.
11. USER_GUIDE documents both subcommands, the JSON shape, and a CI usage
    snippet showing `save-baseline` on main and `diff --fail-on-regression` on
    PRs.

## Out of Scope

- HTML diff report rendering (follow-up candidate).
- Resolving baselines from git refs or CI artifact storage (`--base main`).
- Configurable per-file regression tolerance.
- Coverage exclusion annotations (Track 30 — separate track).
- Baseline history / trend storage (single-valued baseline only).
- Branch-diff integration with the native runtime or GDScript side.

## Open Items (resolved during planning)

- Exact flag name for line detail (`--show-lines` proposed).
- Exact JSON key names for the diff output (align with existing reporter style).
- Where shared data-loading logic lives if the existing parser needs a thin
  adapter (surgical change preferred; no refactor of existing modules).
