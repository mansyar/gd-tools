# Plan: Config JSON Schema + Docs Pass

**Track:** `config_schema_docs_20261001`

## Phase 1: `$schema` Key Support in Config Model
- [ ] Task: Write failing tests for `$schema` key acceptance (Red)
  - [ ] Test: `gd-tools.toml` with `$schema = "..."` loads and validates successfully
  - [ ] Test: `$schema` key does not appear in the parsed config model dump
  - [ ] Test: unknown typo'd keys still fail validation (`extra='forbid'` unchanged)
  - [ ] Test: `config validate` on a `$schema`-bearing config exits 0
- [ ] Task: Implement `$schema` handling in the Pydantic root model (Green)
- [ ] Task: Verify coverage for the changed module (≥80% line / ≥70% branch)
- [ ] Task: Commit (`feat(config): accept and ignore $schema key in gd-tools.toml`) + attach git note
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: `gd-tools config schema` Command
- [ ] Task: Write failing tests for the schema command (Red)
  - [ ] Test: `config schema` prints valid JSON Schema with `$schema` = draft 2020-12 and `$id`
  - [ ] Test: schema output is derived from the live Pydantic model (mutating a model field changes output)
  - [ ] Test: `--output <path>` writes the schema to file, creating parent dirs
  - [ ] Test: exit code 0 on success; error path for unwritable target exits 2
  - [ ] Test: schema output includes top-level sections (`godot`, `test`, `lint`, `format`, `coverage`) matching model structure
- [ ] Task: Implement `schema` subcommand in the config command group (Green)
- [ ] Task: Refactor & verify coverage for the new module (≥80% line / ≥70% branch)
- [ ] Task: Commit (`feat(config): add config schema command exposing JSON Schema`) + attach git note
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Checked-in Snapshot + Sync Test + README
- [ ] Task: Write failing sync test (Red)
  - [ ] Test: `docs/gd-tools.schema.json` is byte-identical to current model schema output; failure message includes the regeneration command
- [ ] Task: Generate and commit `docs/gd-tools.schema.json` (Green)
- [ ] Task: Document schema usage in README (`$schema` key example + editor-side association for taplo/VS Code Even Better TOML)
- [ ] Task: Commit (`feat(config): check in generated JSON Schema snapshot with sync test`) + attach git note
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Docs Truth Pass
- [ ] Task: Fix CHANGELOG v0.5.0 "Known Limitations" stale editor-plugin claim
- [ ] Task: Refresh stale ROADMAP Phase 5 checkboxes/status entries to match delivered reality
- [ ] Task: Targeted sweep of README + `docs/` for demonstrably false claims; correct only verified drift
- [ ] Task: Update CHANGELOG Unreleased section with schema feature + docs fixes
- [ ] Task: Commit (`docs: truth pass — correct stale claims and record schema feature`) + attach git note
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5: Track Finalization
- [ ] Task: Full quality gate: `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest --cov=gd_tools --cov-branch`
- [ ] Task: Verify all acceptance criteria from spec.md
- [ ] Task: Commit (`conductor(plan): mark track complete`) + final checkpoint (Refer to workflow.md)
