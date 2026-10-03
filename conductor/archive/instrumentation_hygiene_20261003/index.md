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
## Summary

Folded four verified defects plus GUT-removal residue into one track.
The largest item: statement points were recorded on lines where no
statement may begin - class-member declaration lines (lambda bodies
assigned to class-level `var`/`static var`/`@export`), function
signature spans (default-parameter lambdas), and - found in review -
bracket- and backslash-continuation lines of multi-line initializer
expressions (e.g. a signal-handler dict of lambdas). Injected trackers
on those lines broke the GDScript parse and silently dropped whole
files from coverage. The generator now guards all three classes via
two pre-passes (`_collect_illegal_lines`, `_collect_continuation_lines`);
`PLAN_VERSION` bumped 3 -> 5. Review also fixed `coverage merge`
silently losing omission reasons (`write_coverage_json` now carries
the `omitted` key), migrated six writers onto one shared crash-safe
`atomic_io` helper (coverage data, JUnit XML, run marker, plan cache,
baselines), deleted the dead GUT hook files with `init` self-healing
of stale copies, removed the empty deprecation machinery, renamed
`test_runner.py` -> `test_results.py`, and corrected stale docs
(protocol-v2 strings, "GUT installation" wording, dead
`run_coverage_test` reference). Known remaining limits: lambda bodies
always co-report with their enclosing statement line; ternary arms
remain co-anchored (span-based plans would be needed); multi-line
`match` patterns are unparseable by gdtoolkit (upstream).
