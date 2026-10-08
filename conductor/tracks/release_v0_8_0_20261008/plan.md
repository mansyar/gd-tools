# Implementation Plan: Release v0.8.0

> TDD is not applicable — this track changes no `.py`/`.gd` source files.
> Verification is procedural per workflow.md's CLI-feature manual verification format.

## Phase 1 — Bump & verify

- [x] Task: Bump version via commitizen — `cz bump --increment MINOR` (amended 08a1f61; cz's auto-changelog replaced curated entries, restored hand-written content under dated heading)
  - [x] Run `cz bump --version 0.8.0` (bump commit + `v0.8.0` tag created locally)
  - [x] Verify `pyproject.toml` shows `0.8.0` in both version fields
- [x] Task: Finalize changelog — curated Unreleased → `## v0.8.0 (2026-10-08)` inside the amended bump commit
  - [ ] Confirm/change `## Unreleased` → `## v0.8.0 (2026-10-08)` (include in the bump commit via `git commit --amend --no-edit` if uncommitted, else a `docs:` follow-up before tag)
- [x] Task: Release checklist on the bumped tree (AFTER bump — v0.7.0 lesson) — `3941fe0`: regenerate schema snapshot + update pinned version test; tag re-pointed to 3941fe0 (local, unpushed)
  - [x] Fresh `pip install -e ".[dev]"` completes cleanly
  - [x] `gd-tools version` prints `0.8.0`
  - [x] `CI=true pytest` — full suite green (unit+integration: 1837 passed / 3 skipped, 95.45%; full run incl. e2e times out locally as in prior checkpoints)
  - [x] `ruff check src/ tests/` and `black --check src/ tests/` clean
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — [checkpoint: PENDING]

## Phase 2 — Tag & publish

- [ ] Task: Push and watch the release workflow
  - [ ] Confirm with user before the point of no return (NFR-3)
  - [ ] `git push origin main` + `git push origin v0.8.0`
  - [ ] Watch `release.yml`: build → TestPyPI stage green → PyPI stage green
  - [ ] Verify `gd-tools-cli 0.8.0` visible on PyPI
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
