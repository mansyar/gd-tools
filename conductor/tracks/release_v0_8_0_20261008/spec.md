# Specification: Release v0.8.0

## Overview

Ship the v0.8.0 release of `gd-tools` — headlined by Patch Coverage for PRs (`coverage diff --patch`), expression-level branch coverage, and the accumulated Unreleased fixes. The release follows the established commitizen-driven flow: bump to 0.8.0, finalize the changelog, run the full quality checklist **after** the bump (v0.7.0 lesson), tag, and let `release.yml` publish to TestPyPI and PyPI.

## Functional Requirements

| # | Requirement |
|---|---|
| FR-1 | Bump version 0.7.0 → 0.8.0 via `cz bump --version 0.8.0` (updates `pyproject.toml`, creates the bump commit and `v0.8.0` tag; commitizen validates main's conventional commits — feat commits since v0.7.0 justify the minor bump). |
| FR-2 | Finalize `CHANGELOG.md`: rename `## Unreleased` → `## v0.8.0 (2026-10-08)` in the same release commit (include in the bump commit's intent; no separate commit unless cz leaves it uncommitted). |
| FR-3 | Run the release checklist **after** the bump, on the bump commit: fresh `pip install -e ".[dev]"` sanity check; `gd-tools version` reports 0.8.0; `CI=true pytest` full suite green; `ruff check src/ tests/` + `black --check src/ tests/` clean; version consistency between `pyproject.toml` and installed metadata. |
| FR-4 | Push `main` + the `v0.8.0` tag; this triggers `release.yml`. |
| FR-5 | Watch `release.yml` to completion: build wheel/sdist → publish to TestPyPI → publish to production PyPI; verify `gd-tools-cli 0.8.0` appears on PyPI. |
| FR-6 | If any checklist step or workflow stage fails: halt, diagnose, fix on a follow-up commit, and re-tag only if necessary (re-pointing a pushed tag requires deleting it — ask before force-moving). |

## Non-Functional Requirements

- **NFR-1**: No source-code changes beyond version metadata and changelog.
- **NFR-2**: Tag must point at a commit whose tree passed the full checklist.
- **NFR-3**: PyPI publish is irreversible — the tag push is the point of no return and must be explicitly confirmed before pushing.

## Acceptance Criteria

1. `pyproject.toml` version is `0.8.0`; `gd-tools version` prints `0.8.0`.
2. `CHANGELOG.md` has `## v0.8.0 (2026-10-08)` containing the Patch Coverage, expression-level branch coverage, and all Unreleased fixes.
3. Full suite + lint + format pass on the bumped tree.
4. Tag `v0.8.0` exists on the release commit and is pushed.
5. `release.yml` completes: TestPyPI stage green, PyPI stage green.
6. `gd-tools-cli 0.8.0` visible on PyPI.

## Out of Scope

- GitHub Release notes drafting (can be a follow-up).
- Any feature work, docs content beyond the changelog date.
- GdUnit4 runtime integration.
