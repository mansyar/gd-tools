"""Shared fixtures for performance benchmarks.

Benchmarks are opt-in (``GD_TOOLS_RUN_BENCHMARK=1``) and excluded from
CI, but they still need a Godot binary.  The ``godot_bin`` fixture
delegates to :func:`require_godot_binary` so a missing Godot skips
locally instead of erroring partway through a benchmark.
"""

import pytest

from conftest import require_godot_binary


@pytest.fixture(scope="session")
def godot_bin():
    """Return the Godot binary path, skipping locally or failing in CI."""
    return require_godot_binary("performance benchmarks")
