# Implementation Plan — Clean Command (Roadmap Track 39)

- **Track ID:** `clean_command_20260930`
- **Spec:** `./spec.md` (approved)
- **Workflow notes:** Source code is touched (`clean.py`, `cli.py`), so TDD
  applies (Red → Green → Refactor) and coverage gates (>80% line / >70%
  branch) are verified after implementation phases. Docs tasks do not require
  tests. Commits follow `<type>(<scope>): <desc>` with git notes; tasks are
  marked `[x]` with 7-char SHAs.

## Phase 1 — `clean.py` Core (TDD) [checkpoint: a4740e8]

- [x] Task: Write failing unit tests for `run_clean` (Red) 05b8224
  - `tests/unit/test_clean.py` with `tmp_path` project fixtures creating
    `.gd-tools/coverage/` (with `plan.json`, `coverage.json`, `baseline.json`),
    `.gd-tools/artifacts/<run_id>/`, `.gd-tools/native/`.
  - Cover: each flag's target; `--all`; missing targets reported as
    "nothing to remove" (exit-style status, not exception); `--baselines`
    removes only `baseline.json`; `--baselines`+`--coverage` subsumption
    (FR-6); `--dry-run` deletes nothing and reports `would remove` (FR-4);
    per-target `CleanResult` statuses + freed bytes (FR-9); protected paths
    untouched after every destructive run (FR-7: `addons/**` incl.
    `.backups/`, `gd-tools.toml`, `.gutconfig.json`; `~/.gd-tools` never
    referenced).
- [x] Task: Implement `src/gd_tools/clean.py` (Green) 4055849
  - `CleanResult` dataclass (per-target status: removed / nothing-to-remove /
    would-remove; freed bytes) and
    `run_clean(coverage, artifacts, baselines, cache, all, dry_run,
    project_root) -> CleanResult`.
  - Fixed constant target map (structural enforcement of FR-7); recursive
    removal; size accounting; error path surfaces the failing path (FR-8).
  - Refactor if needed after green.
- [x] Task: Run coverage gate for `clean.py` 4055849
  - Result: 21 passed; clean.py 95% combined (line+branch); gates met.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) a4740e8

## Phase 2 — CLI Wiring & UX

- [x] Task: Write failing CLI tests (Red) 62803b8
  - Click runner tests: `clean` with no flags → inventory + hint, exit 0,
    nothing deleted; `--dry-run` composition; summary output on real run;
    exit 2 path (mock unremovable target); `--all` help/override behavior
    (FR-1, FR-2, FR-5).
- [x] Task: Register `clean` command in `src/gd_tools/cli.py` (Green) bdb9b95
  - Flags `--coverage --artifacts --baselines --cache --all --dry-run` with
    help text documenting targets and `--all` override; thin handler calling
    `run_clean`; output through the existing output/verbosity conventions.
- [x] Task: Style + full-suite gate bdb9b95
  - Result: ruff + black clean; CI=true pytest --cov=gd_tools --cov-branch:
    1443 passed, 6 skipped, 95.40% total (gates 80/70).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Docs & Closure

- [x] Task: USER_GUIDE documentation a9b3f04
  - New `gd-tools clean` section: flag table with verified targets, no-flag
    inventory behavior, protected paths, `--dry-run`, exit codes.
- [x] Task: Update ROADMAP Track 39 status to Delivered a9b3f04
- [x] Task: Final verification & commit a9b3f04
  - Result: full gate green (1443 passed, 6 skipped, 95.40% coverage).
  - Re-run full gate (`ruff`, `black --check`, `CI=true pytest`); commit
    `feat(clean): add gd-tools clean command` (+ docs in same or follow-up
    `docs:` commit); attach git notes; mark all tasks `[x]` with SHAs.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
