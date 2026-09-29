"""Unit tests for the atomic migration apply flow."""

import json

import pytest

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

from gd_tools.migration.apply import ApplyResult, apply_migration
from gd_tools.migration.scan import (
    MigrationReport,
    MigrationScanError,
    SuiteReport,
    build_migration_report,
)
from gd_tools.native_test.protocol import NativeSuite, NativeTest, RuntimeMode

pytestmark = pytest.mark.unit

_GUT_SOURCE = "extends GutTest\n\n\nfunc test_x() -> void:\n\tpending_test()\n"
_RENAMED = "extends GdToolsTest\n\n\nfunc test_x() -> void:\n\tpending_test()\n"


def _suite(path: str, runtime: RuntimeMode) -> NativeSuite:
    return NativeSuite(
        name=path.rsplit("/", 1)[-1].removesuffix(".gd"),
        path=path,
        runtime=runtime,
        tests=[NativeTest(name="test_x")],
    )


def _write_suite(tmp_path, rel_path: str, source: str) -> None:
    file_path = tmp_path / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(source, encoding="utf-8")


class TestApplyMigration:
    def test_rewrites_gut_suites_on_disk(self, tmp_path):
        """--apply rewrites the extends declaration of every GUT suite."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        result = apply_migration(tmp_path, report, {})

        assert (tmp_path / "test/legacy.gd").read_text(
            encoding="utf-8"
        ) == _RENAMED
        assert result.rewritten == ("res://test/legacy.gd",)

    def test_native_suites_are_never_touched(self, tmp_path):
        """Suites already on the native runtime stay untouched."""

        _write_suite(tmp_path, "test/native.gd", "extends GdToolsTest\n")
        report = build_migration_report(
            tmp_path, [_suite("res://test/native.gd", RuntimeMode.NATIVE)]
        )

        result = apply_migration(tmp_path, report, {})

        assert result.rewritten == ()

    def test_gutconfig_is_translated_into_gd_tools_toml(self, tmp_path):
        """Translatable gutconfig keys land in gd-tools.toml [test]."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        (tmp_path / ".gutconfig.json").write_text(
            json.dumps({"dirs": ["res://test/"], "prefix": "check_"}),
            encoding="utf-8",
        )
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        result = apply_migration(
            tmp_path, report, {"dirs": ["res://test/"], "prefix": "check_"}
        )

        with open(tmp_path / "gd-tools.toml", "rb") as handle:
            data = tomllib.load(handle)
        assert data["test"]["test_dirs"] == ["test"]
        assert data["test"]["prefix"] == "check_"
        assert result.config_updated is True

    def test_gutconfig_file_is_preserved_byte_for_byte(self, tmp_path):
        """The source .gutconfig.json is never modified or deleted."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        gutconfig = tmp_path / ".gutconfig.json"
        original = '{"dirs": ["res://test/"], "log_level": 1}'
        gutconfig.write_text(original, encoding="utf-8")
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        apply_migration(
            tmp_path, report, {"dirs": ["res://test/"], "log_level": 1}
        )

        assert gutconfig.read_text(encoding="utf-8") == original

    def test_existing_config_values_are_never_clobbered(self, tmp_path):
        """Keys already set in gd-tools.toml are left as-is."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        (tmp_path / ".gutconfig.json").write_text(
            json.dumps({"dirs": ["res://test/"]}), encoding="utf-8"
        )
        (tmp_path / "gd-tools.toml").write_text(
            '[test]\ntest_dirs = ["suites"]\n', encoding="utf-8"
        )
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        result = apply_migration(tmp_path, report, {"dirs": ["res://test/"]})

        with open(tmp_path / "gd-tools.toml", "rb") as handle:
            data = tomllib.load(handle)
        assert data["test"]["test_dirs"] == ["suites"]
        assert result.skipped == (("dirs", "test.test_dirs"),)

    def test_config_only_skips_suite_rewrites(self, tmp_path):
        """--config-only translates settings without touching suites."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        (tmp_path / ".gutconfig.json").write_text(
            json.dumps({"dirs": ["res://test/"]}), encoding="utf-8"
        )
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        result = apply_migration(
            tmp_path, report, {"dirs": ["res://test/"]}, config_only=True
        )

        assert (tmp_path / "test/legacy.gd").read_text(
            encoding="utf-8"
        ) == _GUT_SOURCE
        assert result.rewritten == ()
        assert result.config_updated is True

    def test_cli_flags_are_reported_not_written(self, tmp_path):
        """junit_xml_file becomes a suggested CLI flag in the result."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        (tmp_path / ".gutconfig.json").write_text(
            json.dumps({"junit_xml_file": "res://results.xml"}),
            encoding="utf-8",
        )
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        result = apply_migration(
            tmp_path, report, {"junit_xml_file": "res://results.xml"}
        )

        assert result.cli_flags == (("--junit-xml", "res://results.xml"),)

    def test_unreadable_suite_aborts_before_any_write(self, tmp_path):
        """A read failure raises before a single file is modified."""

        _write_suite(tmp_path, "test/first.gd", _GUT_SOURCE)
        _write_suite(tmp_path, "test/second.gd", _GUT_SOURCE)
        suites = [
            SuiteReport(path="res://test/first.gd", test_count=1),
            SuiteReport(path="res://test/second.gd", test_count=1),
            SuiteReport(path="res://test/missing.gd", test_count=1),
        ]
        report = MigrationReport(suites=tuple(suites), gutconfig_path=None)

        with pytest.raises(MigrationScanError):
            apply_migration(tmp_path, report, {})

        assert (tmp_path / "test/first.gd").read_text(
            encoding="utf-8"
        ) == _GUT_SOURCE
        assert (tmp_path / "test/second.gd").read_text(
            encoding="utf-8"
        ) == _GUT_SOURCE

    def test_no_gutconfig_means_no_config_write(self, tmp_path):
        """Without a gutconfig, gd-tools.toml is not created."""

        _write_suite(tmp_path, "test/legacy.gd", _GUT_SOURCE)
        report = build_migration_report(
            tmp_path, [_suite("res://test/legacy.gd", RuntimeMode.GUT)]
        )

        result = apply_migration(tmp_path, report, {})

        assert not (tmp_path / "gd-tools.toml").exists()
        assert result.config_updated is False

    def test_result_shape(self, tmp_path):
        """ApplyResult exposes rewritten suites and config outcome."""

        result = ApplyResult(
            rewritten=(), config_updated=False, cli_flags=(), skipped=()
        )

        assert result.rewritten == ()


class TestApplySkipsDirtySuites:
    def test_suites_with_unsupported_constructs_are_not_rewritten(
        self, tmp_path
    ):
        """--apply renames only clean suites; dirty files stay untouched."""

        _write_suite(
            tmp_path,
            "test/dirty.gd",
            "extends GutTest\n\n\nfunc test_x() -> void:\n\tparameterize(args)\n",
        )
        _write_suite(tmp_path, "test/clean.gd", _GUT_SOURCE)
        suites = [
            _suite("res://test/dirty.gd", RuntimeMode.GUT),
            _suite("res://test/clean.gd", RuntimeMode.GUT),
        ]
        report = build_migration_report(tmp_path, suites)

        result = apply_migration(tmp_path, report, {})

        assert (tmp_path / "test/dirty.gd").read_text(
            encoding="utf-8"
        ) == "extends GutTest\n\n\nfunc test_x() -> void:\n\tparameterize(args)\n"
        assert (tmp_path / "test/clean.gd").read_text(
            encoding="utf-8"
        ) == _RENAMED
        assert result.rewritten == ("res://test/clean.gd",)
