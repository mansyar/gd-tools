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

# ruff: noqa: F401
# Imports below are used in functions implemented in subsequent tasks.

import configparser
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import click
import requests
from rich.console import Console

from .config import (
    GdToolsConfig,
    find_project_root,
    generate_gdformatrc,
    generate_gdlintrc,
    load_config,
    save_config,
)
from .errors import ConfigError, GdToolsError, GodotNotFoundError
from .godot import GodotInfo, find_godot, get_gut_version_for_godot

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


def check_gut_installed(project_root: Path) -> bool:
    """Check if GUT is installed in the project.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        True if ``addons/gut/gut.gd`` exists, False otherwise.
    """
    return (project_root / "addons" / "gut" / "gut.gd").exists()


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
) -> None:
    """Install GUT if not already installed.

    If GUT is already installed, checks the installed version against
    the expected version for the detected Godot version and warns if
    they differ. If GUT is not installed, prompts the user (interactive
    mode) or auto-installs (non-interactive mode).

    Args:
        project_root: Path to the Godot project root.
        godot_version: The detected Godot version (e.g., ``"4.5.1"``).
        non_interactive: If True, skip prompts and assume yes.
    """
    if check_gut_installed(project_root):
        installed_version = get_installed_gut_version(project_root)
        expected_version = get_gut_version_for_godot(godot_version)
        if installed_version != expected_version:
            console.print(
                "[yellow]Warning: GUT version "
                f"{installed_version} does not match expected "
                f"version {expected_version} for Godot "
                f"{godot_version}.[/yellow]"
            )
        return

    if not non_interactive:
        if not click.confirm("Install GUT?", default=True):
            console.print(
                "GUT not installed. To install manually:\n"
                "  1. Download from: "
                "https://godotengine.org/asset-library/asset/116\n"
                "  2. Extract the 'addons/gut/' folder to your "
                "project's 'addons/' directory."
            )
            return

    gut_version = get_gut_version_for_godot(godot_version)
    tmpdir = tempfile.mkdtemp()
    zip_dest = Path(tmpdir) / "gut.zip"
    try:
        download_gut(gut_version, zip_dest)
        extract_gut(zip_dest, project_root)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def enable_gut_plugin(project_root: Path) -> None:
    """Enable the GUT plugin in ``project.godot``.

    Adds the ``[editor_plugins]`` section with the GUT plugin in the
    ``enabled`` list if not already present. Idempotent: running
    multiple times produces the same result.

    Args:
        project_root: Path to the Godot project root.
    """
    project_godot = project_root / "project.godot"
    content = project_godot.read_text()

    gut_entry = f'"{GUT_PLUGIN_PATH}"'

    # Idempotent: if GUT is already in the file, do nothing
    if gut_entry in content:
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
        project_godot.write_text("\n".join(lines))
    else:
        # No [editor_plugins] section, append it
        if not content.endswith("\n"):
            content += "\n"
        content += (
            f"\n[editor_plugins]\n\n"
            f"enabled=PackedStringArray({gut_entry})\n"
        )
        project_godot.write_text(content)


# --- Phase 3: Coverage Addon Deployment ---


def install_coverage_addon(project_root: Path) -> None:
    """Copy bundled coverage addon placeholder files to the project.

    Copies the placeholder GDScript stubs from the package data to
    ``project_root/addons/gd-tools-coverage/``. Always overwrites
    existing files to ensure they are up-to-date.

    Args:
        project_root: Path to the Godot project root.
    """
    source_dir = Path(__file__).parent / "addons" / "gd-tools-coverage"
    target_dir = project_root / "addons" / "gd-tools-coverage"
    target_dir.mkdir(parents=True, exist_ok=True)
    for gd_file in COVERAGE_ADDON_FILES:
        shutil.copy2(source_dir / gd_file, target_dir / gd_file)
