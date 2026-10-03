# Track: Instrumentation Hygiene Sweep (`instrumentation_hygiene_20261003`)

- **Type:** Bug fix + chore
- **Status:** completed
- **Branch:** `fix/instrumentation-hygiene-20261003`
- **Created:** 2026-10-03

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Four independently verified defects folded into one track because each is
small: (1) tracked points recorded on class-body lines make the collector
inject trackers where GDScript permits no statement, so the whole file
fails to parse and silently drops out of coverage; (2) `coverage merge`
writes through `write_coverage_json`, which omits the `omitted` key, so
omission reasons degrade to `_UNKNOWN_REASON`; (3) three writers
(`write_coverage_json`, `_write_junit_xml`, `mark_run_started`) write
non-atomically while the codebase already owns the atomic pattern
elsewhere; (4) `pre_run_hook.gd`/`post_run_hook.gd` extend the removed
`GutHookScript` base class yet are still deployed by `init`. Phase 3 also
clears the accumulated GUT-removal doc debt and three small dead-code
items. Ternary arm spans and multi-line `match` parsing are explicitly out
of scope.
