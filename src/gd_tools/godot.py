"""Godot binary detection and invocation module.

Resolves the Godot binary path via a 5-level priority chain, detects
and validates the Godot version, maps Godot versions to compatible
GUT versions, and provides a subprocess wrapper for invoking Godot.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from gd_tools.config import GodotConfig
from gd_tools.errors import GodotNotFoundError


@dataclass
class GodotInfo:
    """Information about a detected Godot binary.

    Attributes:
        path: Resolved binary path.
        version: Parsed version string (e.g., "4.5.1").
        is_valid: True if version >= 4.5.0.
    """

    path: str
    version: str
    is_valid: bool


# --- Version Detection ---


def get_godot_version(binary: str) -> str:
    """Get the Godot version string from the binary.

    Runs ``godot --version`` and parses the output into a normalized
    ``major.minor.patch`` string.

    Args:
        binary: Path to the Godot binary.

    Returns:
        Normalized version string (e.g., "4.5.1").

    Raises:
        GodotNotFoundError: If the binary fails to run or produces
            unparseable output.
    """
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GodotNotFoundError(
            f"Failed to execute Godot binary at {binary}: {exc}"
        ) from exc

    if result.returncode != 0:
        raise GodotNotFoundError(
            f"Godot binary at {binary} exited with code "
            f"{result.returncode}: {result.stderr.strip()}"
        )

    output = result.stdout.strip()
    match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", output)
    if not match:
        raise GodotNotFoundError(
            f"Could not parse Godot version from output: {output!r}"
        )

    major, minor = match.group(1), match.group(2)
    patch = match.group(3) or "0"
    return f"{major}.{minor}.{patch}"


def check_version_compatible(version: str) -> bool:
    """Check if a Godot version is compatible (>= 4.5.0).

    Args:
        version: Normalized version string (e.g., "4.5.1").

    Returns:
        True if version >= 4.5.0, False otherwise.
    """
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        return False
    major, minor, patch = (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
    )
    return (major, minor, patch) >= (4, 5, 0)


# --- Binary Resolution Chain ---


def _is_executable(path: str) -> bool:
    """Check if a path exists and is executable.

    Args:
        path: File path to check.

    Returns:
        True if the file exists and is executable.
    """
    return Path(path).is_file() and os.access(path, os.X_OK)


def _check_config(config: GodotConfig) -> str | None:
    """Check the user-specified binary path from config.

    Args:
        config: The Godot configuration.

    Returns:
        Binary path if config has a valid binary, None otherwise.
    """
    if config.binary is None:
        return None
    if _is_executable(config.binary):
        return config.binary
    return None


def _check_env_vars() -> str | None:
    """Check environment variables for the Godot binary.

    Checks ``GODOT_BIN``, ``GODOT4_BIN``, and ``GODOT_PATH`` in order.

    Returns:
        Binary path if found in an env var, None otherwise.
    """
    for var_name in ("GODOT_BIN", "GODOT4_BIN", "GODOT_PATH"):
        path = os.environ.get(var_name)
        if path and _is_executable(path):
            return path
    return None


def _check_path() -> str | None:
    """Check PATH for the Godot binary via ``shutil.which``.

    Returns:
        Binary path if found on PATH, None otherwise.
    """
    for name in ("godot", "godot4"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _check_common_locations() -> str | None:
    """Check common install locations for the Godot binary.

    Checks platform-specific standard install paths.

    Returns:
        Binary path if found at a common location, None otherwise.
    """
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Godot\godot.exe",
            os.path.join(
                os.environ.get("LOCALAPPDATA", ""), "Godot", "godot.exe"
            ),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Godot.app/Contents/MacOS/Godot",
            "/opt/homebrew/bin/godot",
        ]
    else:
        candidates = [
            os.path.expanduser("~/.local/bin/godot"),
            "/usr/bin/godot",
            "/usr/local/bin/godot",
        ]

    for candidate in candidates:
        if candidate and _is_executable(candidate):
            return candidate
    return None


def _build_not_found_message() -> str:
    """Build a comprehensive 'Godot not found' error message.

    Returns:
        Error message with resolution methods and install instructions.
    """
    lines = ["Godot binary not found."]
    lines.append("")
    lines.append("Tried the following resolution methods:")
    lines.append("  1. Config: [godot].binary in gd-tools.toml")
    lines.append("  2. Environment: GODOT_BIN, GODOT4_BIN, GODOT_PATH")
    lines.append("  3. PATH: shutil.which('godot'), shutil.which('godot4')")
    lines.append("  4. Common install locations")
    lines.append("")
    if sys.platform == "win32":
        lines.append("Install Godot on Windows:")
        lines.append(
            "  Download from https://godotengine.org/download/windows/"
        )
        lines.append("  Or: winget install GodotEngine.GodotEngine")
    elif sys.platform == "darwin":
        lines.append("Install Godot on macOS:")
        lines.append("  Download from https://godotengine.org/download/macos/")
        lines.append("  Or: brew install --cask godot")
    else:
        lines.append("Install Godot on Linux:")
        lines.append("  Download from https://godotengine.org/download/linux/")
        lines.append("  Or: flatpak install org.godotengine.Godot")
    lines.append("")
    lines.append("To configure manually:")
    lines.append("  - Run 'gd-tools init' to set up interactively")
    lines.append("  - Set the GODOT_BIN environment variable")
    lines.append("  - Add [godot].binary = '/path/to/godot' to gd-tools.toml")
    return "\n".join(lines)


def find_godot(config: GodotConfig) -> GodotInfo:
    """Find the Godot binary using a 5-level priority chain.

    Resolution order (first match wins):
        1. ``config.binary``
        2. Environment variables (``GODOT_BIN``, ``GODOT4_BIN``,
           ``GODOT_PATH``)
        3. PATH lookup (``shutil.which``)
        4. Common install locations
        5. Raise ``GodotNotFoundError``

    Args:
        config: The Godot configuration.

    Returns:
        GodotInfo with resolved path, version, and validity.

    Raises:
        GodotNotFoundError: If no Godot binary is found.
    """
    binary = (
        _check_config(config)
        or _check_env_vars()
        or _check_path()
        or _check_common_locations()
    )

    if binary is None:
        raise GodotNotFoundError(_build_not_found_message())

    try:
        version = get_godot_version(binary)
        is_valid = check_version_compatible(version)
    except GodotNotFoundError:
        version = "unknown"
        is_valid = False

    return GodotInfo(path=binary, version=version, is_valid=is_valid)
