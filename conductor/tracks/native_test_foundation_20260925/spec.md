# Native Test Runtime Foundation

- **Track ID:** native_test_foundation_20260925
- **Type:** Feature / Architecture
- **Status:** New
- **Related decision:** `d04c1ae` — docs: Define native test runtime direction

## Overview

Introduce the first Godot-native test runtime for `gd-tools`.

The native runtime becomes the default execution path for `gd-tools test`,
while the existing GUT subprocess path remains selectable during migration.
Python owns configuration, discovery, filtering, process orchestration,
reporting, and exit codes. Godot owns loading and executing GDScript test
suites.

The foundation track proves a complete vertical slice with a clean,
GUT-free Godot project:

```text
gd-tools test
  -> Python discovery
  -> versioned manifest
  -> transient Godot runner
  -> GdToolsTest suite
  -> synchronous/asynchronous execution
  -> native JSON/JUnit results
  -> line/branch coverage
```

## Context

The current implementation is centered on GUT:

- `init` downloads and installs GUT.
- `test_runner.py` invokes GUT's command-line runner.
- Coverage hooks extend `GutHookScript`.
- `.gutconfig.json` is part of the current test setup.
- E2E fixtures copy a GUT checkout.

The product decision documented in `conductor/product.md` and
`conductor/tech-stack.md` makes the native runtime the long-term default.
This track intentionally proves only the foundation; migration and broader
integration are separate tracks.

## Goals

1. Run native tests in a project with no GUT installation.
2. Make native execution the default for `gd-tools test`.
3. Preserve the existing GUT subprocess path behind explicit runtime selection.
4. Establish a versioned Python-to-Godot manifest/result protocol.
5. Support class-based GDScript suites extending `GdToolsTest`.
6. Support synchronous and asynchronous tests.
7. Provide deterministic suite and test lifecycle management.
8. Produce native JSON, optional NDJSON events, and JUnit XML results.
9. Preserve line and branch coverage using the existing plan schema where possible.
10. Add no new third-party runtime dependency.
11. Establish a performance benchmark against the current GUT path.
12. Validate the architecture with Python, GDScript, and headless E2E tests.

## Functional Requirements

### FR-1: Native runtime identity and packaging

- Public native API: `GdToolsTest` / `GdToolsTestRunner`.
- `GdToolsTest` extends `Node`.
- Ship one native test addon bundled with the Python package.
- Native mode uses a transient Godot runner entrypoint.
- Native mode does not require a permanent native test autoload.
- Framework-owned addon files follow the existing managed-file/backup policy.
- No new third-party GDScript runtime dependency is introduced.

### FR-2: Runtime selection

`gd-tools test` defaults to native execution.

Supported runtime selection:

- No selector: native runtime.
- `--runtime native`: native runtime.
- `--runtime gut`: existing GUT subprocess path.

Runtime selection is explicit. The native path must not silently switch to GUT
based on filesystem detection. If native discovery finds no suites while GUT
tests exist, report a clear migration-oriented configuration/environment error
directing the user to the legacy selector.

### FR-3: Python-owned discovery and manifest

Python reads native test configuration from `gd-tools.toml`, discovers configured
test directories/files, applies path/suite/test/tag filters, and writes a
versioned JSON manifest before launching Godot.

The manifest must contain at least:

- Protocol/schema version.
- Project root.
- Runtime mode.
- Selected suite paths.
- Suite class names.
- Test method names.
- Tags.
- Timeout and retry settings.
- Coverage plan/output paths when coverage is enabled.
- Suite-level settings required by the foundation slice.

The manifest is written atomically.

Python owns:

- Discovery and filtering.
- Process lifecycle.
- Result aggregation.
- JUnit conversion.
- Exit-code mapping.

Godot owns:

- Suite loading and validation.
- Test instantiation.
- Lifecycle execution.
- Async waiting.
- Assertion recording.
- Native coverage activation.

### FR-4: Test API and lifecycle

Native suites use:

```gdscript
extends GdToolsTest
```

The foundation API supports:

- `test_*` methods.
- `before_all`.
- `before_each`.
- `after_each`.
- `after_all`.
- Class-level tags.
- One fresh `GdToolsTest` instance per test.
- Suite-scoped resources within a suite process.
- Independent tests with no implicit test-to-test ordering.

The foundation slice does not support parameterized tests or arbitrary test
method arguments.

### FR-5: Assertions

Provide explicit framework assertions with structured diagnostics:

- `assert_true`
- `assert_false`
- `assert_eq`
- `assert_ne`
- `assert_null`
- `assert_not_null`
- `fail`

Common GUT-compatible names may be used as aliases when they map cleanly to
the native implementation.

Assertions record:

- Suite and test identity.
- Assertion name.
- Actual and expected values where applicable.
- Source location.
- Message.
- Duration.
- Failure category.

Do not rely on GDScript's built-in `assert()` as the primary result mechanism.

### FR-6: Asynchronous execution

Test methods and lifecycle hooks may be coroutines.

The runtime must support helpers for:

- Process-frame waits.
- Physics-frame waits.
- Timer waits.
- Signal waits.

Default timeout:

- Five seconds per test.
- Configurable per suite/test and through the CLI.
- Reported as a distinct timeout status.
- Includes available test and runtime context in diagnostics.

### FR-7: Failure and isolation semantics

- Run one fresh Godot process per suite.
- Continue to the next test after ordinary assertion failures.
- Attempt cleanup after both passing and failing tests.
- Mark unrecoverable engine/process failures as infrastructure failures.
- Continue running other suites after a suite process crash.
- Preserve diagnostics for all failed, timed-out, and crashed tests.
- Do not allow output ordering from suites to hide results.

### FR-8: Result protocol and output

The native protocol produces:

1. An atomically written final native JSON result.
2. Optional structured NDJSON progress events.
3. JUnit XML generated through the shared Python reporting layer.

Native results represent:

- Run ID and schema version.
- Suite and test identity.
- Pass/fail/skip/pending/error/timeout/crash status.
- Start/end timestamps and duration.
- Retry attempt count when retries are enabled.
- Assertion and diagnostic data.
- Engine errors and warnings.
- Coverage artifact references.
- Process and suite crash information.

Python must not parse human-readable Godot stdout as the primary result API.

### FR-9: Exit codes

Preserve the existing contract:

| Code | Meaning |
|---:|---|
| `0` | All selected tests and coverage gates passed |
| `1` | Assertion, test, or coverage-threshold failure |
| `2` | Configuration, environment, manifest, protocol, engine, or process infrastructure failure |

A suite crash is an infrastructure failure and must not hide results from
other suites.

### FR-10: Native coverage

The foundation slice preserves line and branch coverage.

Requirements:

- Reuse coverage plan schema v1 where possible.
- Native runtime owns coverage activation and collection.
- `_GDTCoverage` remains available only for the legacy GUT path during transition.
- Native runtime and generated harness files are automatically excluded.
- Test directories remain excluded by default.
- User-defined exclusions continue to work.
- Filtered runs use the full application coverage denominator.
- Existing HTML, LCOV, Cobertura, and text reports continue to consume the results.
- The clean proof fixture contains no GUT addon or GUT hooks.
- The implementation must prove that transient runtime entry can activate coverage before application code is instrumented.

### FR-11: Configuration

`gd-tools.toml` is the canonical configuration source.

Native test configuration must support the settings required by this track,
including discovery, tags, timeout, retry, runtime selection, and coverage
output. `.gutconfig.json` translation and migration are out of scope for this
track.

### FR-12: Diagnostics

Always capture:

- Structured assertion details.
- Suite/test identity.
- Duration.
- Godot errors.
- Captured warnings.
- Relevant stdout/stderr.
- Timeout context.
- Process exit and crash information.

Optional integration artifacts are deferred to the scene/resource integration
track.

## Non-Functional Requirements

### Compatibility

- Target Godot 4.5+.
- Preserve the existing `0/1/2` exit-code contract.
- Keep the legacy GUT path callable during transition.
- Do not introduce a new runtime dependency.
- Use atomic result writes.

### Performance

- Add a benchmark for a small representative test suite.
- Target no more than approximately 2x the current GUT-based execution time.
- Do not optimize parallelism in this track.

### Testability

- Unit-test Python discovery, manifest serialization, protocol validation, and CLI behavior.
- Add native GDScript runtime tests for assertions, lifecycle, async waits, and cleanup.
- Add headless E2E tests using a clean GUT-free Godot fixture.
- Keep the protocol boundary independently testable without a real Godot process where possible.

## Acceptance Criteria

1. A clean Godot fixture with no GUT addon runs native tests successfully.
2. `gd-tools test` defaults to native execution.
3. `--runtime gut` continues to reach the legacy GUT path.
4. Python discovers a configured native suite.
5. Godot validates and executes a `GdToolsTest` class.
6. At least one synchronous test passes.
7. At least one asynchronous test passes.
8. A failing assertion returns exit code `1`.
9. A malformed manifest or startup failure returns exit code `2`.
10. Core assertions produce structured diagnostics.
11. Suite and test tags/selectors work.
12. Native JSON results are written atomically.
13. JUnit XML is generated from native results.
14. A timeout is reported distinctly.
15. Line and branch coverage are produced.
16. Native coverage works without a permanent `_GDTCoverage` autoload.
17. Engine errors fail appropriately while warnings are reported.
18. A crashed suite does not prevent later suites from running.
19. A benchmark shows no more than approximately 2x regression against the current small-suite GUT path.
20. Existing unit and integration tests remain green.
21. No new runtime dependency is introduced.

## Out of Scope

- Full GUT compatibility bridge.
- Migration command implementation.
- `.gutconfig.json` translation.
- Scene/resource integration suites.
- Full UI automation.
- Parameterized tests.
- Full mocking/double framework.
- Windowed visual tests.
- Parallel suite execution.
- Editor plugin/UI.
- Manual playtesting coverage.
- Removal of existing GUT code or support.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Transient runner activates too late for coverage | Make coverage activation the first foundation proof and fail the track if ordering is unreliable. |
| Godot 4.5–4.7 lifecycle differences | Keep the runtime on documented Godot APIs and add version-matrix E2E coverage before broader expansion. |
| Immediate native default affects existing GUT users | Retain the explicit legacy selector and emit actionable migration guidance. |
| Suite-scoped processes are slow | Benchmark early and defer parallelism until correctness is proven. |
| Core GUT subset does not cover user needs | Keep the compatibility bridge and migration tooling as separately scoped follow-up tracks. |
