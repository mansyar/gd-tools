# Plan: Codecov Patch Ignore for Unmeasured Paths

Single-phase chore; no application code changes, so TDD does not apply
(no `.py`/`.gd` source). Verification is the codecov/patch status on this
track's own PR.

## Phase 1: Config change and verification

- [x] Task 1.1: Update `codecov.yml` — add top-level `ignore` list with
      `src/gd_tools/addons/**` and `tests/**` plus an explanatory comment;
      leave `coverage.status.patch` untouched. Commit
      `chore(codecov): ignore unmeasured addons and tests in patch status`. (25a4def)
- [x] Task 1.2: Push branch, open PR, and verify `codecov/patch` reports
      success and the `CI` workflow is green; merge PR and confirm post-merge
      CI on main. (PR #22: all checks pass, codecov/patch pass)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

  [checkpoint: 64773bf]
