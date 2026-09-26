"""Shared fixtures for end-to-end tests.

E2E tests exercise full gd-tools workflows against a real Godot 4.5+
binary and a sample Godot project.  The ``godot_bin`` fixture delegates
to :func:`require_godot_binary`, which skips when the binary is absent
locally but *fails* when it is absent in CI -- a skip there would
report a green run that executed nothing.
"""

from pathlib import Path

import pytest

from conftest import require_godot_binary

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def godot_bin():
    """Return the Godot binary path, skipping locally or failing in CI.

    This overrides the root conftest's ``godot_bin`` fixture (which
    returns ``None``) so that a missing Godot is an explicit error
    rather than a silent no-op.
    """
    return require_godot_binary("E2E tests")


@pytest.fixture(scope="session")
def sample_project_path() -> Path:
    """Path to the sample Godot project fixture."""
    return FIXTURES_DIR / "projects" / "sample_project"
