"""Tests for the module entry point (__main__.py)."""

import subprocess
import sys

import pytest

from gd_tools.__main__ import main
from gd_tools.errors import ConfigError

pytestmark = pytest.mark.unit


class TestSubprocess:
    """Subprocess tests for python -m gd_tools."""

    def test_python_m_version(self):
        """Test python -m gd_tools --version outputs the correct version."""
        from gd_tools import __version__

        result = subprocess.run(
            [sys.executable, "-m", "gd_tools", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert f"gd-tools {__version__}" in result.stdout

    def test_python_m_help(self):
        """Test python -m gd_tools --help exits with code 0."""
        result = subprocess.run(
            [sys.executable, "-m", "gd_tools", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout

    def test_python_m_test_stub_exit_code_2(self):
        """Test python -m gd_tools test exits with code 2 (stub)."""
        result = subprocess.run(
            [sys.executable, "-m", "gd_tools", "test"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2


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
