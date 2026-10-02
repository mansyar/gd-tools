# Specification: Pre-commit Hook Integration

**Track ID:** `pre_commit_hooks_20261002`
**Type:** Feature
**Roadmap ref:** Track 29 (docs/ROADMAP.md)
**Branch:** `feature/pre-commit-hooks-20261002`

## Overview

Add a `gd-tools install-hooks` command that wires gd-tools into the
[pre-commit](https://pre-commit.com) framework, giving Godot projects automatic
format-checking, linting, and optional test runs on every commit. The command
generates `.pre-commit-hooks.yaml` and writes a `repos: local:` entry block into
`.pre-commit-config.yaml`, with idempotent re-runs that merge by hook id and
never clobber foreign hooks.

## Functional Requirements

### FR-1 — `gd-tools install-hooks` command
- New top-level CLI command registered in the `gd-tools` group.
- Interactive prompt (rich) asks the user to toggle each of three hooks:
  `format --check`, `lint`, `test`. Defaults: format ✅, lint ✅, test ❌.
- Flags:
  - `--all` — enable all three hooks.
  - `--hooks <list>` — explicit selection (e.g. `--hooks format lint`).
  - `--non-interactive` — skip the prompt; apply defaults or explicit flags.

### FR-2 — File generation (both files)
- Generates `.pre-commit-hooks.yaml` in the project root (hook metadata: id,
  name, entry, `language: system`, `files: \.gd$` for format/lint).
- Writes/merges a `repos: local:` entry into `.pre-commit-config.yaml` with a
  `hooks:` list per selected feature.
- The test hook entry is plain `gd-tools test` (no baked flags; `[test]`
  config, including `min_coverage` if configured, applies).

### FR-3 — Idempotent merge-by-id re-runs
- Match gd-tools hook entries by id: `gd-tools-format`, `gd-tools-lint`,
  `gd-tools-test`.
- Re-run behavior: updates existing gd-tools entries in place (correcting
  drifted `entry`/`args`), adds missing ones, never touches foreign hooks or
  foreign keys.
- Never removes previously-added hooks; if a hook was deselected but is still
  present in the file, report it (informational) and leave it intact.

### FR-4 — Non-TTY behavior
- No TTY + no flags → install the default pair (format + lint) without
  prompting. CI-friendly per product guidelines.
- No TTY + `--all` → install all three hooks.

### FR-5 — Exit codes
- `0` — hooks installed/updated.
- `1` — nothing to do (e.g. `--non-interactive` selection resolves to zero
  hooks) or file-write failure.
- `2` — config/environment error (bad project root, malformed existing
  `.pre-commit-config.yaml`).

### FR-6 — Documentation
- README section and USER_GUIDE section: per-hook setup, copy-pasteable
  `.pre-commit-config.yaml` example, `--non-interactive` CI usage, and the
  merge-by-id re-run behavior.

## Non-Functional Requirements

- **NFR-1:** Output via existing output helpers; no direct `click.echo` in new
  code (project style).
- **NFR-2:** >80% line / >70% branch coverage on new source (`pre_commit.py`
  module + CLI wiring).
- **NFR-3:** Cross-platform (Windows/macOS/Linux); YAML merge preserves
  existing content; existing comments preserved where feasible with PyYAML.
- **NFR-4:** No new runtime dependencies (PyYAML is already a dependency).

## Acceptance Criteria

1. `gd-tools install-hooks` on a fresh project prompts, writes both files,
   exits 0.
2. Re-running with the same/different selection updates only gd-tools
   entries; foreign hooks untouched.
3. Non-TTY run installs format+lint without prompting, exit 0.
4. `--hooks test` alone generates only the test hook entry.
5. Malformed `.pre-commit-config.yaml` → exit 2 with an actionable error.
6. Docs cover both files and the merge behavior.
7. All unit tests pass; coverage thresholds met.

## Out of Scope

- Running pre-commit itself, or other hook frameworks (husky, lefthook).
- An `uninstall-hooks` command (users remove entries manually).
- Baking `--min`/`--changed` into the generated test hook.
- Hook management for VCS other than git.
