"""Unit tests for the v0.6.0 GUT bridge removal contract.

The bridge runtime (shim, auto-routing, deprecation notices) is gone; the
native runtime is the sole test runtime and ``gd-tools migrate`` is the
migration path.
"""

import importlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.errors import ConfigError
from gd_tools.native_test.discovery import discover_native_suites

pytestmark = pytest.mark.unit

REMOVED_MESSAGE = "removed in v0.6.0"
MIGRATION_POINTER = "gd-tools migrate"


def _write_gut_suite(tmp_path: Path) -> Path:
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    suite = test_dir / "legacy_test.gd"
    suite.write_text(
        "extends GutTest\n"
        "\n"
        "\n"
        "func test_something() -> void:\n"
        "\tassert_true(true)\n",
        encoding="utf-8",
    )
    return suite


def test_discovery_rejects_guttest_suites(tmp_path: Path):
    """`extends GutTest` files fail discovery with removal guidance."""
    suite = _write_gut_suite(tmp_path)

    with pytest.raises(ConfigError) as exc_info:
        discover_native_suites(tmp_path, ["test"])

    message = str(exc_info.value)
    assert suite.name in message
    assert REMOVED_MESSAGE in message
    assert MIGRATION_POINTER in message


def test_cli_rejects_runtime_gut_with_removal_message():
    """`--runtime gut` exits 2 with the v0.6.0 removal message."""
    result = CliRunner().invoke(cli, ["test", "--runtime", "gut"])

    assert result.exit_code == 2
    assert REMOVED_MESSAGE in result.output
    assert MIGRATION_POINTER in result.output


def test_cli_rejects_config_runtime_gut_with_removal_message():
    """`test.runtime = "gut"` in config exits 2 with the removal message."""
    from unittest.mock import MagicMock, patch

    config = MagicMock()
    config.test.runtime = "gut"
    with patch("gd_tools.cli.load_config", return_value=config):
        result = CliRunner().invoke(cli, ["test"])

    assert result.exit_code == 2
    assert REMOVED_MESSAGE in result.output
    assert MIGRATION_POINTER in result.output


def test_init_with_gut_option_removed():
    """`init --with-gut` no longer exists (unknown option, exit 2)."""
    result = CliRunner().invoke(cli, ["init", "--with-gut"])

    assert result.exit_code == 2
    assert "no such option" in result.output.lower()


def test_init_help_omits_with_gut():
    """Init help no longer advertises the GUT installation switch."""
    result = CliRunner().invoke(cli, ["init", "--help"])

    assert result.exit_code == 0
    assert "--with-gut" not in result.output


def test_gut_shim_gdscript_is_deleted():
    """The GutTest shim no longer ships in the gd-tools-test addon."""
    gd_tools_pkg = Path(importlib.import_module("gd_tools").__file__).parent
    shim = gd_tools_pkg / "addons" / "gd-tools-test" / "gd_tools_gut_bridge.gd"

    assert not shim.exists()
