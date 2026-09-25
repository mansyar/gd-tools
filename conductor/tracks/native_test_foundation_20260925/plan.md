# Implementation Plan: Native Test Runtime Foundation

- **Track ID:** native_test_foundation_20260925
- **Type:** Feature / Architecture
- **Status:** New
- **Specification:** [`spec.md`](./spec.md)

## Phase 1 — Protocol, configuration, and discovery

**Purpose:** Establish the Python-owned contract before introducing GDScript runtime behavior.

- [x] Task: Add failing unit tests for native manifest models and validation [f7d91b5]
  - [ ] Define tests for schema/version validation and required fields.
  - [ ] Define tests for suite, test, tag, timeout, and coverage metadata.
  - [ ] Define tests for invalid paths, malformed manifests, and unsupported runtime modes.
  - [ ] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Add failing tests for native discovery and filtering [5e17c02]
  - [ ] Test configured test-directory discovery.
  - [ ] Test path, suite, exact-test, and tag filters.
  - [ ] Test deterministic ordering and duplicate removal.
  - [ ] Test detection of a GUT-only project when native discovery finds no suites.
  - [ ] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Implement the Python native protocol module [f7d91b5]
  - [ ] Add `src/gd_tools/native_test/` package.
  - [ ] Define internal manifest and native-result models.
  - [ ] Add schema/version validation and serialization helpers.
  - [ ] Add atomic JSON writing for manifests and results.
  - [ ] Run the new unit tests to Green.
- [x] Task: Implement discovery and selection [5e17c02]
  - [ ] Read native test settings from `gd-tools.toml`.
  - [ ] Discover configured native test candidates.
  - [ ] Apply layered selectors and tags.
  - [ ] Emit stable suite/test identifiers for later result aggregation.
  - [ ] Run discovery and protocol tests to Green.
- [x] Task: Add native configuration fields and validation [d4a73f6]
  - [ ] Extend `TestConfig`/related config models only with foundation settings.
  - [ ] Add defaults for native timeout, runtime, retries, and coverage paths.
  - [ ] Preserve existing GUT configuration behavior for legacy execution.
  - [ ] Add configuration serialization/validation tests.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [checkpoint: 1b82bf5]
  - [x] Run targeted unit tests and static checks.
  - [x] Review the manifest contract for forward compatibility.
  - [x] Create the phase checkpoint commit and record its SHA.

## Phase 2 — Native GDScript runtime

**Purpose:** Add the smallest real Godot-native execution engine that can load and run class-based suites.

- [x] Task: Add failing native GDScript fixture tests [f7acc85]
  - [ ] Add a clean fixture with `extends GdToolsTest`.
  - [ ] Add synchronous passing and failing test cases.
  - [ ] Add lifecycle-hook cases.
  - [ ] Add malformed-suite and unsupported-contract cases.
  - [ ] Confirm the fixture cannot pass through the existing GUT path.
- [x] Task: Implement the bundled native addon package data [5b84c40]
  - [ ] Add `src/gd_tools/addons/gd-tools-test/` package files.
  - [ ] Add package-data entries to `pyproject.toml`.
  - [ ] Add the `GdToolsTest` base class extending `Node`.
  - [ ] Add the `GdToolsTestRunner` entrypoint.
  - [ ] Add version/provenance metadata consistent with the existing addon packaging.
- [x] Task: Implement suite loading and lifecycle management [62a40b9]
  - [ ] Load and validate `GdToolsTest` suites.
  - [ ] Discover `test_*` methods.
  - [ ] Run `before_all`, `before_each`, `after_each`, and `after_all`.
  - [ ] Create a fresh test instance per method.
  - [ ] Attempt cleanup after failures.
  - [ ] Add GDScript-level tests for each lifecycle path.
- [x] Task: Implement core assertions and structured failure records [53eb437]
  - [ ] Add `assert_true`, `assert_false`, `assert_eq`, `assert_ne`.
  - [ ] Add `assert_null`, `assert_not_null`, and `fail`.
  - [ ] Record actual/expected values, messages, source context, and category.
  - [ ] Verify assertion failures do not depend on GDScript release-mode behavior.
- [x] Task: Implement native result/event emission [5ba241e]
  - [ ] Emit versioned native result data.
  - [ ] Emit optional structured progress events.
  - [ ] Ensure final result writes are atomic and recoverable after partial execution.
  - [ ] Add result serialization tests.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [checkpoint: bdf2531]
  - [x] Run native GDScript fixture tests headlessly.
  - [x] Verify no GUT files or GUT hooks are required.
  - [x] Review the public API for consistency with the approved specification.
  - [x] Create the phase checkpoint commit and record its SHA.

## Phase 3 — Async execution and failure isolation

**Purpose:** Prove the runtime can handle real Godot coroutine behavior and isolated suite execution.

- [x] Task: Add failing async and timeout tests [5c897c0]
  - [ ] Add a process-frame wait case.
  - [ ] Add a physics-frame wait case.
  - [ ] Add a timer/signal wait case.
  - [ ] Add a deliberately hanging test for timeout validation.
  - [ ] Add tests for cleanup after timeout and assertion failure.
  - [ ] Confirm the expected Red phase.
- [x] Task: Implement async helpers [5c897c0]
  - [ ] Add process-frame, physics-frame, timer, and signal helpers.
  - [ ] Allow lifecycle hooks and test methods to return coroutines.
  - [ ] Enforce the five-second default timeout.
  - [ ] Add per-suite/test and CLI timeout overrides.
  - [ ] Record timeout as a distinct result status.
- [x] Task: Implement suite-scoped process orchestration [755fde6]
  - [ ] Launch one Godot process per suite.
  - [ ] Pass the manifest and coverage settings through a controlled boundary.
  - [ ] Capture process stdout/stderr separately from structured results.
  - [ ] Preserve diagnostics after crashes.
  - [ ] Continue subsequent suites after a process crash.
- [x] Task: Add failure-policy tests [852a24c]
  - [ ] Verify ordinary assertion failures continue within a suite.
  - [ ] Verify infrastructure failures map to exit code `2`.
  - [ ] Verify test/coverage failures map to exit code `1`.
  - [ ] Verify later suites still report after an earlier crash.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run async, timeout, and crash tests.
  - [ ] Run the full existing Python unit suite for regressions.
  - [ ] Create the phase checkpoint commit and record its SHA.

## Phase 4 — Native coverage integration

**Purpose:** Preserve the product’s line/branch coverage differentiator without a permanent native test autoload.

- [ ] Task: Add failing native coverage tests
  - [ ] Test coverage activation from the transient runner.
  - [ ] Test statement and branch hit collection.
  - [ ] Test framework/test-file exclusions.
  - [ ] Test full-project denominator behavior under filtered execution.
  - [ ] Test line and branch report generation.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement native coverage activation and collection
  - [ ] Reuse the existing coverage plan schema v1 where possible.
  - [ ] Make the native runtime activate instrumentation before application execution.
  - [ ] Collect coverage data without requiring `_GDTCoverage` as a native permanent autoload.
  - [ ] Keep existing GUT hook/autoload behavior unchanged for legacy execution.
  - [ ] Write coverage data atomically.
- [ ] Task: Integrate native coverage with the test runner
  - [ ] Pass plan/output paths through the manifest/runtime boundary.
  - [ ] Merge suite coverage shards in the Python orchestrator.
  - [ ] Preserve the full application coverage denominator for filtered runs.
  - [ ] Reuse existing HTML, LCOV, Cobertura, and text report paths.
  - [ ] Preserve threshold behavior and exit-code mapping.
- [ ] Task: Add coverage regression and exclusion tests
  - [ ] Verify generated harness and test files are excluded automatically.
  - [ ] Verify user exclusions remain honored.
  - [ ] Verify line and branch metrics remain stable for the clean fixture.
  - [ ] Verify legacy GUT coverage tests continue to pass.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run native coverage unit, integration, and E2E checks.
  - [ ] Compare native output with the existing coverage plan/reporter contract.
  - [ ] Create the phase checkpoint commit and record its SHA.

## Phase 5 — CLI integration and legacy fallback

**Purpose:** Make native execution the default without removing the working GUT path.

- [ ] Task: Add failing CLI/runtime-selection tests
  - [ ] Test default native selection.
  - [ ] Test `--runtime native`.
  - [ ] Test `--runtime gut`.
  - [ ] Test invalid runtime values.
  - [ ] Test native-empty/GUT-present migration guidance.
  - [ ] Test `--no-exit-code` and existing output flags.
- [ ] Task: Implement runtime dispatch
  - [ ] Extend the test command with explicit runtime selection.
  - [ ] Route native execution through the new discovery/runner path.
  - [ ] Route `--runtime gut` through the existing implementation.
  - [ ] Keep GUT installation checks scoped to the legacy path.
- [ ] Task: Integrate native result reporting
  - [ ] Adapt native results to the existing CLI-facing `TestResult` model where practical.
  - [ ] Generate JUnit XML from normalized native results.
  - [ ] Preserve Rich output and machine-readable behavior.
  - [ ] Add structured diagnostics to failure output without parsing Godot stdout.
- [ ] Task: Update init/doctor/package integration where required
  - [ ] Ensure native addon package data is installed and discoverable.
  - [ ] Keep GUT installation opt-in for the transition.
  - [ ] Update doctor/version checks without removing legacy diagnostics.
  - [ ] Add tests for native and GUT project states.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run CLI unit and integration tests for both runtime modes.
  - [ ] Verify existing command examples and exit codes.
  - [ ] Create the phase checkpoint commit and record its SHA.

## Phase 6 — E2E, performance, and documentation

**Purpose:** Prove the complete workflow and close the track with measurable quality gates.

- [ ] Task: Add clean GUT-free E2E fixture
  - [ ] Create a standalone Godot project with no GUT addon.
  - [ ] Add a synchronous native test.
  - [ ] Add an asynchronous native test.
  - [ ] Add a failing-test project/fixture.
  - [ ] Add a timeout project/fixture.
- [ ] Task: Add full-workflow E2E tests
  - [ ] Run `gd-tools test` on the clean fixture.
  - [ ] Verify native JSON, JUnit XML, and coverage artifacts.
  - [ ] Verify exit codes `0`, `1`, and `2`.
  - [ ] Verify a crashed suite does not hide later suites.
  - [ ] Verify `--runtime gut` remains callable.
- [ ] Task: Add performance benchmark
  - [ ] Measure native and legacy GUT execution on a representative small suite.
  - [ ] Record startup and total runtime.
  - [ ] Assert the approved approximately 2x regression target.
  - [ ] Document benchmark conditions and known variance.
- [ ] Task: Update implementation documentation
  - [ ] Update `docs/PRD.md`, `docs/TDD.md`, and `docs/USER_GUIDE.md` for native default/runtime selection.
  - [ ] Document the temporary GUT fallback and current limitations.
  - [ ] Update the temporary roadmap phase status.
- [ ] Task: Final quality gates
  - [ ] Run the full unit suite.
  - [ ] Run the full integration suite.
  - [ ] Run headless E2E tests.
  - [ ] Run Ruff and Black checks.
  - [ ] Verify the full project coverage threshold behavior.
  - [ ] Verify no new runtime dependencies were added.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run the complete automated verification suite.
  - [ ] Perform the manual CLI verification steps.
  - [ ] Obtain explicit user confirmation of the verification results.
  - [ ] Create the final checkpoint commit and record its SHA.
  - [ ] Update the track registry/status and prepare the implementation handoff.

## Plan Boundaries

The GUT compatibility bridge, scene/resource integration, migration tooling,
windowed/visual tests, parallel execution, editor UI, and GUT removal remain
out of scope for this track. They are tracked in the temporary native runtime
migration roadmap.
