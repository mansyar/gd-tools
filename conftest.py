"""Pytest configuration loaded before any test collection.

Loads environment variables from a local ``.env`` file (gitignored) so
that machine-specific paths like ``GODOT_BIN`` are available to both
the test skip conditions and the production discovery chain without
modifying system environment variables.

Provides a :func:`godot_bin` fixture that resolves the Godot binary
path from ``GODOT_BIN`` or ``PATH``.  Returns ``None`` when not found
so that unit tests can use it without skipping; integration and e2e
conftest files override the fixture to auto-skip when Godot is absent.
"""

import os
import shutil
from pathlib import Path

import pytest

_env_file = Path(__file__).parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        _key = _key.removeprefix("export ").strip()
        os.environ.setdefault(_key, _val.strip().strip('"').strip("'"))


def find_godot_binary() -> str | None:
    """Resolve the Godot binary path.

    Resolution order:
    1. ``GODOT_BIN`` environment variable (set via .env or shell).
    2. ``shutil.which("godot")`` or ``shutil.which("godot4")`` on PATH.

    Returns the binary path as a string, or ``None`` if not found.
    """
    env_bin = os.environ.get("GODOT_BIN")
    if env_bin and Path(env_bin).is_file():
        return env_bin
    return shutil.which("godot") or shutil.which("godot4")


@pytest.fixture(scope="session")
def godot_bin() -> str | None:
    """Return the Godot binary path or ``None``.

    Unit tests can depend on this fixture without skipping.  Integration
    and e2e conftest files override this fixture to auto-skip when the
    binary is not available.
    """
    return find_godot_binary()
