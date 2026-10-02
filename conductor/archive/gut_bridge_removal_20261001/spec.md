# Specification: GUT Bridge Removal (v0.6.0)

**Track ID:** `gut_bridge_removal_20261001`
**Type:** Refactor (breaking removal)
**Status:** Draft
**Branch:** `feature/gut-bridge-removal-20261001`
**Origin:** `conductor/product.md` §9 migration boundary (bridge removal targeted
v0.6.0); ROADMAP Phase 5; deprecation notices shipped in
`gut_compat_bridge_20260928`.

## Overview

One release after its v0.5.0 deprecation, this track removes the **GUT
Compatibility Bridge runtime** — the `GutTest` shim base class, `extends
GutTest` auto-routing, and bridge result normalization — making the native
`GdToolsTest` runtime the sole test runtime. The `gd-tools migrate` command
and its scan/translation machinery are **retained** as the permanent migration
path for users upgrading from ≤v0.5.0. The track concludes with v0.6.0
release preparation.

## Functional Requirements

- **FR-1 — Shim removal.** Delete the `GutTest` shim GDScript from
  `src/gd_tools/addons/gd-tools-test/`. Discovery no longer routes `extends
  GutTest` suites to a bridge; it fails (exit 2) naming each file with
  migration guidance ("run `gd-tools migrate` or see docs/gut-migration.md").
- **FR-2 — Explicit `--runtime gut` error.** The CLI value remains parsed but
  exits 2: *"GUT runtime support was removed in v0.6.0. The native runtime is
  the default. Run `gd-tools migrate` or see docs/gut-migration.md."* Not
  silently remapped.
- **FR-3 — Hard config validation.** `runtime = "gut"` and GUT-era config
  keys are hard validation errors (exit 2) in `config validate` and test
  preflight, with migration guidance.
- **FR-4 — `init --with-gut` removed.** The option is deleted from `init`
  (Click's standard unknown-option error applies); the docs cover the removal
  path.
- **FR-5 — Doctor as migration advisor.** `doctor` detects legacy GUT
  artifacts (`addons/gut`, `.gutconfig.json`, `GutTest` suites) and reports
  informational migration advice; GUT is no longer treated as a supported
  runtime. Bridge deprecation notices in `command.py`, `doctor.py`,
  `init.py` are removed.
- **FR-6 — `gd-tools migrate` retained and updated.** Full behavior preserved
  (report, `.gutconfig.json` translation, `--apply` renames).
  `native_test/bridge_scan.py` is **kept** (migrate's scanner). Guidance text
  updated for the v0.6.0 reality: the bridge no longer exists; migration is
  required to run legacy suites.
- **FR-7 — Test/fixture cleanup.** Bridge-only tests and fixtures deleted;
  new tests assert the removal behaviors (FR-1/2/3/5 errors + migrate still
  working).
- **FR-8 — v0.6.0 release prep.** Version bump to 0.6.0, CHANGELOG release
  section, and a full docs truth pass (README, USER_GUIDE, ARCHITECTURE, PRD,
  ROADMAP Phase 5 checkbox, `docs/gut-migration.md`, `gd-tools.schema.json`
  if the runtime enum changes).

## Non-Functional Requirements

- Exit-code contract unchanged (0 pass / 1 test or coverage failure / 2
  env/config error).
- TDD per `workflow.md`; coverage gate ≥80% line / ≥70% branch maintained.
- No new dependencies; Rich/output conventions unchanged.

## Acceptance Criteria

1. A project with `extends GutTest` suites fails `gd-tools test` (exit 2)
   naming files with migration guidance.
2. `--runtime gut` exits 2 with the v0.6.0 removal message.
3. `config validate` hard-errors on `runtime = "gut"` and GUT-era keys.
4. `doctor` reports legacy GUT artifacts as informational migration advice.
5. `gd-tools migrate` retains full report/translate/apply behavior on a
   legacy project.
6. No bridge runtime code remains (shim, routing, normalization); the
   scanner survives only as migrate's dependency.
7. Docs truth pass complete; version bumped; CHANGELOG release section
   written.
8. Full test suite passes; ruff/black clean; coverage gate holds.

## Out of Scope

- Removing the migration tooling itself (`migrate`, scan/translate/reporter).
- Native runtime or coverage behavior changes beyond deprecation-notice
  removals.
- Pre-commit hooks / GitHub Actions annotations (separate candidate tracks).
- Call-site alias rewrites in `migrate` (still reported, not rewritten).
