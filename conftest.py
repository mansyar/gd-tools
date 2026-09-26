"""Pytest configuration loaded before any test collection.

Loads environment variables from a local ``.env`` file (gitignored) so
that machine-specific paths like ``GODOT_BIN`` are available to both
the test skip conditions and the production discovery chain without
modifying system environment variables.

Provides a :func:`godot_bin` fixture that resolves the Godot binary
path from ``GODOT_BIN`` or ``PATH``.  Returns ``None`` when not found
so that unit tests can use it without skipping; integration and e2e
conftest files override the fixture to use :func:`require_godot_binary`.

Godot-dependent suites must not treat a missing Godot the same way in
every environment.  Locally it is a *skip* -- a developer without Godot
installed should not see failures.  In CI it is a *failure*, because
skipping there would report a green run that executed zero tests, which
is strictly worse than a red one.  That split lives in
:func:`require_godot_binary`, shared by both suites, so the two
hand-edited copies cannot drift apart.
"""

import os
import shutil
import subprocess
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


def require_godot_binary(purpose: str) -> str:
    """Resolve the Godot binary, failing in CI but skipping locally.

    Shared by the integration and e2e suites.  The behaviour intentionally
    diverges on the ``CI`` environment variable:

    - ``CI`` unset: a missing Godot *skips*. A developer without Godot
      installed should not see their run go red.
    - ``CI`` set: a missing Godot *fails*. A skip would be reported as a
      passing run that exercised nothing, masking a broken pipeline --
      most dangerously once CI resolves ``GODOT_BIN`` per-OS and a
      silent install failure would turn every matrix job green.

    An empty ``CI`` is treated as unset, since ``CI=`` is exported by some
    shells without a value and must not break local runs.

    Args:
        purpose: What the caller is running, e.g. ``"integration tests"``,
            used in the skip and failure messages.

    Returns:
        The resolved Godot binary path.

    Raises:
        pytest.fail.Exception: If ``CI`` is set and no Godot is found.
        pytest.skip.Exception: If ``CI`` is unset and no Godot is found.
    """
    binary = find_godot_binary()
    if binary is not None:
        return binary

    if os.environ.get("CI"):
        pytest.fail(
            "[Error] Godot binary not found while running "
            f"{purpose}\n"
            "Cause: no Godot was resolved from GODOT_BIN, PATH, or a "
            "platform install location. In CI this is a broken pipeline, "
            "not a reason to skip -- skipping reports a green run that "
            "executed zero tests.\n"
            "Fix: check the Godot install step for this job, then make "
            "the binary reachable by setting GODOT_BIN or adding it to "
            "PATH."
        )
    pytest.skip(
        f"Godot binary not found - set GODOT_BIN or add to PATH to run "
        f"{purpose}"
    )


def import_godot_project(godot_bin: str, project: Path) -> None:
    """Import a generated Godot project, retrying one transient failure.

    Godot's first project import occasionally exits non-zero after reporting a
    completed filesystem scan, typically when the host is under load. The
    scan is idempotent, so a single retry removes that flakiness without
    hiding a genuine import failure, which fails again and is reported here.

    Args:
        godot_bin: Godot executable.
        project: Project directory to import.

    Raises:
        AssertionError: If the import still fails after one retry.
    """
    command = [godot_bin, "--headless", "--path", str(project), "--import"]

    def run() -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )

    completed = run()
    if completed.returncode != 0:
        completed = run()
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.fixture(scope="session")
def godot_bin() -> str | None:
    """Return the Godot binary path or ``None``.

    Unit tests can depend on this fixture without skipping.  Integration
    and e2e conftest files override this fixture to auto-skip when the
    binary is not available.
    """
    return find_godot_binary()
