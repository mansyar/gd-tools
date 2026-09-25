# Implementation Plan: Native Scene and Resource Integration

- **Track ID:** native_scene_integration_20260925
- **Type:** Feature
- **Status:** In Progress
- **Specification:** [`spec.md`](./spec.md)

## Phase 1 — Protocol v2 and integration metadata contract [checkpoint: `25297e0`]

**Purpose:** Establish the Python-owned data contract before adding Godot preflight or runtime behavior.

- [x] Task: Add failing protocol-v2 unit tests [commit: `71db4c8`]
  - [x] Define valid suite defaults and per-test integration metadata.
  - [x] Define `headless` and `windowed` execution modes.
  - [x] Define named-resource and optional primary-scene fields.
  - [x] Reject protocol v1, unknown fields, unsupported modes, and malformed metadata.
  - [x] Verify JSON round trips and atomic preflight-result writes.
  - [x] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Implement the protocol-v2 Python models [commit: `4158871`]
  - [x] Increment `NATIVE_PROTOCOL_VERSION` to `2`.
  - [x] Add minimal models for effective integration configuration.
  - [x] Extend suite/test/preflight contracts without adding speculative fields.
  - [x] Reuse the existing atomic JSON writer.
  - [x] Update existing fixtures and unit tests to the intentional protocol bump.
  - [x] Run the targeted protocol tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `25297e0`]
  - [x] Run targeted Python unit tests and static checks.
  - [x] Validate protocol compatibility and actionable error behavior.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 2 — Godot metadata preflight [checkpoint: `ce2aba9`]

**Purpose:** Resolve GDScript integration declarations in Godot before Python chooses a suite's display mode.

- [x] Task: Add failing preflight E2E tests [commit: `eea4185`]
  - [x] Cover suites without an `INTEGRATION` declaration.
  - [x] Cover default scenes, named resources, and headless defaults.
  - [x] Cover per-test scene/resource overrides and field-wise merging.
  - [x] Cover explicit removal of inherited values with `null`.
  - [x] Cover resource-only suites and per-test scene clearing.
  - [x] Reject malformed declarations, invalid paths, unsupported modes, unknown fields, and unknown test names.
  - [x] Prove that filtering to one valid test does not invalidate declarations for other real suite tests.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement the bundled Godot preflight entrypoint [commit: `b736bb2`]
  - [x] Add a preflight `SceneTree` script under the managed native addon.
  - [x] Read suite constants through Godot script metadata rather than Python source parsing.
  - [x] Validate the complete suite method list before resolving selected tests.
  - [x] Calculate effective per-test metadata using field-wise merge rules.
  - [x] Write an atomic protocol-v2 preflight result.
  - [x] Do not instantiate the scene or execute lifecycle/test methods.
  - [x] Run the preflight E2E tests to Green.
- [x] Task: Add failing Python preflight-adapter tests [commit: `53e1d8e`]
  - [x] Verify one preflight process runs after project import.
  - [x] Verify manifest/result paths and environment isolation.
  - [x] Verify timeout, malformed result, missing result, and exit-code handling.
  - [x] Verify actionable configuration errors rather than parsed stdout.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement the Python preflight adapter [commit: `4a98908`]
  - [x] Add the smallest preflight command/result boundary required by the protocol.
  - [x] Invoke it exactly once per native command.
  - [x] Capture stdout/stderr separately from the structured result.
  - [x] Convert preflight failures to exit-code `2` diagnostics.
  - [x] Run adapter and E2E tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `ce2aba9`]
  - [x] Run preflight unit and E2E tests.
  - [x] Verify GDScript remains the only integration-metadata parser.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 3 — Mode-aware suite orchestration [checkpoint: `9382627`]

**Purpose:** Launch each suite with the correct Godot display mode while preserving existing process isolation and GUT routing.

- [x] Task: Add failing command/orchestrator tests [commit: `ad5d6a4`]
  - [x] Verify default headless suites retain `--headless`.
  - [x] Verify windowed suites omit the headless display-driver flag.
  - [x] Verify one preflight occurs before all suite processes.
  - [x] Verify one isolated process still runs per selected suite.
  - [x] Verify non-integration native suites require no migration.
  - [x] Verify process timeouts, result mismatches, and later-suite continuation.
  - [x] Verify explicit GUT routing bypasses native preflight unchanged.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement preflight-aware command flow [commit: `8d362cc`]
  - [x] Keep discovery and selection in Python.
  - [x] Run Godot import before loading suite integration metadata.
  - [x] Pass enriched metadata into the existing suite orchestrator.
  - [x] Select process flags from the validated suite execution mode.
  - [x] Preserve `0/1/2` precedence and existing CLI options.
  - [x] Run command/orchestrator tests to Green.
- [x] Task: Add a non-integration regression E2E test [commit: `3e4a525`]
  - [x] Run an existing plain `GdToolsTest` suite through the new flow.
  - [x] Verify assertions, selectors, retries, timeout behavior, and coverage remain valid.
  - [x] Verify no windowed behavior is activated accidentally.
  - [x] Run focused regression tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [commit: `9382627`]
  - [x] Run native command, orchestrator, and non-integration E2E tests.
  - [x] Verify no second GDScript metadata parser or per-suite preflight was introduced.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 4 — Scene/resource integration context

**Purpose:** Provide a deterministic per-attempt scene tree and named-resource API.

- [x] Task: Add failing native integration E2E tests [commit: `95f0ecc`]
  - [x] Add fixture scenes with stable node paths and emitted signals.
  - [x] Add named `.tres`/`.res` fixture resources.
  - [x] Cover suite-default scenes and per-test scene overrides.
  - [x] Cover suite-default resources, per-test resource overrides, and `null` removal.
  - [x] Cover resource-only tests and scenes without resources.
  - [x] Cover root, relative node, pattern lookup, and bounded signal-wait helpers.
  - [x] Cover missing nodes/resources with structured diagnostics.
  - [x] Prove resources are not assigned to node properties automatically.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement `GdToolsTestContext` [commit: `fc9fb8f`]
  - [x] Add the minimal bundled context type.
  - [x] Expose the primary scene root and effective metadata.
  - [x] Add explicit node lookup, pattern lookup, resource lookup, and signal-wait helpers.
  - [x] Record integration lookup failures through the owning test instance.
  - [x] Keep all context state private to the current test attempt.
  - [x] Run focused GDScript fixture tests to Green.
- [x] Task: Implement per-attempt scene/resource setup [commit: `0720c6b`]
  - [x] Load and validate named resources before the test starts.
  - [x] Instantiate and add at most one primary scene.
  - [x] Attach the context before `before_each`.
  - [x] Make the context available to the test and cleanup hooks.
  - [x] Reject runtime scene/resource load failures with actionable paths.
  - [x] Run scene/resource E2E tests to Green.
- [x] Task: Add failing cleanup and retry-isolation tests [commit: `9b55914`]
  - [x] Prove `after_each` can inspect the live scene.
  - [x] Prove teardown occurs after `after_each` on pass, failure, and timeout.
  - [x] Prove retries start with fresh scene/resource/context state.
  - [x] Prove teardown errors become infrastructure failures.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement deterministic teardown [commit: `c3e4c52`]
  - [x] Disconnect/clear context-owned signal waits.
  - [x] Remove and free the primary scene after `after_each`.
  - [x] Release resource and context references before retry/next test.
  - [x] Preserve existing suite state and lifecycle-hook behavior.
  - [x] Run lifecycle, timeout, retry, and integration tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`) [checkpoint: `6c60e97`]
  - [x] Run all headless scene/resource integration tests.
  - [x] Inspect scene ownership and teardown for leaks or cross-test state.
  - [x] Perform the workflow's manual verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 5 — Windowed execution and bounded artifacts

**Purpose:** Add explicit windowed rendering, failure screenshots, and predictable latest-run artifact retention.

- [x] Task: Add failing artifact-management tests [commit: `8da3685`, `9d7f003`]
  - [x] Verify run-scoped suite directories and stable artifact names.
  - [x] Verify manifest, result, event, and log paths are recorded.
  - [x] Verify failed infrastructure runs still leave useful diagnostics.
  - [x] Verify older run directories are pruned only after the latest run is recorded.
  - [x] Verify paths are safe and machine-readable on supported platforms.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement run-scoped artifact management [commit: `bd5a344`]
  - [x] Create the minimal artifact path/retention helpers.
  - [x] Write suite artifacts below `.gd-tools/artifacts/<run_id>/`.
  - [x] Atomically publish final artifacts where required.
  - [x] Prune older runs after successful publication.
  - [x] Keep coverage shards under their existing coverage output boundary.
  - [x] Run artifact unit tests to Green.
- [x] Task: Add failing windowed and screenshot tests [commit: `847e4be`]
  - [x] Verify windowed suites omit headless mode.
  - [x] Verify no hidden headless fallback occurs.
  - [x] Verify display/renderer initialization failure returns `2`.
  - [x] Verify failed/timed-out windowed tests capture a PNG after `after_each` and before teardown.
  - [x] Verify passing tests and headless tests do not create screenshots.
  - [x] Verify screenshot write failure is an infrastructure error.
  - [x] Confirm the expected Red phase.
- [x] Task: Implement windowed readiness and screenshot capture [commit: `087f064`]
  - [x] Add minimal display/renderer readiness validation.
  - [x] Capture the primary viewport after rendering completes.
  - [x] Write screenshots through a temporary file and atomic finalization.
  - [x] Add screenshot paths to structured diagnostics and JUnit output.
  - [x] Run windowed-capable and simulated-failure tests to Green.
- [x] Task: Add display-capable E2E coverage [commit: `847e4be`]
  - [x] Run a real windowed fixture where the environment provides a display.
  - [x] Skip only with an explicit, actionable environment reason when no display exists.
  - [x] Keep the simulated initialization-failure path active in headless CI.
  - [x] Run focused artifact/window tests to Green.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [x] Run artifact, windowed, and failure-diagnostic tests.
  - [x] Verify artifact retention remains bounded.
  - [x] Perform manual headless and display-capable verification.
  - [x] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 6 — Reporting, coverage, doctor, and packaging

**Purpose:** Make integration behavior visible and installable through every existing product boundary.

- [ ] Task: Add failing reporting and exit-code tests
  - [ ] Verify scene, resource, lifecycle, and artifact diagnostics reach Rich output.
  - [ ] Verify JUnit includes integration diagnostics and artifact references.
  - [ ] Verify ordinary test failures remain `1`.
  - [ ] Verify declaration, display, protocol, teardown, and artifact failures dominate as `2`.
  - [ ] Verify later suites still run after an infrastructure failure.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Integrate native integration diagnostics with reporting
  - [ ] Normalize protocol-v2 diagnostics through the existing `TestResult` model.
  - [ ] Add concise actionable CLI messages without parsing engine prose.
  - [ ] Preserve machine-readable result/JUnit data.
  - [ ] Avoid new CLI flags or configuration for this track.
  - [ ] Run reporting tests to Green.
- [ ] Task: Add failing scene-coverage tests
  - [ ] Activate native coverage before scene/resource setup.
  - [ ] Collect line and branch hits from production scripts reached through a scene.
  - [ ] Preserve the full-project denominator and existing exclusions.
  - [ ] Verify per-suite shard merging remains deterministic.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Preserve native coverage through integration setup
  - [ ] Keep transient activation ahead of project scene execution.
  - [ ] Exclude preflight/context/runner support files automatically.
  - [ ] Retain existing threshold and report formats.
  - [ ] Run coverage unit and E2E tests to Green.
- [ ] Task: Update doctor and package-data integration
  - [ ] Add failing tests for new bundled GDScript files and protocol-v2 metadata.
  - [ ] Include preflight/context files in wheel/sdist package data.
  - [ ] Diagnose stale or mismatched managed native addons before execution.
  - [ ] Preserve managed-file backup/update behavior.
  - [ ] Keep optional GUT diagnostics non-blocking in native mode.
  - [ ] Run doctor, init, packaging, and update tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run reporting, coverage, doctor, and packaging tests.
  - [ ] Build package artifacts and inspect native addon contents.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 7 — Acceptance E2E, documentation, and final gates

**Purpose:** Prove the complete user workflow and close implementation against the approved specification.

- [ ] Task: Add full native scene-integration acceptance tests
  - [ ] Run a clean GUT-free project using default and overridden scenes/resources.
  - [ ] Verify selectors, tags, lifecycle hooks, retries, timeouts, and per-test isolation.
  - [ ] Verify native coverage and all report formats.
  - [ ] Verify JUnit, structured diagnostics, and artifact paths.
  - [ ] Verify pass, test-failure, and infrastructure-failure exit codes.
  - [ ] Verify explicit GUT routing remains unchanged.
  - [ ] Run the complete native E2E set to Green.
- [ ] Task: Update implementation and user documentation
  - [ ] Add scene/resource authoring examples to `docs/USER_GUIDE.md`.
  - [ ] Document the explicit context API and field-wise merge behavior.
  - [ ] Document headless defaults, windowed requirements, screenshots, and artifact paths.
  - [ ] Update protocol/addon compatibility notes.
  - [ ] Mark Phase 2 complete in `docs/ROADMAP.md`.
  - [ ] Synchronize `docs/PRD.md`, `conductor/product.md`, and `conductor/tech-stack.md`.
  - [ ] Keep broader README/changelog/release alignment in its separate track.
- [ ] Task: Complete final quality gates
  - [ ] Run the full unit and integration suites.
  - [ ] Run headless and display-capable E2E verification.
  - [ ] Run `ruff check src/ tests/`.
  - [ ] Run `black --check src/ tests/`.
  - [ ] Run branch coverage and confirm more than 80% line and 70% branch coverage for new source modules.
  - [ ] Build package artifacts and verify all bundled addon files.
  - [ ] Confirm no new runtime dependency or configuration surface was introduced.
  - [ ] Inspect the final implementation diff for security, performance, and unrequested changes.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run the complete automated verification suite.
  - [ ] Perform manual headless, windowed, failure-artifact, and exit-code verification.
  - [ ] Obtain explicit user confirmation.
  - [ ] Create the final implementation checkpoint commit, git note, and recorded SHA.

## Plan Boundaries

- No multiple primary scenes, automatic resource assignment, mocking, parameterized tests, playtesting coverage, editor UI, GUT bridge/migration, parallelism, runtime caching, or configurable artifact root.
- No permanent test autoload or project-autoload mutation.
- No automatic windowed-to-headless fallback.
- No release tagging, publishing, or broad README/changelog release alignment.
- Conductor review is intentionally performed separately after implementation finishes.
