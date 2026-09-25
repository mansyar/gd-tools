# Implementation Plan: Native Scene and Resource Integration

- **Track ID:** native_scene_integration_20260925
- **Type:** Feature
- **Status:** New
- **Specification:** [`spec.md`](./spec.md)

## Phase 1 — Protocol v2 and integration metadata contract

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
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run targeted Python unit tests and static checks.
  - [ ] Validate protocol compatibility and actionable error behavior.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 2 — Godot metadata preflight

**Purpose:** Resolve GDScript integration declarations in Godot before Python chooses a suite's display mode.

- [ ] Task: Add failing preflight E2E tests
  - [ ] Cover suites without an `INTEGRATION` declaration.
  - [ ] Cover default scenes, named resources, and headless defaults.
  - [ ] Cover per-test scene/resource overrides and field-wise merging.
  - [ ] Cover explicit removal of inherited values with `null`.
  - [ ] Cover resource-only suites and per-test scene clearing.
  - [ ] Reject malformed declarations, invalid paths, unsupported modes, unknown fields, and unknown test names.
  - [ ] Prove that filtering to one valid test does not invalidate declarations for other real suite tests.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement the bundled Godot preflight entrypoint
  - [ ] Add a preflight `SceneTree` script under the managed native addon.
  - [ ] Read suite constants through Godot script metadata rather than Python source parsing.
  - [ ] Validate the complete suite method list before resolving selected tests.
  - [ ] Calculate effective per-test metadata using field-wise merge rules.
  - [ ] Write an atomic protocol-v2 preflight result.
  - [ ] Do not instantiate the scene or execute lifecycle/test methods.
  - [ ] Run the preflight E2E tests to Green.
- [ ] Task: Add failing Python preflight-adapter tests
  - [ ] Verify one preflight process runs after project import.
  - [ ] Verify manifest/result paths and environment isolation.
  - [ ] Verify timeout, malformed result, missing result, and exit-code handling.
  - [ ] Verify actionable configuration errors rather than parsed stdout.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement the Python preflight adapter
  - [ ] Add the smallest preflight command/result boundary required by the protocol.
  - [ ] Invoke it exactly once per native command.
  - [ ] Capture stdout/stderr separately from the structured result.
  - [ ] Convert preflight failures to exit-code `2` diagnostics.
  - [ ] Run adapter and E2E tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run preflight unit and E2E tests.
  - [ ] Verify GDScript remains the only integration-metadata parser.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 3 — Mode-aware suite orchestration

**Purpose:** Launch each suite with the correct Godot display mode while preserving existing process isolation and GUT routing.

- [ ] Task: Add failing command/orchestrator tests
  - [ ] Verify default headless suites retain `--headless`.
  - [ ] Verify windowed suites omit the headless display-driver flag.
  - [ ] Verify one preflight occurs before all suite processes.
  - [ ] Verify one isolated process still runs per selected suite.
  - [ ] Verify non-integration native suites require no migration.
  - [ ] Verify process timeouts, result mismatches, and later-suite continuation.
  - [ ] Verify explicit GUT routing bypasses native preflight unchanged.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement preflight-aware command flow
  - [ ] Keep discovery and selection in Python.
  - [ ] Run Godot import before loading suite integration metadata.
  - [ ] Pass enriched metadata into the existing suite orchestrator.
  - [ ] Select process flags from the validated suite execution mode.
  - [ ] Preserve `0/1/2` precedence and existing CLI options.
  - [ ] Run command/orchestrator tests to Green.
- [ ] Task: Add a non-integration regression E2E test
  - [ ] Run an existing plain `GdToolsTest` suite through the new flow.
  - [ ] Verify assertions, selectors, retries, timeout behavior, and coverage remain valid.
  - [ ] Verify no windowed behavior is activated accidentally.
  - [ ] Run focused regression tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run native command, orchestrator, and non-integration E2E tests.
  - [ ] Verify no second GDScript metadata parser or per-suite preflight was introduced.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 4 — Scene/resource integration context

**Purpose:** Provide a deterministic per-attempt scene tree and named-resource API.

- [ ] Task: Add failing native integration E2E tests
  - [ ] Add fixture scenes with stable node paths and emitted signals.
  - [ ] Add named `.tres`/`.res` fixture resources.
  - [ ] Cover suite-default scenes and per-test scene overrides.
  - [ ] Cover suite-default resources, per-test resource overrides, and `null` removal.
  - [ ] Cover resource-only tests and scenes without resources.
  - [ ] Cover root, relative node, pattern lookup, and bounded signal-wait helpers.
  - [ ] Cover missing nodes/resources with structured diagnostics.
  - [ ] Prove resources are not assigned to node properties automatically.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement `GdToolsTestContext`
  - [ ] Add the minimal bundled context type.
  - [ ] Expose the primary scene root and effective metadata.
  - [ ] Add explicit node lookup, pattern lookup, resource lookup, and signal-wait helpers.
  - [ ] Record integration lookup failures through the owning test instance.
  - [ ] Keep all context state private to the current test attempt.
  - [ ] Run focused GDScript fixture tests to Green.
- [ ] Task: Implement per-attempt scene/resource setup
  - [ ] Load and validate named resources before the test starts.
  - [ ] Instantiate and add at most one primary scene.
  - [ ] Attach the context before `before_each`.
  - [ ] Make the context available to the test and cleanup hooks.
  - [ ] Reject runtime scene/resource load failures with actionable paths.
  - [ ] Run scene/resource E2E tests to Green.
- [ ] Task: Add failing cleanup and retry-isolation tests
  - [ ] Prove `after_each` can inspect the live scene.
  - [ ] Prove teardown occurs after `after_each` on pass, failure, and timeout.
  - [ ] Prove retries start with fresh scene/resource/context state.
  - [ ] Prove teardown errors become infrastructure failures.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement deterministic teardown
  - [ ] Disconnect/clear context-owned signal waits.
  - [ ] Remove and free the primary scene after `after_each`.
  - [ ] Release resource and context references before retry/next test.
  - [ ] Preserve existing suite state and lifecycle-hook behavior.
  - [ ] Run lifecycle, timeout, retry, and integration tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run all headless scene/resource integration tests.
  - [ ] Inspect scene ownership and teardown for leaks or cross-test state.
  - [ ] Perform the workflow's manual verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

## Phase 5 — Windowed execution and bounded artifacts

**Purpose:** Add explicit windowed rendering, failure screenshots, and predictable latest-run artifact retention.

- [ ] Task: Add failing artifact-management tests
  - [ ] Verify run-scoped suite directories and stable artifact names.
  - [ ] Verify manifest, result, event, and log paths are recorded.
  - [ ] Verify failed infrastructure runs still leave useful diagnostics.
  - [ ] Verify older run directories are pruned only after the latest run is recorded.
  - [ ] Verify paths are safe and machine-readable on supported platforms.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement run-scoped artifact management
  - [ ] Create the minimal artifact path/retention helpers.
  - [ ] Write suite artifacts below `.gd-tools/artifacts/<run_id>/`.
  - [ ] Atomically publish final artifacts where required.
  - [ ] Prune older runs after successful publication.
  - [ ] Keep coverage shards under their existing coverage output boundary.
  - [ ] Run artifact unit tests to Green.
- [ ] Task: Add failing windowed and screenshot tests
  - [ ] Verify windowed suites omit headless mode.
  - [ ] Verify no hidden headless fallback occurs.
  - [ ] Verify display/renderer initialization failure returns `2`.
  - [ ] Verify failed/timed-out windowed tests capture a PNG after `after_each` and before teardown.
  - [ ] Verify passing tests and headless tests do not create screenshots.
  - [ ] Verify screenshot write failure is an infrastructure error.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement windowed readiness and screenshot capture
  - [ ] Add minimal display/renderer readiness validation.
  - [ ] Capture the primary viewport after rendering completes.
  - [ ] Write screenshots through a temporary file and atomic finalization.
  - [ ] Add screenshot paths to structured diagnostics and JUnit output.
  - [ ] Run windowed-capable and simulated-failure tests to Green.
- [ ] Task: Add display-capable E2E coverage
  - [ ] Run a real windowed fixture where the environment provides a display.
  - [ ] Skip only with an explicit, actionable environment reason when no display exists.
  - [ ] Keep the simulated initialization-failure path active in headless CI.
  - [ ] Run focused artifact/window tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run artifact, windowed, and failure-diagnostic tests.
  - [ ] Verify artifact retention remains bounded.
  - [ ] Perform manual headless and display-capable verification.
  - [ ] Create the phase checkpoint commit, git note, and recorded SHA.

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
