# Project Tracks

This file tracks all major tracks for the project. Each track has its own detailed plan in its respective folder.

---

_Archived tracks live in `./archive/`._

- [x] **Track: GDScript AST Edge Cases** (archived → `./archive/ast_edge_cases_20260718/`)

---

- [x] **Track: Native Test Runtime Foundation**
  *Link: [native_test_foundation_20260925](./tracks/native_test_foundation_20260925/index.md)*

---

- [x] **Track: Native Scene and Resource Integration**
  *Link: [native_scene_integration_20260925](./tracks/native_scene_integration_20260925/index.md)*

---

- [x] **Track: Coverage Target Contract** (archived →
  `./archive/coverage_target_contract_20260926/`) - a coverage target that cannot be
  instrumented now warns and continues instead of escalating a process-fatal
  error that contradicted the code's own `return false`. The omission is recorded
  in the run diagnostics, the terminal report, and the artifact index; `--min`
  evaluates against the instrumented set with a separate gate so an omission
  cannot be silently ignored. Covers both runtimes, and stops the native
  collector from aborting all instrumentation on the first failure.

---

- [x] **Track: Godot 4.5+ Compatibility Matrix in CI** (archived → `./archive/godot_compat_ci_matrix_20260926/`)

---

- [x] **Track: Native Documentation Truth Pass** (archived → `./archive/native_docs_truth_pass_20260926/`)

---

- [x] **Track: Native Assertion Parity and `skip_test()`** (archived → `./archive/native_assertion_parity_skip_test_20260927/`) - add runtime skipping (the protocol already reserves the statuses; no GDScript emits them) and ten GUT-core assertions. Closes two of the six Known Limitations in `ARCHITECTURE.md` and unblocks migration roadmap Phase 3.

---

- [x] **Track: Native Runtime Correctness** (archived → `./archive/native_runtime_correctness_20260927/`) - make `wait_for_signal` bounded and honest, fix `_suite_timeout` to consider every test rather than the first, and make per-test timeout cancellation a named operation instead of a hand-maintained token.

---

- [x] **Track: Coverage Diff** (archived → `./archive/coverage_diff_20260928/`) - codecov-style
  coverage comparison: `coverage save-baseline` persists a self-contained plan+data
  snapshot with advisory metadata, and `coverage diff --base` reports per-file line and
  branch deltas (new/removed/improved/regressed files, newly-uncovered lines) with
  `--report-format json` and `--fail-on-regression` exit-1 gating for CI.

---

- [x] **Track: Watch Mode** (archived → `./archive/watch_mode_20260928/`)
- [x] **Track: GUT Compatibility Bridge** (Migration Phase 3)
  *Link: [gut_compat_bridge_20260928](./archive/gut_compat_bridge_20260928/index.md)* (archived → `./archive/gut_compat_bridge_20260928/`) - a
  GutTest-compatible shim base class in the gd-tools-test addon so legacy GUT
  suites run through the native protocol with the same result contract, without
  the GUT addon installed. Auto-routes per suite, preflight-fails unsupported
  constructs with migration guidance, removes the legacy GUT subprocess path,
  and adds coverage support plus `docs/gut-migration.md`.

---

- [x] **Track: Migration Tooling** (Migration Phase 4)
  *Link: [migration_tooling_20260929](./archive/migration_tooling_20260929/index.md)* (archived → `./archive/migration_tooling_20260929/`) - a guided `gd-tools migrate`
  command: read-only per-file migration report reusing the bridge preflight
  scanner (base class, supported/unsupported constructs with file:line
  guidance, bridge-only aliases listed as "works now, rename later"),
  `.gutconfig.json` → `gd-tools.toml` translation (merge, never clobber;
  unmapped options reported), and conservative diff-previewed `--apply`
  rewrites (`extends GutTest` → `extends GdToolsTest` plus config
  translation; files with unsupported constructs are never rewritten). Exit
  codes 0/1/2. Fulfills the promise in `docs/gut-migration.md` §6.

---

- [x] **Track: E2E Test Speed** (CI performance chore) (archived → ./archive/e2e_speed_20260929/)
  *Link: [e2e_speed_20260929](./archive/e2e_speed_20260929/index.md)* - speeds
  up the E2E stage, the CI wall-time bottleneck (5-10.5 min per job, PR CI
  ~13 min vs the 10-min target): `--durations=20` in CI pytest steps, fast
  timing values injected through existing config/fixture seams for
  watch/migration e2e (no production default changes), and an `e2e_smoke`
  marker selecting 3-5 critical-path tests for the unchanged 6-job PR matrix
  while the full E2E suite moves to nightly + `workflow_dispatch`. Acceptance:
  PR CI wall time <= 10 minutes.

---

- [x] **Track: Coverage Exclusion Annotations** (archived → `./archive/coverage_exclusions_20260930/`)
  *Link: [coverage_exclusions_20260930](./archive/coverage_exclusions_20260930/index.md)* -
  support `# gd-tools: no cover` annotations (single-line, block
  `start`/`end`, and func-line exclusion) so users can exclude lines from
  coverage instrumentation. Excluded lines are recorded in the plan JSON
  (plan version bumped to 2 for cache regeneration), removed from the
  coverage percentage denominator and `--min` gate, styled distinctly in the
  HTML report, and summarized compactly in the terminal report only when
  exclusions exist. Malformed annotations warn on stderr and never abort
  generation (warn-and-continue).

- [x] **Track: Native Release Readiness (v0.5.0)** (chore/release: docs truth
  pass, bounded crash-recovery + exit-2 diagnostics hardening, GUT bridge
  deprecation notice for v0.6.0 removal, v0.5.0 release preparation) (archived →
  ./archive/native_release_readiness_20260930/)
  *Link: [native_release_readiness_20260930](./archive/native_release_readiness_20260930/index.md)*

- [x] **Track: macOS CI Matrix** (chore: add `macos-latest` to the CI test
  matrix at full parity — unit, integration, e2e — extend the shared
  `install-godot` action with macOS support, fix macOS-specific issues that
  surface, and update the docs that currently record macOS as uncovered;
  Roadmap Track 36) (archived
  ./archive/macos_ci_matrix_20260930/)
  *Link: [macos_ci_matrix_20260930](./archive/macos_ci_matrix_20260930/index.md)*

---

- [x] **Track: Parallel Suite Execution** (Targets v0.6.0)
  *Link: [native_parallel_suites_20260930](./archive/native_parallel_suites_20260930/index.md)* -
  opt-in bounded worker pool for `gd-tools test`: `--parallel N` flag plus
  `[test] parallel` config (1–32, default 4, N=1 = sequential path),
  discovery-order queue scheduling over native and GUT-bridge suites alike,
  deterministic ordered summary and JUnit XML, suite-tagged NDJSON progress
  events, full `--coverage` support, watch-mode inheritance, continue-on-failure
  with process-tree kill on interrupt (exit 130), unchanged artifact contract,
  and in-track documentation updates.

- [~] **Track: Native Runtime Caching (Preflight Cache)** (Migration Phase 5)
  *Link: [native_runtime_caching_20261001](./tracks/native_runtime_caching_20261001/index.md)* -
  content-hash cache for the native integration preflight under
  `.gd-tools/native/preflight-cache/`: repeat `gd-tools test` runs on unchanged
  projects skip the headless preflight Godot process; keyed on test-file
  hashes, `project.godot`, Godot binary version, and bundled addon hashes;
  `--no-cache` escape hatch, verbose-only hit/miss reporting, fail-open on
  cache errors, cached preflight artifacts copied into run artifacts
  (unchanged artifact index contract), and a >=30% repeat-run speedup gate on
  the dogfood `spike/` project.
