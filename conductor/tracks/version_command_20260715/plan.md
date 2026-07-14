<protect>
# Implementation Plan: Track 24 — Version Command

## Phase 1: Version Detection Module (`version.py`)

- [x] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocol
- [x] Task: Write unit tests for `collect_versions()` function
    - [x] Test all 5 components found (happy path) — gd-tools, Godot, GUT, gdtoolkit, Python all return version strings
    - [x] Test Godot not found — `find_godot()` raises `GodotNotFoundError`, result has `godot: None`
    - [x] Test GUT not installed — no project root found or no `addons/gut/plugin.cfg`, result has `gut: None`
    - [x] Test gdtoolkit not installed — `importlib.metadata.PackageNotFoundError` raised, result has `gdtoolkit: None`
    - [x] Test return structure — dict with exactly 5 keys: `gd-tools`, `godot`, `gut`, `gdtoolkit`, `python`; missing components are `None`
- [x] Task: Implement `collect_versions()` in `src/gd_tools/version.py`
    - [x] Implement gd-tools version detection — return `__version__` from `gd_tools`
    - [x] Implement Godot version detection — call `find_godot()` with default `GodotConfig(binary=None)`, catch `GodotNotFoundError` and return `None`
    - [x] Implement GUT version detection — call `find_project_root()`, then `get_installed_gut_version(project_root)`, catch exceptions and return `None`
    - [x] Implement gdtoolkit version detection — use `importlib.metadata.version("gdtoolkit")`, catch `PackageNotFoundError` and return `None`
    - [x] Implement Python version detection — return `sys.version`
    - [x] Return `dict[str, str | None]` with all 5 keys
    - Commit: `6f8803e`
- [x] Task: Conductor - User Manual Verification 'Version Detection Module' (Protocol in workflow.md)
    - [checkpoint: 4ffab4c]

## Phase 2: CLI Command Integration (`cli.py`)

- [ ] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocol
- [ ] Task: Write unit tests for `version` Click command
    - [ ] Test default table output — Rich table rendered with 5 component rows
    - [ ] Test `--json` flag output — valid JSON, flat object keyed by component name, `null` for missing
    - [ ] Test exit code is always 0 — even when components are missing
    - [ ] Test missing components display — "not detected" for Godot, "not installed" for GUT/gdtoolkit
- [ ] Task: Implement `version` command in `src/gd_tools/cli.py`
    - [ ] Add `@cli.command()` for `version` with `--json` flag option
    - [ ] Call `collect_versions()` and render Rich table by default (Component, Version columns)
    - [ ] Output JSON via `click.echo(json.dumps(...))` when `--json` flag is set
    - [ ] Ensure exit code 0 always (no `ctx.exit(1)` paths)
- [ ] Task: Conductor - User Manual Verification 'CLI Command Integration' (Protocol in workflow.md)

## Phase 3: Documentation & Final Verification

- [ ] Task: Read `spec.md` and `workflow.md` to review requirements and workflow protocol
- [ ] Task: Update documentation
    - [ ] Add `version` command to README command list (if a command list exists)
    - [ ] Add `version` command section to USER_GUIDE (if it exists)
- [ ] Task: Run full test suite and verify all acceptance criteria
    - [ ] Run `CI=true pytest` and confirm all tests pass
    - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/` — no errors
    - [ ] Run `pytest --cov=gd_tools --cov-branch --cov-report=term-missing` — verify >80% line, >70% branch for `version.py`
- [ ] Task: Conductor - User Manual Verification 'Documentation & Final Verification' (Protocol in workflow.md)
</protect>
