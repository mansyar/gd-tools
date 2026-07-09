<protect>
# Implementation Plan: Track 3 — Godot Binary Detection

## Phase 1: Module Foundation [checkpoint: ccc8761]

- [x] Task: Read `spec.md` and `workflow.md` before starting this phase
- [x] Task: Write tests for `GodotInfo` dataclass [4b312d8]
    - [x] Test `GodotInfo` construction with valid path, version, `is_valid=True`
    - [x] Test `GodotInfo` with `version="unknown"`, `is_valid=False`
- [x] Task: Implement `GodotInfo` dataclass and module skeleton [4b312d8]
    - [x] Create `src/gd_tools/godot.py`
    - [x] Define `GodotInfo` dataclass with `path: str`, `version: str`, `is_valid: bool`
    - [x] Add module docstring and imports
- [ ] Task: Conductor - User Manual Verification 'Module Foundation' (Protocol in workflow.md)

## Phase 2: Binary Detection Chain

- [ ] Task: Read `spec.md` and `workflow.md` before starting this phase
- [ ] Task: Write tests for `_check_config()`
    - [ ] Test returns path when `config.godot.binary` is set and file exists
    - [ ] Test returns `None` when `config.godot.binary` is `None`
    - [ ] Test returns `None` when configured path doesn't exist on disk
- [ ] Task: Implement `_check_config()`
- [ ] Task: Write tests for `_check_env_vars()`
    - [ ] Test `GODOT_BIN` is checked first and returned if set
    - [ ] Test `GODOT4_BIN` is checked when `GODOT_BIN` not set
    - [ ] Test `GODOT_PATH` is checked when first two not set
    - [ ] Test returns `None` when no env vars are set
- [ ] Task: Implement `_check_env_vars()`
- [ ] Task: Write tests for `_check_path()`
    - [ ] Test `shutil.which("godot")` is checked first
    - [ ] Test `shutil.which("godot4")` is checked as fallback
    - [ ] Test returns `None` when neither is found
- [ ] Task: Implement `_check_path()`
- [ ] Task: Write tests for `_check_common_locations()`
    - [ ] Test Windows locations checked on `win32` platform
    - [ ] Test macOS locations checked on `darwin` platform
    - [ ] Test Linux locations checked on `linux` platform
    - [ ] Test returns `None` when no locations match
- [ ] Task: Implement `_check_common_locations()`
- [ ] Task: Write tests for `find_godot()`
    - [ ] Test config takes priority over env vars
    - [ ] Test env vars take priority over PATH
    - [ ] Test PATH takes priority over common locations
    - [ ] Test `GodotNotFoundError` raised with install instructions when nothing found
    - [ ] Test returns `GodotInfo` with correct path, version, and `is_valid`
- [ ] Task: Implement `find_godot()`
- [ ] Task: Conductor - User Manual Verification 'Binary Detection Chain' (Protocol in workflow.md)

## Phase 3: Version Detection, Validation & GUT Mapping

- [ ] Task: Read `spec.md` and `workflow.md` before starting this phase
- [ ] Task: Write tests for `get_godot_version()`
    - [ ] Test parsing `"4.5.1-stable"` → `"4.5.1"`
    - [ ] Test parsing `"4.6-dev"` → `"4.6.0"`
    - [ ] Test parsing `"4.7"` → `"4.7.0"`
    - [ ] Test parsing `"4.5.stable.linux"` → `"4.5.0"`
    - [ ] Test raises `GodotNotFoundError` on unparseable output
    - [ ] Test raises `GodotNotFoundError` on subprocess failure
- [ ] Task: Implement `get_godot_version()`
- [ ] Task: Write tests for `check_version_compatible()`
    - [ ] Test `"4.5.0"` → `True`
    - [ ] Test `"4.4.3"` → `False`
    - [ ] Test `"4.6.1"` → `True`
    - [ ] Test `"4.7.0"` → `True`
- [ ] Task: Implement `check_version_compatible()`
- [ ] Task: Write tests for `GUT_VERSION_MAP` and `get_gut_version_for_godot()`
    - [ ] Test `"4.5.1"` → `"9.5.0"`
    - [ ] Test `"4.6.0"` → `"9.6.0"`
    - [ ] Test `"4.7.0"` → `"9.7.0"`
    - [ ] Test raises `ConfigError` for unmapped version (e.g., `"4.4.0"`)
- [ ] Task: Implement `GUT_VERSION_MAP` and `get_gut_version_for_godot()`
- [ ] Task: Conductor - User Manual Verification 'Version Detection, Validation & GUT Mapping' (Protocol in workflow.md)

## Phase 4: Godot Invocation Wrapper

- [ ] Task: Read `spec.md` and `workflow.md` before starting this phase
- [ ] Task: Write tests for `run_godot()`
    - [ ] Test passes `--path` and args correctly to `subprocess.run`
    - [ ] Test merges `env` with `os.environ` (caller values take precedence)
    - [ ] Test uses `capture_output=True, text=True`
    - [ ] Test raises `subprocess.TimeoutExpired` when timeout exceeded
    - [ ] Test returns `subprocess.CompletedProcess`
- [ ] Task: Implement `run_godot()`
- [ ] Task: Conductor - User Manual Verification 'Godot Invocation Wrapper' (Protocol in workflow.md)
</protect>
