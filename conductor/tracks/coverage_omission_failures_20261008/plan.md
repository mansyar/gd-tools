# Plan: coverage_omission_failures_20261008

Workflow: TDD mandatory (Red→Green per task). Quality gates: `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest`; >80% line / >70% branch on `src/gd_tools`. Commit style `fix(...)`/`test(...)`/`feat(...)` with 7-char SHA recorded per task.

## Phase 1 — Plan generator: zero-point exclusion & inference-site detection (R1, R2)

- [ ] Task: Red — unit tests in `tests/unit/test_plan_generator*.py`: visitor flags `:=` statements whose initializer contains a wrapped operand span (nested ternary, boolop operand, multiline initializer, excluded-statement edge). Include an empirical check of untyped `var x = <variant>` under Godot 4.7 → decision gate to also cover `func_var_assigned` sites.
- [ ] Task: Green — implement detection in `CoverageVisitor` (`func_var_inf` runs bottom-up after children, so operand points are already recorded); add per-file `warning_ignores` to `FilePlan` output.
- [ ] Task: Red — unit test: `generate_plan` drops zero-point files and emits a stderr warning per skipped file.
- [ ] Task: Green — implement exclusion + warning; bump `PLAN_VERSION` 7→8; update `load_plan` handshake tests (old-version rejection stays loud).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Collector: annotation injection & omission diagnostics (R2, R3)

- [ ] Task: Red — native-integration tests: plan carrying `warning_ignores` instruments a `var x := cond ? a : b` file — reload OK, no `INFERENCE_ON_VARIANT` in logs, line counts preserved, both arms hit distinctly.
- [ ] Task: Green — `_instrument_file` in `src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd` prepends `@warning_ignore("inference_on_variant")` inline (after indentation, stacking over existing annotations) without changing line counts.
- [ ] Task: Red/Green — `_record_omission` carries the `reload()` error code; cause/fix text describes the real mechanism (injected Variant-typed wrapping interacting with inference) instead of "Fix the script's own syntax."
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — artifacts.json omitted union (R4)

- [ ] Task: Red — test that the run index `omitted` is the deduplicated union across all suites (currently reflects one suite).
- [ ] Task: Green — accumulate the union at the `publish_artifact_index` call site(s), parity with `_merge_coverage_shards`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — e2e repro fixture (R5)

- [ ] Task: Fixture project: pure-const file, `var x := ternary` file, dependency graph (helper class referenced by another module loaded before instrumentation).
- [ ] Task: e2e: full run → zero omissions, zero-point file absent from plan, distinct arm hits.
- [ ] Task: Dependency-hypothesis check — instrument a script whose dependents are already loaded; record evidence for/against in track notes.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Lint honors gdlintrc (R6)

- [ ] Task: Red — unit: `run_lint` passes a loaded gdlintrc config into `lint_code`; `disable: [- class-definitions-order]` suppresses that rule.
- [ ] Task: Green — load `gdlintrc` via gdtoolkit's own config loader; optional explicit `--lint-config` path on the CLI.
- [ ] Task: Test: `gd-tools lint` matches bare `gdlint` behavior on the disable scenario (with and without the disable).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 6 — Wrap-up

- [ ] Task: CHANGELOG entries; README/docs touch-ups where coverage/lint behavior is described.
- [ ] Task: Full pre-commit gate: `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest`; quality gates (>80% line / >70% branch on `src/gd_tools`).
- [ ] Task: Final Phase Verification & Checkpoint (Refer to workflow.md)
