"""Unit tests for the CI-aware Godot requirement guard.

``require_godot_binary()`` lives in the root ``conftest.py`` and is shared
by the integration and e2e suites.  Its contract:

- **Locally** (no ``CI``): a missing Godot *skips*.  A developer without
  Godot installed should not see failures.
- **In CI** (``CI`` set): a missing Godot *fails*.  Skipping would report a
  green run that executed zero tests, which is worse than a red one.

The CI branch is the regression this file exists to pin.  It matters most
once the CI workflow resolves ``GODOT_BIN`` per-OS: a silent Godot install
failure would otherwise turn every Godot matrix job green while running
nothing at all.
"""

import pytest
from _pytest.outcomes import Failed, Skipped

import conftest
from conftest import require_godot_binary

pytestmark = pytest.mark.unit

# --- Local behaviour: skip, not fail ---


def test_require_godot_binary_skips_locally_when_godot_missing(monkeypatch):
    """Without CI set, a missing Godot skips instead of failing."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(conftest, "find_godot_binary", lambda: None)

    with pytest.raises(BaseException) as excinfo:
        require_godot_binary("integration tests")

    assert isinstance(excinfo.value, Skipped)


def test_require_godot_binary_skip_message_names_the_fix(monkeypatch):
    """The local skip message names the missing binary and how to fix it."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(conftest, "find_godot_binary", lambda: None)

    with pytest.raises(BaseException) as excinfo:
        require_godot_binary("integration tests")

    message = str(excinfo.value)
    assert "Godot binary not found" in message
    assert "GODOT_BIN" in message
    assert "integration tests" in message


# --- CI behaviour: fail, not skip (the regression that matters) ---


def test_require_godot_binary_fails_in_ci_when_godot_missing(monkeypatch):
    """In CI a missing Godot raises Failed, never Skipped.

    A ``Skipped`` here would be reported by pytest as a skipped -- i.e.
    passing -- test, so the type is asserted explicitly rather than
    relying on ``pytest.raises(Failed)``, which would let a skip through
    unnoticed.
    """
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(conftest, "find_godot_binary", lambda: None)

    with pytest.raises(BaseException) as excinfo:
        require_godot_binary("integration tests")

    assert isinstance(excinfo.value, Failed), (
        "A missing Godot in CI must raise Failed (the pipeline is broken); "
        f"got {type(excinfo.value).__name__}, which would report a green "
        "run that executed zero tests"
    )


def test_require_godot_binary_ci_failure_message_names_the_fix(monkeypatch):
    """The CI failure message names the missing binary and how to fix it."""
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(conftest, "find_godot_binary", lambda: None)

    with pytest.raises(BaseException) as excinfo:
        require_godot_binary("E2E tests")

    message = str(excinfo.value)
    assert "Godot binary not found" in message
    assert "GODOT_BIN" in message
    assert "E2E tests" in message


# --- Happy path ---


def test_require_godot_binary_returns_path_in_ci(monkeypatch):
    """With CI set and a binary present, the resolved path is returned."""
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(
        conftest, "find_godot_binary", lambda: "/opt/godot/godot"
    )

    assert require_godot_binary("integration tests") == "/opt/godot/godot"


def test_require_godot_binary_returns_path_locally(monkeypatch):
    """With CI unset and a binary present, the resolved path is returned."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setattr(
        conftest, "find_godot_binary", lambda: "/opt/godot/godot"
    )

    assert require_godot_binary("integration tests") == "/opt/godot/godot"


# --- CI detection edge cases ---


def test_require_godot_binary_treats_empty_ci_var_as_not_ci(monkeypatch):
    """An empty CI var must not trigger a failure.

    ``CI=`` is set-but-unset in some environments; failing there would
    break local runs that merely export the variable without a value.
    """
    monkeypatch.setenv("CI", "")
    monkeypatch.setattr(conftest, "find_godot_binary", lambda: None)

    with pytest.raises(BaseException) as excinfo:
        require_godot_binary("integration tests")

    assert isinstance(excinfo.value, Skipped)
