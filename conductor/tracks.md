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