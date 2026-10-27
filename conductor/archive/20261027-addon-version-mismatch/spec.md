# Coverage Addon Version Gate — Specification

> Requirements are stable. Once an `FR`, `NFR`, or `AC` ID is approved, do not
> renumber it. If a requirement is removed, mark it `Withdrawn` instead of
> deleting it.

## Overview

`gd-tools test --coverage` refuses to run with exit code 2 when a deployed
addon it depends on is stale or missing, instead of running into misleading
instrumentation failures that blame the user's source files.

## Problem / Motivation

Testing the 0.9.0 CLI against a still-deployed 0.8.0 coverage addon produced
instrumentation failures pointing at the user's source file, while the real
cause — the stale addon — was a single advisory warning buried at line 1 of
the output and easy to miss. Anyone upgrading the CLI without re-running
`gd-tools init` burns debugging time on the wrong file.

## Goals & Success Metrics

- **Goal:** A version mismatch aborts the coverage run before any suite is
  dispatched, with a message naming both versions and the fix.
- **Metric:** New gate tests fail before the change and pass after; stale and
  missing addons exit 2 with zero suites executed.

## Scope

### In Scope

- Strict pre-dispatch gate for the coverage addon (`addons/gd-tools-coverage`)
  on `test --coverage`: stale or missing → exit 2.
- Same gate for the native test addon (`addons/gd-tools-test`) on
  `test --coverage`.
- Refusal message names deployed vs CLI versions plus the
  `gd-tools init` fix, and states the run was aborted.
- Promote the mismatch at the failure point so it cannot scroll by.
- `GD_TOOLS_NO_UPDATE_CHECK=1` suppresses the gate.

### Out of Scope

- Editor plugin version check (unchanged, advisory only).
- Auto-update of the addon (explicitly rejected; user runs `init`).
- New process exit codes (reuse exit 2, the environment-failure code).
- Changes to `doctor` advisory wording.
- Structured error artifacts in JSON/JUnit modes (stderr + exit 2 only).

## Functional Requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-1 | `test --coverage` exits 2 before dispatching any suite when the deployed coverage addon version is older than the CLI version. | must |
| FR-2 | The gate also refuses (exit 2) when the coverage addon version file is missing. | must |
| FR-3 | The gate applies equally to the native test addon (stale or missing → exit 2) on `test --coverage`. | must |
| FR-4 | `GD_TOOLS_NO_UPDATE_CHECK=1` suppresses the gate entirely. | must |
| FR-5 | A deployed addon newer than the CLI never triggers the gate. | must |
| FR-6 | The refusal message names the deployed version, the CLI version, the `gd-tools init` fix, and states the run aborted before tests. | must |
| FR-7 | The advisory group-level warning remains for non-coverage commands; under `--coverage` the mismatch is surfaced at the refusal point. | must |

## Non-Functional Requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | The gate runs before any Godot process is launched and has no side effects on the project. |
| NFR-2 | Matching versions behave exactly as today (no new output, no exit change). |
| NFR-3 | Version-file read failures keep the current fail-safe posture (no crash on unreadable files). |

## Acceptance Criteria

| ID | Criterion | Verifies |
| --- | --- | --- |
| AC-1 | Stale coverage addon + `--coverage` → exit 2, zero suites run. | FR-1 |
| AC-2 | Missing coverage addon + `--coverage` → exit 2. | FR-2 |
| AC-3 | Stale/missing native test addon + `--coverage` → exit 2. | FR-3 |
| AC-4 | Env suppression set → gate skipped, run proceeds as today. | FR-4 |
| AC-5 | Newer deployed addon → run proceeds, no refusal. | FR-5 |
| AC-6 | Refusal names both versions + init command + aborted-run note. | FR-6 |
| AC-7 | Unparseable version file is treated as stale (exit 2). | FR-1 |

## Edge Cases

- Unparseable `_version.txt` content (treated as stale, consistent with the
  advisory check).
- Command run outside a project root (gate defers to existing behavior; the
  test command fails on its own config path).
- `--watch` mode (gate applies to every dispatched run).
- `--quiet` (refusal is essential output, never suppressed).
- Plain `test` without `--coverage` (gate does not apply; advisory only).

## Dependencies

- **Tracks:** none
- **External:** none

## Open Questions & Assumptions

- **Assumption:** The editor plugin check stays advisory-only; editor flows
  are out of scope.
- **Assumption:** Reusing exit 2 needs no doc change beyond the existing
  environment-failure contract.
- **Assumption:** The gate lives in the `test --coverage` dispatch path
  (exact function placement is a plan detail).

## References

- User feedback (0.9.0 CLI vs 0.8.0 addon misdirection report)
- `src/gd_tools/addon_check.py` (`check_addon_version`)
- `src/gd_tools/doctor.py` (native test addon check, line ~367)
- `src/gd_tools/commands/test.py` (`--coverage` dispatch)
- Exit-code contract: 0 pass, 1 test/coverage failure, 2 environment failure
