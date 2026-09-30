# Implementation Plan — Docs Truth Pass v0.5.0

- **Track ID:** `docs_truth_pass_v050_20260930`
- **Workflow notes:** Documentation-only chore. Per `workflow.md`, tests are
  required only for source code (`.py`/`.gd`); no TDD or coverage tasks apply.
  Quality gates that still apply: no lint regressions (docs don't affect
  `ruff`/`black`), surgical edits, proper commit messages, git notes on
  checkpoint commits.

## Phase 1 — Sweep & Evidence Collection

- [ ] Task: Grep all markdown for stale v0.5.0 claims
  - Sweep `README.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `docs/ROADMAP.md`,
    and all other reachable `.md` files for: "sequentially", "parallel",
    "parameterize", "skip_test", "watch", "baseline", "diff", "no cover",
    "deprecat", editor-plugin capability rows.
  - Enumerate every match with file/line + current wording.
  - For each candidate claim, locate backing evidence in `src/gd_tools/`
    (e.g., `--parallel` in `test_runner.py`, parameterize handling in the
    native runtime, preflight behavior) and record verdict: stale / accurate.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Apply Verified Fixes

- [ ] Task: Fix README.md
  - Known limitations paragraph (~lines 186-187): replace sequential-only
    claim with shipped `--parallel N` behavior.
  - Bridge capability table: update `parameterize()` row (no longer
    "unsupported / preflight rejects").
  - Any other sweep-confirmed stale lines only.
- [ ] Task: Fix CHANGELOG.md
  - Rewrite v0.5.0 "Known Limitations" bullets in place to reflect current
    reality.
  - Add a `Fixed` bullet noting the documentation correction.
- [ ] Task: Fix ARCHITECTURE.md
  - Known-limitations section: apply sweep-confirmed corrections only.
- [ ] Task: Fix docs/ROADMAP.md
  - Mark Phase 5 "optional parallel execution (deferred)" as delivered.
  - Keep remaining deferred items (native runtime caching, v0.5.0
    publication, bridge removal v0.6.0) listed as open.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Final Verification & Closure

- [ ] Task: Re-run sweep grep to confirm no stale claims remain
  - Confirm no non-doc files were touched (`git status` clean of code/config).
- [ ] Task: Commit docs changes (`docs: ...`) and update plan statuses
  - Mark completed tasks `[x]` with commit SHA, commit plan update.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
