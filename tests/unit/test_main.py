"""Tests for the module entry point (__main__.py)."""

import runpy
import sys

import pytest

from gd_tools.__main__ import main
from gd_tools.errors import ConfigError

pytestmark = pytest.mark.unit


class TestPythonDashM:
    """``python -m gd_tools`` tests, executed in-process via ``runpy``.

    ``runpy.run_module`` with ``run_name="__main__"`` is the exact
    machinery ``python -m`` uses, so the module-execution semantics are
    preserved without paying per-test interpreter startup (~1.1s each
    for the original subprocess-based versions).
    """

    @pytest.fixture(autouse=True)
    def _fresh_main_module(self, monkeypatch):
        """Drop the pre-imported ``__main__`` so runpy executes it fresh.

        Without this, runpy warns that ``gd_tools.__main__`` is already
        in ``sys.modules`` (the test module imports it for ``TestMain``)
        and would skip re-execution.
        """
        monkeypatch.delitem(sys.modules, "gd_tools.__main__", raising=False)

    def test_python_m_version(self, monkeypatch, capsys):
        """Test python -m gd_tools --version outputs the correct version."""
        from gd_tools import __version__

        monkeypatch.setattr(sys, "argv", ["gd_tools", "--version"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("gd_tools", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 0
        assert f"gd-tools {__version__}" in capsys.readouterr().out

    def test_python_m_help(self, monkeypatch, capsys):
        """Test python -m gd_tools --help exits with code 0."""
        monkeypatch.setattr(sys, "argv", ["gd_tools", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("gd_tools", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 0
        assert "Usage:" in capsys.readouterr().out

    def test_python_m_test_stub_exit_code_2(self, monkeypatch, capsys):
        """Test python -m gd_tools test exits with code 2 (stub)."""
        monkeypatch.setattr(sys, "argv", ["gd_tools", "test"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("gd_tools", run_name="__main__", alter_sys=True)
        assert exc_info.value.code == 2


class TestMain:
    """Unit tests for the main() function."""

    def test_main_version(self, monkeypatch):
        """Test main() with --version exits 0."""
        monkeypatch.setattr("sys.argv", ["gd-tools", "--version"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_help(self, monkeypatch):
        """Test main() with --help exits 0."""
        monkeypatch.setattr("sys.argv", ["gd-tools", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_main_test_stub_exit_code_2(self, monkeypatch):
        """Test main() with test command exits 2 (stub)."""
        monkeypatch.setattr("sys.argv", ["gd-tools", "test"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_main_catches_gd_tools_error(self, monkeypatch):
        """Test main() catches GdToolsError and exits with error code."""
        monkeypatch.setattr("sys.argv", ["gd-tools", "test"])

        def mock_cli():
            raise ConfigError("Config not found")

        monkeypatch.setattr("gd_tools.__main__.cli", mock_cli)

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2
