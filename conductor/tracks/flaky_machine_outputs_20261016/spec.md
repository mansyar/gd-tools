# Specification — Flaky Tests in Machine-Readable Outputs

**Track ID:** `flaky_machine_outputs_20261016`
**Type:** Feature
**Branch:** `feature/flaky-machine-outputs-20261016`
**Predecessor:** `flaky_test_reporting_20261007` (archived) — this track closes the machine-output gap that track explicitly descoped.

## 1. Overview

The flaky-reporting track surfaces retried-then-passed tests in the terminal
summary only, and explicitly descoped JUnit XML, the artifact index, and JSON
output. CI dashboards (Jenkins, GitHub, GitLab) and post-run tooling therefore
cannot see flakiness. This track closes that gap with purely additive,
serialization-only Python changes — no GDScript, protocol, or runtime changes;
terminal output and exit codes are unchanged.

Grounding correction (applied during spec review): an earlier draft included
"flaky fields in the JSON test output", but `gd-tools test` has no JSON output
flag — verified in `src/gd_tools/commands/test.py` and
`src/gd_tools/native_test/command.py`. The test command's only
machine-readable surfaces are JUnit XML and `artifacts.json`. A JSON output
flag would be a new CLI surface and is reserved for a separate future track.

## 2. Functional Requirements

- **FR-1 — JUnit XML:** `_write_junit_xml`
  (`src/gd_tools/native_test/command.py`) adds a `<properties>` block with
  `flaky=true` and `attempts=N` to each flaky `<testcase>`, reusing the
  existing `is_flaky()` helper from `src/gd_tools/native_test/flaky.py`.
  Non-flaky cases are byte-identical to today (no diff noise). The
  suite-level `artifact_index` property behavior is unchanged.
- **FR-2 — artifacts.json:** `publish_artifact_index`
  (`src/gd_tools/native_test/artifacts.py`) gains per-test `flaky`/`attempts`
  fields plus a top-level flaky summary, both additive keys following the
  `seed`/`omitted` precedent — no version bump, old readers ignore them.
  Threaded through the orchestrator's existing publication call sites
  (`src/gd_tools/native_test/orchestrator.py`, `command.py`); parallel-run
  flaky tests aggregate across workers.
- **FR-3 — Quiet-mode parity:** flaky data is always emitted in both machine
  outputs, even under `--quiet` (quiet trims human commentary only) —
  mirroring the seed-line precedent.
- **FR-4 — Exit codes unchanged:** all-pass-with-flaky stays exit 0. No
  `--fail-on-flaky` flag in this track.
- **FR-5 — Docs:** `USER_GUIDE.md` (flaky section) and `ARCHITECTURE.md`
  (§9.5 artifact index + JUnit docs) describe the new fields.

## 3. Acceptance Criteria

1. A flaky test carries `flaky=true`, `attempts=N` in JUnit XML and
   `artifacts.json`; non-flaky runs produce byte-identical output to today.
2. Quiet-mode runs still carry flaky data in both machine outputs.
3. Parallel-run flaky tests aggregate across workers into both outputs.
4. Unit + integration tests gate the track; `ruff`/`black` clean; new code
   >80% line / >70% branch coverage.
5. Exit codes unchanged (flaky-pass = 0).

## 4. Out of Scope

- `--durations` table markers, coverage JSON outputs, editor dock changes.
- `--fail-on-flaky` gating (possible follow-up track).
- Any runtime / GDScript / protocol change.
- A JSON output flag for `gd-tools test` (future separate track if needed).
