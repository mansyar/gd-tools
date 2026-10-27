# Conductor Migration Report

- **Date:** 2026-10-27
- **From:** Conductor 1.x
- **To:** Conductor 2.0
- **Mode:** Upgrade in place

## Context

- **Preserved:** `product.md`, `tech-stack.md`, `product-guidelines.md`
- **Regenerated:** `workflow.md` with Workflow Config and Verification Strategy
- **Index:** merged in place; version marker added
- **Scaffolding:** `tracks.md`, `tracks/`, `.conductor/` ignore
- **Agents:** installed (OpenCode host, template v2.2)

## Tracks

No active tracks exist under `conductor/tracks/` (only `.gitkeep`). All 90
prior tracks live under `conductor/archive/` and are kept as historical.

| Track | Status | Missing metadata | Plan v2 | Spec v2 | Recommended action |
| --- | --- | --- | --- | --- | --- |
| *(none active)* | — | — | — | — | Keep archive as historical |

## Open Questions & Assumptions

- None. Product context was preserved as-is; workflow values were inferred
  from the repo (Python CLI + GDScript, pytest/ruff/black, base `main`) under
  the Default profile with project-gate coverage and watch-CI PR policy.

## Limits

- Legacy tracks are blocked by `conductor-implement`, `conductor-review`, and
  phase revert until they are recreated or manually repaired.
- Old specs and plans were not rewritten automatically.
- When a track is repaired, remove `legacy: true` from its metadata and update
  the spec/plan to the v2 contract.
- The pre-migration directory is backed up at
  `.conductor/backups/conductor-v1-20261027-181542/`.
- v2 runs sequentially in the current worktree and creates no worktrees. If
  `.conductor/worktrees/` exists, run `git worktree prune` and delete the
  directory manually after confirming the entries are no longer needed.
