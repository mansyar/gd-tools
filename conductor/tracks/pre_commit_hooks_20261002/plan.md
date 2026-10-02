# Implementation Plan: Pre-commit Hook Integration

**Track ID:** `pre_commit_hooks_20261002`
**Branch:** `feature/pre-commit-hooks-20261002`
**Workflow:** TDD (tests before implementation), phase checkpoints per workflow.md

## Phase 1: Core Hook Generation Module (`pre_commit.py`)

- [x] Task: Write failing tests — hook file content generation
      (`.pre-commit-hooks.yaml` + per-hook entries, `files: \.gd$` filters,
      `language: system`)
  - [x] Test: format/lint/test entries render with correct id, name, entry, args
  - [x] Test: selection filtering (`--hooks test` alone → test entry only)
- [x] Task: Write failing tests — merge-by-id logic in `.pre-commit-config.yaml`
  - [x] Test: fresh file → creates `repos: local:` block
  - [x] Test: existing file with foreign hooks → foreign hooks untouched,
        gd-tools entries added
  - [x] Test: drifted existing gd-tools entries → updated in place by id
  - [x] Test: deselected-but-present gd-tools hook → reported, left intact
  - [x] Test: malformed YAML → raises config error (maps to exit 2)
- [x] Task: Implement `pre_commit.py` to pass tests
- [x] Task: Verify coverage (≥80% line / ≥70% branch) on new module
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
      [checkpoint: 936a9ff]

## Phase 2: CLI Command Wiring

- [x] Task: Write failing tests — `gd-tools install-hooks` command
      (12 CLI tests written red-first; one design correction: `--hooks` uses
      comma-separated values with `flag_value=""` so a bare `--hooks`
      resolves to nothing-to-do/exit 1 instead of a click usage error)
  - [ ] Test: interactive prompt toggles (format ✅ / lint ✅ / test ❌ defaults)
  - [ ] Test: `--all`, `--hooks`, `--non-interactive` flags
  - [ ] Test: non-TTY + no flags → default pair (format + lint), exit 0
  - [ ] Test: exit codes — 0 installed, 1 nothing-to-do, 2 config/environment
        error
- [x] Task: Implement command in `cli.py` (registration, flags, rich prompt,
      output helpers)
- [x] Task: Full suite green (`CI=true pytest`) + quality gates (ruff, black)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Documentation

- [ ] Task: README — install-hooks section with `.pre-commit-config.yaml`
      example
- [ ] Task: USER_GUIDE — per-hook setup, merge-by-id behavior,
      non-interactive/CI usage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
