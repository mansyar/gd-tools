<protect>

# Implementation Plan — coverage_autoload_fix

## Phase 1: Hybrid Exclude Matching (FR-1) [checkpoint: 06f391e]

- [x] Task: Read spec.md and workflow.md to align with current requirements and the TDD/verification protocol
- [x] Task: Write failing tests for hybrid exclude matching in `discover_gd_files` (Red) [5f0bcfe]
    - [x] Test bare-name exclude matches a directory basename at any depth (backward compat with `DEFAULT_EXCLUDES`)
    - [x] Test an entry containing `/` (e.g. `scripts/autoload`) excludes by path prefix relative to root
    - [x] Test cross-platform separators (`\` and `/` normalize equivalently)
- [x] Task: Implement hybrid exclude matching in `src/gd_tools/file_discovery.py` (Green) [5f0bcfe]
    - [x] Route entries containing a path separator to path-prefix filtering against each file's relative path
    - [x] Keep existing basename matching for bare entries
    - [x] Refactor and rerun tests to green
- [x] Task: Verify coverage for `file_discovery.py` (>80% line, >70% branch) [5f0bcfe]
- [x] Task: Conductor - User Manual Verification 'Phase 1 - Hybrid Exclude Matching' (Protocol in workflow.md) [06f391e]

## Phase 2: Autoload Auto-Exclusion (FR-2) [checkpoint: 5676d09]

- [x] Task: Read spec.md and workflow.md to align with current requirements and the TDD/verification protocol
- [x] Task: Write failing tests for `project.godot` `[autoload]` parsing & exclusion (Red) [d4c3215]
    - [x] Test parsing `[autoload]` entries from a fixture `project.godot`
    - [x] Test resolving autoload paths (strip leading `*`, normalize `res://` → relative path)
    - [x] Test autoload scripts are excluded from the generated `CoveragePlan`
    - [x] Test missing/empty `[autoload]` section handled gracefully (no crash)
- [x] Task: Implement autoload auto-exclusion in `src/gd_tools/coverage/plan_generator.py` (Green) [d4c3215]
    - [x] Add a helper to read `project.godot` and resolve autoload script paths
    - [x] Filter discovered files against resolved autoload paths before building `FilePlan`s
- [x] Task: Verify coverage for `plan_generator.py` (>80% line, >70% branch) [d4c3215]
- [x] Task: Conductor - User Manual Verification 'Phase 2 - Autoload Auto-Exclusion' (Protocol in workflow.md) [5676d09]

## Phase 3: Harden pre_run_hook.gd (FR-3) [checkpoint: 0e5e86f]

- [x] Task: Read spec.md and workflow.md to align with current requirements and the TDD/verification protocol
- [x] Task: Write failing tests for `_instrument_file` hardening (Red) [10a4d2e]
    - [x] Test a script with active instances is skipped and a warning is logged (no `reload()` call)
    - [x] Test `source_code` is never mutated when the instance pre-check fails
    - [x] Test original `source_code` is restored on a `reload()` failure
- [x] Task: Implement hardening in the canonical `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd` (Green) [10a4d2e]
    - [x] Capture original `source_code` before any mutation
    - [x] Add an active-instance pre-check; skip + warn when instances exist
    - [x] Restore `script.source_code = original` in the `reload()` error path before returning
- [x] Task: Sync the spike copy (`spike/addons/gd-tools-coverage/pre_run_hook.gd`) if needed for integration testing [10a4d2e]
- [x] Task: Conductor - User Manual Verification 'Phase 3 - Harden pre_run_hook.gd' (Protocol in workflow.md) [0e5e86f]

## Phase 4: Multi-Path CLI (FR-4, FR-5, FR-6) [checkpoint: 5323308]

- [x] Task: Read spec.md and workflow.md to align with current requirements and the TDD/verification protocol
- [x] Task: Write failing tests for multi-path `lint` (Red) [0950afb]
    - [x] Test combined discovery across multiple paths into one deduplicated set
    - [x] Test default to `.` with no path args
- [x] Task: Implement multi-path `lint` (cli.py argument + `run_lint`) (Green) [0950afb]
    - [x] Change `lint` argument to accept zero or more paths (`nargs=-1`)
    - [x] `run_lint` / `discover_gd_files` accept multiple roots and deduplicate
- [x] Task: Write failing tests for multi-path `format` (Red) [0950afb]
    - [x] Test combined discovery across multiple paths, deduplicated
    - [x] Test default to `.` with no path args
- [x] Task: Implement multi-path `format` (cli.py argument + `run_format`) (Green) [0950afb]
    - [x] Change `format` argument to accept zero or more paths (`nargs=-1`)
    - [x] `run_format` accepts multiple roots and deduplicates
- [x] Task: Write failing tests for `test` paths filter (Red) [0950afb]
    - [x] Test `paths` arg overrides `config.test.test_dirs` for that invocation
    - [x] Test omitted `paths` uses config (unchanged behavior)
- [x] Task: Implement `test` paths filter (cli.py argument + `run_tests`/`build_gut_args`) (Green) [0950afb]
    - [x] Add optional `paths` positional argument to the `test` command
    - [x] Wire paths through to GUT selection args when provided
- [x] Task: Verify coverage for changed CLI/runner modules (>80% line, >70% branch) [0950afb]
- [x] Task: Conductor - User Manual Verification 'Phase 4 - Multi-Path CLI' (Protocol in workflow.md) [5323308]

## Phase 5: Documentation & Final Verification

- [ ] Task: Read spec.md and workflow.md to align with current requirements and the TDD/verification protocol
- [ ] Task: Update `docs/USER_GUIDE.md` with multi-path CLI usage examples (lint/format/test)
- [ ] Task: Run full test suite with coverage (`CI=true pytest --cov=gd_tools --cov-branch --cov-report=term-missing`)
- [ ] Task: Run lint + format checks on all changed code (`ruff check src/ tests/` && `black --check src/ tests/`)
- [ ] Task: Conductor - User Manual Verification 'Phase 5 - Documentation & Final Verification' (Protocol in workflow.md)

</protect>
