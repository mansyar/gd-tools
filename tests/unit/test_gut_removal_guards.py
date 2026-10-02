"""Guard tests for the v0.6.0 legacy sweep.

Ensure that dead GUT-era symbols removed by the legacy sweep stay
removed (Track ``legacy_sweep_20261002``). These guards fail if any of
the removed symbols are reintroduced anywhere under ``src/gd_tools``.
"""

from pathlib import Path

import gd_tools.errors
import gd_tools.godot
import gd_tools.init
import gd_tools.test_runner

SRC_DIR = Path(gd_tools.__file__).resolve().parent

FORBIDDEN_SYMBOLS = [
    "GUT_VERSION_MAP",
    "get_gut_version_for_godot",
    "GUTNotInstalledError",
    "is_gut_installed",
    "get_installed_gut_version",
]

FORBIDDEN_OUTPUT_LABELS = [
    "--- GUT stdout ---",
    "--- GUT stderr ---",
]


def test_gut_version_mapping_removed():
    """GUT_VERSION_MAP and get_gut_version_for_godot must stay removed."""
    assert not hasattr(gd_tools.godot, "GUT_VERSION_MAP")
    assert not hasattr(gd_tools.godot, "get_gut_version_for_godot")


def test_gut_not_installed_error_removed():
    """GUTNotInstalledError must stay removed from the error hierarchy."""
    assert not hasattr(gd_tools.errors, "GUTNotInstalledError")


def test_is_gut_installed_removed():
    """is_gut_installed must stay removed from test_runner."""
    assert not hasattr(gd_tools.test_runner, "is_gut_installed")


def test_get_installed_gut_version_removed():
    """get_installed_gut_version must stay removed from init."""
    assert not hasattr(gd_tools.init, "get_installed_gut_version")


def test_no_dead_gut_symbols_in_source():
    """No src/gd_tools module may reference removed GUT symbols."""
    offenders = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for symbol in FORBIDDEN_SYMBOLS:
            if symbol in text:
                offenders.append(f"{path.name}: {symbol}")
    assert offenders == []


def test_no_gut_output_labels_in_source():
    """The stale '--- GUT stdout/stderr ---' labels must stay removed."""
    offenders = []
    for path in sorted(SRC_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for label in FORBIDDEN_OUTPUT_LABELS:
            if label in text:
                offenders.append(f"{path.name}: {label}")
    assert offenders == []