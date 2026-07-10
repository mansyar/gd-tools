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

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

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
