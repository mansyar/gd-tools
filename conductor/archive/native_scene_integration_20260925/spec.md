# Native Scene and Resource Integration

- **Track ID:** native_scene_integration_20260925
- **Type:** Feature
- **Status:** Approved
- **Target:** Native `GdToolsTest` runtime

## Overview

Extend the completed native test foundation so integration suites can declaratively run real Godot scenes and load project resources without manually rebuilding process, tree, and rendering setup.

The feature uses typed GDScript constants as the authoring source of truth. A short headless Godot preflight resolves and validates those declarations before Python selects the correct process mode and launches each isolated suite.

## Goals

- Run real scene trees and named resources in native tests.
- Preserve suite-level defaults while allowing targeted per-test overrides.
- Provide explicit, discoverable helpers for accessing scene nodes, resources, and signals.
- Keep headless execution as the default.
- Support explicitly requested windowed suites and failure screenshots.
- Preserve current lifecycle hooks, retries, selectors, coverage, diagnostics, and exit-code semantics.
- Keep artifacts bounded and CI-friendly.

## GDScript Authoring Contract

Suites declare integration data through one optional `INTEGRATION` constant:

```gdscript
const INTEGRATION := {
	"scene": "res://tests/fixtures/player.tscn",
	"resources": {
		"stats": "res://tests/fixtures/stats.tres",
		"theme": "res://tests/fixtures/test_theme.tres",
	},
	"mode": "headless",
	"tests": {
		"test_damage_overlay": {
			"scene": "res://tests/fixtures/player_damaged.tscn",
			"resources": {
				"stats": "res://tests/fixtures/damaged_stats.tres",
			},
		},
		"test_resource_defaults_only": {
			"resources": {
				"theme": null,
			},
		},
	},
}
```

### Supported root fields

- `scene`: Optional `res://` path to one primary `PackedScene`.
- `resources`: Optional logical-name-to-`res://`-path map.
- `mode`: Either `headless` or `windowed`; defaults to `headless`.
- `tests`: Optional map from test method name to field overrides.

### Merge rules

- Suite fields form the defaults for every test.
- A per-test entry replaces only the fields it declares.
- Resource maps merge by logical key.
- `null` explicitly removes an inherited scene or resource.
- An empty path is invalid; use `null` to clear an inherited value.
- Test entries for names unknown to the suite are configuration errors.
- Unknown fields, unsupported modes, and invalid declaration shapes produce actionable configuration diagnostics.
- Execution mode is suite-level because one isolated Godot process represents one suite. Per-test execution modes are not supported.

## Metadata Preflight

Before executing suites:

1. Python performs its existing path, suite, test, and tag discovery.
2. Python writes a discovery manifest containing suite scripts and selected test names.
3. A short headless Godot preflight loads each suite script.
4. The preflight reads `INTEGRATION` through Godot's script metadata, validates it, calculates each test's effective declaration, and writes an enriched versioned manifest.
5. Python uses the resolved suite mode to choose the process launch configuration.

Requirements:

- At most one preflight process is launched per command, regardless of suite count.
- GDScript remains the source of truth; Python does not parse the integration constant.
- Parse, schema, missing-resource, and declaration errors exit as configuration/infrastructure failures with code `2`.
- The Python-to-Godot protocol increments to version `2`.
- A protocol or managed-addon mismatch is diagnosed before suite execution.
- Existing non-integration suites remain valid without an `INTEGRATION` declaration.

## Runtime Integration Context

Each test attempt receives an explicit `GdToolsTestContext`, available through a base-class helper such as:

```gdscript
func get_test_context() -> GdToolsTestContext:
	return _gd_tools_context
```

The context exposes:

- The primary scene root.
- Explicit relative node-path lookup.
- Recursive node lookup by pattern.
- Named resource lookup.
- Signal waiting bounded by the active test timeout.
- Access to the effective integration metadata.
- Optional viewport screenshot capture for windowed execution.

Behavioral requirements:

- Node paths are relative to the primary scene root.
- Missing required nodes/resources produce structured integration failures with the requested logical name or path.
- Resource declarations load and validate before the test starts.
- Resources remain accessible by logical name; the runtime does not assign them to node properties automatically.
- A suite may be resource-only by omitting or clearing `scene`.
- A test may instantiate at most one primary scene.
- No scene-root methods or properties are implicitly proxied onto `GdToolsTest`.

## Setup and Lifecycle Order

For every test attempt, including retries:

1. Create a fresh `GdToolsTest`.
2. Resolve and validate the effective integration declaration.
3. Initialize the requested headless/windowed execution environment.
4. Load declared resources.
5. Instantiate and add the primary scene to the active scene tree.
6. Run `before_each`.
7. Run the test method.
8. Run `after_each`, including when the test timed out.
9. Capture failure evidence when applicable.
10. Tear down the scene/context and release references.
11. Start the next attempt or test from a clean state.

Additional requirements:

- `before_all` and `after_all` remain suite hooks.
- Integration contexts are per-test-attempt; they are not shared across tests.
- `after_each` may inspect the scene.
- Teardown always runs after `after_each`, even if the test or hook failed or timed out.
- A retry never inherits nodes, resources, signals, or context state from a failed attempt.
- Teardown failures become structured infrastructure diagnostics and prevent a false success.

## Headless and Windowed Execution

### Headless

- Remains the default.
- Uses the current isolated process and display-driver behavior.
- Supports scenes, resources, signals, lifecycle hooks, retries, and coverage.

### Windowed

- Is enabled only when the suite declaration requests it.
- Is launched without the headless display-driver flag.
- Supports the same lifecycle and context API as headless execution.
- Captures a PNG from the primary viewport on test failure or timeout after `after_each` and before teardown.
- Records the screenshot path in test diagnostics.

If window initialization or the requested renderer/display cannot start:

- Do not fall back to headless.
- Preserve engine and display diagnostics.
- Return infrastructure exit code `2`.

## Failure Artifacts

Artifacts are written under a run-scoped directory below:

```text
.gd-tools/artifacts/<run_id>/
```

Per-suite artifacts may include:

- Enriched manifest metadata.
- Result JSON.
- Event NDJSON.
- Godot log.
- Windowed failure screenshot.
- Engine and process diagnostics.

Retention policy:

- Keep the latest completed run.
- Remove older artifact run directories.
- Passing headless runs retain only bounded diagnostic metadata needed by current reporting.
- Screenshots are produced only for failed or timed-out windowed tests.
- Screenshot write failure is an infrastructure error rather than silently ignored.
- Artifact paths in results must be valid and machine-readable.

## Reporting and Exit Codes

Preserve the existing contract:

- `0`: all selected tests and coverage requirements pass.
- `1`: one or more tests fail, time out, or exceed coverage thresholds.
- `2`: environment, declaration, protocol, process, rendering, artifact, or other infrastructure failure.

Requirements:

- Integration failures appear as normal test failures when the test or declared asset is invalid at runtime.
- Invalid declarations, display initialization failures, protocol mismatches, and teardown infrastructure failures use code `2`.
- Rich output includes scene/resource path, test, suite, lifecycle stage, and artifact location where applicable.
- JUnit preserves the same status and diagnostics.
- Existing native coverage remains enabled before scene/resource setup.
- Explicit `--runtime gut` behavior is unchanged.

## Configuration

No new user configuration is required for the initial feature:

- `INTEGRATION["mode"]` selects windowed execution.
- The artifact root and retention policy are fixed for predictable CI collection.
- Existing `[test]` settings continue to control paths, selectors, tags, timeouts, retries, and runtime selection.

A future track may add global artifact-directory overrides or runtime rendering options.

## Testing Requirements

### Unit tests

- Integration declaration schema and unknown-field validation.
- Default/per-test field-wise merge behavior.
- Resource-map merge and explicit removal.
- Preflight result and protocol-v2 validation.
- Mode selection and headless/windowed command construction.
- Artifact naming, retention, and pruning.
- Exit-code precedence.
- Doctor/addon compatibility diagnostics.

### Native GDScript E2E tests

- Headless scene startup and node lookup.
- Suite-default scene with per-test override.
- Resource-only tests.
- Named resource loading and explicit assignment by the test.
- Missing node/resource diagnostics.
- Lifecycle cleanup and clean retry state.
- Timeout followed by forced teardown.
- Windowed mode and failure screenshot where a display-capable environment exists.
- Window initialization failure producing code `2`.
- Native coverage across scene-loaded production scripts.
- Existing filters, tags, JUnit, and non-integration suites.

### Regression tests

- Existing native assertion, async, lifecycle, selector, timeout, retry, coverage, and GUT-routing tests remain green.

## Documentation

Update:

- Native test authoring documentation with scene/resource examples.
- Public API/context reference.
- Headless/windowed limitations and CI requirements.
- Protocol/addon compatibility notes.
- Product roadmap Phase 2 status.
- User-facing native testing guide.

This track does not perform the broader README/changelog/release alignment proposed for the separate release-polish track.

## Acceptance Criteria

1. A suite can declare a default scene, named resources, and headless mode entirely in GDScript.
2. A per-test declaration can override scene/resources without duplicating unrelated defaults.
3. One primary scene and any number of named resources are available through an explicit context.
4. Headless remains the default and existing native suites require no migration.
5. A windowed suite runs without `--headless` and captures a failure screenshot.
6. Window initialization failure is explicit and returns `2`; no silent fallback occurs.
7. `after_each` can inspect the context, after which teardown always occurs before retry.
8. Text and screenshot artifacts are retained only for the latest bounded run.
9. Native coverage remains valid when production scripts are exercised through loaded scenes.
10. Rich, JUnit, structured result, selector, tag, timeout, and retry behavior remains compatible.
11. Python and Godot use a validated protocol-v2 contract with actionable mismatch diagnostics.
12. Unit, E2E, regression, formatting, linting, type checking, and coverage quality gates pass.
13. Current user and developer documentation describes the feature and its constraints accurately.

## Out of Scope

- Multiple primary scene roots per test.
- Automatic Resource-to-node-property assignment.
- Broad mocking or test doubles.
- Parameterized tests.
- Playtesting coverage.
- Editor UI or an editor plugin.
- GUT compatibility bridge or migration assistant.
- Parallel suite execution.
- Runtime/import caching.
- A user-configurable artifact root.
- Automated fallback from windowed to headless execution.
- Permanent test autoloads or modification of project autoloads.
