"""Unit tests for the migration scanner and report model."""

import pytest

from gd_tools.migration.scan import (
    ConstructHit,
    MigrationScanError,
    build_migration_report,
    scan_source,
)
from gd_tools.native_test.bridge_scan import find_unsupported_constructs
from gd_tools.native_test.protocol import NativeSuite, NativeTest, RuntimeMode

pytestmark = pytest.mark.unit


def _suite(path: str, runtime: RuntimeMode, test_count: int = 1) -> NativeSuite:
    return NativeSuite(
        name=path.rsplit("/", 1)[-1].removesuffix(".gd"),
        path=path,
        runtime=runtime,
        tests=[NativeTest(name=f"test_{index}") for index in range(test_count)],
    )


class TestScanSource:
    def test_detects_unsupported_constructs_with_line_numbers(self):
        """Each unsupported helper call is reported with its source line."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            '    assert_setget(prop, "value")\n'
            "    assert_freed(node)\n"
        )

        findings = scan_source(source)

        assert findings.unsupported == (
            ConstructHit(name="assert_setget", line=4),
            ConstructHit(name="assert_freed", line=5),
        )
        assert findings.aliases == ()

    def test_reports_every_occurrence_not_only_the_first(self):
        """The migration report needs every site, not a deduplicated one."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            '    assert_setget("res://a.gd")\n'
            '    assert_setget("res://b.gd")\n'
        )

        findings = scan_source(source)

        assert findings.unsupported == (
            ConstructHit(name="assert_setget", line=4),
            ConstructHit(name="assert_setget", line=5),
        )

    def test_ignores_member_calls_on_objects(self):
        """A method call like ``helper.double()`` is not a GUT helper call."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            "    var helper = MyHelper.new()\n"
            "    helper.double()\n"
            "    helper.assert_freed()\n"
        )

        findings = scan_source(source)

        assert findings.unsupported == ()
        assert findings.aliases == ()

    def test_detects_bridge_only_aliases(self):
        """Bridge-only alias calls are reported separately from unsupported."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            "    assert_in(item, container)\n"
            "\n"
            "func test_y() -> void:\n"
            '    pending_test("not written yet")\n'
        )

        findings = scan_source(source)

        assert findings.unsupported == ()
        assert findings.aliases == (
            ConstructHit(name="assert_in", line=4),
            ConstructHit(name="pending_test", line=7),
        )

    def test_does_not_confuse_aliases_with_prefixed_names(self):
        """``assert_invalid_thing`` is not an ``assert_in`` alias call."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            "    assert_invalid_thing()\n"
        )

        findings = scan_source(source)

        assert findings.aliases == ()

    def test_clean_source_reports_nothing(self):
        """The documented supported subset produces no findings."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            "    assert_eq(1 + 1, 2)\n"
            "    await wait_seconds(0.1)\n"
        )

        findings = scan_source(source)

        assert findings.unsupported == ()
        assert findings.aliases == ()


class TestBuildMigrationReport:
    def test_reports_gut_suite_findings(self, tmp_path):
        """A bridge suite's findings land in a per-suite report entry."""
        suite_dir = tmp_path / "test"
        suite_dir.mkdir()
        (suite_dir / "legacy_test.gd").write_text(
            "extends GutTest\n\nfunc test_x() -> void:\n    assert_setget(obj)\n",
            encoding="utf-8",
        )
        suite = _suite("res://test/legacy_test.gd", RuntimeMode.GUT, 3)

        report = build_migration_report(tmp_path, [suite])

        assert len(report.suites) == 1
        suite_report = report.suites[0]
        assert suite_report.path == "res://test/legacy_test.gd"
        assert suite_report.test_count == 3
        assert suite_report.unsupported == (
            ConstructHit(name="assert_setget", line=4),
        )
        assert not suite_report.is_clean

    def test_skips_native_suites(self, tmp_path):
        """Native suites do not run through the bridge and are not scanned."""
        report = build_migration_report(
            tmp_path, [_suite("res://test/native_test.gd", RuntimeMode.NATIVE)]
        )

        assert report.suites == ()

    def test_clean_gut_suite_is_flagged_clean(self, tmp_path):
        """A suite using only supported constructs is reported as clean."""
        suite_dir = tmp_path / "test"
        suite_dir.mkdir()
        (suite_dir / "legacy_test.gd").write_text(
            "extends GutTest\n\nfunc test_x() -> void:\n"
            "    assert_eq(1, 1)\n",
            encoding="utf-8",
        )
        suite = _suite("res://test/legacy_test.gd", RuntimeMode.GUT)

        report = build_migration_report(tmp_path, [suite])

        assert report.suites[0].is_clean
        assert report.suites[0].unsupported == ()

    def test_hits_are_sorted_by_line_within_a_suite(self, tmp_path):
        """Findings are ordered by source line regardless of scan order."""
        suite_dir = tmp_path / "test"
        suite_dir.mkdir()
        (suite_dir / "legacy_test.gd").write_text(
            "extends GutTest\n\nfunc test_x() -> void:\n"
            "    assert_freed(a)\n"
            '    assert_setget(prop, "v")\n',
            encoding="utf-8",
        )
        suite = _suite("res://test/legacy_test.gd", RuntimeMode.GUT)

        report = build_migration_report(tmp_path, [suite])

        assert [hit.line for hit in report.suites[0].unsupported] == [4, 5]

    def test_records_gutconfig_path_when_present(self, tmp_path):
        """An existing .gutconfig.json is noted for translation."""
        (tmp_path / ".gutconfig.json").write_text("{}", encoding="utf-8")

        report = build_migration_report(tmp_path, [])

        assert report.gutconfig_path == "res://.gutconfig.json"

    def test_gutconfig_absent_reports_none(self, tmp_path):
        """A project without .gutconfig.json reports None."""

        report = build_migration_report(tmp_path, [])

        assert report.gutconfig_path is None

    def test_unreadable_suite_raises_migration_scan_error(self, tmp_path):
        """A suite listed but unreadable on disk is an infrastructure error."""
        suite = _suite("res://test/missing_test.gd", RuntimeMode.GUT)

        with pytest.raises(MigrationScanError, match="missing_test.gd"):
            build_migration_report(tmp_path, [suite])


class TestFindUnsupportedConstructs:
    def test_reports_all_occurrences(self):
        """The public helper reports every construct call with its line."""
        source = (
            "extends GutTest\n"
            "\n"
            "func test_x() -> void:\n"
            '    assert_setget(a, "x")\n'
            '    assert_setget(b, "y")\n'
        )

        assert find_unsupported_constructs(source) == [
            ("assert_setget", 4),
            ("assert_setget", 5),
        ]

    def test_clean_source(self):
        """A supported source produces no hits."""
        source = (
            "extends GutTest\n\nfunc test_x() -> void:\n    assert_eq(1, 1)\n"
        )

        assert find_unsupported_constructs(source) == []
