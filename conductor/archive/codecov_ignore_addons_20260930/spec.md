# Spec: Codecov Patch Ignore for Unmeasured Paths

## Overview

Fix the structural false failure of the `codecov/patch` status check by
excluding paths that the pytest coverage report can never measure
(`src/gd_tools/addons/**` GDScript addons and `tests/**`) from Codecov's
coverage calculation via the repo-level `codecov.yml` `ignore` list.

## Functional Requirements

1. `codecov.yml` gains a top-level `ignore` list containing:
   - `src/gd_tools/addons/**` — GDScript addon code; its behavior is verified
     by the real-Godot integration suite, not by Python coverage.
   - `tests/**` — the test suite itself is never inside the `--cov=gd_tools`
     report.
2. The existing `coverage.status.patch` settings (target 80%, threshold 0%)
   are unchanged.
3. A comment in `codecov.yml` records why the paths are ignored.

## Non-Functional Requirements

- No application code is touched.
- The project coverage gates (80% line / 70% branch on `src/gd_tools`) are
  unaffected — those paths were never in the pytest report.

## Acceptance Criteria

- On the PR for this track, the `codecov/patch` status is **success** (the
  PR's diff contains no measurable code, so the patch check must pass).
- The `CI` workflow remains green.

## Out of Scope

- Measuring GDScript coverage in Codecov (would require exporting GDScript
  coverage in a codecov-compatible format — a separate, larger effort).
- Any change to pytest coverage configuration or the CI workflow.
