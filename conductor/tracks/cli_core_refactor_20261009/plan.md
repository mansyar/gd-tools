# Implementation Plan: CLI Core Refactor

*Track ID: `cli_core_refactor_20261009` · Branch: `feature/cli-core-refactor-20261009`*

Methodology: per `conductor/workflow.md` — TDD for all new code (failing tests first), full suite green at every phase boundary, phase checkpoints with manual verification, commit format `<type>(<scope>): <description>` with task-summary git notes.

Sequencing rationale: hygiene → dedup → conflict table → decomposition → verification. The safety net strengthens before the riskiest move (full decomposition); the conflict table lands before the `test` command extraction so the extracted module consumes it on arrival.

## Phase 1: Baseline & Repo Hygiene (FR-5)

- [ ] Task: Record baseline — run `CI=true pytest` and `CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`; record test count, line/branch coverage, and `ruff`/`black` status in this plan as the no-regression reference
  - [ ] Baseline numbers recorded below under "Baseline"
- [ ] Task: Repo hygiene sweep — verify unreferenced (grep for imports/references), then delete: stray `out.json`, stale `__pycache__/test_runner.cpython-313*.pyc`, duplicate `gd_tools_cli.egg-info/`, `tools/verify_watch_phase2.py`
  - [ ] Reference check performed before each deletion
  - [ ] Suite still green after deletion
  - [ ] Commit: `chore(repo): remove dead artifacts`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Atomic-Write Consolidation (FR-4) — TDD

- [ ] Task: Red — add unit tests for `atomic_io.atomic_write_json` (serialize + atomic replace semantics: temp file + os.replace, parent-dir creation, failure leaves no partial file) in `tests/unit/test_atomic_io.py`; confirm they fail
  - [ ] Failing tests confirmed
- [ ] Task: Green — implement `atomic_write_json` in `atomic_io.py`
  - [ ] Tests pass
- [ ] Task: Migrate the four call sites — `native_test/artifacts.py` (`_write_json_atomic`), `native_test/orchestrator.py` inline copy, `native_test/protocol.py` inline copy, plus `atomic_io` internal reuse; delete duplicated helpers
  - [ ] All four sites delegate to `atomic_io`
  - [ ] Suite green
  - [ ] Commit: `refactor(atomic): consolidate duplicate atomic JSON writers`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Declarative Flag-Conflict Table (FR-3) — TDD

- [ ] Task: Red — capture current behavior: exact error messages and exit codes for every pairwise constraint in cli.py:800–873; encode them as unit tests for `src/gd_tools/commands/test_validation.py`; confirm failures
  - [ ] Existing constraints catalogued
  - [ ] Failing tests confirmed
- [ ] Task: Green — implement the data-driven conflict table + validator in `commands/test_validation.py`; wire into the `test` command replacing hand-written checks
  - [ ] Suite green with byte-identical error messages
  - [ ] Commit: `refactor(test): declarative flag-conflict validation table`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Full Command Decomposition (FR-1, FR-2)

- [ ] Task: Create `src/gd_tools/commands/` package; extract low-risk commands first (version, clean, completion, config group, install-hooks, doctor, init, lint, format, migrate)
  - [ ] Commands import shared modules directly (config, output, verbosity, errors) — no new context layer
  - [ ] Existing suite is the safety net; test import-path updates mechanical only
  - [ ] Suite green; commit: `refactor(cli): extract low-risk commands into commands/ package`
- [ ] Task: Extract the `test` command module (largest; consumes the Phase 3 conflict table)
  - [ ] Suite green; commit: `refactor(cli): extract test command`
- [ ] Task: Extract the `coverage` subcommand group (6 subcommands)
  - [ ] Suite green; commit: `refactor(cli): extract coverage subcommand group`
- [ ] Task: Slim `cli.py` to the thin dispatcher (GdToolsGroup, completion, UTF-8 setup, command registration)
  - [ ] Import smoke test passes (`python -c "import gd_tools.cli"` + `python -m gd_tools --help`)
  - [ ] No circular imports
  - [ ] Suite green; commit: `refactor(cli): reduce cli.py to thin dispatcher`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5: Final Verification & NFR Gates

- [ ] Task: Full gate run against Baseline
  - [ ] `CI=true pytest` — full suite green, test count ≥ baseline
  - [ ] `CI=true pytest --cov=gd_tools --cov-branch` — line ≥80%, branch ≥70% overall; new `commands/` modules ≥ replaced-code coverage
  - [ ] `ruff check src/ tests/` and `black --check src/ tests/` clean
  - [ ] Behavior-freeze spot-check: `gd-tools --help`, one sample command's output identical to pre-track behavior
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

---

## Baseline

*To be recorded in Phase 1, Task 1.*
