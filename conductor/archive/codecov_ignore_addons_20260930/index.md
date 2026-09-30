# Track: Codecov Patch Ignore for Unmeasured Paths

**Track ID:** codecov_ignore_addons_20260930
**Type:** chore
**Status:** new
**Branch:** `chore/codecov-ignore-addons-20260930`

The `codecov/patch` status check fails on any PR that touches GDScript addon
code or the Python test suite, because the project's coverage report measures
only the `gd_tools` Python package (`pytest --cov=gd_tools`). Lines in
`src/gd_tools/addons/**` (GDScript, verified by real-Godot integration tests)
and `tests/**` (the suite itself) can never appear in the report, so the patch
math counts them as uncovered — PR #20 scored 47.57% against an 80% target
despite 99% coverage on the new Python module and passing integration tests.

## Documents

- [spec.md](./spec.md)
- [plan.md](./plan.md)
- [metadata.json](./metadata.json)

## Context

- [Product Definition](../../product.md)
- [Tech Stack](../../tech-stack.md)
- [Workflow](../../workflow.md)
