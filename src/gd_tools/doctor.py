"""Diagnostic command for checking gd-tools project health.

Implements ``gd-tools doctor``, which runs a series of environment
and configuration checks and reports pass/fail status with actionable
fix hints. See TDD \u00a73.6 and PRD \u00a78.
"""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from packaging.version import parse as parse_version
from rich.table import Table

from . import __version__
from .config import GdToolsConfig, find_project_root, load_config
from .errors import ConfigError
from .godot import (
    GodotNotFoundError,
    check_version_compatible,
    find_godot,
)
from .init import (
    COVERAGE_ADDON_FILES,
    EDITOR_PLUGIN_FILES,
    NATIVE_TEST_ADDON_FILES,
)


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


def _legacy_optional_result(
    result: CheckResult,
    required: bool,
) -> CheckResult:
    """Downgrade an optional legacy diagnostic to a non-blocking warning."""
    if required:
        return result
    return CheckResult(
        name=result.name,
        passed=True,
        message=f"{result.message} (optional for native runtime)",
        fix_hint=result.fix_hint,
        severity="warning",
    )


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


# --- Legacy GUT Advisory ---


def check_legacy_gut(
    project_root: Path,
    test_dirs: list[str] | None = None,
) -> CheckResult:
    """Detect legacy GUT artifacts and advise migration (informational).

    The GUT compatibility bridge was removed in v0.6.0, so leftover
    GUT artifacts no longer run anywhere. Their presence never fails
    the doctor report; the check only surfaces what ``gd-tools
    migrate`` would handle.

    Args:
        project_root: Path to the Godot project root.
        test_dirs: Test directories to scan for ``GutTest`` suites;
            defaults to the gd-tools defaults (``test`` and ``tests``).

    Returns:
        CheckResult: always passes; the message lists any legacy
        artifacts found and the fix hint points at ``gd-tools migrate``.
    """
    if test_dirs is None:
        test_dirs = ["test", "tests"]
    artifacts: list[str] = []

    if (project_root / "addons" / "gut").is_dir():
        artifacts.append("addons/gut (GUT addon)")
    if (project_root / ".gutconfig.json").is_file():
        artifacts.append(".gutconfig.json")

    _gut_suite_re = re.compile(r"^\s*extends\s+GutTest(?:\s|$)", re.MULTILINE)
    suites: list[str] = []
    for test_dir in test_dirs:
        base = project_root / test_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.gd")):
            try:
                source = path.read_text(encoding="utf-8")
            except OSError:  # pragma: no cover - unreadable file
                continue
            if _gut_suite_re.search(source):
                suites.append(path.relative_to(project_root).as_posix())
    if suites:
        listing = ", ".join(suites[:5])
        if len(suites) > 5:
            listing += f" (+{len(suites) - 5} more)"
        artifacts.append(f"GutTest suites: {listing}")

    if not artifacts:
        return CheckResult(
            name="Legacy GUT",
            passed=True,
            message="No legacy GUT artifacts found",
        )
    return CheckResult(
        name="Legacy GUT",
        passed=True,
        message=(
            "Legacy GUT artifacts found (unused since the v0.6.0 "
            f"bridge removal): {'; '.join(artifacts)}"
        ),
        fix_hint=(
            "Run `gd-tools migrate` to move suites to the native "
            "runtime, or remove the artifacts. See docs/gut-migration.md."
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
    # All addon files present — check version file for staleness.
    version_file = cov_dir / "_version.txt"
    if not version_file.exists():
        return CheckResult(
            name="Coverage Addon",
            passed=True,
            message="Coverage addon installed (version file missing)",
            fix_hint="Run `gd-tools init` to create the version file.",
            severity="warning",
        )

    addon_version = version_file.read_text(encoding="utf-8").strip()

    is_stale = True
    try:
        addon_parsed = parse_version(addon_version)
        package_parsed = parse_version(__version__)
        is_stale = addon_parsed < package_parsed
    except (TypeError, ValueError):
        # Unparseable version — treated as stale (raw string shown).
        pass

    if is_stale:
        return CheckResult(
            name="Coverage Addon",
            passed=True,
            message=(
                f"Coverage addon is outdated (v{addon_version} "
                f"deployed, v{__version__} available)"
            ),
            fix_hint="Run `gd-tools init` to update.",
            severity="warning",
        )

    return CheckResult(
        name="Coverage Addon",
        passed=True,
        message=f"Coverage addon installed (v{addon_version})",
    )


def check_native_test_addon(project_root: Path) -> CheckResult:
    """Check that the bundled native test runtime is present and current.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether the native addon is usable.
    """
    addon_dir = project_root / "addons" / "gd-tools-test"
    missing = [
        name
        for name in NATIVE_TEST_ADDON_FILES
        if not (addon_dir / name).is_file()
    ]
    if missing:
        return CheckResult(
            name="Native Test Addon",
            passed=False,
            message=f"Missing native test files: {', '.join(missing)}",
            fix_hint="Run `gd-tools init` to deploy the native test addon.",
            severity="critical",
        )
    version_file = addon_dir / "_version.txt"
    if not version_file.exists():
        return CheckResult(
            name="Native Test Addon",
            passed=True,
            message="Native test addon installed (version file missing)",
            fix_hint="Run `gd-tools init` to create the version file.",
            severity="warning",
        )
    addon_version = version_file.read_text(encoding="utf-8").strip()
    is_stale = True
    try:
        is_stale = parse_version(addon_version) < parse_version(__version__)
    except (TypeError, ValueError):
        pass
    if is_stale:
        return CheckResult(
            name="Native Test Addon",
            passed=True,
            message=(
                f"Native test addon is outdated (v{addon_version} deployed, "
                f"v{__version__} available)"
            ),
            fix_hint="Run `gd-tools init` to update.",
            severity="warning",
        )
    return CheckResult(
        name="Native Test Addon",
        passed=True,
        message=f"Native test addon installed (v{addon_version})",
    )


def check_editor_plugin(project_root: Path) -> CheckResult:
    """Check that the optional editor plugin addon is present and current.

    Args:
        project_root: Path to the Godot project root.

    Returns:
        CheckResult indicating whether the editor plugin is usable.
        Missing files are a non-blocking warning because the plugin
        is an optional editor enhancement.
    """
    addon_dir = project_root / "addons" / "gd-tools-editor"
    missing = [
        name for name in EDITOR_PLUGIN_FILES if not (addon_dir / name).is_file()
    ]
    if missing:
        return CheckResult(
            name="Editor Plugin",
            passed=False,
            message=f"Missing editor plugin files: {', '.join(missing)}",
            fix_hint="Run `gd-tools init` to deploy the editor plugin.",
            severity="warning",
        )
    version_file = addon_dir / "_version.txt"
    if not version_file.exists():
        return CheckResult(
            name="Editor Plugin",
            passed=True,
            message="Editor plugin installed (version file missing)",
            fix_hint="Run `gd-tools init` to create the version file.",
            severity="warning",
        )
    addon_version = version_file.read_text(encoding="utf-8").strip()
    is_stale = True
    try:
        is_stale = parse_version(addon_version) < parse_version(__version__)
    except (TypeError, ValueError):
        pass
    if is_stale:
        return CheckResult(
            name="Editor Plugin",
            passed=True,
            message=(
                f"Editor plugin is outdated (v{addon_version} deployed, "
                f"v{__version__} available)"
            ),
            fix_hint="Run `gd-tools init` to update.",
            severity="warning",
        )
    return CheckResult(
        name="Editor Plugin",
        passed=True,
        message=f"Editor plugin installed (v{addon_version})",
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


def check_autoload(
    project_root: Path,
    required: bool = True,
) -> CheckResult:
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
        return _legacy_optional_result(
            CheckResult(
                name="Autoload",
                passed=False,
                message="project.godot not found",
                fix_hint="Run `gd-tools init` to deploy coverage addon.",
                severity="critical",
            ),
            required,
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
    if not required:
        return CheckResult(
            name="Autoload",
            passed=True,
            message="_GDTCoverage autoload is not registered (optional for native runtime)",
        )
    return CheckResult(
        name="Autoload",
        passed=False,
        message="_GDTCoverage autoload is not registered",
        fix_hint="Run `gd-tools init` to deploy the coverage autoload and register it.",
        severity="critical",
    )


# --- Orchestration ---


def run_doctor() -> DoctorResult:
    """Run all diagnostic checks and return aggregated result.

    Resolves project root, loads config, and runs all 12 checks in
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

    check_specs = [
        ("Godot Binary", lambda: check_godot_binary(config)),
        ("Godot Version", lambda: check_godot_version(config)),
        (
            "Native Test Addon",
            lambda: check_native_test_addon(project_root),
        ),
        (
            "Legacy GUT",
            lambda: check_legacy_gut(project_root, config.test.test_dirs),
        ),
        ("Coverage Addon", lambda: check_coverage_addon(project_root)),
        (
            "Editor Plugin",
            lambda: check_editor_plugin(project_root),
        ),
        ("gd-tools.toml", lambda: check_gd_tools_toml(project_root)),
        ("GD Toolkit", lambda: check_gdtoolkit()),
        (
            "Autoload",
            lambda: check_autoload(project_root, required=False),
        ),
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
