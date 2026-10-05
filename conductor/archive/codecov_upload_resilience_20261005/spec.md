# Track Specification: Codecov Upload Resilience

**Track ID:** `codecov_upload_resilience_20261005`
**Type:** Chore
**Branch:** `feature/codecov-upload-resilience-20261005`

## Overview

During PR #42, the `Upload coverage to Codecov` step in `.github/workflows/ci.yml`
failed three consecutive runs with TLS handshake errors (`write EPROTO ... ssl/tls
alert handshake failure`) while every lint/format/unit gate passed. The failure is
environmental (codecov.io reachability), unrelated to code changes, and currently
blocks PR merging because the step has no error tolerance.

## Functional Requirements

- **FR1**: The `Upload coverage to Codecov` step in `.github/workflows/ci.yml` sets
  `continue-on-error: true` so a codecov outage or network failure does not fail the
  job (and therefore does not block Stage 2/3 or PR merges).
- **FR2**: Coverage artifacts remain uploaded via the existing
  `actions/upload-artifact` step, so coverage data is still preserved when the
  Codecov upload fails.

## Non-Functional Requirements

- No other workflow steps or jobs are modified.
- The change is config-only; no source code or tests are affected (per workflow.md,
  tests are not required for config changes).

## Acceptance Criteria

1. `ci.yml` contains `continue-on-error: true` on the Codecov upload step and nowhere
   else.
2. The workflow parses (GitHub Actions accepts the file; verified by CI running the
   workflow on the PR).
3. A future codecov upload failure leaves the Stage 1 job green.

## Out of Scope

- Switching Codecov action versions or upload mechanisms.
- Adding retry logic beyond `continue-on-error`.
- Changes to e2e-nightly, release, or commit-check workflows.
