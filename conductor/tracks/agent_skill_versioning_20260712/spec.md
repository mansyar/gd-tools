# Track Specification: Agent Skill & Automated Versioning

## Overview

This track delivers two related improvements to the `gd-tools` project:

1. **Agent Skill (SKILL.md):** A self-contained skill file that enables AI coding agents (Claude, Cursor, Copilot, etc.) to reliably use `gd-tools` CLI commands. The skill follows the Anthropic skill format (YAML frontmatter + markdown body) and covers all CLI commands, flags, exit codes, and common workflows. Located at `skills/gd-tools/SKILL.md` in the repository root.

2. **Automated Version Bumping & Changelog Generation:** Integration of Commitizen to automate version bumps, changelog generation, and git tag creation from the project's existing conventional commit history. Includes a CI check to enforce conventional commit message format on pull requests.

## Functional Requirements

### FR-1: Agent Skill File

**FR-1.1** Create `skills/gd-tools/SKILL.md` following the Anthropic skill format:
- YAML frontmatter with `name` and `description` fields
- `description` includes trigger conditions (when to activate the skill) and is "pushy" to combat undertriggering
- Markdown body with structured instructions

**FR-1.2** The skill must be **self-contained** — all essential information (commands, flags, exit codes, workflows) is inline in SKILL.md. References to `docs/` are limited to edge cases and deep configuration details.

**FR-1.3** The skill must cover **all CLI commands** with their flags and exit codes:

| Command | Key Flags | Exit Codes |
|---------|-----------|------------|
| `gd-tools init` | `--non-interactive` | 0 (success), 2 (config error) |
| `gd-tools doctor` | — | 0 (all pass), 1 (issues found) |
| `gd-tools test` | `--coverage`, `--min`, `--suite`, `--test`, `--junit-xml`, `--no-exit-code`, `--timeout` | 0 (pass), 1 (test failure), 2 (config error) |
| `gd-tools lint` | `--report-format {text,json}`, `--fix` | 0 (no errors), 1 (lint errors), 2 (config error) |
| `gd-tools format` | `--check`, `--diff` | 0 (formatted), 1 (needs format), 2 (config error) |
| `gd-tools coverage report` | `--format`, `--output-dir` | 0 (success), 2 (config error) |
| `gd-tools coverage merge` | `--output` | 0 (success), 2 (config error) |
| `gd-tools coverage show` | `--min` | 0 (above threshold), 1 (below threshold), 2 (config error) |

**FR-1.4** The skill must include **common workflow recipes** — step-by-step sequences for typical development tasks:
- **Bootstrap workflow:** `gd-tools init` → `gd-tools test` → `gd-tools test --coverage --min 80`
- **Pre-commit workflow:** `gd-tools lint` → `gd-tools format --check` → commit
- **CI workflow:** `gd-tools lint --report-format json` → `gd-tools format --check` → `gd-tools test --junit-xml report.xml` → `gd-tools test --coverage --min 80`
- **Diagnosis workflow:** `gd-tools doctor` to verify environment

**FR-1.5** The skill must document:
- Configuration via `gd-tools.toml` (key sections: `[godot]`, `[test]`, `[lint]`, `[format]`, `[coverage]`)
- Godot binary detection chain (config → `$GODOT_BIN` → `$GODOT4_BIN` → `$GODOT_PATH` → PATH → common locations)
- Non-interactive/CI mode guidance (`--non-interactive`, `CI=true` for watch-mode tools)

**FR-1.6** The SKILL.md must be under 500 lines (per Anthropic skill convention).

### FR-2: Commitizen Integration

**FR-2.1** Add `commitizen` to dev dependencies in `pyproject.toml` under `[project.optional-dependencies] dev`.

**FR-2.2** Configure commitizen in `pyproject.toml` under `[tool.commitizen]`:
- `name = "cz_conventional_commits"` (matches existing commit format)
- `version` synced with `[project] version`
- `version_files = ["pyproject.toml:version"]`
- `changelog_file = "CHANGELOG.md"`
- `tag_format = "v$version"`
- `update_changelog_on_bump = true`

**FR-2.3** `cz bump` must:
- Update the `version` field in `pyproject.toml`
- Generate/update `CHANGELOG.md` from conventional commit history
- Create an annotated git tag (`vX.Y.Z`)

**FR-2.4** Generate an initial `CHANGELOG.md` from the existing commit history using `cz changelog`.

**FR-2.5** Manual build + PyPI publish remains unchanged (per workflow.md release steps). Commitizen handles version + changelog + tag only.

### FR-3: Conventional Commit CI Check

**FR-3.1** Add a GitHub Action workflow (`.github/workflows/commit-check.yml`) that validates conventional commit messages on pull requests.

**FR-3.2** The workflow runs `cz check` on the commit range `origin/main..HEAD` to enforce conventional commit format.

**FR-3.3** The workflow must fail (exit 1) if any commit message does not conform to the conventional commit format.

## Non-Functional Requirements

**NFR-1:** Commitizen is a **dev-only dependency** — it must not appear in runtime `dependencies`, only in `[project.optional-dependencies] dev`.

**NFR-2:** No changes to existing CLI commands, source code, or test suite behavior. This track is purely additive (new files + config changes).

**NFR-3:** The SKILL.md follows the Anthropic skill format convention (YAML frontmatter + progressive disclosure). No framework-specific tooling required to read it.

**NFR-4:** All new files are configuration/documentation — no new `.py` source code files are created. Per workflow.md testing requirements, no unit tests are required for this track's deliverables.

## Acceptance Criteria

- **AC-1:** `skills/gd-tools/SKILL.md` exists with valid YAML frontmatter (`name`, `description`) and markdown body.
- **AC-2:** SKILL.md covers all 8 CLI commands with their flags and exit codes.
- **AC-3:** SKILL.md includes at least 4 common workflow recipes (bootstrap, pre-commit, CI, diagnosis).
- **AC-4:** SKILL.md is under 500 lines.
- **AC-5:** `commitizen` is listed in `pyproject.toml` dev dependencies and configured under `[tool.commitizen]`.
- **AC-6:** `cz bump --dry-run` produces a correct version bump preview and changelog diff without modifying files.
- **AC-7:** `CHANGELOG.md` exists at repository root, generated from existing commit history.
- **AC-8:** `.github/workflows/commit-check.yml` exists and validates conventional commit format on PRs.
- **AC-9:** Existing test suite passes unchanged (`CI=true pytest`).
- **AC-10:** `ruff check` and `black --check` pass (no Python source changes, but verify no regressions).

## Out of Scope

- Full release automation (auto-build + PyPI publish triggered by tag push) — manual build/publish per workflow.md remains.
- Pre-commit hooks for local conventional commit validation — CI check only.
- IDE/editor integration for gd-tools.
- Changes to existing CLI commands, source code, or configuration system.
- Custom changelog templates — using commitizen's default conventional commits template.
- Agent skill evaluation/testing infrastructure (evals, benchmark viewer) as described in the Anthropic skill-creator reference.
- Bundled resources (`scripts/`, `references/`, `assets/`) in the skill directory — SKILL.md is self-contained.
