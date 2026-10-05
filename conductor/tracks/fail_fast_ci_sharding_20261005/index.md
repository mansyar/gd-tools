# Track: Fail-Fast and CI Sharding

- **ID:** fail_fast_ci_sharding_20261005
- **Type:** Feature
- **Status:** new
- **Branch:** `feature/fail-fast-ci-sharding-20261005`
- **Created:** 2026-10-06

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Pytest-parity orchestration features for `gd-tools test`: `--exitfirst`/`-x`
(stop dispatching suites on the first failing suite result, drain in-flight
workers) and `--shard k/N` (suite-level round-robin sharding over the
deterministic plan order for CI parallelism, with `coverage merge` across
shards). CLI-only flags in v1; no GDScript runtime changes.
