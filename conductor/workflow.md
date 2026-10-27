# Project Workflow

## Guiding Principles

1. **The plan is the source of truth.** Every phase, task, result, checkpoint,
   and evidence link lives in `plan.md`.
2. **The tech stack is deliberate.** A change to the stack is recorded in
   `tech-stack.md` before the implementation depends on it.
3. **Verification is agent-executed.** The phase subagent runs the configured
   checks and writes evidence. The user is not asked to manually verify routine
   work.
4. **Evidence over assertion.** A phase is complete only when the configured
   checks pass and the evidence file exists.
5. **No silent debt.** A finding is fixed, explicitly accepted with a reason, or
   tracked as an issue. It is never quietly ignored.
6. **Stay inside the phase contract.** `Touches` defines the expected blast
   radius. A required deviation is allowed, recorded, and reviewed.
7. **Non-interactive and CI-aware.** Prefer commands that terminate. Use
   `CI=true` for watch-mode tools where the ecosystem supports it.

## Workflow Config

```yaml
project:
  type: "python-cli"
  languages: ["Python", "GDScript"]
commands:
  setup: "pip install -e \".[dev]\""
  dev: "gd-tools --help"
  test: "CI=true pytest"
  coverage: "CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing"
  lint: "ruff check src/ tests/"
  format: "black --check src/ tests/"
  typecheck: "echo 'no typecheck configured'"
  build: "python -m build"
  verify_phase: "ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest"
coverage:
  gate: { line: 80, branch: 70 }
  scope: "project"
verification:
  layers: ["static", "unit", "integration", "e2e"]
  retry: 2
  manual_exceptions: ["Godot binary install for parse/e2e checks", "PyPI/TestPyPI credentials", "external release approvals"]
git:
  base_branch: "main"
  fetch: true
  commit_style: "conventional"
  task_commits: true
  phase_squash: true
review:
  strict: false
  issues:
    enabled: true
    auto_create: false
    min_severity: "medium"
    group_low: true
    labels: ["tech-debt", "conductor"]
pr:
  enabled: true
  tool: "gh"
  base: "main"
  media: "always"
  watch_ci: true
  watch_timeout_minutes: 15
  merge_method: "squash"
```

## Development Commands

### Setup

```bash
pip install -e ".[dev]"
```

### Daily Development

```bash
# Sanity check the CLI
gd-tools --help

# Run tests
CI=true pytest

# Run coverage
CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing

# Lint
ruff check src/ tests/

# Format (check only; write with `black src/ tests/`)
black --check src/ tests/

# Typecheck
echo 'no typecheck configured'

# Build
python -m build
```

### Before Committing

```bash
ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest
```

## Phase & Task Workflow

Implementation is executed one phase at a time by a phase subagent. The primary
agent owns `plan.md`, `metadata.json`, the registry, and review artifacts.

### Task Lifecycle

1. Read the phase contract in `plan.md`, the relevant requirements in `spec.md`,
   and the applicable style guides.
2. Work through the phase's tasks in order.
3. This project uses test-first development: write or update the failing test
   before the implementation.
4. Implement the smallest change that satisfies the task.
5. Run the targeted checks for the task.
6. Commit the task with a conventional commit message.
7. Report the task's status and commit SHA to the primary agent.

The subagent does **not** edit `plan.md`. The primary marks tasks complete after
it accepts the phase.

### Deviations

- If the phase goal requires a file outside `Touches`, make the smallest
  necessary change and record it in the report under `deviations`.
- If the work requires a product or design decision, stop and report `blocked`.
- Do not silently expand scope, add a dependency, or migrate unrelated code.

### Phase Completion

1. Run the phase's `Verification` command exactly as written in `plan.md`.
2. Run `verify_phase` when it is configured and different from the phase command.
3. Write the evidence file using the configured evidence path.
4. Return the structured report to the primary agent.
5. Do not merge, rebase, reset, push, open a PR, or edit Conductor state files.

## Verification Strategy

### Layers

- **Static:** ruff lint + black format check (required every phase).
- **Unit:** isolated behavior and edge cases via pytest `tests/unit` (required).
- **Integration:** module boundaries and GDScript fixture flows via pytest
  `tests/integration`, including the batched Godot parse check (required when
  the phase touches `src/gd_tools/` or `*.gd`).
- **E2E:** complete user flows via pytest `tests/e2e` (only when the phase
  touches runtime flows; the PR-critical subset is `e2e_smoke`).

No typecheck layer: the project configures no typechecker. `compileall` is not
a substitute and is intentionally not wired in.

### Commands

| Layer | Command | Required |
| --- | --- | --- |
| static | `ruff check src/ tests/` | yes |
| static | `black --check src/ tests/` | yes |
| unit | `CI=true pytest tests/unit -q` | yes |
| integration | `CI=true pytest tests/integration -q` | when phase touches src or .gd |
| e2e | `CI=true pytest -m e2e_smoke -q` | when phase touches runtime flows |

### Services and Fixtures

- **Services:** Godot binary (4.5+, repo uses 4.7.x) for parse checks and e2e;
  no ports, containers, or databases.
- **Fixtures/seed data:** `tests/fixtures/gdscript/` GDScript fixtures,
  `tests/fixtures/projects/` sample projects.
- **Environment variables:** `CI=true` for single-execution runs.
- **Start/stop commands:** none; Godot is invoked headless per test.

### Pass Criteria

- Every required command exits `0`.
- The coverage gate is met for the configured scope (line >= 80, branch >= 70).
- Every acceptance criterion has a test or a documented evidence artifact.
- No new Critical or High review findings remain.

### Evidence

Write a report to:

```text
conductor/tracks/<track-id>/verification/phase-<n>.md
```

Include: title; track, phase, date, branch, base and head commits; result
(`verified`, `failed`, `blocked`, or `partial`); a commands table (layer,
command, exit, summary); an acceptance-criteria table (ID, criterion, evidence,
status); evidence paths; deviations; and notes. Put binaries, screenshots, and
large reports under `.conductor/evidence/`; that directory is gitignored. The
report itself is committed with the track.

### Fallback Ladder

1. Run the full configured layer.
2. If the Godot binary is missing, report which check could not run and mark
   the phase `partial` with the reason; do not fake a parse result.
3. If it still cannot run, run the narrowest reliable subset and mark the phase
   `partial` with the reason.
4. Stop and ask the user (via the question tool) only for credentials, hardware, or an external
   approval.

### Retry Policy

- A failed check may be fixed and re-run at most **2** times.
- If it still fails, report `failed` with the command and output.
- Never mark a phase `verified` when a required check did not run.

### Human-Only Exceptions

- Godot binary installation when it is absent from the machine.
- PyPI/TestPyPI credentials for release steps.
- External release approvals.

## Quality Gates

Before a phase is accepted:

- [ ] Required tests pass
- [ ] Coverage gate is met for the configured scope
- [ ] Lint and format checks pass
- [ ] Code follows the applicable `conductor/code_styleguides/`
- [ ] No secrets, credentials, or PII are introduced
- [ ] Public behavior is documented when it changed
- [ ] Evidence is written and linked in `plan.md`

## Commit Guidelines

### Message Format

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation only
- `style`: formatting
- `refactor`: behavior-preserving change
- `test`: tests only
- `chore`: maintenance

### Examples

```bash
git commit -m "feat(config): Implement gd-tools.toml loading and validation"
git commit -m "fix(coverage): Correct Godot 4.6 version detection"
git commit -m "test(coverage): Add tests for plan generator branch detection"
```

Task-level commits are made by the phase subagent. The primary squashes them
into one phase commit on acceptance, unless a foreign commit landed in the range.
The plan update is a separate state commit.

## Definition of Done

A track is complete when:

1. Every phase is `verified` with a checkpoint and evidence.
2. The integrated verification on the track branch passes.
3. Review is `PASS`, or every finding is fixed, accepted with a reason, or
   tracked as an issue. No Critical or High finding remains unresolved without an
   explicit user override recorded in `review.md`.
4. Post-review documentation sync is complete.
5. The registry and `metadata.json` show the track as complete.
6. When a remote exists, the branch is pushed. When `pr.enabled` is true, a PR
   is open or `pr_state: "unavailable"` records that PR creation could not run.
   When `pr.enabled` is false, no PR is expected.

## Emergency Procedures

### Critical Bug in Production

1. Create a hotfix branch from the configured base.
2. Write a failing regression test.
3. Implement the minimal fix.
4. Run the full verification strategy.
5. Open a PR immediately; do not batch unrelated work.

### Data Loss

1. Stop all write operations.
2. Restore from the latest verified backup.
3. Verify data integrity.
4. Document the incident and update the recovery procedure.

### Security Breach

1. Rotate all affected secrets.
2. Review access logs.
3. Patch the vulnerability.
4. Notify affected users when required.
5. Document the incident and update the security procedure.

## Deployment

### Pre-Deployment Checklist

- [ ] All required checks pass (`ruff check`, `black --check`, `CI=true pytest`)
- [ ] Coverage gate met (line >= 80, branch >= 70)
- [ ] `pyproject.toml` metadata correct (version, changelog via commitizen)
- [ ] Package builds (`python -m build`) and `twine check dist/*` passes
- [ ] Tested on TestPyPI first

### Deployment Steps

1. Merge the track PR.
2. Bump version with commitizen (`cz bump`).
3. Tag the release (`vX.Y.Z`).
4. Build (`python -m build`) and verify with `twine check`.
5. Upload to TestPyPI, verify install, then upload to PyPI.
6. Create the GitHub release with notes.
7. Monitor PyPI stats and issue reports.

### Post-Deployment

1. Monitor analytics and error logs.
2. Gather user feedback.
3. Record follow-ups as issues or a new track.

## Continuous Improvement

- Review this workflow after each track.
- Update commands and verification layers when the tooling changes.
- Record recurring review findings as process improvements.
- Keep the process as small as the project allows.
