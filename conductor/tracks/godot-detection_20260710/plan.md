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

## Phase 2: Binary Detection Chain [checkpoint: 8c649b0]

- [x] Task: Read `spec.md` and `workflow.md` before starting this phase
- [x] Task: Write tests for `_check_config()`
    - [x] Test returns path when `config.godot.binary` is set and file exists
    - [x] Test returns `None` when `config.godot.binary` is `None`
    - [x] Test returns `None` when configured path doesn't exist on disk
- [x] Task: Implement `_check_config()`
- [x] Task: Write tests for `_check_env_vars()`
    - [x] Test `GODOT_BIN` is checked first and returned if set
    - [x] Test `GODOT4_BIN` is checked when `GODOT_BIN` not set
    - [x] Test `GODOT_PATH` is checked when first two not set
    - [x] Test returns `None` when no env vars are set
- [x] Task: Implement `_check_env_vars()`
- [x] Task: Write tests for `_check_path()`
    - [x] Test `shutil.which("godot")` is checked first
    - [x] Test `shutil.which("godot4")` is checked as fallback
    - [x] Test returns `None` when neither is found
- [x] Task: Implement `_check_path()`
- [x] Task: Write tests for `_check_common_locations()`
    - [x] Test Windows locations checked on `win32` platform
    - [x] Test macOS locations checked on `darwin` platform
    - [x] Test Linux locations checked on `linux` platform
    - [x] Test returns `None` when no locations match
- [x] Task: Implement `_check_common_locations()`
- [x] Task: Write tests for `find_godot()`
    - [x] Test config takes priority over env vars
    - [x] Test env vars take priority over PATH
    - [x] Test PATH takes priority over common locations
    - [x] Test `GodotNotFoundError` raised with install instructions when nothing found
    - [x] Test returns `GodotInfo` with correct path, version, and `is_valid`
- [x] Task: Implement `find_godot()` [f238796]
- [x] Task: Conductor - User Manual Verification 'Binary Detection Chain' (Protocol in workflow.md)

## Phase 3: Version Detection, Validation & GUT Mapping [checkpoint: 44851d9]

- [x] Task: Read `spec.md` and `workflow.md` before starting this phase
- [x] Task: Write tests for `get_godot_version()` [f238796]
    - [x] Test parsing `"4.5.1-stable"` → `"4.5.1"`
    - [x] Test parsing `"4.6-dev"` → `"4.6.0"`
    - [x] Test parsing `"4.7"` → `"4.7.0"`
    - [x] Test parsing `"4.5.stable.linux"` → `"4.5.0"`
    - [x] Test raises `GodotNotFoundError` on unparseable output
    - [x] Test raises `GodotNotFoundError` on subprocess failure
- [x] Task: Implement `get_godot_version()` [f238796]
- [x] Task: Write tests for `check_version_compatible()` [f238796]
    - [x] Test `"4.5.0"` → `True`
    - [x] Test `"4.4.3"` → `False`
    - [x] Test `"4.6.1"` → `True`
    - [x] Test `"4.7.0"` → `True`
- [x] Task: Implement `check_version_compatible()` [f238796]
- [x] Task: Write tests for `GUT_VERSION_MAP` and `get_gut_version_for_godot()` [663ab22]
    - [x] Test `"4.5.1"` → `"9.5.0"`
    - [x] Test `"4.6.0"` → `"9.6.0"`
    - [x] Test `"4.7.0"` → `"9.7.0"`
    - [x] Test raises `ConfigError` for unmapped version (e.g., `"4.4.0"`)
- [x] Task: Implement `GUT_VERSION_MAP` and `get_gut_version_for_godot()` [663ab22]
- [x] Task: Conductor - User Manual Verification 'Version Detection, Validation & GUT Mapping' (Protocol in workflow.md)

## Phase 4: Godot Invocation Wrapper

- [x] Task: Read `spec.md` and `workflow.md` before starting this phase
- [x] Task: Write tests for `run_godot()` [3a8a99f]
    - [x] Test passes `--path` and args correctly to `subprocess.run`
    - [x] Test merges `env` with `os.environ` (caller values take precedence)
    - [x] Test uses `capture_output=True, text=True`
    - [x] Test raises `subprocess.TimeoutExpired` when timeout exceeded
    - [x] Test returns `subprocess.CompletedProcess`
- [x] Task: Implement `run_godot()` [3a8a99f]
- [ ] Task: Conductor - User Manual Verification 'Godot Invocation Wrapper' (Protocol in workflow.md)
</protect>
