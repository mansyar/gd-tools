# Feature Spec: Min-Branch Gate on `coverage run` + Zero-Branch Exemption

Track ID: `min_branch_coverage_run_20261004`
Type: bug
Branch: `feature/min-branch-coverage-run-parity-20261004`

## 1. Overview

`gd-tools test` and `gd-tools coverage show` accept `--min-branch` (added in
PR #39 / Ternary Branch Separation, PLAN_VERSION 6), but `gd-tools coverage
run` — the playtest-session coverage entry point — does not. A user who
gates branches via `coverage run` in CI gets no branch threshold at all.
Additionally, the branch gate as implemented fails when a project has zero
branch points (`branch_rate = 0.0`), which punishes projects that simply
contain no ternaries/match-arms.

This track wires `--min-branch` through `coverage run` and defines the
zero-branch-point rule consistently across all three commands: **exempt
with an explicit console note**, not a failure.

## 2. Root Cause

- `cli.py` `coverage run` handler (~line 1275) never forwards a branch
  threshold to the runtime/report generator (`run_native_test_command`).
  PR #39 added the parameter only on the `test` CLI seam and
  `coverage show`.
- `reporter.CoverageSummary.branch_rate = covered/total if total > 0 else 0.0`
  (reporter.py ~529). With `total_branches == 0`, any positive
  `--min-branch` fails the gate.

## 3. Functional Requirements

**FR-1 — CLI option.** `gd-tools coverage run` accepts
`--min-branch <int 0-100>`, validated like `--min`, default `None` (off).
Threaded through `run_playtest_coverage`/native command →
`_generate_native_report` → `reporter.generate_report(min_branch_threshold=…)`.

**FR-2 — Zero-branch exemption.** When `summary.total_branches == 0` and a
branch threshold is set, the gate passes and the console output prints a
single note line (e.g. `Branch coverage: no branch points; --min-branch gate
not applied.`). Applied consistently to `test`, `coverage run`, and
`coverage show`.

**FR-3 — Populated-branch behavior unchanged.** With
`total_branches > 0`, `branch_rate` gates exactly as today:
`branch_rate >= min_branch` or `CoverageThresholdError` with a
branch-specific message, exit 1, and the report already written so CI can
still read it.

**FR-4 — Docs.** USER_GUIDE adds `--min-branch` to the `coverage run` flag
table and documents the zero-branch exemption; CHANGELOG gains a Fix entry;
ARCHITECTURE notes the convention if it touches the threshold section.

**FR-5 — Tests.** Unit tests: `generate_report` with `total_branches=0` +
positive threshold returns success with the note (no raise); populated-
branch failure still raises. CLI: `coverage run --min-branch` e2e —
uncovered branch fails; zero-branch project passes. Full suite
`CI=true pytest` passes.

## 4. Non-Functional Requirements

- Coverage JSON schema unchanged (no new keys).
- No behavior change when `--min-branch` is omitted.
- Exit codes 0/1/2 semantics per product guidelines (2 reserved for
  environment/env errors like omissions).
- Failing-open not introduced: the exemption is explicit, never silent.

## 5. Acceptance Criteria

1. `coverage run --min-branch 100` fails (exit 1) on a fixture with an
   uncovered ternary arm, succeeds without the flag.
2. `coverage run --min-branch 100` exits 0 with the exemption note on a
   project containing zero branch points.
3. `test --min-branch` and `coverage show --min-branch` apply the same
   zero-branch exemption (consistency).
4. Unit tests cover exempt/fail/populated-pass paths.
5. `ruff`, `black --check`, and full `CI=true pytest` (incl. e2e) pass;
   plan.md tasks committed per workflow.

## 6. Out of Scope

- `--min-branch` on watch mode (documented line-only today) and
  `[coverage].min_branch` config key.
- Per-arm branch display changes; nested ternary coverage; short-circuit
  `and`/`or` instrumentation.
- Touching `hit_ret` naming or plan schema (PR #39 remains as-is).
