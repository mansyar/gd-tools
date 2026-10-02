# Track: Coverage Format Bugfix + CLI Unification (`coverage_format_unification_20261002`)

- **Type:** Bug fix + chore
- **Status:** new
- **Branch:** `fix/coverage-format-unification-20261002`
- **Created:** 2026-10-02

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Fix `coverage run --report-format json` always failing with
`CoveragePlanError` after the playtest session completes by making
json a first-class report format mirroring the coverage-diff JSON
shape; unify the `--format` vs `--report-format` flag naming across
coverage subcommands with `click.Choice` validation, keep `--format`
as a hidden backwards-compatible alias on `coverage report`, and
align the `[coverage].format` config validator with the same format
set.
