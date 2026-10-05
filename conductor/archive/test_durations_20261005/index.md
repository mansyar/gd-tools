# Track: Test Durations Reporting

- **ID:** test_durations_20261005
- **Type:** Feature
- **Status:** new
- **Branch:** `feature/test-durations-20261005`
- **Created:** 2026-10-05

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Pytest-parity `--durations N` slowest-test reporting for `gd-tools test`,
with a `[test] durations` config key, built on existing per-test timing data
from protocol v3 (no GDScript/protocol changes).
