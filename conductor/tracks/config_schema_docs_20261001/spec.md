# Spec: Config JSON Schema + Docs Pass

**Track ID:** `config_schema_docs_20261001` · **Type:** Feature + Docs Chore · **Branch:** `feature/config-schema-docs-20261001`

## Overview

Publish a JSON Schema for `gd-tools.toml` so users get editor autocomplete, inline validation, and hover documentation. The schema is generated from the Pydantic config model (the single source of truth), delivered via a new `gd-tools config schema` subcommand plus a checked-in snapshot. Accompanied by a targeted documentation truth pass fixing claims that no longer match shipped behavior.

## Functional Requirements

1. **`$schema` key support** — The Pydantic root config model accepts a top-level `$schema` key (string) and ignores it during validation; all other unknown keys still fail with `extra='forbid'` errors. `$schema` must not appear in `config show` output nor affect behavior.
2. **`gd-tools config schema` command** — Under the existing `config` command group:
   - Prints the JSON Schema (draft 2020-12) to stdout.
   - `--output <path>` writes it to a file instead (creating parent dirs).
   - The schema is generated from the live Pydantic model of the *installed* version (never hardcoded).
3. **Checked-in snapshot** — `docs/gd-tools.schema.json` is generated and committed. A test asserts the snapshot is byte-identical to the current model's schema output (drift = test failure with a regen hint). README documents how to reference the schema (`$schema` key in `gd-tools.toml` or editor-side association such as taplo/VS Code Even Better TOML).

## Non-Functional Requirements

- No new runtime dependencies (Pydantic v2's `model_json_schema()` is the generator).
- Schema uses `draft: 2020-12`, includes `$id` and a `description` noting the gd-tools version that produced it.
- Coverage targets per `workflow.md` (>80% line / >70% branch) apply to the new module.

## Acceptance Criteria

- [ ] `gd-tools.toml` with `$schema = "..."` passes `config validate` and test preflight; a typo'd key still errors.
- [ ] `gd-tools config schema` prints valid JSON Schema; `--output` writes it; exit code 0.
- [ ] `docs/gd-tools.schema.json` exists and a sync test passes; deliberately corrupting the model makes the test fail with a clear message.
- [ ] An invalid `gd-tools.toml` validated in an editor against the schema surfaces the error before running the CLI (spot-check with a schema-aware editor).
- [ ] CHANGELOG "Known Limitations" no longer claims the editor plugin is missing; ROADMAP Phase 5 checkboxes match reality; README/docs claims sweep is complete with no known false statements remaining.
- [ ] All tests pass; CI green.

## Out of Scope

- GitHub Actions annotations / SARIF (Roadmap Track 31) — separate track.
- GUT bridge removal (v0.6.0) — separate track.
- Publishing the schema to a stable public URL (e.g., GitHub Pages) — README documents the in-repo path and the CLI command; URL strategy can be revisited later.
- Rewriting documentation structure or style — corrections only.
