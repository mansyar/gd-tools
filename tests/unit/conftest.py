"""Shared fixtures for unit tests.

Unit tests are fast, do not require Godot, and mock all external
dependencies (subprocess, network, filesystem via tmp_path).

Fixtures provided:
- ``read_fixture``: Load text fixture files from ``tests/fixtures/``.
- ``read_json_fixture``: Load and parse JSON fixture files.
- ``mock_subprocess_run``: Factory for mocking ``subprocess.run``.
- ``mock_requests_get``: Factory for mocking ``requests.get``.
- ``mock_godot_on_path``: Context manager that patches ``shutil.which``
  to return a fake Godot binary path.
"""

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def read_fixture():
    """Return a callable that reads text fixtures by relative path."""

    def _read(rel_path: str) -> str:
        return (FIXTURES_DIR / rel_path).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def read_json_fixture():
    """Return a callable that reads and parses JSON fixtures by relative path."""

    def _read(rel_path: str) -> dict | list:
        return json.loads((FIXTURES_DIR / rel_path).read_text(encoding="utf-8"))

    return _read


@pytest.fixture
def mock_subprocess_run():
    """Factory for mocking ``subprocess.run``.

    Usage::

        def test_foo(mock_subprocess_run):
            with mock_subprocess_run(stdout="4.5.stable\\n"):
                ...
    """

    def _mock(
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
        args=None,
    ):
        result = MagicMock()
        result.returncode = returncode
        result.stdout = stdout
        result.stderr = stderr
        result.args = args or []
        return patch("subprocess.run", return_value=result)

    return _mock


@pytest.fixture
def mock_requests_get():
    """Factory for mocking ``requests.get``.

    Usage::

        def test_download(mock_requests_get):
            with mock_requests_get(content=b"zip-data"):
                ...
    """

    def _mock(
        status_code: int = 200,
        content: bytes = b"",
        json_data=None,
    ):
        response = MagicMock()
        response.status_code = status_code
        response.content = content
        if json_data is not None:
            response.json.return_value = json_data
        return patch("requests.get", return_value=response)

    return _mock


@pytest.fixture
def mock_godot_on_path():
    """Context manager that patches ``shutil.which`` to find a fake Godot.

    Usage::

        def test_version(mock_godot_on_path):
            with mock_godot_on_path("/fake/godot"):
                ...
    """

    @contextmanager
    def _ctx(godot_path: str = "/fake/godot"):
        with patch("gd_tools.godot.shutil.which", return_value=godot_path):
            yield godot_path

    return _ctx


@pytest.fixture(autouse=True)
def _mock_cli_update_check():
    """Prevent update check network calls in all unit tests.

    Patches ``gd_tools.cli.check_for_update`` (the reference in cli.py),
    NOT ``gd_tools.update_check.check_for_update`` (the original), so
    tests in test_update_check.py that call the original directly are
    unaffected. Tests that need to control update behaviour override
    this with their own patch on the same target.
    """
    with patch("gd_tools.cli.check_for_update", return_value=None):
        yield


@pytest.fixture(autouse=True)
def _reset_verbosity():
    """Reset verbosity to DEFAULT after each test to avoid state leakage."""
    yield
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.DEFAULT)
