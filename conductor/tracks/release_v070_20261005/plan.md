# Implementation Plan — Ship v0.7.0

**Track ID:** release_v070_20261005
**Branch:** `feature/release-v070-20261005`
**Spec:** [spec.md](./spec.md)

> Note: This is a chore/release track. Per workflow.md, TDD applies only to source
> code files (`.py`, `.gd`); this track modifies documentation, configuration, and
> release automation, so no new tests are required unless source code changes.

## Phase 1: Documentation Truth Pass

- [x] Task: Audit documentation against the v0.7.0 feature set
  - [x] Audit README.md for GH Actions annotations, `--min-branch`, spy framework upgrades (`any` wildcard, `to_return_seq`, `to_fail`, `assert_call_order`, `assert_property_is`), and the `error` test outcome
  - [x] Audit docs/USER_GUIDE.md for the same features plus snapshot testing and `[coverage].format github-actions`
  - [x] Audit docs/ARCHITECTURE.md for stale GUT-era or pre-v0.6.0 content
  - [x] Audit docs/gd-tools.schema.json consistency with the current config model (min_branch, coverage format enum)
  - [x] Apply documentation updates for all gaps found
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Pre-Release Verification

- [ ] Task: Run the workflow.md pre-release checklist
  - [ ] `CI=true pytest` — full suite green with coverage >80% line / >70% branch
  - [ ] `ruff check src/ tests/` and `black --check src/ tests/` clean
  - [ ] `python -m build` produces fresh sdist + wheel
  - [ ] `twine check dist/*` passes on fresh artifacts
  - [ ] `gd-tools --version` reports the current version correctly
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Release Execution

- [ ] Task: Bump version via commitizen
  - [ ] Run `cz bump` (expect minor bump to 0.7.0, dated `## v0.7.0` CHANGELOG section, `v0.7.0` tag created)
  - [ ] Verify CHANGELOG content, `pyproject.toml` version, and tag
- [ ] Task: Merge to main and push tag
  - [ ] Merge feature branch to `main`
  - [ ] Push `main` and the `v0.7.0` tag to origin
- [ ] Task: Verify automated release pipeline
  - [ ] Confirm `.github/workflows/release.yml` run is green (build → twine check → TestPyPI → PyPI)
  - [ ] Confirm package is live on PyPI at version 0.7.0
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
