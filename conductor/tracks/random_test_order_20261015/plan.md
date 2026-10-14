# Plan: Random Test Order & Seed Reproducibility (`random_test_order_20261015`)

## Phase 1 — Config and CLI surface

- [ ] Task: Write failing unit tests for the new config keys (`tests/unit/test_config.py`)
  - [ ] Test: `TestConfig` defaults are `random_order=False` and `seed=None`
  - [ ] Test: `[test] random_order = true` and `[test] seed = 1234` load and round-trip through `save_config`
  - [ ] Test: unknown-key rejection still fires for a typo'd sibling (guards `extra="forbid"`)
  - [ ] Test: `seed = -1` and `seed = "abc"` are rejected by validation
- [ ] Task: Add `random_order: bool = False` and `seed: int | None = None` to `TestConfig` in `src/gd_tools/config.py`, matching the docstring style of the neighbouring `parallel`/`durations` fields
- [ ] Task: Regenerate the checked-in schema snapshot — `gd-tools config schema --output docs/gd-tools.schema.json` — and confirm `tests/unit/test_schema.py::test_checked_in_schema_snapshot_is_current` passes (FR-6)
- [ ] Task: Write failing CLI tests (`tests/unit/test_cli_random_order.py`)
  - [ ] Test: `--random-order` parses and reaches dispatch with `random_order=True`
  - [ ] Test: `--seed 1234` alone implies random ordering (FR-3)
  - [ ] Test: `--seed -1` and `--seed abc` exit 2 with an actionable message naming the accepted range (FR-2)
  - [ ] Test: config `random_order`/`seed` are used when the flags are absent; `--seed 99` overrides `[test] seed`
  - [ ] Test: existing flag-conflict table in `commands/test_validation.py` is unchanged for unrelated combinations
- [ ] Task: Add `--random-order` and `--seed` to the `test` command in `src/gd_tools/commands/test.py` with a validating callback, extend `FlagState`, and thread both through `run_native_test_command` and `run_watch_mode`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Seeded ordering core

- [ ] Task: Write failing unit tests for a new `src/gd_tools/native_test/ordering.py` (`tests/unit/test_native_ordering.py`)
  - [ ] Test: seed resolution precedence — explicit CLI seed > config seed > generated seed
  - [ ] Test: a generated seed is a non-negative 31-bit integer and differs across calls
  - [ ] Test: shuffling the same suite set twice with the same seed yields the identical order (FR-7, FR-16)
  - [ ] Test: two different seeds produce different orders for a >= 5-suite fixture
  - [ ] Test: each suite's method list is shuffled deterministically from the same seeded stream (FR-8)
  - [ ] Test: no suite or method is dropped or duplicated — the shuffled result is a permutation of the input
  - [ ] Test: empty and single-item inputs are returned unchanged without consuming RNG state
  - [ ] Test: 1,000 suites / 10,000 tests order in under 50 ms (NFR-2)
- [ ] Task: Implement `resolve_seed(...)` and `apply_random_order(suites, seed) -> RandomOrderResult` in `src/gd_tools/native_test/ordering.py` using one `random.Random(seed)` stream; return the resolved seed alongside the shuffled suites. No new dependencies (NFR-5)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Pipeline integration and reporting

- [ ] Task: Write failing tests for pipeline application order (`tests/unit/test_native_command.py`, `tests/unit/test_native_random_order_pipeline.py`)
  - [ ] Test: ordering is applied after `--changed` narrowing and after the preflight result replaces `suites` (FR-9)
  - [ ] Test: the per-suite manifest dispatched to Godot carries the shuffled method order (AC-4)
  - [ ] Test: with randomization disabled the `run_native_tests` call is byte-identical to today's (NFR-1)
- [ ] Task: Apply ordering in `run_native_test_command` immediately before `run_native_tests`, then print the seed line (FR-13) and, under `--verbose`, the resolved order (FR-15)
- [ ] Task: Write failing tests for seed persistence in the run artifact index (`tests/unit/test_native_artifacts.py`)
  - [ ] Test: `publish_artifact_index` accepts and writes the seed as an additive top-level key
  - [ ] Test: the key is absent when randomization is off, so existing index shape is untouched (NFR-1, NFR-4)
  - [ ] Test: `protocol_version` is unchanged
- [ ] Task: Extend `publish_artifact_index` in `src/gd_tools/native_test/artifacts.py` with the additive record and pass it from the orchestrator's index publication call sites
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Composition guarantees

- [ ] Task: Write failing tests for flag composition (`tests/unit/test_native_shard.py` extensions, `tests/unit/test_native_random_order_composition.py`)
  - [ ] Test: `--shard 1/2` and `--shard 2/2` under two different seeds select the same disjoint suite sets as the unrandomized path, and their union is the full set (FR-11, FR-12, AC-8)
  - [ ] Test: `--shard K/N --random-order --seed S` selects the same suites as `--shard K/N --seed S` — the seed changes only execution order (AC-9)
  - [ ] Test: `--random-order --changed` shuffles only the narrowed set (FR-17, AC-12)
  - [ ] Test: `--random-order --parallel 4` yields the same pass/fail totals as sequential, with the summary in shuffled order (AC-10)
  - [ ] Test: `--random-order --exitfirst` triggers on the first executed failing suite (FR-17, AC-11)
  - [ ] Test: `--random-order --coverage` produces identical coverage numbers to an unrandomized run on a stable fixture
  - [ ] Test: `--watch --random-order` reports one seed and reuses it for every re-run (FR-18, AC-13)
- [ ] Task: Fix any composition gaps surfaced by the tests; add no new flag-conflict rules for `--random-order` + `--shard` (FR-19)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Documentation and final verification

- [ ] Task: Document the feature — README §5 flag list, `docs/USER_GUIDE.md` §3.4 (flag reference, seed replay recipe, shard membership contract, Python-version reproducibility caveat), and `CHANGELOG.md` under the unreleased section
- [ ] Task: Full quality gate — `CI=true pytest`, `ruff check src/ tests/`, `black --check src/ tests/`, new module at >= 80% line coverage, and the schema snapshot in sync (NFR-6, AC-15)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
