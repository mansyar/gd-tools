# Plan: Native Parameterized Tests + Suite-Level Skip

**Track:** `native_parameterized_skip_20260929` · **Branch:** `feature/native-parameterized-suite-skip-20260929`

Workflow notes: every task follows the TDD lifecycle from `conductor/workflow.md`
(mark `[~]` in progress → failing tests (red) → implement (green) → coverage →
commit → git note → mark `[x]` with SHA → commit plan update). Each phase ends
with a verification checkpoint task.

## Phase 1 — Protocol & Preflight: Parameter-Aware Discovery and Validation

- [ ] Task: Write failing Python tests for manifest expansion metadata
    - [ ] `tests/test_native_protocol.py` (or nearest existing file): suite manifest carries per-method parameter declarations (`params`, `values`, case count) discovered through the preflight
    - [ ] Test: parameterized methods appear in discovered tests with declared case count; zero-arg methods unchanged
- [ ] Task: Write failing Python tests for preflight validation (exit 2)
    - [ ] Mismatched `params`/`values` lengths → error naming suite path, method, and expected shape
    - [ ] Non-array arguments and duplicate parameter names → same class of failure
    - [ ] Empty values list → valid declaration, test marked skipped (asserted in later runtime phase, validated here)
- [ ] Task: Implement GDScript preflight changes (`gd_tools_test_preflight.gd`)
    - [ ] `_test_method_names()`: include parameterized `test_*` methods when a `before_all` `parameterize` declaration matches their signature
    - [ ] Validate declarations (lengths, types, duplicates); emit structured preflight errors with expected shape
    - [ ] Record expansion metadata in the suite manifest
- [ ] Task: Implement Python-side manifest/protocol support (`native_test/protocol.py`, `discovery.py`, `preflight.py`)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2 — Native Runtime: Case Expansion, Lifecycle, Naming, Selectors

- [ ] Task: Write failing GDScript-side runtime tests (Godot fixture suites)
    - [ ] Fixture suite: `parameterize` in `before_all` → one result entry per value set, each with own hooks/timeout/artifacts, declaration order
    - [ ] Fixture suite: `use_parameters` inside a test body → one case per value set
    - [ ] Case naming: stringified values, hyphen-join, index fallback for unstable types; deterministic across runs
    - [ ] Async parameterized test method runs identically to sync
- [ ] Task: Implement `GdToolsTest` API (`gd_tools_test.gd`)
    - [ ] `parameterize(params, values)` — suite-level declaration storage with preflight-consistent validation
    - [ ] `use_parameters(values)` — per-case value resolution inside test body
- [ ] Task: Implement case expansion in the runner (`gd_tools_test_runner.gd`)
    - [ ] Expand declared methods into per-case executions with full lifecycle, per-case timeout, retries, artifacts
    - [ ] Result entries and NDJSON events use `test_foo[case-name]` identifiers
- [ ] Task: Write failing Python tests + implement selector interaction (`native_test/discovery.py` / `command.py`)
    - [ ] `--test method` → all cases; `--test "method[case]"` → single case; tags at method level
- [ ] Task: Verify coverage attribution aggregates per-case hits back to the method (integration check; plan change only if needed)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Suite-Level Skip in `before_all`

- [ ] Task: Write failing tests (fixture suite + Python result assertions)
    - [ ] `skip_test("reason")` in `before_all` → every test reported `skipped` with the reason; per-test entries present
    - [ ] Per-test `skip_test()` behavior unchanged (existing suite regression)
    - [ ] Suite skip interacts correctly with parameterized methods (all cases skipped)
- [ ] Task: Implement suite-level skip state (`gd_tools_test.gd`, `gd_tools_test_runner.gd`)
    - [ ] Record skip on the instance the runner reads from `before_all`; propagate to every test result
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — GUT Bridge Unblocking

- [ ] Task: Write failing tests for bridge parameterization support
    - [ ] Remove `parameterize`/`use_parameters` from `_UNSUPPORTED_NAMES` in `bridge_scan.py` (update existing negative tests to positive)
    - [ ] Bridge fixture suite (`extends GutTest`) using `parameterize` runs through the native machinery with the same result contract
    - [ ] Bridge suite with malformed declaration → exit 2 preflight (inherited validation)
- [ ] Task: Implement: `bridge_scan.py` list update + any bridge shim passthrough (`gd_tools_gut_bridge.gd`)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Documentation, Reporting, and Final Verification

- [ ] Task: Update `docs/ARCHITECTURE.md` — Known Limitations 4 → 2; document parameterization + suite-skip semantics in Part II
- [ ] Task: Update `docs/USER_GUIDE.md` (usage) and `docs/gut-migration.md` (constructs now supported)
- [ ] Task: Update `CHANGELOG.md` (feat entry)
- [ ] Task: Full-suite verification
    - [ ] `ruff check src/ tests/` && `black --check src/ tests/`
    - [ ] `CI=true pytest --cov=gd_tools --cov-branch` (≥80% line / ≥70% branch on touched modules)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
