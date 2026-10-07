# Plan: coverage_omission_failures_20261008

Workflow: TDD mandatory (Red→Green per task). Quality gates: `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest`; >80% line / >70% branch on `src/gd_tools`. Commit style `fix(...)`/`test(...)`/`feat(...)` with 7-char SHA recorded per task.

## Phase 1 — Plan generator: zero-point exclusion & inference-site detection (R1, R2)

- [x] Task: Red — unit tests in `tests/unit/test_plan_generator*.py`: visitor flags `:=` statements whose initializer contains a wrapped operand span (nested ternary, boolop operand, multiline initializer, excluded-statement edge). Include an empirical check of untyped `var x = <variant>` under Godot 4.7 → decision gate to also cover `func_var_assigned` sites. *(Gate resolved: untyped `=` is clean on Godot 4.7.2 — only `:=` annotated.)*
- [x] Task: Green — implement detection in `CoverageVisitor` (`func_var_inf` runs bottom-up after children, so operand points are already recorded); add per-file `warning_ignores` to `FilePlan` output.
- [x] Task: Red — unit test: `generate_plan` drops zero-point files and emits a stderr warning per skipped file.
- [x] Task: Green — implement exclusion + warning; bump `PLAN_VERSION` 7→8; update `load_plan` handshake tests (old-version rejection stays loud).
- [~] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - Full suite + lint gate in progress. Regression fallout resolved: golden plan fixtures regenerated to v8; zero-point test fixtures made pointful (`pass`/bare-`extends` sources) in `test_plan_generator.py`, `test_plan_generator_boolops.py`, `test_plan_generator_ternary.py`, `test_native_coverage.py`; `test_coverage_exclusions.py` helpers tolerate unplanned (fully-excluded) files and the unterminated-start fixture keeps a point before the block; `test_coverage_playtest_cli.py` version assert → 8; `ternary_export_wrapped` integration fixture gains a trailing function so the file stays a plan target.
  - Environment note (not a code failure): e2e tests that shell out via `python -m gd_tools` resolve the pip-installed CLI from another checkout (protocol 4 / plan 7), not this worktree. `test_native_cli_runs_scene_suite_with_default_and_overridden_metadata` and `test_watch_session_end_to_end` fail without it and pass with `PYTHONPATH=<worktree>/src`. Pre-existing environmental issue, unaffected by this track.

## Phase 2 — Collector: annotation injection & omission diagnostics (R2, R3)

- [x] Task: Red — native-integration tests: plan carrying `warning_ignores` instruments a `var x := cond ? a : b` file — reload OK, no `INFERENCE_ON_VARIANT` in logs, line counts preserved, both arms hit distinctly. *(Added `test_native_coverage_annotates_inferred_declarations` e2e; parse-harness case `inferred_wrapped` + guard regex pinning collector injection; same-line annotation verified empirically on Godot 4.7.2.)*
- [x] Task: Green — `_instrument_file` in `src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd` prepends `@warning_ignore("inference_on_variant")` inline (after indentation, stacking over existing annotations) without changing line counts. *(Applied after wrapping, before line insertion, on original plan indices.)*
- [x] Task: Red/Green — `_record_omission` carries the `reload()` error code; cause/fix text describes the real mechanism (injected Variant-typed wrapping interacting with inference) instead of "Fix the script's own syntax." *(Reason now embeds `Godot error code %d`; fix points at the SCRIPT ERROR lines / `--no-cache` / exclusion; e2e `test_native_omission_reports_reload_error_code` + updated broken.gd expectation.)*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) *(Full gate green: 1836 passed, 7 skipped, coverage 95.84%; hermetic e2e CLI resolution added — see Phase 4.)*

## Phase 3 — artifacts.json omitted union (R4)

- [x] Task: Red — test that the run index `omitted` is the deduplicated union across all suites (currently reflects one suite). *(Result: test `test_index_omitted_is_union_across_suites` passed immediately — the union is already implemented (commit `5480625`: per-suite diagnostics deduped at orchestrator lines 349-372, published at 416; shard merge unions at `_merge_coverage_shards`). The reporter's "one suite's omissions" observation matches the case where every suite process instruments the same plan and reports identical omissions, so the union equals any single suite's list. Test retained as a regression pin.)*
- [x] Task: Green — accumulate the union at the `publish_artifact_index` call site(s), parity with `_merge_coverage_shards`. *(No code change needed; pin test added instead.)*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) *(Covered by the Phase 4 final gate.)*

## Phase 4 — e2e repro fixture (R5)

- [x] Task: Fixture project: pure-const file, `var x := ternary` file, dependency graph (helper class referenced by another module loaded before instrumentation).
- [x] Task: e2e: full run → zero omissions, zero-point file absent from plan, distinct arm hits. *(Single e2e run: plan excludes `waypoint_data.gd` (pure const), includes part_def/consumer/inferred_subject; coverage records hits for all three, both ternary arms distinct, `omitted` absent.)*
- [x] Task: Dependency-hypothesis check — instrument a script whose dependents are already loaded; record evidence for/against in track notes. *(Verdict: AGAINST the hypothesis for this runner. Each suite runs in a fresh process and `_activate_coverage` instruments before any suite script loads, so `load()`+`reload()` succeed for the definition module even though a consumer preloads it. The repro suite (`test_coverage_repro_omission_classes_from_bug_report`) loads a consumer preloading `part_def.gd` and records zero omissions with no "did not reload" in the log. Conclusion: the reported Class 2 was the zero-point silent skip (R1) — definition/data modules plan `lines: []`, the collector skipped them without an omission record, and the reconciler substituted its generic reason. The Class-1 files (main.gd, lead_tracker.gd) were the only true reload failures, caused by the wrapped-operand inference issue (R2).)*
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) *(Covered by the Phase 4 final gate. While here, the two formerly-environmental e2e failures were made hermetic: `_gd_tools_command()` in `test_native_integration_cli.py` / `test_watch_e2e.py` now prepends the repository's `src` to PYTHONPATH and callers copy `os.environ` after resolution — the pip-installed CLI from another checkout (protocol 4) no longer shadows the worktree.)*

## Phase 5 — Lint honors gdlintrc (R6)

- [ ] Task: Red — unit: `run_lint` passes a loaded gdlintrc config into `lint_code`; `disable: [- class-definitions-order]` suppresses that rule.
- [ ] Task: Green — load `gdlintrc` via gdtoolkit's own config loader; optional explicit `--lint-config` path on the CLI.
- [ ] Task: Test: `gd-tools lint` matches bare `gdlint` behavior on the disable scenario (with and without the disable).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 6 — Wrap-up

- [ ] Task: CHANGELOG entries; README/docs touch-ups where coverage/lint behavior is described.
- [ ] Task: Full pre-commit gate: `ruff check src/ tests/ && black --check src/ tests/ && CI=true pytest`; quality gates (>80% line / >70% branch on `src/gd_tools`).
- [ ] Task: Final Phase Verification & Checkpoint (Refer to workflow.md)
