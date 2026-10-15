# Track Specification: Random Test Order & Seed Reproducibility

**Track ID:** `random_test_order_20261015`
**Type:** Feature
**Branch:** `feature/random-test-order-20261015`
**Status:** New
**Created:** 2026-10-15

---

## 1. Overview

`gd-tools test` executes suites in a fixed order derived from the filesystem:
`_iter_test_files` sorts test files by POSIX path, `discover_native_suites`
emits suites in that order with each suite's test methods in declaration order,
and `run_native_tests` dispatches them in that sequence. That order is stable,
which is good for reproducibility — and it means a suite that leaks state onto
a global, an autoload, or the scene tree can pass forever simply because the
suite that would expose it always runs afterwards.

This track adds an opt-in, seeded shuffle of the execution order: suites are
shuffled, and test methods are shuffled inside each suite. The seed that
produced an order is reported and recorded, so any failure is replayable
exactly with `--seed`.

The feature composes with the orchestration flags already shipped —
`--changed`, `--shard`, `--parallel`, `--exitfirst`, `--watch`, `--coverage` —
without changing shard membership or any exit code.

### 1.1 Why opt-in

Randomization changes which of two order-dependent tests fails, and it makes
run-to-run output order unstable. Turning that on by default on upgrade would
make existing green CI unpredictable for every user. `--parallel` and
`--exitfirst` were both shipped opt-in for the same reason; this follows them.
Projects that want it always set `[test] random_order = true`.

---

## 2. Functional Requirements

### 2.1 CLI Surface

| ID | Requirement |
| --- | --- |
| **FR-1** | `gd-tools test --random-order` shuffles the execution order of the selected suites and of the test methods within each suite. The flag is opt-in and defaults to off. |
| **FR-2** | `gd-tools test --seed <int>` sets the shuffle seed. The value must be a non-negative integer; a negative value, or a value that is not an integer, exits 2 with an actionable message. |
| **FR-3** | Passing `--seed` without `--random-order` implies random ordering. A seed is only meaningful as an ordering input, so requiring both flags would be a trap rather than a safeguard. |

### 2.2 Configuration

| ID | Requirement |
| --- | --- |
| **FR-4** | `[test] random_order: bool = False` persists the opt-in per project. |
| **FR-5** | `[test] seed: int \| None = None` optionally pins the project's order. Unset (the default) generates a fresh seed on every run; set, it makes every run use one fixed permutation. The CLI `--seed` overrides the config value. |
| **FR-6** | The checked-in JSON Schema snapshot at `docs/gd-tools.schema.json` is regenerated so `test_checked_in_schema_snapshot_is_current` stays green. |

### 2.3 Ordering

| ID | Requirement |
| --- | --- |
| **FR-7** | Suites are shuffled with a single seeded RNG stream over the deterministic discovery order. |
| **FR-8** | Test methods are shuffled within each suite using the same seeded stream, so the whole run is a deterministic function of `(seed, suite set, test set)`. |
| **FR-9** | Shuffling is applied after `--changed` narrowing and after the integration preflight, so parameterized cases expanded by preflight are ordered consistently with the manifest actually sent to Godot. |
| **FR-10** | The seed is auto-generated when neither `--seed` nor `[test] seed` supplies one. Generation uses `random.SystemRandom` and yields a 31-bit unsigned integer for terminal-friendly reporting. |

### 2.4 Sharding Contract (preserved)

| ID | Requirement |
| --- | --- |
| **FR-11** | `--shard K/N` membership continues to be computed by round-robin over the **deterministic discovery order**, independent of any seed. Randomization affects the order in which a shard's selected suites execute, never which shard owns which suite. |
| **FR-12** | Consequently, a sharded run with different seeds on each matrix job still covers every suite exactly once. This is deliberate: seed-dependent membership would let a mistyped seed silently drop suites from all shards. |

### 2.5 Reporting & Replay

| ID | Requirement |
| --- | --- |
| **FR-13** | Every random-order run prints the seed it used, in the form `Random order: seed <N> (replay with --seed <N>)`, adjacent to the existing summary footer. |
| **FR-14** | The seed is recorded in the run artifact index at `.gd-tools/artifacts/<run_id>/artifacts.json` as an additive key, so a run can be reproduced from its own artifacts. |
| **FR-15** | Under `--verbose`, the resolved execution order is listed (suite names in run order, each with its shuffled method order) so the user can inspect what will run without guessing. |
| **FR-16** | Passing the reported seed back reproduces the identical order for the same suite and test sets. |

### 2.6 Composition

| ID | Requirement |
| --- | --- |
| **FR-17** | Composes with `--changed` (narrow first, then shuffle), `--shard` (FR-11), `--parallel` (dispatch order is the shuffled order; results still aggregate in submission order), `--exitfirst` (the trigger is still the first *executed* failing suite), `--coverage`, `--suite`/`--test`/`--tag` filters, and positional paths. |
| **FR-18** | Under `--watch`, one seed is generated for the session, reported once, and reused for every re-run, so successive re-runs stay comparable. `--seed` pins it explicitly. A re-run that selects a different suite set shuffles that set with the same session seed. |
| **FR-19** | `--random-order` combined with `--shard` is accepted, not rejected. Declaring the combination a flag conflict is explicitly not the implementation strategy for FR-11. |

---

## 3. Non-Functional Requirements

| ID | Requirement |
| --- | --- |
| **NFR-1** | With randomization disabled, behavior is unchanged: byte-identical stdout for the same run, identical exit codes, identical JUnit XML, and an artifact index identical apart from the additive seed key. |
| **NFR-2** | Ordering overhead is under 50 ms for 1,000 suites and 10,000 tests. |
| **NFR-3** | Order is reproducible across operating systems for the same seed and inputs on the same Python minor version. Reproducibility across Python minor versions is explicitly not guaranteed and is documented as such. |
| **NFR-4** | No native protocol change: `NATIVE_PROTOCOL_VERSION` is not bumped, no GDScript is modified, and the artifact index gains only an additive key (no version field is bumped). |
| **NFR-5** | No new runtime dependencies; ordering uses the standard library `random` module. |
| **NFR-6** | The new ordering module reaches >= 80% line coverage with ruff and black clean, per the project's quality gates. |

---

## 4. Acceptance Criteria

1. `gd-tools test --random-order` runs the selected suites in an order that differs from the discovery order for a fixture with >= 5 suites, and prints a seed line.
2. `gd-tools test --random-order --seed 1234` run twice produces the identical execution order both times.
3. `gd-tools test --seed 1234` (no `--random-order`) randomizes, per FR-3.
4. Test methods inside a suite execute in a shuffled order, verified against the per-suite manifest the orchestrator dispatches.
5. `[test] random_order = true` randomizes without any CLI flag; `[test] seed = 1234` additionally makes the order fixed across runs; `--seed 99` overrides the config seed.
6. `--seed -1` and `--seed abc` exit 2 with an actionable message naming the accepted range.
7. `gd-tools test` with no flag and no config key produces output byte-identical to the current release for the same project.
8. `--shard 1/2` and `--shard 2/2` run under two *different* seeds select the same two disjoint suite sets as they do on the unrandomized path, and their union is the full suite set.
9. `--shard K/N --random-order --seed S` and `--shard K/N --seed S` select the same suites; the seed changes only the order within the shard.
10. `--random-order --parallel 4` completes with the same pass/fail totals as a sequential random run, and the summary lists results in the shuffled order.
11. `--random-order --exitfirst` still stops dispatching after the first executed failing suite.
12. `--random-order --changed` shuffles only the narrowed suite set.
13. `--watch --random-order` reports one seed, and every re-run in the session uses that seed.
14. The run artifact index contains the seed, and `test_checked_in_schema_snapshot_is_current` passes after regenerating `docs/gd-tools.schema.json`.
15. The full suite passes: `CI=true pytest`, `ruff check src/ tests/`, `black --check src/ tests/`.

---

## 5. Out of Scope

- **Shuffling expanded parameterized cases** (e.g. the individual `name[case]`
  entries preflight derives). Suites and their declared methods are shuffled;
  case expansion order is left to preflight. They can be added later without
  changing the seed contract, because the shuffle already runs after preflight.
- **Randomization on by default.** FR-1 fixes the opt-in default; a future
  track can revisit it after field evidence.
- **Randomizing anything other than `gd-tools test`** — not `coverage run`,
  lint, format, or the migration report.
- **Persisting an auto-generated seed back into `gd-tools.toml`.** The seed is
  reported and recorded in the artifact index; writing it into user config is
  not done implicitly.
- **pytest-randomly-style fixture/class-level hooks** (reset of RNG per test,
  test-order-aware fixtures). There is no equivalent extension point in the
  native runtime, and this track does not add one.
- **Any change to the native protocol, the GDScript addons, or the coverage
  plan schema.**
