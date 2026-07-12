"""Tests for the gd_tools package."""

import pytest

pytestmark = pytest.mark.unit


def test_version():
    """Test that __version__ is defined and equals '0.1.0'."""
    from gd_tools import __version__

    assert __version__ == "0.1.0"
