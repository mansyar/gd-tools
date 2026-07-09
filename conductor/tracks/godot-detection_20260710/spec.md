# Track 3: Godot Binary Detection

## Overview

Implement the Godot binary detection and invocation module (`src/gd_tools/godot.py`) that resolves the Godot binary path via a 5-level priority chain, detects and validates the Godot version, maps Godot versions to compatible GUT versions, and provides a subprocess wrapper for invoking Godot.

This module is a foundational dependency for Track 6 (Test Runner) and Track 7 (Init Command). Only `gd-tools test` and `gd-tools init` require the Godot binary; `gd-tools lint`, `gd-tools format`, and `gd-tools coverage` use gdtoolkit (pure Python) and do not invoke Godot.

## Design Decisions

1. **Return Type:** The main detection function `find_godot()` returns a `GodotInfo` dataclass (path, version, is_valid) — not a bare string. This gives callers (init, doctor) both path and version in one call.
2. **GUT Version Mapping:** `GUT_VERSION_MAP` and `get_gut_version_for_godot()` are included in this track, as the TDD §3.3 places them in `godot.py` and they are logically tied to Godot version detection.
3. **run_godot() Wrapper:** The `run_godot()` subprocess wrapper is included in this track, as the TDD §3.3 places it in `godot.py` and having it early means Track 6 can simply call it.
4. **Configurable Search Paths:** Core common locations are hardcoded per OS, plus users can add custom search paths via `gd-tools.toml` `[godot].search_paths`. This requires extending the existing `GodotConfig` model with a `search_paths` field.

## Functional Requirements

### FR-1: Godot Binary Resolution Chain

The function `find_godot(config: GodotConfig) -> GodotInfo` resolves the Godot binary via a 5-level priority chain (first match wins):

1. **Config:** `config.godot.binary` — user-specified path in `gd-tools.toml` (highest priority)
2. **Environment variables:** `GODOT_BIN` → `GODOT4_BIN` → `GODOT_PATH` (checked in order)
3. **PATH lookup:** `shutil.which("godot")` → `shutil.which("godot4")`
4. **Common install locations** (platform-specific, hardcoded core paths + user-configured `search_paths`):
   - **Windows:** `C:\Program Files\Godot\`, `%LOCALAPPDATA%\Godot\`
   - **macOS:** `/Applications/Godot.app/Contents/MacOS/Godot`, `/opt/homebrew/bin/godot`
   - **Linux:** `~/.local/bin/godot`, `/usr/bin/godot`, `/usr/local/bin/godot`
   - **User-configured:** Any paths in `config.godot.search_paths` (checked after hardcoded locations)
5. **Not found** → `GodotNotFoundError` with platform-specific install instructions

Internal helper functions (private):
- `_check_config(config: GodotConfig) -> str | None`
- `_check_env_vars() -> str | None`
- `_check_path() -> str | None`
- `_check_common_locations(config: GodotConfig) -> str | None`

Each candidate path must be verified to exist and be executable before being returned.

### FR-2: GodotInfo Dataclass

```python
@dataclass
class GodotInfo:
    path: str          # Resolved binary path
    version: str       # Parsed version string (e.g., "4.5.1")
    is_valid: bool     # True if version >= 4.5.0
```

`find_godot()` returns a fully populated `GodotInfo`. If the binary is found but version detection fails, `version` is set to `"unknown"` and `is_valid` is `False`.

### FR-3: Version Detection

`get_godot_version(binary: str) -> str` runs `godot --version` and parses the output.

- Input examples: `4.5.1-stable`, `4.6-dev`, `4.7`, `4.5.stable.linux`
- Output: normalized `major.minor.patch` string (e.g., `4.5.1`, `4.6.0`, `4.7.0`)
- Strips suffixes like `-stable`, `-dev`, `.linux`, `.win64`
- If patch is missing, defaults to `.0`
- Raises `GodotNotFoundError` if the binary fails to run or produces unparseable output

### FR-4: Version Validation

`check_version_compatible(version: str) -> bool` returns `True` if the parsed version is >= 4.5.0.

- `4.5.0` → `True`
- `4.4.3` → `False`
- `4.6.1` → `True`
- `4.7.0` → `True`

### FR-5: GUT Version Mapping

```python
GUT_VERSION_MAP = {
    "4.5": "9.5.0",
    "4.6": "9.6.0",
    "4.7": "9.7.0",
}
```

`get_gut_version_for_godot(godot_version: str) -> str` maps a Godot version to its compatible GUT version.
- Uses `major.minor` prefix (e.g., `4.5.1` → `4.5` → `9.5.0`)
- Raises `ConfigError` if the Godot version is not in the map

### FR-6: Godot Invocation Wrapper

```python
def run_godot(
    binary: str,
    project_path: Path,
    args: list[str],
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess
```

- Sets `--path` to `project_path`
- Merges `env` with current `os.environ` (caller values take precedence)
- Returns `subprocess.CompletedProcess`
- Raises `subprocess.TimeoutExpired` if `timeout` is exceeded
- Uses `subprocess.run` with `capture_output=True, text=True`

### FR-7: Config Extension

Extend the existing `GodotConfig` model in `config.py` with a `search_paths` field:

```python
class GodotConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    binary: str | None = None
    search_paths: list[str] = Field(default_factory=list)  # NEW: custom Godot search paths
```

This is a backward-compatible change — `search_paths` defaults to an empty list.

## Non-Functional Requirements

### NFR-1: Cross-Platform Support
- Must work on Windows, macOS, and Linux
- Path handling must use `pathlib.Path` or `os.path` for OS-agnostic path construction
- Platform detection via `sys.platform` (e.g., `win32`, `darwin`, `linux`)

### NFR-2: Testability
- All unit tests must mock `shutil.which`, `os.environ`, `subprocess.run`, and `sys.platform`
- No unit test may invoke the real Godot binary
- Tests must use `@pytest.mark.unit` marker
- Test file: `tests/unit/test_godot.py`

### NFR-3: Error Messages
- `GodotNotFoundError` message must include:
  - Which resolution methods were tried
  - Platform-specific install instructions (download URL, package manager commands)
  - How to configure via `gd-tools.toml` or environment variables

## Acceptance Criteria

1. `find_godot()` returns a `GodotInfo` with correct path when `GODOT_BIN` env var is set
2. `find_godot()` returns a `GodotInfo` with correct path when `config.godot.binary` is set in `gd-tools.toml`
3. PATH lookup finds `godot` or `godot4` when available via `shutil.which`
4. Platform-specific common locations are checked on the respective OS
5. User-configured `search_paths` are checked after hardcoded locations
6. `GodotNotFoundError` is raised with platform-specific install instructions when no binary is found
7. Version parsing handles `4.5.1-stable`, `4.6-dev`, `4.7`, `4.5.stable.linux` formats
8. `check_version_compatible()` returns `False` for versions < 4.5.0
9. `get_gut_version_for_godot()` maps `4.5.1` → `9.5.0`, `4.6.0` → `9.6.0`
10. `get_gut_version_for_godot()` raises `ConfigError` for unmapped versions (e.g., `4.4.0`)
11. `run_godot()` passes `--path` and args correctly to `subprocess.run`
12. `run_godot()` raises `subprocess.TimeoutExpired` when timeout is exceeded
13. `GodotConfig` accepts `search_paths` as a list of strings
14. Line coverage > 80%, branch coverage > 70% for `godot.py`

## Out of Scope

- GUT installation logic (Track 7: Init Command)
- Test runner orchestration (Track 6: Test Runner)
- Doctor command health checks (Track 8)
- CLI command wiring (Track 1 stubs exist; full wiring in later tracks)
- Scoop/Chocolatey/Steam path detection (users can add these via `search_paths` if needed)
