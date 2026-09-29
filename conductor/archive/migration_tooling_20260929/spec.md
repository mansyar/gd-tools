# Specification: Migration Tooling (Roadmap §8 Phase 4)

**Track ID:** `migration_tooling_20260929`
**Type:** Feature
**Branch:** `feature/gut-migration-tooling-20260929`

## Overview

Add a guided `gd-tools migrate` command that helps users move legacy GUT suites to the native runtime end state (`extends GdToolsTest`). It produces a read-only migration report by default, translates `.gutconfig.json` into `gd-tools.toml`, and optionally performs conservative, diff-previewed rewrites.

This fulfills the documented promise in `docs/gut-migration.md` §6 ("`.gutconfig.json` translation arrives with the guided migration tooling") and `product.md`'s migration boundary ("a guided migration command previews changes before rewriting user files").

## Functional Requirements

### 1. Report (default mode, read-only)

- Discovers suites via the same discovery as `gd-tools test` (respects `gd-tools.toml` test paths and include/exclude patterns).
- Per-file inventory: base class (`GdToolsTest` / `GutTest` / other), supported constructs in use, unsupported constructs with `file:line` and migration guidance — reusing the bridge preflight scanner's categories and guidance text from `gut-migration.md`.
- Separate **"works now, rename later"** section listing bridge-only aliases (`assert_in`, `pending_test`, etc.) that run today but have native spellings.
- `.gutconfig.json` mapping results: which options map to `[test]` keys in `gd-tools.toml`, which are unmapped (listed with guidance).
- Unified diffs of all proposed rewrites (shown whenever rewrites are proposed, in every mode).
- Migration state summary: suites ready to rename / bridge-eligible with unsupported constructs / already native.

### 2. Config translation (`--config-only` or part of `--apply`)

- Maps known `.gutconfig.json` options into the `[test]` section of `gd-tools.toml`.
- **Merge, never clobber:** existing user-set values in `gd-tools.toml` are preserved; conflicts are reported for manual resolution.
- Unmapped options are reported, never silently dropped.
- If `.gutconfig.json` is absent, translation is a no-op (reported as such).

### 3. Rewrites (`--apply`)

- Conservative scope only: `extends GutTest` → `extends GdToolsTest` base-class rename, plus config translation. Nothing else is rewritten.
- Files with unsupported constructs are **not** rewritten; they are reported with guidance instead.
- Atomic per-file writes; a failure mid-apply leaves files untouched.

### 4. Exit codes

- `0` = nothing to migrate.
- `1` = migration items found (report generated, nothing written).
- `2` = infrastructure error (unreadable files, parse failures).

## Non-Functional Requirements

- Reuses the existing preflight scanner (`native_test/bridge_scan.py`) rather than duplicating GUT-construct detection.
- Report output uses the existing Rich conventions (`output.py`); no new dependencies.
- Unit-tested with pytest per project standards (TDD per workflow.md).

## Acceptance Criteria

1. `gd-tools migrate` on a project with bridge suites prints the per-file report and exits 1; nothing is modified.
2. A project with only `GdToolsTest` suites and no `.gutconfig.json` prints "nothing to migrate" and exits 0.
3. `--apply` renames only clean bridge suites' base classes and translates config; diffs are shown before writing; unsupported-construct files remain untouched.
4. `.gutconfig.json` translation merges into existing `gd-tools.toml` without overwriting user-set values; conflicts and unmapped options are reported.
5. Unreadable/parse-failing files produce exit 2 with actionable errors.

## Out of Scope

- Phase 5 (crash recovery, parallel execution, bridge removal).
- Call-site alias rewrites (e.g., `assert_in` → native spelling) — reported, not rewritten.
- Mocking/parameterization migration (separate in-progress track).
- `doctor` changes (self-contained command).
- Interactive per-file confirmation prompts.

## Open Items Resolved During Planning

- The exact `.gutconfig.json` option set is not documented in-repo; the plan includes a task to inventory GUT 9.x config options and define the mapping table explicitly.
- Suites containing only bridge-only aliases (no unsupported constructs) are clean by preflight standards and are therefore rewritten under `--apply`; the aliases keep working through the bridge until users rename them manually.
