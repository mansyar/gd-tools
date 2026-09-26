# Track godot_compat_ci_matrix_20260926 Context

Run the Godot-dependent CI stages across a real version × OS matrix so the
declared Godot 4.5+ support claim is verified rather than assumed.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

`product.md` declares Godot 4.5+ support on Windows, macOS, and Linux, and
ROADMAP §8 Phase 5 gates the native runtime release on running the Godot 4.5+
compatibility matrix. Today both Godot stages run on `ubuntu-latest` only,
pinned to a single `GODOT_VERSION: '4.6.1'`. The Windows Godot path has never
executed in CI.

**Matrix:** `4.5.2` / `4.6.1` / `4.7.1` × `ubuntu-latest` / `windows-latest`,
applied to both `integration` and `e2e` — 6 jobs per stage, 12 total.

## Load-bearing decision

**Phase 1 lands the CI skip-guard before the matrix is wired.** The integration
and e2e conftests currently *skip* when Godot is absent, which is masked today
by a hard-failing `godot --version` step. Once `GODOT_BIN` becomes dynamic per
OS, a silent install failure would turn 12 jobs green that ran zero tests. The
guard must exist before the first matrix run.

## Deliberately out of scope

- **macOS runners** — remains ROADMAP Track 36
- **Parallel test execution within a job**
- **Externalising `GUT_VERSION_MAP`** — ROADMAP Track 32
- **Quarantining the known-flaky Godot tests** — `known_flakes.md` items 1 and 2
  are an explicit product decision
- **Tightening `check_version_compatible()` to a closed supported set** — a
  product decision, not a CI change

## Accepted tradeoffs

- **CI wall clock.** 2 Godot jobs become 12, taken serially, which will likely
  exceed the `product.md` < 10 min criterion. Accepted deliberately; Phase 3
  measures the real figure. A nightly schedule for the widest axes is a
  follow-up decision, not smuggled in here.
- **Failure fixes are capped** at 3 distinct root causes. Exceeding the cap is
  an explicit decision point — extend the track, or mark that single axis
  `continue-on-error` and file a follow-up to re-ratchet.
