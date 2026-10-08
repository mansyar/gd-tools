# Track: Flaky Test Reporting

- **Track ID:** `flaky_test_reporting_20261007`
- **Type:** Feature
- **Status:** New
- **Branch:** `feature/flaky-test-reporting-20261007`

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Surface tests that pass only after a retry ("flaky") in the native test run
summary. Protocol v4 adds an optional `first_failure_message` field (first
failed attempt's error message); the terminal summary gains a flaky panel
(suite, test, "passed on attempt N", first-line truncated message). Exit codes
unchanged; CLI-only; suppressed when no flaky tests exist or under `--quiet`.
