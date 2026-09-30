# Implementation Plan — Docs Truth Pass v0.5.0

- **Track ID:** `docs_truth_pass_v050_20260930`
- **Workflow notes:** Documentation-only chore. Per `workflow.md`, tests are
  required only for source code (`.py`/`.gd`); no TDD or coverage tasks apply.
  Quality gates that still apply: no lint regressions (docs don't affect
  `ruff`/`black`), surgical edits, proper commit messages, git notes on
  checkpoint commits.

## Phase 1 — Sweep & Evidence Collection [checkpoint: 33fe1ed]

- [x] Task: Grep all markdown for stale v0.5.0 claims
  - Sweep `README.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `docs/ROADMAP.md`,
    and all other reachable `.md` files for: "sequentially", "parallel",
    "parameterize", "skip_test", "watch", "baseline", "diff", "no cover",
    "deprecat", editor-plugin capability rows.
  - Enumerate every match with file/line + current wording.
  - For each candidate claim, locate backing evidence in `src/gd_tools/`
    (e.g., `--parallel` in `test_runner.py`, parameterize handling in the
    native runtime, preflight behavior) and record verdict: stale / accurate.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Apply Verified Fixes [checkpoint: e1f52e4]

- [x] Task: Fix README.md
  - Known limitations paragraph (~lines 186-187): replace sequential-only
    claim with shipped `--parallel N` behavior.
  - Bridge capability table: update `parameterize()` row (no longer
    "unsupported / preflight rejects").
  - Any other sweep-confirmed stale lines only.
- [x] Task: Fix CHANGELOG.md
  - Rewrite v0.5.0 "Known Limitations" bullets in place to reflect current
    reality.
  - Add a `Fixed` bullet noting the documentation correction.
- [x] Task: Fix ARCHITECTURE.md
  - Sweep verdict: Known-limitations section is already accurate (only "No
    editor integration" listed, which is true); no changes required.
  - Known-limitations section: apply sweep-confirmed corrections only.
- [x] Task: Fix docs/ROADMAP.md
  - Also fixed (sweep-confirmed): foundation-defers paragraph (lines 45-49),
    Phase 5 status line (line 1564), and docs/PRD.md Non-Goals #1 +
    Current-runtime-limits sentence (parameterized tests and parallel
    execution shipped).
  - Mark Phase 5 "optional parallel execution (deferred)" as delivered.
  - Keep remaining deferred items (native runtime caching, v0.5.0
    publication, bridge removal v0.6.0) listed as open.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Final Verification & Closure [checkpoint: 7662a33]

- [x] Task: Re-run sweep grep to confirm no stale claims remain
  - Confirm no non-doc files were touched (`git status` clean of code/config).
- [x] Task: Commit docs changes (`docs: ...`) and update plan statuses
  - Mark completed tasks `[x]` with commit SHA, commit plan update.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
