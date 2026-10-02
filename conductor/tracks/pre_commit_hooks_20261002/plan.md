# Implementation Plan: Pre-commit Hook Integration

**Track ID:** `pre_commit_hooks_20261002`
**Branch:** `feature/pre-commit-hooks-20261002`
**Workflow:** TDD (tests before implementation), phase checkpoints per workflow.md

## Phase 1: Core Hook Generation Module (`pre_commit.py`)

- [ ] Task: Write failing tests — hook file content generation
      (`.pre-commit-hooks.yaml` + per-hook entries, `files: \.gd$` filters,
      `language: system`)
  - [ ] Test: format/lint/test entries render with correct id, name, entry, args
  - [ ] Test: selection filtering (`--hooks test` alone → test entry only)
- [ ] Task: Write failing tests — merge-by-id logic in `.pre-commit-config.yaml`
  - [ ] Test: fresh file → creates `repos: local:` block
  - [ ] Test: existing file with foreign hooks → foreign hooks untouched,
        gd-tools entries added
  - [ ] Test: drifted existing gd-tools entries → updated in place by id
  - [ ] Test: deselected-but-present gd-tools hook → reported, left intact
  - [ ] Test: malformed YAML → raises config error (maps to exit 2)
- [ ] Task: Implement `pre_commit.py` to pass tests
- [ ] Task: Verify coverage (≥80% line / ≥70% branch) on new module
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: CLI Command Wiring

- [ ] Task: Write failing tests — `gd-tools install-hooks` command
  - [ ] Test: interactive prompt toggles (format ✅ / lint ✅ / test ❌ defaults)
  - [ ] Test: `--all`, `--hooks`, `--non-interactive` flags
  - [ ] Test: non-TTY + no flags → default pair (format + lint), exit 0
  - [ ] Test: exit codes — 0 installed, 1 nothing-to-do, 2 config/environment
        error
- [ ] Task: Implement command in `cli.py` (registration, flags, rich prompt,
      output helpers)
- [ ] Task: Full suite green (`CI=true pytest`) + quality gates (ruff, black)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Documentation

- [ ] Task: README — install-hooks section with `.pre-commit-config.yaml`
      example
- [ ] Task: USER_GUIDE — per-hook setup, merge-by-id behavior,
      non-interactive/CI usage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
