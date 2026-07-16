"""Unit tests for the verbosity context module.

Tests the Verbosity enum (QUIET, DEFAULT, VERBOSE) and the context
accessors get_verbosity() / set_verbosity() that store and retrieve
the active verbosity level.
"""

import pytest

from gd_tools.verbosity import Verbosity, get_verbosity, set_verbosity

pytestmark = pytest.mark.unit


# --- Verbosity enum ---


def test_verbosity_has_quiet():
    """Verbosity enum has a QUIET member."""
    assert hasattr(Verbosity, "QUIET")


def test_verbosity_has_default():
    """Verbosity enum has a DEFAULT member."""
    assert hasattr(Verbosity, "DEFAULT")


def test_verbosity_has_verbose():
    """Verbosity enum has a VERBOSE member."""
    assert hasattr(Verbosity, "VERBOSE")


def test_verbosity_three_members():
    """Verbosity enum has exactly three members."""
    assert len(list(Verbosity)) == 3


# --- get_verbosity / set_verbosity ---


def test_get_verbosity_default_is_default():
    """get_verbosity() returns DEFAULT before any set_verbosity() call."""
    set_verbosity(Verbosity.DEFAULT)  # reset to default
    assert get_verbosity() == Verbosity.DEFAULT


def test_set_verbosity_to_quiet():
    """set_verbosity(QUIET) updates the active level."""
    set_verbosity(Verbosity.QUIET)
    assert get_verbosity() == Verbosity.QUIET


def test_set_verbosity_to_verbose():
    """set_verbosity(VERBOSE) updates the active level."""
    set_verbosity(Verbosity.VERBOSE)
    assert get_verbosity() == Verbosity.VERBOSE


def test_set_verbosity_back_to_default():
    """set_verbosity(DEFAULT) restores the default level."""
    set_verbosity(Verbosity.VERBOSE)
    set_verbosity(Verbosity.DEFAULT)
    assert get_verbosity() == Verbosity.DEFAULT
