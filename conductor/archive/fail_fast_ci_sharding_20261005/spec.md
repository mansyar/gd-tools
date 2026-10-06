# Spec: Fail-Fast and CI Sharding (`fail_fast_ci_sharding_20261005`)

## Overview

Add two pytest-parity orchestration features to `gd-tools test`, reducing CI wall-clock and feedback latency for large suites: **fail-fast** (`--exitfirst`) and **CI sharding** (`--shard k/N`). Both operate at the orchestration layer (`cli.py` → `orchestrator.py`) on top of the existing suite-per-process native runtime; no GDScript runtime changes are required.

## Functional Requirements

### 1. `--exitfirst` (fail-fast)

- **FR1.1** New flag `--exitfirst` on `gd-tools test`. Alias `-x` (pytest-compatible short form).
- **FR1.2** When a suite's **final result** is a failure, stop dispatching new suites. In-flight suites (already dispatched to parallel workers) are allowed to complete and their results are collected normally ("stop dispatch, drain in-flight").
- **FR1.3** "Failure" means any failing suite result: test failures, infrastructure errors, preflight failures, or timeouts. Suite-level skips and passes never trigger the stop.
- **FR1.4** Retries are respected: a test that fails once but passes on a configured retry does **not** trigger fail-fast; only a suite whose final aggregated result is a failure does.
- **FR1.5** Without `--parallel`, semantics are identical but trivially sequential (current suite finishes, no further suite starts).
- **FR1.6** On early stop, output includes a clear summary line, e.g. `Stopped early: fail-fast after suite <id> (K of M suites skipped)`. Unstarted suites are reported as skipped-due-to-fail-fast in the run summary/artifact index.
- **FR1.7** Exit code is unchanged: the run exits 1 (the existing failure code) per the documented exit map (ARCHITECTURE §9.7). No new exit codes.
- **FR1.8** **Coverage interplay:** in a `--coverage` run stopped early, coverage data from all executed (in-flight drained) suites is still collected and the report is generated from the partial data, with the summary and HTML report clearly labeled as partial (e.g., "partial run — fail-fast stop"). This matches the existing precedence that the report is written before errors propagate (§6.4).
- **FR1.9** `--exitfirst` is allowed with `--watch`: each watch iteration applies fail-fast independently; the stop state resets per iteration so a fixed test restores full subsequent runs.
- **FR1.10** Caches (preflight, import) behave as usual; fail-fast does not poison or invalidate caches.

### 2. `--shard k/N` (CI sharding)

- **FR2.1** New flag `--shard k/N` on `gd-tools test` (e.g. `--shard 2/4`). `k` is 1-based; invalid forms (k<1, k>N, N<1, malformed) exit 2 with a usage error before any work.
- **FR2.2** **Suite-level** sharding: whole suites are assigned to shards; no test-level splitting.
- **FR2.3** Assignment is **round-robin over the deterministic plan order**: after the plan is built and sorted (existing deterministic ordering), suite *i* (0-based) goes to shard ((i mod N) + 1). Assignment is stable across runs, machines, and shard count changes for unchanged plan prefixes.
- **FR2.4** **Flag pipeline (order of operations):** changed-filtering (`--changed`) is applied first to build the plan; sharding then selects the shard's subset of the filtered plan; parallelism (`--parallel`) then applies within the shard. Each flag keeps exactly one job.
- **FR2.5** `--shard` is rejected with `--watch` (exit 2): sharding is a CI concern, watch is a dev-loop concern.
- **FR2.6** Sharding composes freely with `--exitfirst` (fail-fast applies within the shard's run).
- **FR2.7** The run banner/header reports shard context: `Running shard k/N (M of T suites)`.
- **FR2.8** `--shard 1/1` is valid and equivalent to no sharding.
- **FR2.9** Coverage runs work per-shard as they do today (each shard produces its own coverage data/report); merging across shards remains the existing `coverage merge` workflow. Coverage plan cache keys are unaffected (plan is built pre-shard).

### 3. Configuration

- **FR3.1** Both flags are **CLI-only** in v1. No additions to `gd-tools.toml` `[test]` and no JSON Schema changes.

### 4. Documentation

- **FR4.1** README: flag reference entries for `--exitfirst`/`-x` and `--shard k/N`, including the interplay rules (FR1.9, FR2.5, FR2.4).
- **FR4.2** A CI recipe (docs) demonstrating a GitHub Actions matrix over shard indices with `coverage merge` across shards.
- **FR4.3** ARCHITECTURE.md: orchestration section updated for the dispatch loop change (fail-fast gate, shard selection step) and the round-robin assignment rule.

## Non-Functional Requirements

- **NFR1** No behavior change when neither flag is passed (zero-risk default path).
- **NFR2** Shard selection must be deterministic and side-effect-free on the plan cache (plan is built full, selection is a filter).
- **NFR3** Output remains machine-parseable; existing JUnit XML/JSON result shapes gain at most additive fields (e.g., fail-fast skip reason), never breaking changes.

## Acceptance Criteria

1. `--exitfirst` with a failing first suite: no further suites dispatched; in-flight results collected; summary line present; exit 1; artifacts complete for executed suites.
2. `--exitfirst` + retries: a test that fails then passes on retry does not stop the run.
3. `--exitfirst` + `--parallel N`: workers drain; no deadlock or orphaned processes; results coherent.
4. `--exitfirst` + `--coverage`: partial report generated and labeled partial.
5. `--shard 2/3` (of 12 suites) runs exactly suites 2, 5, 8, 11 in plan order; identical selection on re-run.
6. `--changed` + `--shard`: shard selection applies to the changed-filtered plan.
7. `--shard` + `--parallel`: parallelism applies within the shard only.
8. `--shard 4/3`, `--shard 0/3`, `--shard 3` → exit 2 usage errors.
9. `--shard` + `--watch` → exit 2 usage error.
10. Neither flag: byte-identical behavior to v0.7.0 (regression safety).
11. Unit + integration + e2e tests pass across the CI matrix; coverage of new orchestration code ≥ project standard.

## Out of Scope

- Test-level sharding or dynamic work-stealing between shards.
- Config-file equivalents (`[test] exitfirst`/`[test] shard`) — deferred.
- Distinct exit code for fail-fast early stop.
- Hard-cancel of in-flight suites on failure.
- `--shard` integration with `--watch` (rejected, not deferred-composed).
- CI workflow changes to this repo's own pipeline beyond what's needed to validate the feature.
