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
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Pre-Release Verification

- [x] Task: Run the workflow.md pre-release checklist
  - [x] `CI=true pytest` — full suite green with coverage >80% line / >70% branch
  - [x] `ruff check src/ tests/` and `black --check src/ tests/` clean
  - [x] `python -m build` produces fresh sdist + wheel
  - [x] `twine check dist/*` passes on fresh artifacts
  - [x] `gd-tools --version` reports the current version correctly
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Release Execution

- [x] Task: Bump version via commitizen
  - [x] Run `cz bump` (expect minor bump to 0.7.0, dated `## v0.7.0` CHANGELOG section, `v0.7.0` tag created)
  - [x] Verify CHANGELOG content, `pyproject.toml` version, and tag
- [x] Task: Merge to main and push tag
  - [x] Merge feature branch to `main`
  - [x] Push `main` and the `v0.7.0` tag to origin
- [x] Task: Verify automated release pipeline
  - [x] Confirm `.github/workflows/release.yml` run is green (build → twine check → TestPyPI → PyPI)
  - [x] Confirm package is live on PyPI at version 0.7.0
- [x] Task: Post-merge CI hotfix (release gates pin pre-bump state)
  - [x] Fix `test_package_version_is_0_6_0` → `test_package_version_is_0_7_0` (fresh-install CI caught the stale pin)
  - [x] Regenerate `docs/gd-tools.schema.json` (schema embeds the package version)
  - [x] Re-run full unit suite green (1479 passed)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
