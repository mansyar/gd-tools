"""Tests for the gd_tools package."""

import pytest

pytestmark = pytest.mark.unit


def test_version():
    """Test that __version__ is defined and is a non-empty string."""
    from gd_tools import __version__

    assert isinstance(__version__, str)
    assert __version__ != ""
