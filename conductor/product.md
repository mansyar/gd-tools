# Initial Concept

A Python CLI tool (`gd-tools`) that brings a modern development workflow to GDScript projects in Godot 4.5+. It wraps mature, community-trusted tools for unit testing (GUT), linting (gdlint), and formatting (gdformat), and fills the remaining gap — code coverage — with a custom hybrid instrumentation system (Python plan generation + GDScript runtime instrumentation + Python reporting).

---

# Product Definition

## 1. Vision Statement

`gd-tools` gives GDScript developers the same professional tooling parity that developers in JavaScript, Python, and Go ecosystems take for granted. One install, one config, one mental model — test, lint, format, and coverage for Godot 4.5+ projects.

The unique value proposition is **production-quality code coverage for GDScript** — a capability that no existing tool provides for Godot 4. This is delivered through a custom hybrid architecture, while the familiar tool wrappers (lint, format, test) provide immediate, low-risk value and onboard users into the ecosystem.

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

The roadmap phases:
1. **Phase 0 — Spike:** Validate the riskiest assumption (runtime GDScript instrumentation) before building coverage.
2. **Phase 1 — Foundation:** Project scaffolding, configuration system, Godot binary detection.
3. **Phase 2 — MVP1 (Tool Wrappers):** Lint, format, test runner, init, doctor.
4. **Phase 3 — MVP2 (Coverage System):** Plan generator, tracker addon, hooks, reporter, CLI integration.
5. **Phase 4 — Polish & Release:** Test suite, CI/CD pipeline, documentation, PyPI release.

## 4. Product Positioning

**Phased reveal.** The product is positioned with a gradual introduction of value:

1. **Lead with the familiar.** Lint, format, and test commands are the on-ramp. They wrap tools developers already know (gdlint, gdformat, GUT) and deliver immediate value with low risk. This builds trust and establishes `gd-tools` as the unified entry point.

2. **Introduce the differentiator.** Code coverage is revealed as the unique capability that no other GDScript tooling provides. Once users are comfortable with the familiar commands, coverage extends the same workflow with line and branch reporting, CI-friendly formats (LCOV, Cobertura), and HTML reports.

This positioning avoids leading with the riskiest, most complex feature and instead builds toward it through tools that already prove the unified-CLI value proposition.

## 5. Core Value Propositions

| Value | Description |
|-------|-------------|
| **Unified workflow** | One install, one config (`gd-tools.toml`), one mental model for test, lint, format, and coverage. |
| **Zero-friction bootstrap** | `gd-tools init` gets a project fully set up in under a minute — GUT installed, coverage addon deployed, configs generated. |
| **Coverage gap-filling** | Production-quality line and branch coverage for GDScript — HTML, LCOV, and Cobertura reports that integrate with CI and code review tools. |
| **CI/CD friendly** | Exit codes, `--check` flags, machine-readable output, no interactive prompts when run non-interactively. |
| **Standalone compatibility** | gdlint, gdformat, and GUT continue to work if invoked directly. `gd-tools` is a layer on top, not a lock-in. |
| **Convention over configuration** | Sensible defaults out of the box; config for when conventions don't fit. |

## 6. Design Philosophy

- **Wrap, don't reinvent.** GUT, gdlint, and gdformat are battle-tested. We orchestrate them; we do not replace them.
- **Build only what's missing.** No production-quality GDScript line/branch coverage tool exists for Godot 4. This is the unique value of `gd-tools`.
- **Single source of truth.** One `gd-tools.toml` config drives all tools. `gd-tools init` generates per-tool config files so individual tools still work standalone.

## 7. Non-Goals (v1)

1. Not a test framework — we use GUT.
2. Not a linter/formatter engine — we use gdtoolkit.
3. Not a Godot plugin manager — we bootstrap GUT and our own coverage addon only.
4. No C# support — GDScript only.
5. No Godot < 4.5 support.
6. No IDE/editor integration in v1 — CLI only.

## 8. Success Criteria

A successful v1.0 release is defined by:

- **PyPI publish.** The package is published to PyPI and installable via `pip install gd-tools-cli`. This is the primary release gate — the product is not "released" until it is on PyPI and a clean-environment install produces a working `gd-tools --version`.

Supporting success metrics (measured but not gating):
- All CLI commands (test, lint, format, coverage, init, doctor, config) functional end-to-end.
- gd-tools itself achieves ≥80% line coverage, ≥70% branch coverage.
- GitHub Actions CI pipeline completes in under 10 minutes.
- Install-to-first-run time under 2 minutes.
