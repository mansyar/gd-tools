"""Diagnostic command for checking gd-tools project health.

Implements ``gd-tools doctor``, which runs a series of environment
and configuration checks and reports pass/fail status with actionable
fix hints. See TDD \u00a73.6 and PRD \u00a78.
"""

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .config import GdToolsConfig
from .godot import (
    GodotNotFoundError,
    check_version_compatible,
    find_godot,
    get_gut_version_for_godot,
)
from .init import COVERAGE_ADDON_FILES, get_installed_gut_version


@dataclass
class CheckResult:
    """Result of a single diagnostic check.

    Attributes:
        name: Human-readable name of the check.
        passed: Whether the check passed.
        message: Description of what was found.
        fix_hint: Actionable suggestion for failures.
        severity: "critical" or "warning".
    """

    name: str
    passed: bool
    message: str
    fix_hint: str = ""
    severity: str = "critical"


@dataclass
class DoctorResult:
    """Aggregate result of all diagnostic checks.

    Attributes:
        checks: List of individual check results.
        all_passed: True if every check passed.
    """

    checks: list[CheckResult]
    all_passed: bool


# --- Godot and External Tool Checks ---


def check_godot_binary(config: GdToolsConfig) -> CheckResult:
    """Check that a Godot binary is found via the detection chain.

    Args:
        config: The gd-tools configuration containing Godot settings.

    Returns:
        CheckResult indicating whether the Godot binary was found.
    """
    try:
        info = find_godot(config.godot)
    except GodotNotFoundError:
        return CheckResult(
            name="Godot Binary",
            passed=False,
            message="Godot binary not found",
            fix_hint=(
                "Install Godot 4.5+ from "
                "https://godotengine.org and set GODOT_BIN "
                "or add to PATH."
            ),
            severity="critical",
        )
    return CheckResult(
        name="Godot Binary",
        passed=True,
        message=f"Godot {info.version} at {info.path}",
    )


def check_godot_version(config: GdToolsConfig) -> CheckResult:
    """Check that the detected Godot version is >= 4.5.0.

    Args:
        config: The gd-tools configuration containing Godot settings.

    Returns:
        CheckResult indicating whether the Godot version is compatible.
    """
    try:
        info = find_godot(config.godot)
    except GodotNotFoundError:
        return CheckResult(
            name="Godot Version",
            passed=False,
            message="Godot binary not found - cannot check version",
            fix_hint=(
                "Install Godot 4.5+ from "
                "https://godotengine.org and set GODOT_BIN "
                "or add to PATH."
            ),
            severity="critical",
        )
    if check_version_compatible(info.version):
        return CheckResult(
            name="Godot Version",
            passed=True,
            message=f"Godot {info.version} is >= 4.5.0",
        )
    return CheckResult(
        name="Godot Version",
        passed=False,
        message=f"Godot {info.version} is below required 4.5.0",
        fix_hint=(
            "Install Godot 4.5+ from "
            "https://godotengine.org and set GODOT_BIN "
            "or add to PATH."
        ),
        severity="critical",
    )


def check_gdtoolkit() -> CheckResult:
    """Check that gdlint and gdformat CLI tools are installed.

    Returns:
        CheckResult indicating whether both tools are available.
    """
    missing = []
    for tool in ("gdlint", "gdformat"):
        try:
            subprocess.run(
                [tool, "--version"],
                capture_output=True,
            )
        except FileNotFoundError:
            missing.append(tool)

    if missing:
        return CheckResult(
            name="GD Toolkit",
            passed=False,
            message=f"Missing tools: {', '.join(missing)}",
            fix_hint="Install gdtoolkit: pip install gdtoolkit",
            severity="critical",
        )
    return CheckResult(
        name="GD Toolkit",
        passed=True,
        message="gdlint and gdformat are installed",
    )


# --- GUT and Project Configuration Checks ---


def check_gut_installed(project_root: Path) -> CheckResult:
    """Check that GUT is installed in the project.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether GUT is installed.
    """
    gut_path = project_root / "addons" / "gut" / "gut.gd"
    if gut_path.exists():
        return CheckResult(
            name="GUT Installed",
            passed=True,
            message="GUT is installed",
        )
    return CheckResult(
        name="GUT Installed",
        passed=False,
        message="GUT is not installed",
        fix_hint=(
            "Run `gd-tools init` to install GUT, "
            "or see https://github.com/bitwes/Gut."
        ),
        severity="critical",
    )


def check_gut_version(project_root: Path, godot_version: str) -> CheckResult:
    """Check that the installed GUT version matches the expected version.

    Args:
        project_root: Path to the Godot project root.
        godot_version: The detected Godot version string.

    Returns:
        CheckResult indicating whether the GUT version is compatible.
    """
    installed = get_installed_gut_version(project_root)
    if installed is None:
        return CheckResult(
            name="GUT Version",
            passed=True,
            message="GUT version unknown - cannot verify",
        )
    expected = get_gut_version_for_godot(godot_version)
    if installed == expected:
        return CheckResult(
            name="GUT Version",
            passed=True,
            message=f"GUT version {installed} matches expected {expected}",
        )
    return CheckResult(
        name="GUT Version",
        passed=False,
        message=(
            f"GUT version {installed} does not match " f"expected {expected}"
        ),
        fix_hint=(
            f"Install GUT version {expected} " f"for Godot {godot_version}"
        ),
        severity="warning",
    )


def check_coverage_addon(project_root: Path) -> CheckResult:
    """Check that the gd-tools-coverage addon files are present.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether all coverage addon files exist.
    """
    cov_dir = project_root / "addons" / "gd-tools-coverage"
    missing = [f for f in COVERAGE_ADDON_FILES if not (cov_dir / f).exists()]
    if missing:
        return CheckResult(
            name="Coverage Addon",
            passed=False,
            message=f"Missing coverage files: {', '.join(missing)}",
            fix_hint="Run `gd-tools init` to install the coverage addon.",
            severity="warning",
        )
    return CheckResult(
        name="Coverage Addon",
        passed=True,
        message="Coverage addon is installed",
    )
