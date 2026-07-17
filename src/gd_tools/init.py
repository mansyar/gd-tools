"""Initialize a Godot project for use with gd-tools.

This module implements the ``gd-tools init`` command, which bootstraps
a Godot project by:
- Detecting the project root and Godot version
- Installing GUT (Godot Unit Test) if not present
- Deploying the coverage addon as placeholder stubs
- Creating configuration files (``.gutconfig.json``, ``gd-tools.toml``,
  ``gdlintrc``, ``gdformatrc``)
- Creating the ``.gd-tools/`` data directory
- Printing a summary of actions taken

The command is idempotent: running it multiple times produces the
same end state without duplicating entries.
"""

import configparser
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import click
import requests
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
from .errors import GdToolsError
from .godot import find_godot, get_gut_version_for_godot
from .test_runner import is_gut_installed
from .verbosity import Verbosity, get_verbosity

# --- Constants ---

GUTCONFIG_TEMPLATE: dict = {
    "dirs": ["res://test/", "res://tests/"],
    "include_subdirs": True,
    "prefix": "test_",
    "suffix": ".gd",
    "should_exit": True,
    "junit_xml_file": ".gd-tools/results.xml",
    "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
    "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd",
}

GUT_DOWNLOAD_URL = (
    "https://github.com/bitwes/Gut/archive/refs/tags/v{version}.zip"
)

GUT_PLUGIN_PATH = "res://addons/gut/plugin.gd"

COVERAGE_ADDON_FILES = [
    "coverage.gd",
    "pre_run_hook.gd",
    "post_run_hook.gd",
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


# --- Phase 2: GUT Installation ---


def get_installed_gut_version(project_root: Path) -> str | None:
    """Get the installed GUT version from ``addons/gut/plugin.cfg``.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        The GUT version string (e.g., ``"9.5.0"``), or ``None`` if
        ``plugin.cfg`` does not exist or has no ``version`` key.
    """
    plugin_cfg = project_root / "addons" / "gut" / "plugin.cfg"
    if not plugin_cfg.exists():
        return None
    parser = configparser.ConfigParser()
    parser.read(plugin_cfg)
    version = parser.get("plugin", "version", fallback=None)
    if version is None:
        return None
    return version.strip('"')


def download_gut(version: str, dest: Path) -> Path:
    """Download the GUT zip archive for the given version.

    Args:
        version: The GUT version string (e.g., ``"9.5.0"``).
        dest: Destination path for the downloaded zip file.

    Returns:
        The path to the downloaded zip file.

    Raises:
        GdToolsError: If the download fails (network error, HTTP error,
            etc.). The error message includes manual install instructions.
    """
    url = GUT_DOWNLOAD_URL.format(version=version)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GdToolsError(
            f"[Error] Failed to download GUT v{version}\n"
            f"  Cause: {exc}\n"
            f"  Fix: Download GUT manually from:\n"
            f"    - Godot Asset Library: "
            f"https://godotengine.org/asset-library/asset/116\n"
            f"    - GitHub: {url}\n"
            f"    Extract the 'addons/gut/' folder to your project's "
            f"'addons/' directory."
        ) from exc
    dest.write_bytes(response.content)
    return dest


def extract_gut(zip_path: Path, project_root: Path) -> None:
    """Extract the GUT zip archive and copy addons/gut/ to the project.

    The GitHub archive contains a top-level directory (e.g.,
    ``Gut-9.5.0/``) with ``addons/gut/`` inside it. This function
    extracts to a temporary directory, locates ``addons/gut/``, copies
    it to ``project_root/addons/gut/``, and cleans up the temp dir.

    Args:
        zip_path: Path to the downloaded GUT zip file.
        project_root: Path to the Godot project root.

    Raises:
        GdToolsError: If the archive does not contain an
            ``addons/gut/`` directory.
    """
    tmpdir = tempfile.mkdtemp()
    try:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        gut_source: Path | None = None
        for addons_dir in tmp_path.rglob("addons"):
            gut_dir = addons_dir / "gut"
            if gut_dir.is_dir():
                gut_source = gut_dir
                break
        if gut_source is None:
            raise GdToolsError(
                "[Error] Failed to extract GUT\n"
                "  Cause: addons/gut/ directory not found in archive\n"
                "  Fix: Download GUT manually from:\n"
                "    - Godot Asset Library: "
                "https://godotengine.org/asset-library/asset/116\n"
                "    - GitHub: https://github.com/bitwes/Gut\n"
                "    Extract the 'addons/gut/' folder to your project's "
                "'addons/' directory."
            )
        dest = project_root / "addons" / "gut"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(gut_source, dest)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def install_gut(
    project_root: Path, godot_version: str, non_interactive: bool
) -> bool:
    """Install GUT if not already installed.

    If GUT is already installed, checks the installed version against
    the expected version for the detected Godot version and warns if
    they differ. If GUT is not installed, prompts the user (interactive
    mode) or auto-installs (non-interactive mode).

    Args:
        project_root: Path to the Godot project root.
        godot_version: The detected Godot version (e.g., ``"4.5.1"``).
        non_interactive: If True, skip prompts and assume yes.

    Returns:
        True if GUT is installed (or was already present),
        False if the user declined installation.
    """
    if is_gut_installed(project_root):
        installed_version = get_installed_gut_version(project_root)
        expected_version = get_gut_version_for_godot(godot_version)
        if installed_version != expected_version:
            console.print(
                "[yellow]Warning: GUT version "
                f"{installed_version} does not match expected "
                f"version {expected_version} for Godot "
                f"{godot_version}.[/yellow]"
            )
        return True

    if not non_interactive:
        if not click.confirm("Install GUT?", default=True):
            console.print(
                "GUT not installed. To install manually:\n"
                "  1. Download from: "
                "https://godotengine.org/asset-library/asset/116\n"
                "  2. Extract the 'addons/gut/' folder to your "
                "project's 'addons/' directory."
            )
            return False

    gut_version = get_gut_version_for_godot(godot_version)
    tmpdir = tempfile.mkdtemp()
    zip_dest = Path(tmpdir) / "gut.zip"
    try:
        download_gut(gut_version, zip_dest)
        extract_gut(zip_dest, project_root)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return True


def enable_gut_plugin(project_root: Path) -> None:
    """Enable the GUT plugin in ``project.godot``.

    Adds the ``[editor_plugins]`` section with the GUT plugin in the
    ``enabled`` list if not already present. Idempotent: running
    multiple times produces the same result.

    Args:
        project_root: Path to the Godot project root.
    """
    project_godot = project_root / "project.godot"
    content = project_godot.read_text(encoding="utf-8")

    gut_entry = f'"{GUT_PLUGIN_PATH}"'

    # Idempotent: if GUT is already enabled, do nothing.
    # Use regex to match only within enabled=PackedStringArray(...),
    # not in comments or other contexts.
    if re.search(
        rf"enabled=PackedStringArray\([^\)]*{re.escape(gut_entry)}",
        content,
    ):
        return

    if "[editor_plugins]" in content:
        # Section exists, add GUT to enabled list
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == "[editor_plugins]":
                # Look for enabled= in subsequent lines
                for j in range(i + 1, len(lines)):
                    next_stripped = lines[j].strip()
                    if next_stripped.startswith("["):
                        # Reached next section, insert enabled= before it
                        lines.insert(
                            j,
                            f"enabled=PackedStringArray({gut_entry})",
                        )
                        break
                    if next_stripped.startswith("enabled="):
                        # Add GUT to existing PackedStringArray
                        lines[j] = lines[j].replace(
                            "PackedStringArray(",
                            f"PackedStringArray({gut_entry}, ",
                        )
                        break
                else:
                    # No enabled= and no next section, append at end
                    lines.append(f"enabled=PackedStringArray({gut_entry})")
                break
        project_godot.write_text("\n".join(lines), encoding="utf-8")
    else:
        # No [editor_plugins] section, append it
        if not content.endswith("\n"):
            content += "\n"
        content += (
            f"\n[editor_plugins]\n\n"
            f"enabled=PackedStringArray({gut_entry})\n"
        )
        project_godot.write_text(content, encoding="utf-8")


# --- Phase 3: Coverage Addon Deployment ---


def install_coverage_addon(project_root: Path) -> None:
    """Copy bundled coverage addon files to the project.

    Copies the GDScript files from the package data to
    ``project_root/addons/gd-tools-coverage/``. Always overwrites
    existing files to ensure they are up-to-date. If an existing file
    differs from the bundled version (indicating user modification),
    a backup copy is saved to ``addons/gd-tools-coverage/.backups/``
    before overwriting, and a yellow warning is printed. Also writes
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
                shutil.copy2(target_file, backups_dir / f"{gd_file}.bak")
                console.print(
                    f"[yellow]Warning: {gd_file} was modified. "
                    f"Backed up to {backups_dir / f'{gd_file}.bak'}"
                    f" before overwriting.[/yellow]"
                )
        shutil.copy2(source_file, target_file)
    version_file = target_dir / "_version.txt"
    version_file.write_text(f"{__version__}\n", encoding="utf-8")


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

# Keys in .gutconfig.json that are always overwritten from the template.
_GUTCONFIG_OVERWRITE_KEYS = (
    "should_exit",
    "junit_xml_file",
    "pre_run_script",
    "post_run_script",
)

# Keys in .gutconfig.json that are preserved from the user's existing file.
_GUTCONFIG_PRESERVE_KEYS = (
    "dirs",
    "prefix",
    "suffix",
    "include_subdirs",
)


def update_gutconfig(project_root: Path, config: GdToolsConfig) -> None:
    """Create or merge ``.gutconfig.json`` in the project root.

    If the file does not exist, writes ``GUTCONFIG_TEMPLATE`` as JSON.
    If it exists, merges: preserves the user's ``dirs``, ``prefix``,
    ``suffix``, and ``include_subdirs``; always overwrites
    ``should_exit``, ``junit_xml_file``, ``pre_run_script``, and
    ``post_run_script`` from the template.

    Args:
        project_root: Path to the Godot project root.
        config: The gd-tools configuration (unused but kept for
            signature consistency with other init functions).
    """
    gutconfig_path = project_root / ".gutconfig.json"

    if not gutconfig_path.exists():
        gutconfig_path.write_text(
            json.dumps(GUTCONFIG_TEMPLATE, indent=2) + "\n"
        )
        return

    existing = json.loads(gutconfig_path.read_text())
    merged = GUTCONFIG_TEMPLATE.copy()
    for key in _GUTCONFIG_PRESERVE_KEYS:
        if key in existing:
            merged[key] = existing[key]
    gutconfig_path.write_text(json.dumps(merged, indent=2) + "\n")


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
    """Run the full init flow to bootstrap a Godot project.

    Orchestrates all initialization steps:
    1. Detect project root
    2. Load or create config
    3. Detect Godot version
    4. Resolve GUT version
    5. Check if GUT is installed
    6. Install GUT if needed
    7. Enable GUT plugin in project.godot
    8. Deploy coverage addon
    9. Create/update .gutconfig.json
    10. Create gd-tools.toml if missing
    11. Generate gdlintrc and gdformatrc
    12. Create .gd-tools/ data directory
    13. Print summary

    Args:
        non_interactive: If True, skip all interactive prompts
            and assume defaults.
    """
    project_root = find_project_root()
    config = load_config(project_root)

    actions: list[str] = []

    godot_version = detect_godot_version(config)
    gut_version = get_gut_version_for_godot(godot_version)

    is_installed = is_gut_installed(project_root)
    if is_installed:
        installed = get_installed_gut_version(project_root)
        if installed:
            actions.append(f"GUT already installed (v{installed})")
        else:
            actions.append("GUT already installed (version unknown)")
    else:
        actions.append(f"Installing GUT v{gut_version}")

    if not install_gut(
        project_root, godot_version, non_interactive=non_interactive
    ):
        console.print(
            "\n[yellow]Init aborted: GUT was not installed.[/yellow]\n"
            "Install GUT manually, then re-run 'gd-tools init'."
        )
        sys.exit(1)

    enable_gut_plugin(project_root)
    actions.append("Enabled GUT plugin in project.godot")

    install_coverage_addon(project_root)
    actions.append("Deployed coverage addon")
    actions.append(f"Wrote addon version file (v{__version__})")

    register_coverage_autoload(project_root)
    actions.append("Registered _GDTCoverage autoload")

    update_gutconfig(project_root, config)
    actions.append("Created/updated .gutconfig.json")

    create_config_file(project_root, config)
    actions.append("Ensured gd-tools.toml exists")

    generate_lint_format_rcs(project_root, config)
    actions.append("Generated gdlintrc and gdformatrc")

    create_data_dir(project_root)
    actions.append("Created .gd-tools/ directory")

    print_summary(project_root, actions)
