"""Diagnostic command for checking gd-tools project health.

Implements ``gd-tools doctor``, which runs a series of environment
and configuration checks and reports pass/fail status with actionable
fix hints. See TDD \u00a73.6 and PRD \u00a78.
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from rich.table import Table

from .config import GdToolsConfig, find_project_root, load_config
from .errors import ConfigError
from .godot import (
    GodotNotFoundError,
    check_version_compatible,
    find_godot,
    get_gut_version_for_godot,
)
from .init import COVERAGE_ADDON_FILES, get_installed_gut_version
from .test_runner import is_gut_installed


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
                timeout=10,
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
    gut_installed = is_gut_installed(project_root)
    if gut_installed:
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


def check_gutconfig(project_root: Path) -> CheckResult:
    """Check that .gutconfig.json is valid JSON with hook script keys.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether .gutconfig.json exists, is valid
        JSON, and contains both ``pre_run_script`` and ``post_run_script``
        keys.
    """
    gutconfig_path = project_root / ".gutconfig.json"
    if not gutconfig_path.exists():
        return CheckResult(
            name="GUT Config",
            passed=False,
            message=".gutconfig.json not found",
            fix_hint="Run `gd-tools init` to generate .gutconfig.json.",
            severity="warning",
        )
    try:
        content = json.loads(gutconfig_path.read_text())
    except ValueError as exc:
        return CheckResult(
            name="GUT Config",
            passed=False,
            message=f".gutconfig.json is invalid JSON: {exc}",
            fix_hint="Fix the JSON syntax in .gutconfig.json or run `gd-tools init`.",
            severity="warning",
        )
    missing_keys = [
        key
        for key in ("pre_run_script", "post_run_script")
        if key not in content
    ]
    if missing_keys:
        return CheckResult(
            name="GUT Config",
            passed=False,
            message=f"Missing keys: {', '.join(missing_keys)}",
            fix_hint="Run `gd-tools init` to regenerate .gutconfig.json with hook scripts.",
            severity="warning",
        )
    return CheckResult(
        name="GUT Config",
        passed=True,
        message=".gutconfig.json is valid with hook scripts",
    )


def check_gd_tools_toml(project_root: Path) -> CheckResult:
    """Check that gd-tools.toml exists and is parseable TOML.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether gd-tools.toml exists and
        is valid TOML.
    """
    toml_path = project_root / "gd-tools.toml"
    if not toml_path.exists():
        return CheckResult(
            name="gd-tools.toml",
            passed=False,
            message="gd-tools.toml not found",
            fix_hint="Run `gd-tools init` to generate gd-tools.toml.",
            severity="critical",
        )
    try:
        with open(toml_path, "rb") as f:
            tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        return CheckResult(
            name="gd-tools.toml",
            passed=False,
            message=f"gd-tools.toml is invalid TOML: {exc}",
            fix_hint="Fix the TOML syntax in gd-tools.toml or run `gd-tools init`.",
            severity="critical",
        )
    return CheckResult(
        name="gd-tools.toml",
        passed=True,
        message="gd-tools.toml is valid",
    )


def check_autoload(project_root: Path) -> CheckResult:
    """Check that _GDTCoverage autoload is registered in project.godot.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether the ``_GDTCoverage`` autoload
        is registered in the ``[autoload]`` section of
        ``project.godot``.
    """
    project_godot = project_root / "project.godot"
    if not project_godot.exists():
        return CheckResult(
            name="Autoload",
            passed=False,
            message="project.godot not found",
            fix_hint="Run `gd-tools init` to deploy coverage addon.",
            severity="critical",
        )
    content = project_godot.read_text()
    in_autoload = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_autoload = stripped == "[autoload]"
            continue
        if in_autoload and stripped.startswith("_GDTCoverage="):
            return CheckResult(
                name="Autoload",
                passed=True,
                message="_GDTCoverage autoload is registered",
            )
    return CheckResult(
        name="Autoload",
        passed=False,
        message="_GDTCoverage autoload is not registered",
        fix_hint=(
            "Run `gd-tools init` to deploy coverage addon "
            "(autoload registration in Phase 3)."
        ),
        severity="critical",
    )


# --- Orchestration ---


def run_doctor() -> DoctorResult:
    """Run all diagnostic checks and return aggregated result.

    Resolves project root, loads config, and runs all 9 checks in
    order. Never raises — all exceptions are caught and converted
    to failed CheckResults.

    Returns:
        DoctorResult with all check results.
    """
    checks = []

    try:
        project_root = find_project_root()
    except ConfigError:
        project_root = Path.cwd()

    try:
        config = load_config()
    except ConfigError:
        config = GdToolsConfig()

    godot_version = "unknown"
    try:
        info = find_godot(config.godot)
        godot_version = info.version
    except GodotNotFoundError:
        pass

    check_specs = [
        ("Godot Binary", lambda: check_godot_binary(config)),
        ("Godot Version", lambda: check_godot_version(config)),
        ("GUT Installed", lambda: check_gut_installed(project_root)),
        (
            "GUT Version",
            lambda: check_gut_version(project_root, godot_version),
        ),
        ("Coverage Addon", lambda: check_coverage_addon(project_root)),
        ("GUT Config", lambda: check_gutconfig(project_root)),
        ("gd-tools.toml", lambda: check_gd_tools_toml(project_root)),
        ("GD Toolkit", lambda: check_gdtoolkit()),
        ("Autoload", lambda: check_autoload(project_root)),
    ]

    for name, fn in check_specs:
        try:
            checks.append(fn())
        except Exception as exc:
            checks.append(
                CheckResult(
                    name=name,
                    passed=False,
                    message=f"Unexpected error: {exc}",
                    severity="critical",
                )
            )

    all_passed = all(c.passed for c in checks)
    return DoctorResult(checks=checks, all_passed=all_passed)


def format_doctor_table(result: DoctorResult) -> Table:
    """Build a rich Table from doctor check results.

    Creates a color-coded table with Check, Status, Message, and
    Fix Hint columns. Passing checks show a green checkmark, critical
    failures show a red X, and warning failures show a yellow warning
    symbol. A summary line shows the pass count.

    Args:
        result: The DoctorResult to format.

    Returns:
        A rich.table.Table ready for console printing.
    """
    table = Table(title="gd-tools Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Fix Hint")

    passed_count = 0
    for check in result.checks:
        if check.passed:
            status = "[green]\u2713[/green]"
            passed_count += 1
        elif check.severity == "critical":
            status = "[red]\u2717[/red]"
        else:
            status = "[yellow]\u26a0[/yellow]"
        table.add_row(check.name, status, check.message, check.fix_hint)

    total = len(result.checks)
    table.caption = f"{passed_count}/{total} checks passed"

    return table
