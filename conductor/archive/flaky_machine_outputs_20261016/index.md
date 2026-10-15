# Track: Flaky Tests in Machine-Readable Outputs

**Track ID:** `flaky_machine_outputs_20261016` | **Type:** Feature |
**Status:** new | **Branch:** `feature/flaky-machine-outputs-20261016`

Surface retried-then-passed ("flaky") tests in the two machine-readable
outputs of `gd-tools test` — JUnit XML and `artifacts.json` — closing the gap
the flaky-reporting track explicitly descoped. Purely additive,
serialization-only Python changes; terminal output and exit codes unchanged.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
