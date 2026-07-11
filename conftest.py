"""Pytest configuration loaded before any test collection.

Loads environment variables from a local ``.env`` file (gitignored) so
that machine-specific paths like ``GODOT_BIN`` are available to both
the test skip conditions and the production discovery chain without
modifying system environment variables.
"""

import os
from pathlib import Path

_env_file = Path(__file__).parent / ".env"
if _env_file.is_file():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        _key = _key.removeprefix("export ").strip()
        os.environ.setdefault(_key, _val.strip().strip('"').strip("'"))
