# Initial Concept

A Python CLI tool (`gd-tools`) that brings a modern development workflow to GDScript projects in Godot 4.5+. It provides a Godot-native GDScript test runtime (`GdToolsTest`) for unit and scene/resource integration tests, wraps mature, community-trusted tools for linting (gdlint) and formatting (gdformat), and fills the remaining gap — code coverage — with a custom hybrid instrumentation system (Python plan generation + GDScript runtime instrumentation + Python reporting).

---

# Product Definition

## 1. Vision Statement

`gd-tools` gives GDScript developers the same professional tooling parity that developers in JavaScript, Python, and Go ecosystems take for granted. One install, one config, one mental model — test, lint, format, and coverage for Godot 4.5+ projects.

The native test runtime provides a familiar CLI and Godot-native lifecycle for unit and scene/resource integration tests. The unique value proposition remains **production-quality code coverage for GDScript** — a capability that no existing tool provides for Godot 4. This is delivered through a custom hybrid architecture, while lint and format continue to provide immediate, low-risk value and onboard users into the ecosystem.

## 2. Target Users (v1 Priority)

The v1 release targets two primary user groups:

### 2.1 GDScript Developers
Individual developers on Godot 4.5+ who want professional tooling parity with other languages. They value:
- Fast, frictionless setup (`gd-tools init` in under a minute)
- Familiar CLI conventions (Jest, pytest, `go test -cover` mental models)
- Readable terminal output with colors and tables

### 2.2 Teams with CI/CD Pipelines
Development teams requiring automated quality gates. They value:
- Exit codes for CI integration (0 = pass, 1 = failure, 2 = config error)
- `--check` flags for non-mutating CI mode
- Machine-readable output (JSON, JUnit XML, LCOV, Cobertura)
- Coverage threshold enforcement (`--min N`)
- Cross-platform support (Windows, macOS, Linux)

> *Open-source Godot project maintainers are a secondary audience served by the same tooling, but not the primary design driver for v1.*

## 3. Release Strategy

**Full v1 release.** All five phases of the roadmap are completed before any public release. No incremental/alpha releases ship to PyPI; the first publishable artifact is the complete v1.0.

**Native runtime migration (post-v1).** The `GdToolsTest` initiative is a
product evolution track. It does not retroactively change the historical v1
release gates, but the native runtime must be the supported default before
the temporary GUT bridge is removed.

The roadmap phases:
1. **Phase 0 — Spike:** Validate the riskiest assumption (runtime GDScript instrumentation) before building coverage.
2. **Phase 1 — Foundation:** Project scaffolding, configuration system, Godot binary detection.
3. **Phase 2 — MVP1 (Tool Wrappers):** Lint, format, test runner, init, doctor.
4. **Phase 3 — MVP2 (Coverage System):** Plan generator, tracker addon, hooks, reporter, CLI integration.
5. **Phase 4 — Polish & Release:** Test suite, CI/CD pipeline, documentation, PyPI release.

## 4. Product Positioning

**Phased reveal.** The product is positioned with a gradual introduction of value:

1. **Lead with the familiar.** Lint, format, and the test command are the on-ramp. Lint and format wrap mature tools developers already know, while the native `GdToolsTest` runtime provides a familiar Godot-native testing model without making GUT a permanent dependency.

2. **Introduce the differentiator.** Code coverage is revealed as the unique capability that no other GDScript tooling provides. Once users are comfortable with the unified workflow, coverage extends it with line and branch reporting, CI-friendly formats (LCOV, Cobertura), and HTML reports.

This positioning avoids leading with the riskiest, most complex feature while making the native test runtime the long-term foundation for the unified CLI.

## 5. Core Value Propositions

| Value | Description |
|-------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. |
| **Native test runtime** | `GdToolsTest` provides Godot-native unit and scene/resource integration tests with async execution, structured diagnostics, and line/branch coverage. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute — native test runtime and coverage addon deployed, configs generated. GUT is opt-in during migration. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript — HTML, LCOV, and Cobertura reports that integrate with CI and code review tools. |
| **CI/CD friendly** | Exit codes, `--check` flags, `--quiet` for minimal CI output, machine-readable output, no interactive prompts when run non-interactively. |
| **Migration-friendly testing** | A bounded GUT bridge supports gradual migration from existing suites without making GUT a permanent architectural dependency. |
| **Standalone compatibility** | gdlint and gdformat continue to work if invoked directly. GUT remains available through the temporary bridge. `gd-tools` is a layer on top, not a lock-in. |
| **Convention over configuration** | Sensible defaults out of the box; config for when conventions don't fit. |

## 6. Design Philosophy

- **Wrap mature tools where they fit.** gdlint and gdformat remain battle-tested integrations. Where the Godot testing gap requires project-owned behavior, `gd-tools` owns the focused `GdToolsTest` runtime instead of inheriting a permanent external test-engine dependency.
- **Build only what's missing.** No production-quality GDScript line/branch coverage tool exists for Godot 4. This is the unique value of `gd-tools`.
- **Single source of truth.** One `gd-tools.toml` config drives all tools. `gd-tools init` generates per-tool config files where standalone compatibility is required.

## 7. Non-Goals (v1)

1. The native test runtime is intentionally focused on GDScript unit and scene/resource integration tests; it is not a general-purpose testing ecosystem.
2. Not a linter/formatter engine — we use gdtoolkit.
3. Not a Godot plugin manager — we bootstrap the native test addon, coverage addon, and optional GUT bridge only.
4. No C# support — GDScript only.
5. No Godot < 4.5 support.
6. No IDE/editor integration in v1 — CLI only.

## 8. Success Criteria

A successful v1.0 release is defined by:

- **PyPI publish.** The package is published to PyPI and installable via `pip install gd-tools-cli`. This is the primary release gate — the product is not "released" until it is on PyPI and a clean-environment install produces a working `gd-tools --version`.

Native test runtime migration gates (completed before the temporary GUT bridge is removed):

- A clean Godot project runs native tests without GUT installed.
- `gd-tools test` uses the native runtime by default.
- Native unit and scene/resource integration tests run on Godot 4.5+.
- Async execution, lifecycle hooks, selectors, tags, and structured diagnostics are reliable.
- Line and branch coverage work without a permanent native test autoload.
- The bounded GUT bridge supports migration without silent configuration loss.

Supporting success metrics (measured but not gating):
- All CLI commands (test, lint, format, coverage, init, doctor, config) functional end-to-end.
- gd-tools itself achieves ≥80% line coverage, ≥70% branch coverage.
- GitHub Actions CI pipeline completes in under 10 minutes.
- Install-to-first-run time under 2 minutes.

## 9. Native Test Runtime Direction

**Status:** Foundation completed; broader migration gates remain
**Scope:** Post-v0.4 native testing initiative

### Decision

`gd-tools` will develop its own Godot-native test runtime and addon. The
public native API is `GdToolsTest` / `GdToolsTestRunner`.

The native runtime is the default execution path for `gd-tools test`.
GUT remains available during a one-release migration period through a
bounded compatibility path.

### Runtime model

- Python owns configuration, discovery, filtering, process orchestration,
  reporting, and exit codes.
- Godot owns test loading, lifecycle execution, assertions, async waits,
  scene-tree interaction, and native coverage activation.
- Native suites are class-based and extend `GdToolsTest`, which extends
  `Node`.
- Tests are discovered by configured directories or exact file selectors, with
  class-level tag filters and `test_*` method discovery.
- The default per-test timeout is configurable independently from the Godot
  process/import timeout.
- Suites run in isolated Godot processes by default.
- Tests run sequentially by default; optional parallelism is deferred.
- Headless execution is the default; windowed execution is explicit and
  requires a real display; there is no automatic fallback to headless.
- The runtime has no new third-party runtime dependency.

### Scene and resource integration

- Suites declare at most one primary scene, any number of named resources, a
  suite-level execution mode, and per-test overrides through a class-level
  `INTEGRATION` constant.
- Declaration metadata is read through Godot, never by parsing GDScript in
  Python, and is validated once per command in a headless preflight before any
  suite is constructed.
- Overrides merge field by field: omitted fields are inherited, resource maps
  merge by logical name, and `null` removes an inherited scene or resource.
- Invalid paths, modes, fields, or override targets are configuration failures
  that exit `2` with the suite path and the expected shape.
- Tests reach the scene through an explicit context object rather than
  proxied scene methods; resources are never assigned to nodes automatically.
- Project autoloads run exactly as in production; the runtime installs no
  test-only autoloads and mutates no project autoload.
- Every attempt rebuilds the scene, context, and resources so retries are
  isolated, and each run publishes a machine-readable artifact index retaining
  only the latest run.

### Results and coverage

- Native results use a versioned JSON protocol and JUnit XML output.
- Results include timestamps, lifecycle assertion diagnostics, and captured
  Godot engine errors/warnings; engine errors map to infrastructure exit `2`.
- Godot progress events use structured NDJSON when enabled.
- Existing exit-code semantics remain:
  - `0`: pass
  - `1`: test or coverage failure
  - `2`: environment, configuration, protocol, engine, or process failure
- Native coverage preserves line and branch metrics.
- Existing coverage plan schema v1 is reused where possible.
- The native test addon and generated harness files are excluded from
  application coverage automatically.

### Migration boundary

- `gd-tools test` defaults to native execution.
- The existing GUT execution path remains selectable during migration.
- The future GUT bridge supports only a documented core subset:
  base class, test discovery, lifecycle hooks, core assertions, and async
  helpers.
- Unsupported GUT features fail with actionable migration guidance.
- `.gutconfig.json` is translated and preserved during migration.
- `gd-tools.toml` is the canonical configuration source.
- A guided migration command previews changes before rewriting user files.
- New projects install the native runtime by default; GUT installation is
  opt-in during the migration period.

### Product success criteria

The migration is complete when:

1. A clean Godot project can run native tests without GUT installed.
2. `gd-tools test` uses the native runtime by default.
3. Native unit and scene/resource integration tests run in Godot 4.5+.
4. Async tests, lifecycle hooks, selectors, tags, and structured diagnostics
   work reliably.
5. Line and branch coverage work without a permanent native test autoload.
6. GUT bridge users can migrate with reviewable changes.
7. The bridge is removed after the bounded migration period.
8. Documentation, CI, packaging, and release checks reflect the native
   runtime as the supported path.

See the temporary migration roadmap in
[docs/ROADMAP.md](../docs/ROADMAP.md#8-temporary-native-test-runtime-migration-roadmap).
