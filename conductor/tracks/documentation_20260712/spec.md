# Specification: Track 16 — Documentation

## Overview

This track delivers the complete documentation set for `gd-tools` v1.0, aligned with Phase 4 (Polish & Release) of the product roadmap. The project currently has a minimal 33-line README.md placeholder and comprehensive internal docs (PRD.md, ROADMAP.md, TESTING_STRATEGY.md, TDD.md, SPIKE_coverage_instrumentation.md), but lacks user-facing documentation, a contributing guide, and standalone architecture documentation.

The deliverables are:
1. **README.md** — Expanded from placeholder to full project README for PyPI and GitHub.
2. **docs/USER_GUIDE.md** — Unified user guide with CLI reference for all 6 commands.
3. **docs/CONTRIBUTING.md** — Contributor onboarding guide.
4. **docs/ARCHITECTURE.md** — Standalone architecture document for the coverage system.

**Approach:** Additive only — existing docs (PRD.md, ROADMAP.md, TESTING_STRATEGY.md, TDD.md, SPIKE_*.md) are not modified. New files sit alongside them in `docs/`.

---

## Functional Requirements

### FR-1: README.md Expansion

Expand the existing 33-line README.md into a full project README suitable for both PyPI (rendered as long_description) and GitHub.

**Required sections:**
- Project title and one-line tagline
- Feature overview (unified workflow, zero-friction bootstrap, coverage gap-filling, CI/CD friendly, standalone compatibility)
- Badges (CI status, code coverage, PyPI version, Python versions, Godot version)
- Installation instructions (`pip install gd-tools`)
- Quick start guide (install → `gd-tools init` → `gd-tools test` → `gd-tools test --coverage`)
- CLI command summary table (6 commands with one-line descriptions)
- Configuration overview (`gd-tools.toml` — single source of truth, link to user guide)
- Links to detailed documentation (User Guide, Contributing Guide, Architecture, PRD, Roadmap)
- License

**Constraints:**
- Must follow Product Guidelines §1 (prose & documentation style): technical, direct, active voice, em-dash asides.
- Must render correctly on PyPI (verify `long_description` in `pyproject.toml` points to README.md).
- ASCII-only output per Product Guidelines §7 (no emoji; use text symbols).

### FR-2: User Guide (docs/USER_GUIDE.md)

Create a new unified user guide covering all CLI commands with a narrative flow.

**Required sections:**
- **Getting Started:** Prerequisites (Python 3.10+, Godot 4.5+), installation, `gd-tools init` walkthrough.
- **Configuration:** `gd-tools.toml` reference — all sections (`[godot]`, `[test]`, `[lint]`, `[format]`, `[coverage]`), all keys, defaults, examples.
- **Command Reference:** One section per command, each with: description, usage syntax, flags table, examples, exit codes.
  - `gd-tools init` — project bootstrapping
  - `gd-tools doctor` — diagnostics
  - `gd-tools test` — GUT test runner (with `--coverage`, `--min`, `--suite`, `--test`, `--junit-xml`, `--no-exit-code`)
  - `gd-tools lint` — gdlint wrapper (with `--fix`, `--report-format`)
  - `gd-tools format` — gdformat wrapper (with `--check`, `--diff`)
  - `gd-tools coverage` — subcommands: `report`, `merge`, `show`
- **Examples:** Common workflows (first test run, CI/CD pipeline setup, coverage threshold enforcement, lint+format in CI).
- **Troubleshooting:** Common issues (Godot not found, GUT not installed, version mismatch, coverage not generating).

**Constraints:**
- All code examples use language tags (`bash`, `toml`, `gdscript`, `json`, `yaml`).
- All CLI commands and flags must match the actual implemented CLI (not aspirational).
- Link to PRD §5 for deep technical command surface details.

### FR-3: Contributing Guide (docs/CONTRIBUTING.md)

Create a new contributor onboarding guide.

**Required sections:**
- **Development Setup:** Clone, `pip install -e ".[dev]"`, `.env` configuration for Godot binary path.
- **Code Style:** `ruff` (lint), `black` (format), naming conventions table (from Product Guidelines §3), pre-commit checks.
- **Testing Requirements:** `pytest` with `CI=true`, coverage thresholds (>80% line, >70% branch), test file naming conventions, mocking guidelines.
- **PR Process:** Branch naming, commit message format (from workflow.md §Commit Guidelines), review checklist, CI checks.
- **Project Structure:** Source layout overview (`src/gd_tools/` modules, `tests/`, `docs/`, `conductor/`).
- **Debugging Tips:** Common development issues and how to resolve them.

**Constraints:**
- Reference (not duplicate) `workflow.md`, `TESTING_STRATEGY.md`, and `conductor/code_styleguides/`.
- Reference `docs/ARCHITECTURE.md` for contributors working on the coverage system.

### FR-4: Architecture Documentation (docs/ARCHITECTURE.md)

Create a new standalone architecture document focused on the coverage system (Architecture C — Hybrid).

**Required sections:**
- **Overview:** Why code coverage for GDScript is needed and unique to `gd-tools`.
- **Architecture C (Hybrid):** Explanation of the three-phase hybrid approach, comparison with alternatives (Architecture A — Pure Python, Architecture B — Fork), why C was chosen.
- **Full Flow:** End-to-end diagram of `gd-tools test --coverage` — Python plan generation → GDScript runtime instrumentation → Python reporting. ASCII diagram within 80 columns.
- **Data Formats:** Instrumentation plan JSON schema, coverage data JSON schema, with field descriptions.
- **Component Details:** Brief description of each module:
  - `coverage/plan_generator.py` — Lark AST traversal, line/branch identification
  - `addons/gd-tools-coverage/coverage.gd` — Tracker autoload singleton
  - `addons/gd-tools-coverage/pre_run_hook.gd` — Source instrumentation + reload
  - `addons/gd-tools-coverage/post_run_hook.gd` — Coverage data serialization
  - `coverage/reporter.py` — Report orchestration (HTML, LCOV, Cobertura, terminal)
- **Design Decisions:** Key choices (bottom-to-top injection, env var activation, source restoration approach).

**Constraints:**
- Complement (not duplicate) PRD §10 — link to PRD for full specification details.
- ASCII diagrams within 80-column width where possible.
- Focus on the coverage system; general CLI architecture is covered in PRD §4.

---

## Non-Functional Requirements

- **NFR-1:** All documentation follows Product Guidelines §1 (prose & documentation style): technical, direct, active voice, em-dash asides, numbered sections, tables for structured data, short paragraphs.
- **NFR-2:** All code examples use proper Markdown language tags.
- **NFR-3:** All internal links use relative paths (e.g., `./USER_GUIDE.md`, `../docs/PRD.md`).
- **NFR-4:** Documentation is ASCII-only — no emoji (per Product Guidelines §7).
- **NFR-5:** All CLI commands, flags, and config keys documented match the actual implementation (verified against source code, not PRD aspirational content).
- **NFR-6:** Documentation is additive — existing docs are not modified.

---

## Acceptance Criteria

- **AC-1:** README.md renders correctly on GitHub and PyPI, includes all required sections (FR-1).
- **AC-2:** User Guide covers all 6 CLI commands with usage syntax, flags tables, and at least one example each (FR-2).
- **AC-3:** Contributing Guide covers development setup, code style, testing requirements, and PR process (FR-3).
- **AC-4:** Architecture Document explains Architecture C with flow diagrams and data format schemas (FR-4).
- **AC-5:** All documentation follows Product Guidelines prose style — technical, direct, active voice (NFR-1).
- **AC-6:** All internal links resolve correctly — no broken links between docs (NFR-3).
- **AC-7:** All documented CLI commands and flags match the implemented CLI — verified against `src/gd_tools/cli.py` and command modules (NFR-5).
- **AC-8:** No existing documentation files are modified — diff shows only new files and the expanded README.md (NFR-6).

---

## Out of Scope

- Documentation site generation (mkdocs, Sphinx) — deferred to post-v1.
- Python API reference (autodoc) — not needed for v1 CLI-only product.
- Internationalization / translations.
- Video tutorials or interactive demos.
- Modifying existing docs (PRD.md, ROADMAP.md, TESTING_STRATEGY.md, TDD.md, SPIKE_*.md).
- CHANGELOG.md — can be added in Track 17 (PyPI Release).
- pyproject.toml `long_description` configuration changes — verify only, do not restructure.
