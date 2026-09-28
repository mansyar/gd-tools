"""Static scan of bridge suites for GUT constructs the bridge cannot run.

The scan runs in Python before any Godot process spawns so an unsupported
construct fails the whole run before any test executes, with a per-file list
of constructs and migration guidance (spec FR-3).
"""

from __future__ import annotations

import re
from pathlib import Path

from gd_tools.errors import GdToolsError

from .protocol import NativeSuite, RuntimeMode

MIGRATION_DOC = "docs/gut-migration.md"

# Longest names first so regex alternation captures the full construct name
# (``assert_property_with_backing_variable`` rather than ``assert_property``).
_UNSUPPORTED_NAMES: tuple[str, ...] = sorted(
    (
        # Mocking.
        "double",
        "partial_double",
        "stub",
        # Parameterization.
        "parameterize",
        "use_parameters",
        # Mock assertions.
        "assert_called",
        "assert_call_count",
        # Property, orphan, and interactive assertions.
        "assert_setget",
        "assert_accessors",
        "assert_exports",
        "assert_property",
        "assert_freed",
        "assert_no_new_orphans",
        "pause_before_teardown",
        # Engine error and push diagnostics.
        "assert_engine_error",
        "assert_push_",
    ),
    key=len,
    reverse=True,
)

_UNSUPPORTED_CALL_RE = re.compile(
    rf"(?<![\w.])((?:{'|'.join(re.escape(name) for name in _UNSUPPORTED_NAMES)})"
    r"\w*)\s*\("
)


class BridgeScanError(GdToolsError):
    """Bridge suites use GUT constructs outside the supported subset."""


def scan_bridge_suites(project_root: Path, suites: list[NativeSuite]) -> None:
    """Fail when a bridge suite calls an unsupported GUT helper.

    Args:
        project_root: Godot project root used to resolve ``res://`` paths.
        suites: Discovered suites; only ``RuntimeMode.GUT`` suites are scanned.

    Raises:
        BridgeScanError: If any bridge suite calls an unsupported construct.
    """
    findings: dict[str, dict[str, int]] = {}
    for suite in suites:
        if suite.runtime is not RuntimeMode.GUT:
            continue
        source_path = project_root / suite.path.removeprefix("res://")
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _UNSUPPORTED_CALL_RE.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            suite_findings = findings.setdefault(suite.path, {})
            suite_findings.setdefault(match.group(1), line)

    if findings:
        raise BridgeScanError(_format_error(findings))


def _plural(count: int, singular: str) -> str:
    """Return ``<count> <word>`` with a plural suffix when needed."""
    return f"{count} {singular}{'' if count == 1 else 's'}"


def _format_error(findings: dict[str, dict[str, int]]) -> str:
    """Build the per-file, actionable error message for scan findings."""
    construct_count = sum(len(names) for names in findings.values())
    lines = [
        f"The GUT compatibility bridge does not support "
        f"{_plural(construct_count, 'construct')} used in "
        f"{_plural(len(findings), 'bridge suite')}:",
        "",
    ]
    for suite_path, constructs in findings.items():
        lines.append(f"{suite_path}:")
        lines.extend(
            f"  - {name} (line {line})"
            for name, line in sorted(
                constructs.items(), key=lambda item: item[1]
            )
        )
        lines.append("")
    lines.extend(
        (
            "Migrate these constructs to GdToolsTest or remove them. See "
            f"{MIGRATION_DOC} for the supported subset and migration steps.",
        )
    )
    return "\n".join(lines)
