# Plan: Native Mocking & Stubbing

Track ID: `native_mocking_stubbing_20260929` · Branch: `feature/native-mocking-stubbing-20260929`

All tasks follow the TDD workflow: Red (failing tests first) → Green (minimum implementation) → Refactor. Coverage gates: >80% line, >70% branch for new source code.

## Phase 1 — Double engine (GDScript) `[checkpoint: 204f2aa]`
- [x] Task: Red — write failing native suites for `double()` / `partial_double()` semantics (unstubbed double returns `null`; partial runs real implementation; `to_call_super()` calls parent; doubles of scripts by path and preloaded `Script`; fresh instances per call) `[a83b5d1]`
- [x] Task: Green — implement the doubler (runtime-generated extending script) as a new addon module (e.g. `gd_tools_mock.gd`) `[cb1b320]`
- [x] Task: Refactor + full native suite green `[f43f1e3]`
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) `[204f2aa]`

## Phase 2 — Stub matching & call recording (GDScript) `[checkpoint: d6b3b96]`
- [x] Task: Red — failing tests for `stub()` chain (`to_return`, `to_call_super`), exact-argument matching, "any" wildcard, default fallback, per-test isolation `[211f352]`
- [x] Task: Green — implement stub registry + call recorder wired into generated doubles `[61eec36]`
- [x] Task: Refactor + suite green `[967f830]`
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3 — Call assertions (GDScript)
- [ ] Task: Red — failing tests for `assert_called`, `assert_not_called`, `assert_call_count`, `assert_call_arguments`, incl. actionable failure diagnostics (expected vs actual)
- [ ] Task: Green — implement assertions on `GdToolsTest`
- [ ] Task: Refactor + suite green
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4 — Fail-fast validation + addon packaging (Python + GDScript)
- [ ] Task: Red (pytest) — `init` deploys the new mock module file; `doctor` verifies it; addon version handling
- [ ] Task: Red (GDScript) — failing tests: `stub()` on a nonexistent method fails immediately; `double()` on a non-script value fails immediately, diagnostics name method + target
- [ ] Task: Green — implement validation in the mock module; update `init.py`/`addon_check.py` manifests
- [ ] Task: Refactor + `CI=true pytest` + native suites green, coverage gates met
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5 — Bridge un-rejection (GDScript)
- [ ] Task: Red — failing preflight tests: bridge suites using `double()`/`stub()`/`assert_called*` are no longer flagged; unsupported constructs (incl. `parameterize()`) still rejected with guidance
- [ ] Task: Green — update `gd_tools_test_preflight.gd` refusal list and `gd_tools_gut_bridge.gd` forwarding
- [ ] Task: Refactor + mixed native/bridge run green
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 6 — Coverage honesty (Python + GDScript)
- [ ] Task: Red — failing tests proving generated double scripts never appear in coverage plan/report; real-script metrics unaffected by stubbing
- [ ] Task: Green — implement exclusion in plan generation/data collection as needed
- [ ] Task: Refactor + coverage command regression green
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 7 — Documentation truth pass
- [ ] Task: Update `docs/USER_GUIDE.md` (mocking API reference)
- [ ] Task: Update `docs/gut-migration.md` (remove double/stub rows from refused table)
- [ ] Task: Update `docs/ARCHITECTURE.md` (drop "No mocking or stubbing" limitation; describe the facility)
- [ ] Task: Update `README.md` capability table
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
