"""Stale addon detection module.

Checks whether the deployed coverage addon version matches the installed
gd-tools-cli package version. Prints warnings to stderr when the addon
is missing or stale. Fails silently on any error and can be disabled via
the GD_TOOLS_NO_UPDATE_CHECK environment variable.
"""

import os

import click
from packaging.version import parse as parse_version

from gd_tools import __version__
from gd_tools.config import find_project_root

ADDON_VERSION_FILENAME = "_version.txt"


def check_addon_version() -> None:
    """Check if the deployed coverage addon version is stale.

    Compares the version in _version.txt against the installed package
    version. Prints a warning to stderr if the addon is missing or stale.
    Fails silently on any unexpected error.

    FR2: Stale Addon Check on CLI Invocation.
    FR3: Suppressed by GD_TOOLS_NO_UPDATE_CHECK=1.
    FR4: Uses packaging.version.parse() for comparison.
    """
    # FR3.1: Environment variable disables check entirely.
    if os.environ.get("GD_TOOLS_NO_UPDATE_CHECK") == "1":
        return

    try:
        project_root = find_project_root()
        version_file = (
            project_root
            / "addons"
            / "gd-tools-coverage"
            / ADDON_VERSION_FILENAME
        )

        if not version_file.exists():
            click.echo(
                "WARNING: Coverage addon version file not found. "
                "Run `gd-tools init` to deploy the addon.",
                err=True,
            )
            return

        addon_version = version_file.read_text(encoding="utf-8").strip()
        stale_msg = (
            f"WARNING: Coverage addon is outdated (v{addon_version} "
            f"deployed, v{__version__} available). "
            f"Run `gd-tools init` to update."
        )

        # FR4.1: Compare versions using packaging.version.parse().
        try:
            addon_parsed = parse_version(addon_version)
            package_parsed = parse_version(__version__)
        except (TypeError, ValueError):
            # FR4.2: Unparseable version = treated as stale.
            click.echo(stale_msg, err=True)
            return

        # FR2.4: Stale (addon < package)
        if addon_parsed < package_parsed:
            click.echo(stale_msg, err=True)
        # FR2.5: Match = no warning
        # FR2.6: Newer addon (downgrade) = no warning
    except Exception:
        # FR2.8: Fail silently on any unexpected error.
        pass
