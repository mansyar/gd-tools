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
COVERAGE_ADDON_DIR = "gd-tools-coverage"
NATIVE_ADDON_DIR = "gd-tools-test"


def _stale_refusal(label: str, deployed: str) -> str:
    """Build the refusal message for a stale/unparseable addon.

    Args:
        label: Human-readable addon label ("Coverage"/"Native test").
        deployed: Deployed version string (raw, may be unparseable).

    Returns:
        Refusal message naming both versions, the fix, and the abort.
    """
    return (
        f"Error: {label} addon is outdated (v{deployed} deployed, "
        f"v{__version__} installed). Run `gd-tools init` to "
        "update. Aborted before running tests."
    )


def _missing_refusal(label: str) -> str:
    """Build the refusal message for a missing version file.

    Args:
        label: Human-readable addon label ("Coverage"/"Native test").

    Returns:
        Refusal message naming the CLI version, the fix, and abort.
    """
    return (
        f"Error: {label} addon version file not found "
        f"(deployed version unknown, v{__version__} installed). "
        "Run `gd-tools init` to deploy the addon. "
        "Aborted before running tests."
    )


def check_coverage_addon_gate() -> str | None:
    """Check the coverage-run addon gate before suite dispatch.

    Compares the deployed coverage and native test addon versions
    against the CLI version. A missing, unparseable, or older
    deployed version refuses the run. Newer deployed addons and
    matching versions pass. Suppressed by
    ``GD_TOOLS_NO_UPDATE_CHECK=1``. Never raises; unexpected
    errors defer to the caller's existing behavior.

    Returns:
        Refusal message when the run must abort, else None.
    """
    if os.environ.get("GD_TOOLS_NO_UPDATE_CHECK") == "1":
        return None
    try:
        project_root = find_project_root()
    except Exception:
        return None
    for addon_dir, label in (
        (COVERAGE_ADDON_DIR, "Coverage"),
        (NATIVE_ADDON_DIR, "Native test"),
    ):
        version_file = (
            project_root / "addons" / addon_dir / ADDON_VERSION_FILENAME
        )
        try:
            exists = version_file.exists()
        except Exception:
            return None
        if not exists:
            return _missing_refusal(label)
        try:
            addon_version = version_file.read_text(encoding="utf-8").strip()
        except Exception:
            return None
        try:
            addon_parsed = parse_version(addon_version)
            package_parsed = parse_version(__version__)
        except (TypeError, ValueError):
            return _stale_refusal(label, addon_version)
        if addon_parsed < package_parsed:
            return _stale_refusal(label, addon_version)
    return None


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
