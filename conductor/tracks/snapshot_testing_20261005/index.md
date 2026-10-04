# Track: Snapshot Testing in the Native Runtime

- **Track ID:** `snapshot_testing_20261005`
- **Type:** Feature
- **Status:** new
- **Branch:** `feature/snapshot-testing-20261005`

Jest-style snapshot testing in the native GdToolsTest runtime:
`assert_snapshot(value, name)` with deterministic 3-tier serialization
(values / objects / node trees), `.gd-tools/snapshots/` storage,
fail-with-diff mismatches, `gd-tools test --snapshot-update`, obsolete
snapshot reporting, and `gd-tools clean --snapshots`.

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
