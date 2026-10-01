# Track: Native Signal Assertions

Status: **new**

## Documents

- **Specification:** [spec.md](./spec.md)
- **Implementation Plan:** [plan.md](./plan.md)
- **Metadata:** [metadata.json](./metadata.json)

## Summary

Adds first-class signal assertions to the native `GdToolsTest` runtime: an
explicit `watch_signals(target)` capture model, four assertions
(`assert_signal_emitted`, `assert_signal_not_emitted`,
`assert_signal_emit_count`, `assert_signal_emitted_with_args` with `"any"`
wildcards), and the awaitable `assert_signal_emitted_after` helper — with
per-test lifecycle isolation, unwatched-target guidance failures, and rich
diagnostics. No result-protocol changes.
