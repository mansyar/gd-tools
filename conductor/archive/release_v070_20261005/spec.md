# Specification — Ship v0.7.0

**Track ID:** release_v070_20261005
**Type:** Chore (Release)
**Branch:** `feature/release-v070-20261005`

## Overview

Cut the v0.7.0 release. Post-v0.6.0 work (GitHub Actions annotations for lint and coverage, the `--min-branch` coverage gate, `[coverage].format github-actions`, spy framework upgrades — `any` wildcard, `to_return_seq`, `to_fail`, `assert_call_order`, `assert_property_is` — the script-error → `error` outcome fix, and ternary instrumentation fixes) currently sits under an undated "Unreleased" CHANGELOG section. This track versions, documents, verifies, and tags that work so users receive it via `pip install`.

Publishing is automated: `.github/workflows/release.yml` triggers on any `v*` tag push (build → `twine check` → TestPyPI → production PyPI). No local upload step is required.

## Functional Requirements

1. **Version bump via commitizen** — run `cz bump` to set version `0.7.0` in `pyproject.toml` (package `gd-tools-cli`) and generate a dated `## v0.7.0` CHANGELOG section from the Unreleased content, creating the `v0.7.0` tag per the documented `v$version` tag convention. Features present in the unreleased set make a minor bump correct.
2. **Full documentation truth pass** — audit and update README, USER_GUIDE, ARCHITECTURE, and `docs/gd-tools.schema.json` against the v0.7.0 feature set:
   - Verify GH Actions annotations usage (`[coverage].format github-actions`, lint/coverage annotation output) is documented.
   - Verify `--min-branch` / `[coverage].min_branch` is documented.
   - Verify spy framework upgrades (`any` wildcard, `to_return_seq`, `to_fail`, `assert_call_order`, `assert_property_is`) are documented in USER_GUIDE.
   - Verify the script-error → `error` outcome and ternary instrumentation fixes are reflected where behavior is described.
   - Confirm no stale GUT-era or pre-v0.6.0 content remains.
3. **Pre-release verification** — run the workflow.md pre-release checklist locally: full pytest suite (`CI=true pytest`), coverage gates (>80% line / >70% branch), `ruff check src/ tests/`, `black --check src/ tests/`, `python -m build`, `twine check dist/*`.
4. **Release trigger** — merge to `main` and push the `v0.7.0` tag, firing `.github/workflows/release.yml`. Verify the workflow goes green and the package is live on PyPI.

## Acceptance Criteria

- [ ] `pyproject.toml` version is `0.7.0` and `gd-tools --version` reports it.
- [ ] CHANGELOG has a dated `## v0.7.0` section; "Unreleased" is empty or removed.
- [ ] All v0.7.0 features are documented in README/USER_GUIDE; no stale documentation remains.
- [ ] Local pre-release checklist passes (tests, coverage, lint, format, build, twine check).
- [ ] Tag `v0.7.0` pushed; `release.yml` workflow run succeeds; package live on PyPI.

## Out of Scope

- New features, bug fixes, or refactors beyond documentation corrections discovered during the audit.
- Removing stale `dist/` artifacts beyond what `python -m build` refreshes.
- Any GdUnit4 forward-compatibility work.
