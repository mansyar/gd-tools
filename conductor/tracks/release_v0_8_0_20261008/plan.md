# Implementation Plan: Release v0.8.0

> TDD is not applicable — this track changes no `.py`/`.gd` source files.
> Verification is procedural per workflow.md's CLI-feature manual verification format.

## Phase 1 — Bump & verify

- [ ] Task: Bump version via commitizen
  - [ ] Run `cz bump --version 0.8.0` (bump commit + `v0.8.0` tag created locally)
  - [ ] Verify `pyproject.toml` shows `0.8.0` in both version fields
- [ ] Task: Finalize changelog
  - [ ] Confirm/change `## Unreleased` → `## v0.8.0 (2026-10-08)` (include in the bump commit via `git commit --amend --no-edit` if uncommitted, else a `docs:` follow-up before tag)
- [ ] Task: Release checklist on the bumped tree (AFTER bump — v0.7.0 lesson)
  - [ ] Fresh `pip install -e ".[dev]"` completes cleanly
  - [ ] `gd-tools version` prints `0.8.0`
  - [ ] `CI=true pytest` — full suite green
  - [ ] `ruff check src/ tests/` and `black --check src/ tests/` clean
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Tag & publish

- [ ] Task: Push and watch the release workflow
  - [ ] Confirm with user before the point of no return (NFR-3)
  - [ ] `git push origin main` + `git push origin v0.8.0`
  - [ ] Watch `release.yml`: build → TestPyPI stage green → PyPI stage green
  - [ ] Verify `gd-tools-cli 0.8.0` visible on PyPI
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
