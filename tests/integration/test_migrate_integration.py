"""Integration tests for the `gd-tools migrate` command."""

import json

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.integration

_CLEAN_GUT = "extends GutTest\n\n\nfunc test_x() -> void:\n\tpending_test()\n"
_RENAMED = "extends GdToolsTest\n\n\nfunc test_x() -> void:\n\tpending_test()\n"
_NATIVE = (
    "extends GdToolsTest\n\n\nfunc test_x() -> void:\n\tassert_true(true)\n"
)


def _write(path, rel_path: str, content: str) -> None:
    file_path = path / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


class TestMigrateCommand:
    def test_dry_run_reports_and_writes_nothing(self, tmp_path):
        """Default mode prints the report and exits 1 without changes."""

        _write(tmp_path, "test/legacy.gd", _CLEAN_GUT)
        _write(
            tmp_path, ".gutconfig.json", json.dumps({"dirs": ["res://test/"]})
        )
        runner = CliRunner()

        result = runner.invoke(cli, ["migrate", str(tmp_path)])

        assert result.exit_code == 1
        assert "Migration Report" in result.output
        assert "res://test/legacy.gd" in result.output
        assert "+extends GdToolsTest" in result.output
        assert (tmp_path / "test/legacy.gd").read_text(
            encoding="utf-8"
        ) == _CLEAN_GUT
        assert not (tmp_path / "gd-tools.toml").exists()

    def test_native_project_without_gutconfig_exits_zero(self, tmp_path):
        """A fully native project has nothing to migrate."""

        _write(tmp_path, "test/native.gd", _NATIVE)
        runner = CliRunner()

        result = runner.invoke(cli, ["migrate", str(tmp_path)])

        assert result.exit_code == 0
        assert "Nothing to migrate" in result.output

    def test_apply_rewrites_and_translates_config(self, tmp_path):
        """--apply renames clean suites and writes the translated config."""

        _write(tmp_path, "test/legacy.gd", _CLEAN_GUT)
        _write(
            tmp_path, ".gutconfig.json", json.dumps({"dirs": ["res://test/"]})
        )
        runner = CliRunner()

        result = runner.invoke(cli, ["migrate", "--apply", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / "test/legacy.gd").read_text(
            encoding="utf-8"
        ) == _RENAMED
        with open(tmp_path / "gd-tools.toml", "rb") as handle:
            import tomllib

            data = tomllib.load(handle)
        assert data["test"]["test_dirs"] == ["test"]

    def test_config_only_leaves_suites_untouched(self, tmp_path):
        """--config-only translates settings without rewriting suites."""

        _write(tmp_path, "test/legacy.gd", _CLEAN_GUT)
        _write(
            tmp_path, ".gutconfig.json", json.dumps({"dirs": ["res://test/"]})
        )
        runner = CliRunner()

        result = runner.invoke(cli, ["migrate", "--config-only", str(tmp_path)])

        assert result.exit_code == 0
        assert (tmp_path / "test/legacy.gd").read_text(
            encoding="utf-8"
        ) == _CLEAN_GUT
        assert (tmp_path / "gd-tools.toml").exists()

    def test_invalid_gutconfig_exits_two(self, tmp_path):
        """Unparseable config files are infrastructure errors."""

        _write(tmp_path, "test/legacy.gd", _CLEAN_GUT)
        _write(tmp_path, ".gutconfig.json", "{not json")
        runner = CliRunner()

        result = runner.invoke(cli, ["migrate", str(tmp_path)])

        assert result.exit_code == 2
