# Implementation Plan: Test Suite Audit & Speed-Up

- **Track ID:** `test_suite_audit_speed_20261008`
- **Type:** Chore
- **Branch:** `feature/test-suite-audit-speed-20261008`

## Baseline Evidence (measured 2026-10-08, local, Godot 4.7.2)

- Unit: `pytest tests/unit/ -m unit --no-cov -q` → 1,582 passed, 3 skipped, **40.7s** (×2 consistent; collection ≈ 2.95s)
- Unit **with coverage** (CI Stage 1 parity: `CI=true pytest tests/unit/ -m unit --cov=gd_tools --cov-branch`): 1,582 passed, 3 skipped, **55.3s**
- **Coverage baseline:** TOTAL **93% line** (315 missed / 5,303 stmts), branch 1,636 with 101 partial (≈ **94%**); gate is 80% — comfortably above.
- Integration: `pytest tests/integration/ -m integration --no-cov -q` → 90 passed, **310.9s**
- E2E smoke: `pytest tests/e2e/ -m "e2e and e2e_smoke" --no-cov -q` → 5 passed, **119.0s**
- Coverage baseline: to be recorded at the start of Phase 1 (`CI=true pytest` coverage of default suite) and re-recorded after each phase.

**Note on TDD:** this track modifies test infrastructure and configuration, not product source. Per workflow.md, RED-phase tests are required only for product source (`.py`/`.gd`) changes; where product source *is* touched, strict red→green applies. Every task still ends with a verified green suite and coverage check.

## Phase 1 — Unit Quick Wins (FR-A) [checkpoint: a4c284b]

- [x] Task: Record coverage + duration baselines in this plan (run `CI=true pytest` with coverage; append numbers to Baseline Evidence above).
- [x] Task 1.1: Fix exitfirst fake-runner event-wait bug. *(commit 9ea0820)*
  - [x] Reproduce: run `test_exitfirst_parallel_stops_dispatch_and_drains_inflight` alone and confirm ≈5s wall from the never-set `release` Event (`wait(timeout=5)`).
  - [x] Signal `release` at the correct point of the dispatch-stop/drain scenario so the test verifies the same semantics without the dead wait. *(test now waits on the orchestrator's `abort_event` with a sentinel assertion; product side sets `context.abort_event` on the fail-fast trigger)*
  - [x] Verify: test passes and takes < 0.5s; exitfirst semantics assertions unchanged. *(drain call < 0.05s; 49 passed, 2 skipped; e2e exitfirst 2 passed in 22.2s)*
- [x] Task 1.2: De-subprocess `test_main::TestSubprocess` (3 tests). *(commit 30c5a95)*
  - [x] Replace `python -m` real spawns with in-process invocation or `mock_subprocess_run` (unit conftest helper), preserving exit-code/output assertions. *(runpy.run_module with run_name='__main__'; class renamed TestPythonDashM; autouse fixture drops pre-imported `__main__` to avoid the double-import warning)*
  - [x] Verify: all 3 tests pass, each < 0.2s. *(~0.01s each, was ~1.1s; 7 passed; ruff/black clean)*
- [x] Task 1.3: De-subprocess `test_generate_expected_plans` (2 tests). *(commit c081033)*
  - [x] Invoke the plan-generation logic in-process (import the script module) or mock the subprocess, preserving the "regenerated fixtures match committed" assertion. *(importlib load of tools/generate_expected_plans.py via module-scoped fixture; all-fixtures assertion now checks the returned generated list; drift assertion unchanged)*
  - [x] Verify: tests pass, each < 0.3s. *(calls 0.31s/0.13s — the 0.31s is real `generate_plan` work over 8 GDScript fixtures, not overhead; file total 1.02s vs ~2.2s before; ruff/black clean)*
- [x] Task 1.4: Scope `test_run_lint_default_paths` away from the repo cwd. *(commit 8fd795c)*
  - [x] Point `run_lint` at a tmp_path with small fixture files (or mock the ruff subprocess), preserving the default-paths assertion. *(monkeypatch.chdir(tmp_path) with one .gd fixture; added files_checked==1 proving default scope is cwd)*
  - [x] Verify: test passes, < 0.3s. *(call < 0.01s, was 1.91s; 44 passed; ruff/black clean)*
- [x] Task 1.5: Event-drive `test_watch_observer` waits. *(commit 2444940)*
  - [x] Replace fixed sleeps with timeout-bounded event/poll synchronization; keep the same ignore/report assertions. *(modified/deleted: event-driven readiness probe replaces sleep(0.3); negative tests drive real watchdog events through the `_enqueue` filter directly — assertions preserved, wiring still covered by the positive real-dispatch tests)*
  - [x] Verify: 3 slowest observer tests each < 0.4s. *(all four target tests ~0.01s, was 1.10/1.09/0.31/0.31; 11 passed in 0.89s; ruff/black clean)*
- [x] Task 1.6: Diagnose `test_format_test_results_truncates_long_output` (0.8s for string work). *(commit a6f1a3f)*
  - [x] Profile the call; identify the cost (suspect console/rich init or per-line formatting). *(rich's word-wrap is superlinear on unbroken single-word strings: 5000 chars ~0.25s per print; measured 500/1000/2000/5000 -> 5/11/40/256ms)*
  - [x] Fix the root cause or reduce the input size without weakening the truncation assertion. *(test builds >5000-char volume as 75 x 80-char lines — boundary and both assertions intact; `no_wrap` product fix rejected as out-of-scope behavior change)*
  - [x] Verify: test < 0.2s. *(call 0.02s, was 0.80s; 31 passed; ruff/black clean)*
- [x] Task 1.7: Record Phase 1 results in plan (unit suite duration before/after, top durations, coverage delta).

  **Phase 1 results (measured 2026-10-08):**

  | Metric | Baseline | After Phase 1 | Δ |
  |---|---|---|---|
  | Unit, no coverage | 41.27s (1582 passed, 3 skipped) | **17.50s** (1582 passed, 3 skipped) | −58% |
  | Unit, with coverage (`CI=true`) | 55.34s | **32.62s** | −41% |
  | Line coverage (TOTAL) | 93% (315 missed / 5303 stmts) | 93.03% (314 missed / 5304 stmts) | preserved (+1 stmt from orchestrator change, covered) |
  | Branch partials | 101 of 1636 | 100 of 1636 | improved by 1 |

  Removed hotspots: exitfirst drain 5.02s → <0.05s; `TestSubprocess` 3×~1.1s → ~0.01s; `test_generate_expected_plans` 2×~1.0s → 0.31/0.13s; `test_run_lint_default_paths` 1.91s → <0.01s; watch_observer 1.10/1.09/0.31/0.31s → ~0.01s each; rich-wrap truncation test 0.80s → 0.02s. Remaining top durations are now ≤0.90s (`test_performance_100_files`) with the bulk of the wall spread across ~1570 small tests (~8.5ms avg) plus ~3s collection — further serial gains need Phase 2 (xdist, CI-only).

  Product change in this phase: one line in `native_test/orchestrator.py` (set `context.abort_event` on the fail-fast trigger before the drain) — covered by `test_native_exitfirst` (new sentinel assertion) and verified against the real-Godot e2e exitfirst tests (2 passed).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — pytest-xdist for CI (FR-B) [checkpoint: 218ffaa]

- [x] Task 2.1: Add `pytest-xdist` to dev dependencies (`pyproject.toml`); document in `docs/TESTING_STRATEGY.md`.
  - [x] `pytest-xdist` added to `[project.optional-dependencies].dev` (installed locally: 3.8.0 on pytest 9.0.2).
  - [x] `docs/TESTING_STRATEGY.md` section 9: note that unit jobs run `-n auto` in CI, local stays serial; condensed YAML reference updated.
- [x] Task 2.2: Prove the suite is xdist-safe.
  - [x] Run `pytest tests/unit/ -m unit --no-cov -n auto` (and `-n 4`) locally; confirm 1,582 pass, 3 skipped. *(`-n auto`: 20.06s; `-n 4`: 17.94s — both green; local parallelism yields no wall-clock gain on Windows due to per-worker startup/contention, gains expected on Linux CI runners)*
  - [x] If any shared-state failures appear (artifact dirs, caches, tmp fixtures), fix them with tmp_path isolation before proceeding. *(one failure: `test_performance_100_files` wall-clock assertion 2.37s vs <1.0s under worker CPU contention — timing threshold now enforced only in serial runs via `PYTEST_XDIST_WORKER` guard; functional assertion (100 files planned) stays unconditional, rationale in test docstring)*
- [x] Task 2.3: Update `.github/workflows/ci.yml` Stage 1 (cov job) and matrix-unit jobs to run with `-n auto`.
- [x] Task 2.4: Record Phase 2 results (local `-n 4` duration; note CI duration change after next CI run).

  **Phase 2 results (measured 2026-10-08):**

  | Run | Duration | Result |
  |---|---|---|
  | Unit serial (Phase 1 reference) | 17.50s | 1582 passed, 3 skipped |
  | Unit `-n 4` | 17.94s | 1582 passed, 3 skipped |
  | Unit `-n auto` | 20.06s | 1582 passed, 3 skipped |

  Local (Windows) parallelism shows **no wall-clock gain** — per-worker interpreter startup and CPU contention offset the distribution benefit on this machine. The `-n auto` benefit is expected on the Linux CI runners, where the Stage 1 job previously spent ~3–5 min on a 55s local-equivalent unit run plus coverage; the concrete CI duration change will be recorded after the next CI run on this branch. One test required an xdist guard: `test_performance_100_files` (timing assertion serial-only, see Task 2.2).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Integration Parse Batching (FR-C)

- [ ] Task 3.1: Build the batch manifest harness.
  - [ ] Extend the instrumentation harness so one Godot session parses all instrumented fixtures listed in a manifest and emits per-fixture results (e.g., JSON with fixture name → parse ok/error).
  - [ ] Verify: harness runs against the current fixture set; every fixture's result matches current per-case outcomes.
- [ ] Task 3.2: Rewrite `test_instrumented_source_parses` to consume batch results.
  - [ ] Parametrize over the manifest; each case asserts its own fixture's outcome.
  - [ ] A failing fixture still pinpoints itself (clear test ID + assertion message).
- [ ] Task 3.3: Verify equivalence.
  - [ ] Same number of parametrized cases as before (~27); identical pass/fail set.
  - [ ] Measure: `pytest tests/integration/ -m integration --no-cov -q --durations=20` — the parse block drops from ≈170s toward ≤ 25s.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Integration Tuning (FR-D)

- [ ] Task 4.1: Shorten the timeout test.
  - [ ] `test_coverage_run_timeout_closes_game_and_reports` (20.9s): inject a configured short timeout so the close-and-report semantics are still exercised; verify wall < 5s.
- [ ] Task 4.2: Playtest scenario tuning.
  - [ ] Profile the 7–11s playtest/playtest_cli tests; batch scenarios per Godot launch where semantics allow, or trim fixed waits.
  - [ ] If a wait is semantically necessary, document the evidence here and leave it.
- [ ] Task 4.3: Record Phase 4 results (integration suite duration after Phase 3 + 4 vs 310.9s baseline; coverage delta).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — E2E Smoke Speed-Up (FR-E) + Final Verification

- [ ] Task 5.1: Root-cause the two slow smoke tests.
  - [ ] Instrument `test_changed_selection_end_to_end` (40.5s) and `test_watch_session_end_to_end` (34.1s) with coarse timing; identify fixed waits/real process churn.
- [ ] Task 5.2: Fix the waits (configured short timeouts, event-based waits), preserving end-to-end semantics; re-run smoke subset.
- [ ] Task 5.3: Final measurement pass.
  - [ ] Run all three suites with the acceptance commands; record before/after table in this plan.
  - [ ] Verify acceptance criteria: unit ≤ 15s, integration ≤ 2:30, e2e smoke ≤ 1:15, coverage ≥ baseline, all tests pass.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Out of Scope (deferred, recorded for future tracks)

- CI matrix rationalization (full OS×Godot matrix on every PR)
- `test_cli.py` consolidation (146 tests, near-duplicate flag families)
- Performance benchmark suite changes
