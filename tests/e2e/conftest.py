"""Shared fixtures for end-to-end tests.

E2E tests exercise full gd-tools workflows against a real Godot 4.5+
binary and a sample Godot project.  The ``godot_bin`` fixture
auto-skips the entire test when the binary is not available.
"""

from pathlib import Path

import pytest

from conftest import find_godot_binary

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def godot_bin():
    """Return the Godot binary path or skip the test.

    This overrides the root conftest's ``godot_bin`` fixture (which
    returns ``None``) to auto-skip E2E tests when Godot is not
    available.
    """
    binary = find_godot_binary()
    if binary is None:
        pytest.skip(
            "Godot binary not found — set GODOT_BIN or add to PATH "
            "to run E2E tests"
        )
    return binary


@pytest.fixture(scope="session")
def sample_project_path() -> Path:
    """Path to the sample Godot project fixture."""
    return FIXTURES_DIR / "projects" / "sample_project"
