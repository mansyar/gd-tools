# Specification: Smart Backup of Coverage Addon Files Before Overwrite

## Overview

When `gd-tools init` is re-run on an existing project, `install_coverage_addon` blindly overwrites all coverage addon files (`coverage.gd`, `pre_run_hook.gd`, `post_run_hook.gd`) using `shutil.copy2`. If a user has customized any of these files, their modifications are silently destroyed with no backup, no warning, and no recovery path.

This track implements a **smart backup** mechanism: before overwriting each file, compare the existing file's content to the bundled version. If they differ (indicating user modification), create a backup copy in a `.backups/` subdirectory before proceeding with the overwrite.

## Background

The current implementation in `src/gd_tools/init.py` (`install_coverage_addon`, line 326):

```python
COVERAGE_ADDON_FILES = [
    "coverage.gd",
    "pre_run_hook.gd",
    "post_run_hook.gd",
]

def install_coverage_addon(project_root: Path) -> None:
    """...Always overwrites existing files..."""
    source_dir = Path(__file__).parent / "addons" / "gd-tools-coverage"
    target_dir = project_root / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True, exist_ok=True)
    for gd_file in COVERAGE_ADDON_FILES:
        shutil.copy2(source_dir / gd_file, target_dir / gd_file)
```

`shutil.copy2` performs a blind overwrite — no comparison, no backup, no warning.

## Functional Requirements

### FR1: Smart Backup Before Overwrite
Before overwriting each file in `COVERAGE_ADDON_FILES`, the function must:
1. Check if the target file exists.
2. If it exists, compare its content (byte-level) to the bundled source file.
3. If the content differs, copy the existing file to `addons/gd-tools-coverage/.backups/<filename>.bak`.
4. Proceed with the overwrite (copy bundled version to target).

### FR2: Backup Directory Creation
The `.backups/` subdirectory (`addons/gd-tools-coverage/.backups/`) must be created automatically if it does not exist.

### FR3: User Notification
When a backup is created, print a warning to the user (via `rich` console, yellow color) indicating:
- Which file was backed up
- The backup location

### FR4: No Backup for Unchanged Files
If the existing file content is identical to the bundled version, no backup is created. The overwrite still proceeds (idempotent, no user-visible effect).

## Non-Functional Requirements

### NFR1: Performance
File comparison is a simple byte-level read + compare. Negligible overhead for 3 small GDScript files.

### NFR2: Backward Compatibility
- First-time install (no existing files): behavior unchanged — files are copied directly.
- Re-init with unmodified files: behavior unchanged — no backups created, files overwritten silently.
- Re-init with modified files: backup created before overwrite.

## Acceptance Criteria

1. **AC1**: When re-running `gd-tools init` on a project with unmodified addon files, no `.bak` files are created.
2. **AC2**: When re-running `gd-tools init` on a project where `pre_run_hook.gd` has been modified by the user, a backup is created at `addons/gd-tools-coverage/.backups/pre_run_hook.gd.bak` containing the user's modified version, and the file is then overwritten with the bundled version.
3. **AC3**: Same as AC2 for `post_run_hook.gd` and `coverage.gd`.
4. **AC4**: The user sees a yellow warning message naming the backed-up file and its backup location.
5. **AC5**: First-time install (no existing addon files) produces no backups and no warnings — behavior is identical to current.
6. **AC6**: The `.backups/` directory is created automatically if it does not exist.

## Out of Scope

- Timestamped backups (preserving backup history across multiple re-inits) — a simple `.bak` is sufficient for v1.
- Adding `.backups/` to `.gitignore` — user can manage this themselves.
- Backup behavior for other init-managed files (`.gutconfig.json`, `gdlintrc`, `gdformatrc`) — those already have their own protection logic.
- Checksum-based detection of "unmodified stock vs user-modified" — simple content comparison is sufficient.
