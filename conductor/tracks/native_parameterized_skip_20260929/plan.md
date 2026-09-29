# Plan: Native Parameterized Tests + Suite-Level Skip

**Track:** `native_parameterized_skip_20260929` · **Branch:** `feature/native-parameterized-suite-skip-20260929`

Workflow notes: every task follows the TDD lifecycle from `conductor/workflow.md`
(mark `[~]` in progress → failing tests (red) → implement (green) → coverage →
commit → git note → mark `[x]` with SHA → commit plan update). Each phase ends
with a verification checkpoint task.

## Phase 1 — Protocol & Preflight: Parameter-Aware Discovery and Validation [checkpoint: de010af]

- [x] Task: Write failing Python tests for manifest expansion metadata (d7d6586)
    - [ ] `tests/test_native_protocol.py` (or nearest existing file): suite manifest carries per-method parameter declarations (`params`, `values`, case count) discovered through the preflight
    - [ ] Test: parameterized methods appear in discovered tests with declared case count; zero-arg methods unchanged
- [x] Task: Write failing Python tests for preflight validation (exit 2) (909072f)
    - [x] Mismatched `params`/`values` lengths → error naming suite path, method, and expected shape
    - [x] Non-array arguments and duplicate parameter names → same class of failure
    - [x] Empty values list → valid declaration, test marked skipped (asserted in later runtime phase, validated here)
- [x] Task: Implement GDScript preflight changes (`gd_tools_test_preflight.gd`) (909072f)
    - [x] `_test_method_names()`: include parameterized `test_*` methods when a `before_all` `parameterize` declaration matches their signature
    - [x] Validate declarations (lengths, types, duplicates); emit structured preflight errors with expected shape
    - [x] Record expansion metadata in the suite manifest
- [x] Task: Implement Python-side manifest/protocol support (`native_test/protocol.py`, `discovery.py`, `preflight.py`) (d7d6586; `preflight.py` required no change — the adapter already round-trips `NativeTest` fields, and the added `parameters` field flows through manifest JSON unchanged)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 - Native Runtime: Case Expansion, Lifecycle, Naming, Selectors [checkpoint: ec2c227]

- [x] Task: Write failing GDScript-side runtime tests (Godot fixture suites) (e9b6ede)
    - [ ] Fixture suite: `parameterize` in `before_all` → one result entry per value set, each with own hooks/timeout/artifacts, declaration order
    - [ ] Fixture suite: `use_parameters` inside a test body → one case per value set
    - [ ] Case naming: stringified values, hyphen-join, index fallback for unstable types; deterministic across runs
    - [ ] Async parameterized test method runs identically to sync
- [x] Task: Implement `GdToolsTest` API (`gd_tools_test.gd`) (e9b6ede)
    - [ ] `parameterize(params, values)` — suite-level declaration storage with preflight-consistent validation
    - [ ] `use_parameters(values)` — per-case value resolution inside test body
- [x] Task: Implement case expansion in the runner (`gd_tools_test_runner.gd`) (e9b6ede)
    - [ ] Expand declared methods into per-case executions with full lifecycle, per-case timeout, retries, artifacts
    - [ ] Result entries and NDJSON events use `test_foo[case-name]` identifiers
- [x] Task: Write failing Python tests + implement selector interaction (`native_test/discovery.py` / `command.py`) (b1974dc)
    - [x] Note: case-selector trimming is implemented in the GDScript preflight (shared by all callers) rather than `command.py`; discovery preserves the selector verbatim and the full pipeline is verified end to end
- [x] Task: Verify coverage attribution aggregates per-case hits back to the method (integration check; plan change only if needed) (2dec2a7)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 - Suite-Level Skip in `before_all` [checkpoint: 9e842f8]

- [x] Task: Write failing tests (fixture suite + Python result assertions) (52c3a36)
    - [x] `skip_test("reason")` in `before_all` → every test reported `skipped` with the reason; per-test entries present
    - [x] Per-test `skip_test()` behavior unchanged (existing suite regression; 4 skip regression e2e tests still pass)
    - [x] Suite skip interacts correctly with parameterized methods (all cases skipped)
- [x] Task: Implement suite-level skip state (`gd_tools_test.gd`, `gd_tools_test_runner.gd`) (52c3a36)
    - [x] Record skip on the instance the runner reads from `before_all`; propagate to every test result
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 - GUT Bridge Unblocking [checkpoint: e62c934]

- [x] Task: Write failing tests for bridge parameterization support (5e0ae1f)
    - [x] Remove `parameterize`/`use_parameters` from `_UNSUPPORTED_NAMES` in `bridge_scan.py` (update existing negative tests to positive)
    - [x] Bridge fixture suite (`extends GutTest`) using `parameterize` runs through the native machinery with the same result contract
    - [x] Bridge suite with malformed declaration → exit 2 preflight (inherited validation)
- [x] Task: Implement: `bridge_scan.py` list update + any bridge shim passthrough (`gd_tools_gut_bridge.gd`) (5e0ae1f)
    - Note: no shim passthrough needed — `GutTest` extends `GdToolsTest`, so the shim inherits the native parameterize/use_parameters API; only its docstring was updated.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Documentation, Reporting, and Final Verification

- [x] Task: Update `docs/ARCHITECTURE.md` - Known Limitations 4 → 2; document parameterization + suite-skip semantics in Part II (d4ef941)
- [x] Task: Update `docs/USER_GUIDE.md` (usage) and `docs/gut-migration.md` (constructs now supported) (d4ef941)
- [x] Task: Update `CHANGELOG.md` (feat entry) (d4ef941)
- [x] Task: Full-suite verification (d4ef941)
    - [x] `ruff check src/ tests/` && `black --check src/ tests/` — both clean
    - [x] `CI=true pytest --cov=gd_tools --cov-branch` — 1230 passed / 2 skipped, 95.83% coverage (≥80% gate)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
