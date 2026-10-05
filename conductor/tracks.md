# Project Tracks

This file tracks all major tracks for the project. Each track has its own detailed plan in its respective folder.

---

_Archived tracks live in `./archive/`._

- [x] **Track: GDScript AST Edge Cases** (archived → `./archive/ast_edge_cases_20260718/`)

---

- [x] **Track: Native Test Runtime Foundation**
  *Link: [native_test_foundation_20260925](./archive/native_test_foundation_20260925/index.md)*

---

- [x] **Track: Native Scene and Resource Integration**
  *Link: [native_scene_integration_20260925](./archive/native_scene_integration_20260925/index.md)*

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

---

- [x] **Track: Native Runtime Caching (Preflight Cache)** (Migration Phase 5)
  *Link: [native_runtime_caching_20261001](./archive/native_runtime_caching_20261001/index.md)* -
  content-hash cache for the native integration preflight under
  `.gd-tools/native/preflight-cache/`: repeat `gd-tools test` runs on unchanged
  projects skip the headless preflight Godot process; keyed on test-file
  hashes, `project.godot`, Godot binary version, bundled addon hashes, and
  integration scenes/resources; `--no-cache` escape hatch, verbose-only
  hit/miss reporting, fail-open on cache errors, cached preflight artifacts
  copied into run artifacts (unchanged artifact index contract). Benchmark
  evidence: warm repeat runs are strictly faster (preflight process
  eliminated; ~7% end-to-end on the benchmark fixture, gain scales with
  project size; spec NFR-3 revised from the original >=30% gate on
  2026-10-01).

---

- [x] **Track: `test --changed` — Affected-Suite Selection** (feature: add
  `gd-tools test --changed [--base <ref>]` to run only suites affected by
  changed files — working tree or git ref via merge-base — reusing the
  watch-mode file→suite mapping as shared selection logic, with full-suite
  fallback on unmapped files, exit-0 empty-set, exit-2 repo/ref errors,
  composition with `--parallel`/`--coverage`/filters, summary + verbose
  reporting, and E2E validation on a git-backed fixture project)
  *Link: [test_changed_20261001](./archive/test_changed_20261001/index.md)*

---

- [x] **Track: Godot Editor Plugin** (archived → ./archive/editor_plugin_20260930) (Roadmap Track 35 — editor plugin deployed
  by `gd-tools init` with a test/coverage dock panel (async runs, summary +
  failures, friendly missing-CLI fallback) and a `CodeEdit` coverage heatmap
  overlay reading `.gd-tools/` artifacts; lint margin descoped)
  *Link: [editor_plugin_20260930](./archive/editor_plugin_20260930/index.md)*
- [x] **Track: Native Signal Assertions** (archived  `./archive/native_signal_assertions_20261001`) (`watch_signals` capture model with
  `assert_signal_emitted`, `assert_signal_not_emitted`, `assert_signal_emit_count`,
  `assert_signal_emitted_with_args`, and the awaitable `assert_signal_emitted_after`
  helper; per-test lifecycle isolation, unwatched-target guidance, rich diagnostics,
  no protocol change)
  *Link: [native_signal_assertions_20261001](./archive/native_signal_assertions_20261001/index.md)*

---

- [x] **Track: Roadmap & Docs Truth Pass** (archived →
  `./archive/roadmap_docs_truth_pass_20261001/`) - fold the temporary
  native-runtime migration roadmap (`docs/ROADMAP.md` §8) into the main
  roadmap with anchor links rewritten, refresh `ARCHITECTURE.md` known
  limitations against shipped tracks, and reconcile README / USER_GUIDE /
  PRD factual claims with the shipped v0.5.0 feature set; explicit Phase 5
  leftover, no `src/` changes, clears the path for the v0.6.0
  bridge-removal track
- [x] **Track: Config JSON Schema + Docs Pass** (feature+chore: a JSON Schema for
  `gd-tools.toml` generated from the Pydantic model — new `gd-tools config schema`
  command, checked-in `docs/gd-tools.schema.json` snapshot with a sync test, and
  `$schema` key support in the config model — plus a targeted docs truth pass fixing
  the stale CHANGELOG "Known Limitations" editor-plugin claim, ROADMAP Phase 5
  checkboxes, and other demonstrably false docs claims)
  *Link: [config_schema_docs_20261001](./archive/config_schema_docs_20261001/index.md)*

---

- [x] **Track: Import-Step Caching** (feature: skip the unconditional
  `godot --headless --import` on unchanged projects via a content-hash
  import-freshness cache under `.gd-tools/native/import-cache/`, mirroring the
  preflight-cache conventions — fail-open, `--no-cache` bypass, verbose
  hit/miss — with benchmark evidence that warm runs are strictly faster)
  *Link: [import_step_caching_20261001](./archive/import_step_caching_20261001/index.md)*

---

- [x] **Track: GUT Bridge Removal (v0.6.0)** (refactor: remove the deprecated
  GUT Compatibility Bridge runtime — `GutTest` shim, `extends GutTest`
  auto-routing, bridge normalization — make the native runtime the sole test
  runtime with explicit v0.6.0 removal errors for `--runtime gut` and GUT
  config values, keep `gd-tools migrate` and its scanner as the permanent
  migration path, reframe `doctor` as a migration advisor, and prepare the
  v0.6.0 release: version bump, CHANGELOG, full docs truth pass)
  *Link: [gut_bridge_removal_20261001](./archive/gut_bridge_removal_20261001/index.md)*

---

- [x] **Track: v0.6.0 Legacy Sweep** (chore: remove code and configuration
  orphaned by the GUT bridge removal — dead `GUT_VERSION_MAP` version mapping,
  audited GUT remnants, legacy `[test].gutconfig` config key — keep the
  single-valued `runtime` field for GdUnit4 forward-compat, truth-pass the
  living docs, and retire Roadmap Track 32 as obsolete)
  *Link: [legacy_sweep_20261002](./archive/legacy_sweep_20261002/index.md)*

---

- [x] **Track: Pre-commit Hook Integration** (feature: add a
  `gd-tools install-hooks` command that wires gd-tools into the pre-commit
  framework - generate `.pre-commit-hooks.yaml`, write/merge a `repos: local:`
  entry into `.pre-commit-config.yaml` with idempotent merge-by-id re-runs
  that never clobber foreign hooks, offer format/lint/test hooks via an
  interactive prompt plus `--all`/`--hooks`/`--non-interactive` flags, and
  document the integration in README and USER_GUIDE)
  *Link: [pre_commit_hooks_20261002](./archive/pre_commit_hooks_20261002/index.md)*


- [x] **Track: Coverage Format Bugfix + CLI Unification** (bugfix + chore:
  make json a first-class coverage report format mirroring the diff JSON
  shape, unify the --report-format flag across coverage subcommands with
  validation, keep --format as a hidden alias, and align the
  [coverage].format config validator)
  *Link: [coverage_format_unification_20261002](./archive/coverage_format_unification_20261002/index.md)*


- [x] **Track: Ternary Branch Instrumentation Correctness** (bugfix: anchor
  ternary coverage branch points to the nearest node whose line is a legal
  tracker insertion point instead of the first operand's line, drop ternaries
  with no anchor at all (class-level const/var/static var, @export, default
  parameter), fix GDScript that fails to parse for multi-line parenthesized
  expressions, widen the anchor set to cover if/while/for/match headers after
  review found them silently dropped, and bump PLAN_VERSION to 3 so stale
  cached plans are invalidated)
  *Link: [ternary_instrumentation_20261003](./archive/ternary_instrumentation_20261003/index.md)*
- [x] **Track: Instrumentation Hygiene Sweep** *Link: [./archive/instrumentation_hygiene_20261003/index.md](./archive/instrumentation_hygiene_20261003/index.md)*

- [x] **Track: GitHub Actions Annotations** (feature: add a
  `github-actions` report format to lint, coverage report, and coverage
  run, emitting official GitHub Actions workflow log commands
  (`::error`/`::warning`) so lint violations and coverage threshold
  failures surface as native PR annotations; includes config alignment
  and CI docs — Roadmap Track 31)
  *Link: [gh_actions_annotations_20261002](./archive/gh_actions_annotations_20261002/index.md)*

- [x] **Track: Ternary Branch Separation** (bugfix: make ternary branch
  coverage measurable by instrumenting each ternary arm at its operand
  expression with a value-preserving wrapper call
  (`_gdtools_coverage_hit_ret`) instead of the shared anchor-line insertion,
  so `ternary_true`/`ternary_false` are measured and gated independently and
  an uncovered arm can fail `--min-branch`; bumps PLAN_VERSION to 4)
  *Link: [ternary_branch_separation_20261003](./archive/ternary_branch_separation_20261003/index.md)*

- [x] **Track: Min-Branch Gate on coverage run + Zero-Branch Exemption** (bugfix: wire --min-branch into gd-tools coverage run, and make the branch gate exempt-with-note when a project has zero branch points, consistently across `test`, coverage run, coverage show) *Link: [min_branch_coverage_run_20261004](./archive/min_branch_coverage_run_20261004/index.md)*

---

- [x] **Track: Doubles & Spy Framework Upgrade** (feature: complete the native
  runtime doubles & spy framework — `"any"` wildcard arg matchers in spy
  assertions sharing stub matching semantics, rich failure diagnostics with
  recorded call lists and per-argument diffs, `to_return_seq` sequenced
  returns and `to_fail` fail stubs, `assert_call_order` subsequence
  verification, and property get/set spying via the Doubler generator)
  *Link: [spy_framework_upgrade_20261004](./archive/spy_framework_upgrade_20261004/index.md)*

---

- [x] **Track: Snapshot Testing in the Native Runtime** (feature: Jest-style
  `assert_snapshot(value, name)` in the native GdToolsTest runtime —
  deterministic 3-tier serialization (values / object property dumps /
  node-tree dumps), versioned human-readable `.snap` files under
  `.gd-tools/snapshots/`, first-run auto-write with summary counts,
  fail-with-unified-diff mismatches, `gd-tools test --snapshot-update`,
  obsolete-snapshot reporting, and snapshot-aware `gd-tools clean`)
  *Link: [snapshot_testing_20261005](./archive/snapshot_testing_20261005/index.md)*

---

- [~] **Track: Codecov upload resilience** (chore: continue-on-error on the Codecov upload step in ci.yml so codecov outages cannot fail CI or block PR merges; coverage remains preserved as a workflow artifact) *Link: [codecov_upload_resilience_20261005](./tracks/codecov_upload_resilience_20261005/index.md)*
