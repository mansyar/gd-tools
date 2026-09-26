# Godot 4.5+ Compatibility Matrix in CI

- **Track ID:** `godot_compat_ci_matrix_20260926`
- **Type:** Chore (infrastructure / verification)
- **Status:** Draft — awaiting approval
- **Origin:** Surfaced during Conductor codebase review of `main` @ `afb58c2`, after
  `native_scene_integration_20260925` completed. Closes the gap between a *declared*
  support matrix and a *verified* one.

---

## 1. Problem

`conductor/product.md` declares support for **Godot 4.5+** across **Windows, macOS, and
Linux**, and lists a native-runtime success criterion that the Godot 4.5+ compatibility
matrix must run. `docs/ROADMAP.md` §8 Phase 5 gates the native runtime release on
"Run the Godot 4.5+ compatibility matrix."

CI verifies neither claim.

`.github/workflows/ci.yml` defines four jobs:

| Job | Runner | Python | Godot |
|---|---|---|---|
| `lint-format-unit` | `ubuntu-latest` | 3.12 | n/a |
| `matrix-unit` | `ubuntu-latest`, `windows-latest` | 3.10/3.11/3.12 | n/a |
| `integration` | `ubuntu-latest` | 3.12 | **4.6.1 only** |
| `e2e` | `ubuntu-latest` | 3.12 | **4.6.1 only** |

The only OS matrix (`ci.yml:82`) applies to `matrix-unit`, which runs
`pytest tests/unit/ -m unit --no-cov` — pure Python, no Godot. Both Godot-dependent
stages are `runs-on: ubuntu-latest` with a single global `GODOT_VERSION: '4.6.1'`
(`ci.yml:14`).

**Consequences:**

1. The Windows Godot code path has never executed in CI — on the platform this
   repository is developed from.
2. Godot 4.5 (the declared minimum) and 4.7 (the current stable line) are untested.
   A user on the minimum supported version can hit a break we would not have caught.
3. `check_version_compatible()` (`src/gd_tools/godot.py:89`) accepts an open
   `>= (4, 5, 0)` range, so `gd-tools` will happily run on versions no test has ever
   exercised.

**The production code is already cross-platform.** This track is CI wiring, not a
portability rewrite:

- `find_godot_binary()` (root `conftest.py`) resolves `GODOT_BIN` when it is a real
  file, else `shutil.which("godot")` — which resolves `godot.exe` on Windows via
  `PATHEXT`.
- `_check_common_locations()` (`godot.py:204`) has complete `win32` / `darwin` /
  linux candidate lists.
- `_build_not_found_message()` (`godot.py:240`) has per-platform install instructions.
- Test fixtures are `pathlib`-based throughout.

**What actually blocks a Windows/multi-version run is confined to `ci.yml`:**

| Blocker | Location |
|---|---|
| `GODOT_BIN: /usr/local/bin/godot` — hardcoded POSIX path | `ci.yml:116`, `ci.yml:159` |
| `wget` / `unzip` / `chmod` / `sudo mv` — bash-only install | `ci.yml:130-135`, `ci.yml:173-179` |
| Single `GODOT_VERSION` env var | `ci.yml:14` |
| Artifact names collide across matrix jobs | `ci.yml:146`, `ci.yml:192` |

---

## 2. Scope

Make the `integration` and `e2e` stages run across a Godot-version × OS matrix,
blocking on day one, with a platform-aware Godot install. Fix any failures the new
axes surface, subject to §7.

**Matrix:** `godot-version: ['4.5.2', '4.6.1', '4.7.1']` ×
`os: [ubuntu-latest, windows-latest]` = **6 jobs per stage, 12 Godot jobs total**.

All three versions are confirmed published, so no axis can 404:

| Version | Status | Released |
|---|---|---|
| 4.5.2 | latest 4.5 maintenance | 2026-03-19 |
| 4.6.1 | current CI pin | — |
| 4.7.1 | latest 4.7 maintenance; 4.7 is the current stable line | 2026-07-14 |

This aligns with `GUT_VERSION_MAP` (`godot.py:109`), which already maps 4.5/4.6/4.7.

---

## 3. Out of Scope

- **macOS runners** — deliberately excluded; remains ROADMAP Track 36.
- **Parallel test execution within a job** — the suite is already sequential and
  `known_flakes.md` reports contention-sensitive Godot exits.
- **`GUT_VERSION_MAP` externalisation / user override** — ROADMAP Track 32.
- **Quarantining the known-flaky Godot tests** — `known_flakes.md` items 1 and 2 are
  explicitly "the project's call, not an implementation detail."
- **Raising `timeout-minutes` beyond what the new axes demonstrably need** except as
  required to avoid false failures (see §6).
- **`check_version_compatible()` tightening** to a closed supported set — a product
  decision, not a CI change.

---

## 4. Functional Requirements

### R1 — Platform-aware Godot install

Replace the bash-only install block in both Godot stages with a step that selects the
release asset by runner OS. Godot publishes per-platform asset names:

| Runner | Asset |
|---|---|
| `ubuntu-latest` | `Godot_v<version>-stable_linux.x86_64.zip` |
| `windows-latest` | `Godot_v<version>-stable_win64.exe.zip` |
| `macos-latest` | `Godot_v<version>-stable_macos.universal.zip` (out of scope) |

The Windows zip contains `Godot_v<version>-stable_win64.exe`; the Linux zip contains
`Godot_v<version>-stable_linux.x86_64`. Each must be renamed or exposed as `godot` /
`godot.exe` consistently. The existing `chmod +x` must be applied only on Linux, and
`sudo mv` only on Linux.

### R2 — Dynamic `GODOT_BIN`

Remove the hardcoded `/usr/local/bin/godot`. Set `GODOT_BIN` from the step that
installed the binary, per OS (`$GITHUB_WORKSPACE` on Windows, `/usr/local/bin` on
Linux), so `find_godot_binary()` resolves it via its existing "env var is a real file"
branch.

### R3 — Guard against a falsely-green matrix *(critical)*

`tests/integration/conftest.py` and `tests/e2e/conftest.py` both **auto-skip** the
entire suite when Godot is absent:

```python
binary = find_godot_binary()
if binary is None:
    pytest.skip("Godot binary not found - set GODOT_BIN or add to PATH ...")
```

Today this is masked because the install step is followed by a bare
`godot --version` that hard-fails. Once `GODOT_BIN` becomes dynamic per OS, a silent
install failure would turn **6 jobs green that ran zero tests** — strictly worse than
the current single-version job, because the regression is invisible.

Required: when `CI` is set (already exported as `CI: 'true'` at `ci.yml:13`), a missing
Godot binary must **fail** the run, not skip it. Local runs must keep skipping
gracefully so a contributor without Godot is not blocked.

A skipped-everything run must never be reportable as passing.

### R4 — Matrix hygiene

- `fail-fast: false` — one failing axis must not cancel the other five, or a single
  Godot regression hides the rest of the matrix.
- Artifact names must be suffixed with `${{ matrix.godot-version }}-${{ matrix.os }}`.
  The current fixed names (`junit-results-integration`, `junit-results-e2e`) would
  collide across 6 jobs each and overwrite one another in `upload-artifact@v4`.
- Keep `godot-version` and `os` on **separate matrix axes** (not combined strings) so
  GitHub renders a readable grid and a failure names both dimensions.

### R5 — Keep the Godot stages off the Python axis

The Godot stages stay pinned to Python 3.12. The 3.10/3.11/3.12 axis is already
covered by `matrix-unit`, which needs no Godot. Adding it here would take 12 jobs to 36.

### R6 — Document the matrix

Update `docs/ROADMAP.md` §8 Phase 5 to record that the 4.5/4.6/4.7 matrix runs on
Windows and Linux, and note that macOS remains Track 36. Update the CI section of
`docs/CONTRIBUTING.md` if it documents the job layout.

---

## 5. Non-Functional Requirements

- **Correctness over speed.** A green matrix must mean the tests ran (R3).
- **No new product dependencies.** No `watchdog`-class additions; this is CI config plus
  at most a small conftest guard.
- **Failure legibility.** A red job must name the Godot version and OS in the job name.
- **Repeatable.** No reliance on runner-local state; the Godot binary path must be
  explicit per job.

---

## 6. Known Tradeoff — CI Duration

`product.md` sets a **CI < 10 min** criterion. This track takes the Godot stages from
2 jobs to 12. The stages currently run serially (`e2e` `needs: integration`), so wall
clock becomes roughly the sum of two matrix waves rather than the max.

The two Godot stages are already `timeout-minutes: 10` each, which is a per-job cap
rather than a total-CI budget — the existing pipeline is likely already near or over
10 minutes of total wall clock before this change.

This is accepted deliberately: verifying a declared support matrix is worth more than
the duration criterion, and the two concerns are separable. But it must be recorded,
not glossed over — if CI duration becomes a problem, the lever is a nightly schedule
for the widest axes, which is a follow-up decision, not something to smuggle in here.

`known_flakes.md` also predicts this will help: a 12-job matrix surfaces
intermittent Godot failures sooner and with better attribution than a single serial
run.

---

## 7. Fixing Surfaced Failures

The user chose **blocking from day one**, which means this track also owns the fixes
for whatever the new axes reveal.

**Proposed cap:** up to **3 distinct root causes**, each a self-contained fix with its
own test. Rationale: keeps the track reviewable and bounded while honoring "blocking."

**If a fix exceeds the cap, this is an explicit decision point, not something to
resolve silently.** The options, in order of preference:

1. Extend the track — accept the larger scope knowingly.
2. Relax that specific axis to non-blocking (`continue-on-error: true`) and file a
   follow-up track to fix and re-ratchet. A documented, tracked, non-blocking axis is
   strictly better than an untracked one.
3. Defer the axis entirely (e.g. drop 4.7) and revisit.

**Expected failure surface, ranked by likelihood:**

1. **Windows `res://` path handling** in the native runtime or fixture projects —
   the highest-risk unknown, and the reason this track is worth doing.
2. **Windows process/exit-code semantics** — `known_flakes.md` records that whether a
   `push_error` escalates Godot's exit code is timing- and contention-sensitive.
   `native_test/orchestrator.py` asserts exact agreement between the result-file
   status and the process return code; a Windows-specific difference here would fail
   loudly rather than silently.
3. **Godot 4.5 vs 4.7 behavioral differences** in the GDScript runtime or addon API.
4. **Test-suite timing** — Windows runners are slower; fixed timeouts may need raising.
   Raising a timeout to accommodate the matrix is in scope; changing what a timeout
   *means* is not.

---

## 8. Success Criteria

1. `integration` runs as a 6-job matrix over `{4.5.2, 4.6.1, 4.7.1} ×
   {ubuntu-latest, windows-latest}`.
2. `e2e` runs as the same 6-job matrix.
3. `GODOT_BIN` is no longer a hardcoded POSIX path anywhere in `ci.yml`.
4. No bash-only construct (`wget`, `sudo mv`, `chmod` without guard) executes on a
   Windows runner.
5. **A deliberately broken Godot install (R3) fails all 12 Godot jobs** — verified by
   a negative test, not by inspection.
6. `fail-fast: false` is set on both matrices.
7. JUnit artifact names are unique per matrix cell; 6 artifacts upload per stage
   without collision.
8. Both Godot stages remain pinned to a single Python version (3.12).
9. Every discovered failure is either fixed within the §7 cap, or recorded in a
   follow-up track with its axis explicitly marked non-blocking.
10. `docs/ROADMAP.md` §8 Phase 5 and (if applicable) `docs/CONTRIBUTING.md` reflect
    the actual matrix.
11. `godot --version` is verified inside every matrix job and its output is captured
    in the job log, so a version mismatch is diagnosable from CI output alone.
12. Ruff and Black pass; the project self-coverage gate (≥80% line / ≥70% branch) is
    unchanged or better.

---

## 9. Verification Approach

The matrix itself cannot be verified by running the local suite — it is verified by
the CI run itself. Local verification therefore covers:

- **R3 negative test:** a unit test proving the conftest guard fails (not skips) when
  `CI` is set and Godot is absent. This is the one requirement with real logic and must
  be test-covered rather than eyeballed.
- **Workflow syntax:** `actionlint` or equivalent YAML/scheme validation of `ci.yml`.
- **Matrix expansion assertion:** a check that the job set resolves to the expected
  6 × 2 cell count.
- **Post-merge:** the first full CI run on this branch is the real acceptance gate for
  everything else.

---

## 10. Related

- `conductor/product.md` §9 — Native Test Runtime Direction (declares 4.5+)
- `docs/ROADMAP.md` §8 Phase 5 — Hardening and Release (compatibility matrix gate)
- `docs/ROADMAP.md` Track 36 — macOS CI Matrix (explicitly still open)
- `docs/ROADMAP.md` Track 32 — Configurable Version Mapping (GUT map externalisation)
- `conductor/tracks/coverage_target_contract_20260926/known_flakes.md` — the
  contention-sensitive Godot behaviour this track will stress
