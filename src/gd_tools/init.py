"""Initialize a Godot project for use with gd-tools.

This module implements the ``gd-tools init`` command, which bootstraps
a Godot project by:
- Detecting the project root and Godot version
- Deploying the bundled native test and coverage addons
- Creating native/default configuration files
- Creating the ``.gd-tools/`` data directory
- Printing a summary of actions taken

The command is idempotent: running it multiple times produces the
same end state without duplicating entries. Managed addon files preserve
user modifications in per-addon ``.backups/`` directories before replacement.
"""

import shutil
import sys
from pathlib import Path

from rich.console import Console

from .config import (
    GdToolsConfig,
    find_project_root,
    gdformatrc_content,
    gdlintrc_content,
    load_config,
    save_config,
)
from . import __version__
from . import output
from .godot import find_godot
from .verbosity import Verbosity, get_verbosity

# --- Constants ---

COVERAGE_ADDON_FILES = [
    "coverage.gd",
]

#: Files earlier versions deployed that gd-tools no longer ships. They
#: extended the GUT hook base class removed by the GUT-bridge removal, so
#: a stale copy in a project cannot work; ``init`` moves them aside and
#: reports the cleanup instead of leaving doctor to flag them forever.
REMOVED_COVERAGE_FILES = [
    "pre_run_hook.gd",
    "post_run_hook.gd",
]

NATIVE_TEST_ADDON_FILES = [
    "gd_tools_test.gd",
    "gd_tools_mock.gd",
    "gd_tools_parameter_naming.gd",
    "gd_tools_test_context.gd",
    "gd_tools_test_runner.gd",
    "gd_tools_test_preflight.gd",
    "gd_tools_native_coverage.gd",
    "gd_tools_snapshot_serializer.gd",
    "gd_tools_snapshot_store.gd",
]

EDITOR_PLUGIN_FILES = [
    "plugin.cfg",
    "plugin.gd",
    "dock.gd",
    "coverage_overlay.gd",
]

COVERAGE_AUTOLOAD_PATH = "res://addons/gd-tools-coverage/coverage.gd"

console = Console()


# --- Phase 1: Project Detection and Godot Version Detection ---


def detect_godot_version(config: GdToolsConfig) -> str:
    """Detect the Godot version using the config's Godot settings.

    Calls :func:`find_godot` to resolve the binary and parse its
    version. If the detected version is below 4.5.0, a warning is
    printed but the version is still returned.

    Args:
        config: The gd-tools configuration containing Godot settings.

    Returns:
        The detected Godot version string (e.g., ``"4.5.1"``).

    Raises:
        GodotNotFoundError: If the Godot binary cannot be found.
    """
    info = find_godot(config.godot)
    if not info.is_valid:
        console.print(
            "[yellow]Warning: Godot "
            f"{info.version} is below the required "
            "version 4.5.0. Some features may not "
            "work.[/yellow]"
        )
    return info.version


# --- Phase 3: Coverage Addon Deployment ---


def install_coverage_addon(project_root: Path) -> None:
    """Copy bundled coverage addon files to the project.

    Copies the GDScript files from the package data to
    ``project_root/addons/gd-tools-coverage/``. Always overwrites
    existing files to ensure they are up-to-date. If an existing file
    differs from the bundled version (indicating user modification),
    a backup copy is saved to ``addons/gd-tools-coverage/.backups/``
    before overwriting, and a yellow warning is printed. Files from
    earlier versions that gd-tools no longer deploys (see
    ``REMOVED_COVERAGE_FILES``) are backed up and removed. Also writes
    a ``_version.txt`` file stamping the deployed addon with the current
    package version.

    Args:
        project_root: Path to the Godot project root.
    """
    source_dir = Path(__file__).parent / "addons" / "gd-tools-coverage"
    target_dir = project_root / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = target_dir / ".backups"
    for gd_file in COVERAGE_ADDON_FILES:
        target_file = target_dir / gd_file
        source_file = source_dir / gd_file
        if target_file.exists():
            existing_bytes = target_file.read_bytes()
            bundled_bytes = source_file.read_bytes()
            if existing_bytes != bundled_bytes:
                backups_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backups_dir / f"{gd_file}.bak"
                shutil.copy2(target_file, backup_path)
                console.print(
                    f"[yellow]Warning: {gd_file} was modified. "
                    f"Backed up to {backup_path}"
                    f" before overwriting.[/yellow]"
                )
        shutil.copy2(source_file, target_file)
    _remove_stale_addon_files(target_dir, backups_dir)
    version_file = target_dir / "_version.txt"
    version_file.write_text(f"{__version__}\n", encoding="utf-8")


def _remove_stale_addon_files(target_dir: Path, backups_dir: Path) -> None:
    """Remove files gd-tools no longer deploys, backing each one up.

    A stale file cannot be byte-compared against a bundled version
    (none ships anymore), so any copy found is preserved in
    ``.backups/`` before deletion. Removing instead of ignoring keeps
    ``doctor``'s coverage-addon check meaningful for projects upgraded
    from older gd-tools releases.

    Args:
        target_dir: Addon directory to clean.
        backups_dir: Directory the removed files are backed up into.
    """
    for gd_file in REMOVED_COVERAGE_FILES:
        target_file = target_dir / gd_file
        if not target_file.exists():
            continue
        backups_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backups_dir / f"{gd_file}.bak"
        shutil.copy2(target_file, backup_path)
        target_file.unlink()
        console.print(
            f"[yellow]Removed {gd_file} (no longer part of gd-tools). "
            f"Backed up to {backup_path}[/yellow]"
        )


def install_native_test_addon(project_root: Path) -> None:
    """Copy the bundled native runtime with managed-file backups.

    Args:
        project_root: Path to the Godot project root.
    """
    source_dir = Path(__file__).parent / "addons" / "gd-tools-test"
    target_dir = project_root / "addons" / "gd-tools-test"
    target_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = target_dir / ".backups"
    for file_name in NATIVE_TEST_ADDON_FILES:
        source_file = source_dir / file_name
        target_file = target_dir / file_name
        if (
            target_file.exists()
            and target_file.read_bytes() != source_file.read_bytes()
        ):
            backups_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backups_dir / f"{file_name}.bak"
            shutil.copy2(target_file, backup_path)
            console.print(
                f"[yellow]Warning: {file_name} was modified. "
                f"Backed up to {backup_path} before overwriting.[/yellow]"
            )
        shutil.copy2(source_file, target_file)
    (target_dir / "_version.txt").write_text(
        f"{__version__}\n", encoding="utf-8"
    )


def install_editor_plugin(project_root: Path) -> None:
    """Copy the bundled editor plugin addon to the project.

    Deploys ``plugin.cfg``, ``plugin.gd``, ``dock.gd``, and
    ``coverage_overlay.gd`` from the package data to
    ``project_root/addons/gd-tools-editor/``. Existing files that
    differ from the bundled version are backed up to the per-addon
    ``.backups/`` directory before replacement, with a yellow
    warning printed. Writes a ``_version.txt`` stamp with the
    current package version.

    Args:
        project_root: Path to the Godot project root.
    """
    source_dir = Path(__file__).parent / "addons" / "gd-tools-editor"
    target_dir = project_root / "addons" / "gd-tools-editor"
    target_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = target_dir / ".backups"
    for file_name in EDITOR_PLUGIN_FILES:
        source_file = source_dir / file_name
        target_file = target_dir / file_name
        if (
            target_file.exists()
            and target_file.read_bytes() != source_file.read_bytes()
        ):
            backups_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backups_dir / f"{file_name}.bak"
            shutil.copy2(target_file, backup_path)
            console.print(
                f"[yellow]Warning: {file_name} was modified. "
                f"Backed up to {backup_path} before overwriting.[/yellow]"
            )
        shutil.copy2(source_file, target_file)
    (target_dir / "_version.txt").write_text(
        f"{__version__}\n", encoding="utf-8"
    )


def register_coverage_autoload(project_root: Path) -> None:
    """Register the coverage tracker autoload in ``project.godot``.

    Adds ``_GDTCoverage`` as the **first** entry in the ``[autoload]``
    section, pointing at ``res://addons/gd-tools-coverage/coverage.gd``.
    This ordering is critical: ``_GDTCoverage._ready()`` must run before
    any other autoload creates script instances, so instrumentation via
    ``reload()`` succeeds.

    If ``_GDTCoverage`` is already registered but not in position 0, it
    is moved to position 0 and a warning is printed to stderr.

    Idempotent: if ``_GDTCoverage`` is already the first autoload with
    the correct path, no changes are made.

    Args:
        project_root: Path to the Godot project root.
    """
    project_godot = project_root / "project.godot"
    content = project_godot.read_text(encoding="utf-8")

    autoload_entry = f'_GDTCoverage="*{COVERAGE_AUTOLOAD_PATH}"'
    lines = content.split("\n")

    # Find the [autoload] section header and its entries (in order).
    autoload_header_idx: int | None = None
    autoload_entries: list[tuple[int, str]] = []
    in_autoload = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_autoload = stripped == "[autoload]"
            if in_autoload:
                autoload_header_idx = i
            continue
        if in_autoload and stripped and "=" in stripped:
            autoload_entries.append((i, line))

    # Find _GDTCoverage among existing autoload entries.
    gdtc_entry_idx: int | None = None
    for idx, (_, line) in enumerate(autoload_entries):
        if line.strip().startswith("_GDTCoverage="):
            gdtc_entry_idx = idx
            break

    if gdtc_entry_idx is None:
        # _GDTCoverage not registered yet — prepend as first entry.
        if autoload_header_idx is not None:
            insert_at = autoload_header_idx + 1
            # Skip blank lines after header to find first entry position.
            while insert_at < len(lines) and lines[insert_at].strip() == "":
                insert_at += 1
            lines.insert(insert_at, autoload_entry)
            project_godot.write_text("\n".join(lines), encoding="utf-8")
        else:
            # No [autoload] section — create one.
            if not content.endswith("\n"):
                content += "\n"
            content += f"\n[autoload]\n\n{autoload_entry}\n"
            project_godot.write_text(content, encoding="utf-8")
        return

    # _GDTCoverage is already registered.
    gdtc_line_idx, gdtc_line = autoload_entries[gdtc_entry_idx]
    needs_write = False

    # Fix wrong path if needed.
    if gdtc_line.strip() != autoload_entry:
        lines[gdtc_line_idx] = autoload_entry
        needs_write = True

    # Check if _GDTCoverage is the first autoload entry.
    if gdtc_entry_idx == 0:
        if needs_write:
            project_godot.write_text("\n".join(lines), encoding="utf-8")
        return

    # Not first — move to position 0.
    lines.pop(gdtc_line_idx)
    assert autoload_header_idx is not None  # guaranteed: entries found
    insert_at = autoload_header_idx + 1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    lines.insert(insert_at, autoload_entry)
    project_godot.write_text("\n".join(lines), encoding="utf-8")

    print(
        "Moved _GDTCoverage to first autoload position "
        "for coverage to work correctly.",
        file=sys.stderr,
    )


# --- Phase 4: Configuration File Generation ---


def create_config_file(project_root: Path, config: GdToolsConfig) -> None:
    """Create ``gd-tools.toml`` if it does not exist.

    If the file already exists, it is preserved unchanged. If it
    does not exist, the provided config is written via
    :func:`save_config`.

    Args:
        project_root: Path to the Godot project root.
        config: The configuration to write if the file is missing.
    """
    config_file = project_root / "gd-tools.toml"
    if config_file.exists():
        return
    save_config(config, project_root)


def generate_lint_format_rcs(project_root: Path, config: GdToolsConfig) -> None:
    """Generate ``gdlintrc`` and ``gdformatrc`` if missing, warn if differs.

    For each file:
    - If the file does not exist: generate it from the config's
      exclude lists.
    - If the file exists but differs from what init would produce:
      print a warning. Do not overwrite.
    - If the file exists and matches: do nothing.

    Args:
        project_root: Path to the Godot project root.
        config: The configuration to read exclude lists from.
    """
    # gdlintrc — YAML set format (via shared helper)
    expected_lint = gdlintrc_content(config)
    lint_file = project_root / "gdlintrc"
    if not lint_file.exists():
        lint_file.write_text(expected_lint, encoding="utf-8")
    elif lint_file.read_text(encoding="utf-8") != expected_lint:
        console.print(
            "[yellow]Warning: gdlintrc differs from expected "
            "content. Delete it and re-run 'gd-tools init' to "
            "regenerate.[/yellow]"
        )

    # gdformatrc — one exclude per line (via shared helper)
    expected_format = gdformatrc_content(config)
    format_file = project_root / "gdformatrc"
    if not format_file.exists():
        format_file.write_text(expected_format, encoding="utf-8")
    elif format_file.read_text(encoding="utf-8") != expected_format:
        console.print(
            "[yellow]Warning: gdformatrc differs from expected "
            "content. Delete it and re-run 'gd-tools init' to "
            "regenerate.[/yellow]"
        )


# --- Phase 5: Data Directory, Summary, and Orchestration ---


def create_data_dir(project_root: Path) -> None:
    """Create the ``.gd-tools/`` data directory and update ``.gitignore``.

    Creates ``project_root/.gd-tools/`` if it does not exist (idempotent).
    Appends ``.gd-tools/`` to ``project_root/.gitignore``, creating the
    file if necessary. If ``.gd-tools/`` is already present in
    ``.gitignore``, no duplicate is added.

    Args:
        project_root: Path to the Godot project root.
    """
    data_dir = project_root / ".gd-tools"
    data_dir.mkdir(exist_ok=True)

    gitignore = project_root / ".gitignore"
    entry = ".gd-tools/"
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        if entry not in lines:
            with gitignore.open("a", encoding="utf-8") as f:
                f.write(f"\n{entry}\n")
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")


def print_summary(project_root: Path, actions: list[str]) -> None:
    """Print a Rich-formatted summary of init actions and next steps.

    Lists all actions taken during initialization and prints guidance
    on what the user should do next (e.g., run tests).

    In quiet mode, only a one-line success status is printed.

    Args:
        project_root: Path to the Godot project root.
        actions: List of action descriptions to display.
    """
    if get_verbosity() == Verbosity.QUIET:
        output.print_success("Initialized")
        return
    console.print("\n[bold green]gd-tools init complete![/bold green]\n")
    console.print("[bold]Actions taken:[/bold]")
    for action in actions:
        console.print(f"  - {action}")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  - Run [cyan]gd-tools test[/cyan] to execute tests")
    console.print("  - Run [cyan]gd-tools lint[/cyan] to check code style")
    console.print(
        "  - Run [cyan]gd-tools format[/cyan] to format GDScript files"
    )


def run_init(non_interactive: bool = False) -> None:
    """Bootstrap a project for the native test runtime."""
    project_root = find_project_root()
    config = load_config(project_root)

    actions: list[str] = []
    detect_godot_version(config)  # validates Godot is present before deploying

    install_native_test_addon(project_root)
    actions.append("Deployed native test addon")

    install_coverage_addon(project_root)
    actions.append("Deployed coverage addon")
    actions.append(f"Wrote addon version file (v{__version__})")

    install_editor_plugin(project_root)
    actions.append("Deployed editor plugin addon")

    create_config_file(project_root, config)
    actions.append("Ensured gd-tools.toml exists")

    generate_lint_format_rcs(project_root, config)
    actions.append("Generated gdlintrc and gdformatrc")

    create_data_dir(project_root)
    actions.append("Created .gd-tools/ directory")

    print_summary(project_root, actions)
