# Plan: Random Test Order & Seed Reproducibility (`random_test_order_20261015`)

## Phase 1 — Config and CLI surface [checkpoint: 067c04e]

- [x] Task: Write failing unit tests for the new config keys (`tests/unit/test_config.py`) — `a699de8`
  - [x] Test: `TestConfig` defaults are `random_order=False` and `seed=None`
  - [x] Test: `[test] random_order = true` and `[test] seed = 1234` load and round-trip through `save_config`
  - [x] Test: unknown-key rejection still fires for a typo'd sibling (guards `extra="forbid"`)
  - [x] Test: `seed = -1` and `seed = "abc"` are rejected by validation (asserted on the pydantic error location/type, not just the exception class — `extra="forbid"` raises the same class for an undefined field)
- [x] Task: Add `random_order: bool = False` and `seed: int | None = None` to `TestConfig` in `src/gd_tools/config.py`, matching the docstring style of the neighbouring `parallel`/`durations` fields — `eadb3f2` (implemented as `Field(default=None, ge=0)` for the integer bound)
- [x] Task: Regenerate the checked-in schema snapshot — `gd-tools config schema --output docs/gd-tools.schema.json` — and confirm `tests/unit/test_schema.py::test_checked_in_schema_snapshot_is_current` passes (FR-6) — `eadb3f2` (red before regen, green after; diff purely additive)
- [x] Task: Write failing CLI tests (`tests/unit/test_cli_random_order.py`) — `ca5d159`
  - [x] Test: `--random-order` parses and reaches dispatch with `random_order=True`
  - [x] Test: `--seed 1234` alone implies random ordering (FR-3)
  - [x] Test: `--seed -1` and `--seed abc` exit 2 with an actionable message naming the accepted range (FR-2)
  - [x] Test: config `random_order`/`seed` are used when the flags are absent; `--seed 99` overrides `[test] seed`
  - [x] Test: existing flag-conflict table in `commands/test_validation.py` is unchanged for unrelated combinations (asserted positively: `--random-order --shard 2/4` must NOT exit 2, per FR-19)
- [x] Task: Add `--random-order` and `--seed` to the `test` command in `src/gd_tools/commands/test.py`, and thread both through `run_native_test_command` and `run_watch_mode` — `29c3228`. Deviation: `FlagState` was **not** extended. It exists only to feed `TEST_FLAG_RULES`, and FR-19 defines no rule for this feature, so the fields would have been dead. `--seed` uses `click.IntRange(min=0)` rather than a hand-written callback, which supplies the exit-2 range message for free.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — `067c04e`

## Phase 2 — Seeded ordering core [checkpoint: 0f9dfe5]

- [x] Task: Write failing unit tests for a new `src/gd_tools/native_test/ordering.py` (`tests/unit/test_native_ordering.py`) — `6a34b44`
  - [x] Test: seed resolution precedence — explicit CLI seed > config seed > generated seed (including seed 0, which must not read as "absent")
  - [x] Test: a generated seed is a non-negative 31-bit integer and differs across calls
  - [x] Test: shuffling the same suite set twice with the same seed yields the identical order (FR-7, FR-16)
  - [x] Test: two different seeds produce different orders for a >= 5-suite fixture
  - [x] Test: each suite's method list is shuffled deterministically from the same seeded stream (FR-8)
  - [x] Test: no suite or method is dropped or duplicated — the shuffled result is a permutation of the input
  - [x] Test: empty and single-item inputs are returned unchanged without consuming RNG state (asserted by spying on `random.Random.shuffle` rather than inferring it)
  - [x] Test: 1,000 suites / 10,000 tests order in under 50 ms (NFR-2)
- [x] Task: Implement `resolve_seed(...)` and `apply_random_order(suites, seed) -> RandomOrderResult` in `src/gd_tools/native_test/ordering.py` using one `random.Random(seed)` stream; return the resolved seed alongside the shuffled suites. No new dependencies (NFR-5) — `68b51c7`
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — `0f9dfe5`

## Phase 3 — Pipeline integration and reporting [checkpoint: 8fc1d95]

- [x] Task: Write failing tests for pipeline application order (delivered as the new `tests/unit/test_native_random_order_pipeline.py`, reusing the shard test's patch harness rather than extending `test_native_command.py`) — `a651d8c`
  - [x] Test: ordering is applied after the preflight result replaces `suites` (FR-9) — asserted by checking the preflight manifest still holds discovery order while the dispatched list is shuffled
  - [x] Test: the per-suite manifest dispatched to Godot carries the shuffled method order (AC-4)
  - [x] Test: with randomization disabled the `run_native_tests` call is byte-identical to today's (NFR-1)
  - [x] Test: the seed line is printed, and is absent when randomization is off (FR-13, NFR-1)
  - [x] Test: `--verbose` lists the resolved order (FR-15)
- [x] Task: Apply ordering in `run_native_test_command` after the preflight and before `run_native_tests`, print the seed line (FR-13) and, under `--verbose`, the resolved order (FR-15) — `36b8dec`
- [x] Task: Write failing tests for seed persistence in the run artifact index (`tests/unit/test_native_artifacts.py`) — `bd4beb8`
  - [x] Test: `publish_artifact_index` accepts and writes the seed as an additive top-level key
  - [x] Test: the key is absent when randomization is off, so existing index shape is untouched (NFR-1, NFR-4)
  - [x] Test: `protocol_version` is unchanged
- [x] Task: Extend `publish_artifact_index` in `src/gd_tools/native_test/artifacts.py` with the additive record and pass it from the orchestrator's index publication call sites (required threading `random_seed` through `run_native_tests`, since the orchestrator is what publishes the final index) — `bd4beb8`
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — `8fc1d95`

## Phase 4 — Composition guarantees [checkpoint: 872f613]

- [x] Task: Write failing tests for flag composition — delivered in `tests/unit/test_native_random_order_pipeline.py` (reusing its patch harness) and `tests/unit/test_watch_session.py`, rather than the planned `test_native_shard.py` extensions plus a separate composition module; one harness in one place beat duplicating it — `1d521e2`, `6a842fd`
  - [x] Test: `--shard 1/2` and `--shard 2/2` under two different seeds select the same disjoint suite sets as the unrandomized path, and their union is the full set (FR-11, FR-12, AC-8)
  - [x] Test: `--shard K/N --random-order --seed S` selects the same suites under seeds 1 and 2 — the seed changes only execution order (AC-9)
  - [x] Test: `--random-order --changed` shuffles only the narrowed set (FR-17, AC-12)
  - [x] Test: `--random-order --parallel 4` yields the same pass/fail totals as sequential (AC-10) — coexistence asserted in the unit harness, and totals verified on the native fixture: sequential and `--parallel 4` both reported 1 failed / 26 passed
  - [~] Test: `--random-order --exitfirst` — coexistence with a shuffled shard is asserted (FR-17). The trigger-on-first-failing-suite behaviour itself is exercised by the pre-existing exitfirst tests and was **not** re-verified under a randomized order; the trigger is order-agnostic by construction (it keys off the first failing suite among those executed), but that is reasoning, not a measurement.
  - [x] Test: `--random-order --coverage` produces identical coverage numbers to an unrandomized run — verified on the native fixture: 42.2% lines / 68.0% branches in both the baseline and the seeded run
  - [x] Test: `--watch --random-order` uses one session seed and reuses it for every re-run (FR-18, AC-13) — asserted for a generated seed and for an explicit `--seed 99`
- [x] Task: Fix any composition gaps surfaced by the tests; add no new flag-conflict rules for `--random-order` + `--shard` (FR-19) — `6a842fd`. The one real gap was the `--watch` per-re-run seed, fixed by resolving the session seed once before the loop. No conflict rules were added.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) — `872f613`

## Phase 5 — Documentation and final verification

- [ ] Task: Document the feature — README §5 flag list, `docs/USER_GUIDE.md` §3.4 (flag reference, seed replay recipe, shard membership contract, Python-version reproducibility caveat), and `CHANGELOG.md` under the unreleased section
- [ ] Task: Full quality gate — `CI=true pytest`, `ruff check src/ tests/`, `black --check src/ tests/`, new module at >= 80% line coverage, and the schema snapshot in sync (NFR-6, AC-15)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
