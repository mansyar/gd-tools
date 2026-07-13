<protect>
# Implementation Plan: Agent Skill & Automated Versioning

> **Note:** All deliverables in this track are non-code files (`.md`, `.toml`, `.yml`). Per workflow.md §Testing Requirements, TDD (Red/Green phases) is not applicable — tests are only required for source code files (`.py`, `.gd`). Tasks focus on creation, configuration, and verification.

## Phase 1: Agent Skill Creation

- [x] Task: Read `spec.md` and `workflow.md` for context before starting phase tasks
- [x] Task: Create `skills/gd-tools/SKILL.md` [f92664e]
    - [x] Create directory structure: `skills/gd-tools/`
    - [x] Write YAML frontmatter with `name: gd-tools` and `description` (trigger conditions, pushy tone to prevent undertriggering)
    - [x] Write CLI command reference — all 8 commands (init, doctor, test, lint, format, coverage report, coverage merge, coverage show) with flags and exit codes
    - [x] Write common workflow recipes (bootstrap, pre-commit, CI, diagnosis)
    - [x] Write configuration reference (`gd-tools.toml` key sections: `[godot]`, `[test]`, `[lint]`, `[format]`, `[coverage]`)
    - [x] Write environment & detection guide (Godot binary detection chain, CI mode, `--non-interactive`)
    - [x] Verify SKILL.md is under 500 lines and content is self-contained (AC-1, AC-2, AC-3, AC-4)
- [x] Task: Conductor - User Manual Verification 'Agent Skill Creation' (Protocol in workflow.md)

## Phase 2: Commitizen Integration

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting phase tasks
- [ ] Task: Update `tech-stack.md` to document commitizen (before implementation — workflow.md §Guiding Principles #2)
    - [ ] Add `commitizen` to Development Dependencies table (§3)
    - [ ] Add dated note about the automated version bumping and changelog workflow
- [ ] Task: Add commitizen to dev dependencies and configure in `pyproject.toml`
    - [ ] Add `"commitizen"` to `[project.optional-dependencies] dev` list
    - [ ] Add `[tool.commitizen]` section: `name`, `version`, `version_files`, `changelog_file`, `tag_format`, `update_changelog_on_bump = true`
    - [ ] Run `pip install -e ".[dev]"` to install commitizen
- [ ] Task: Generate initial `CHANGELOG.md` from existing commit history
    - [ ] Run `cz changelog` to generate from git history
    - [ ] Review generated `CHANGELOG.md` for accuracy (AC-7)
- [ ] Task: Verify commitizen bump workflow
    - [ ] Run `cz bump --dry-run` and verify version bump preview (AC-6)
    - [ ] Verify changelog diff is generated correctly
    - [ ] Confirm no files are modified in dry-run mode
    - [ ] Verify existing test suite passes unchanged: `CI=true pytest` (AC-9)
    - [ ] Verify `ruff check src/ tests/` and `black --check src/ tests/` pass (AC-10)
- [ ] Task: Conductor - User Manual Verification 'Commitizen Integration' (Protocol in workflow.md)

## Phase 3: Conventional Commit CI Check

- [ ] Task: Read `spec.md` and `workflow.md` for context before starting phase tasks
- [ ] Task: Create `.github/workflows/commit-check.yml`
    - [ ] Write workflow YAML: trigger on `pull_request` (opened, edited, reopened, synchronize)
    - [ ] Configure job: `actions/checkout@v4` with `fetch-depth: 0`, `actions/setup-python@v5` (Python 3.12), install commitizen, run `cz check --rev-range origin/${{ github.base_ref }}..HEAD`
    - [ ] Match conventions from existing `ci.yml` (action versions, Python version, structure)
- [ ] Task: Verify CI workflow configuration
    - [ ] Validate YAML syntax
    - [ ] Review workflow against FR-3.1 through FR-3.3 (AC-8)
    - [ ] Note: commitizen tags (`v*`) will naturally feed into existing `release.yml` workflow — no changes needed to `release.yml`
- [ ] Task: Conductor - User Manual Verification 'Conventional Commit CI Check' (Protocol in workflow.md)
</protect>
