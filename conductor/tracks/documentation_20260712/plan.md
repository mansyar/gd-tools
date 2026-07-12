<protect>
# Implementation Plan: Track 16 — Documentation

## Phase 1: CLI Implementation Research

- [x] Task: Read `spec.md` and `workflow.md` before starting phase implementation
- [x] Task: Audit actual CLI implementation against PRD
    - [x] Read `src/gd_tools/cli.py` to extract command structure and all flags
    - [x] Read `src/gd_tools/init.py` for actual init behavior and flags
    - [x] Read `src/gd_tools/doctor.py` for actual doctor checks and output
    - [x] Read `src/gd_tools/test_runner.py` for actual test command flags and behavior
    - [x] Read `src/gd_tools/lint_runner.py` for actual lint command flags and behavior
    - [x] Read `src/gd_tools/format_runner.py` for actual format command flags and behavior
    - [x] Read `src/gd_tools/coverage/orchestrator.py` for actual coverage subcommands and flags
    - [x] Read `src/gd_tools/config.py` to verify config model sections and keys
    - [x] Document any discrepancies between PRD §5/§6 and actual implementation
- [x] Task: Conductor - User Manual Verification 'CLI Implementation Research' (Protocol in workflow.md)
    - Checkpoint SHA: 6dc7ae1

## Phase 2: README.md Expansion (FR-1)

- [x] Task: Read `spec.md` and `workflow.md` before starting phase implementation
- [x] Task: Expand README.md from 33-line placeholder to full project README
    - [x] Write project title, one-line tagline, and feature overview
    - [x] Add badges section (CI status, code coverage, PyPI version, Python versions, Godot version)
    - [x] Write installation instructions (`pip install gd-tools`)
    - [x] Write quick start guide (install → `gd-tools init` → `gd-tools test` → `gd-tools test --coverage`)
    - [x] Add CLI command summary table (6 commands with one-line descriptions)
    - [x] Add configuration overview (`gd-tools.toml` single source of truth, link to user guide)
    - [x] Add links to detailed documentation (User Guide, Contributing Guide, Architecture, PRD, Roadmap)
    - [x] Add license section
    - [x] Verify `pyproject.toml` `long_description` configuration points to README.md
- [x] Task: Conductor - User Manual Verification 'README.md Expansion' (Protocol in workflow.md)
    - Checkpoint SHA: fde2d5c

## Phase 3: User Guide (FR-2)

- [x] Task: Read `spec.md` and `workflow.md` before starting phase implementation
- [x] Task: Create `docs/USER_GUIDE.md` — unified user guide with CLI reference (abda758)
    - [x] Write Getting Started section (prerequisites: Python 3.10+, Godot 4.5+; installation; `gd-tools init` walkthrough)
    - [x] Write Configuration reference section (`gd-tools.toml` — all sections: `[godot]`, `[test]`, `[lint]`, `[format]`, `[coverage]`; all keys, defaults, examples)
    - [x] Write Command Reference: `gd-tools init` (description, usage, flags, examples, exit codes)
    - [x] Write Command Reference: `gd-tools doctor` (description, usage, checks table, examples, exit codes)
    - [x] Write Command Reference: `gd-tools test` (description, usage, flags table, `--coverage` workflow, examples, exit codes)
    - [x] Write Command Reference: `gd-tools lint` (description, usage, flags, `--report-format`, examples, exit codes)
    - [x] Write Command Reference: `gd-tools format` (description, usage, `--check`, `--diff`, examples, exit codes)
    - [x] Write Command Reference: `gd-tools coverage` (subcommands: `report`, `merge`, `show`; flags, examples, exit codes)
    - [x] Write Examples section (first test run, CI/CD pipeline setup, coverage threshold enforcement, lint+format in CI)
    - [x] Write Troubleshooting section (Godot not found, GUT not installed, version mismatch, coverage not generating)
- [x] Task: Conductor - User Manual Verification 'User Guide' (Protocol in workflow.md)
    - Checkpoint SHA: 96444b4

## Phase 4: Contributing Guide (FR-3)

- [x] Task: Read `spec.md` and `workflow.md` before starting phase implementation
- [x] Task: Create `docs/CONTRIBUTING.md` — contributor onboarding guide (24f62cd)
    - [x] Write Development Setup section (clone, `pip install -e ".[dev]"`, `.env` configuration for Godot binary)
    - [x] Write Code Style section (`ruff` lint, `black` format, naming conventions table from Product Guidelines §3, pre-commit checks)
    - [x] Write Testing Requirements section (`pytest` with `CI=true`, coverage thresholds >80% line / >70% branch, test file naming, mocking guidelines)
    - [x] Write PR Process section (branch naming, commit message format from workflow.md, review checklist, CI checks)
    - [x] Write Project Structure section (`src/gd_tools/` module overview, `tests/`, `docs/`, `conductor/`)
    - [x] Write Debugging Tips section (common development issues and resolutions)
- [x] Task: Conductor - User Manual Verification 'Contributing Guide' (Protocol in workflow.md)
    - Checkpoint SHA: 4348571

## Phase 5: Architecture Documentation (FR-4)

- [x] Task: Read `spec.md` and `workflow.md` before starting phase implementation
- [x] Task: Create `docs/ARCHITECTURE.md` — standalone coverage system architecture document (c7324b9)
    - [x] Write Overview section (why GDScript coverage is needed, unique to `gd-tools`)
    - [x] Write Architecture C (Hybrid) section (three-phase approach, comparison with Architecture A/B, why C was chosen)
    - [x] Write Full Flow section (end-to-end ASCII diagram of `gd-tools test --coverage`, 80-column width)
    - [x] Write Data Formats section (instrumentation plan JSON schema, coverage data JSON schema, field descriptions)
    - [x] Write Component Details section (plan_generator.py, coverage.gd, pre_run_hook.gd, post_run_hook.gd, reporter.py)
    - [x] Write Design Decisions section (bottom-to-top injection, env var activation, source restoration approach)
- [~] Task: Conductor - User Manual Verification 'Architecture Documentation' (Protocol in workflow.md)

## Phase 6: Final Verification

- [ ] Task: Read `spec.md` and `workflow.md` before starting phase implementation
- [ ] Task: Cross-document verification and polish
    - [ ] Verify all internal links resolve correctly — no broken links between docs (AC-6)
    - [ ] Verify all CLI commands and flags match the implemented CLI — cross-check against source code (AC-7)
    - [ ] Verify prose style compliance with Product Guidelines §1 — technical, direct, active voice (AC-5)
    - [ ] Verify ASCII-only — no emoji in any documentation file (NFR-4)
    - [ ] Verify no existing documentation files were modified — `git diff --name-only` check (AC-8)
    - [ ] Run existing test suite (`CI=true pytest`) to ensure no regressions from documentation changes
- [ ] Task: Conductor - User Manual Verification 'Final Verification' (Protocol in workflow.md)
</protect>
