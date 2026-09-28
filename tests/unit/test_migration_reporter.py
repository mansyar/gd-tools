"""Unit tests for the migration report Rich renderer."""

import pytest

from gd_tools.migration.gutconfig import translate_gutconfig
from gd_tools.migration.reporter import render_migration_report
from gd_tools.migration.scan import ConstructHit, MigrationReport, SuiteReport

pytestmark = pytest.mark.unit


def _dirty_suite() -> SuiteReport:
    return SuiteReport(
        path="res://test/legacy_test.gd",
        test_count=3,
        unsupported=(
            ConstructHit(name="double", line=4),
            ConstructHit(name="stub", line=5),
        ),
        aliases=(ConstructHit(name="assert_in", line=7),),
    )


def _clean_suite() -> SuiteReport:
    return SuiteReport(path="res://test/clean_test.gd", test_count=2)


class TestRenderMigrationReport:
    def test_lists_dirty_suite_with_constructs_and_lines(self):
        """Unsupported constructs are shown per suite with line numbers."""

        report = MigrationReport(suites=(_dirty_suite(),))
        rendered = render_migration_report(report)

        assert "[FAIL] res://test/legacy_test.gd" in rendered
        assert "line 4: double" in rendered
        assert "line 5: stub" in rendered
        assert "3 tests" in rendered

    def test_lists_clean_suite_with_ok_marker(self):
        """Clean suites are marked [OK] with no findings."""

        report = MigrationReport(suites=(_clean_suite(),))
        rendered = render_migration_report(report)

        assert "[OK] res://test/clean_test.gd" in rendered
        assert "2 tests" in rendered
        assert "no unsupported constructs" in rendered

    def test_reports_aliases_in_rename_later_section(self):
        """Bridge-only aliases are shown as rename candidates, not errors."""

        report = MigrationReport(suites=(_dirty_suite(),))
        rendered = render_migration_report(report)

        assert "line 7: assert_in" in rendered
        assert "rename later" in rendered.lower()
        # Aliases must not be rendered as failures.
        assert "[FAIL] res://test/legacy_test.gd (3 tests)" in rendered
        assert "[FAIL] res://test/legacy_test.gd (3 tests, " not in rendered

    def test_includes_migration_doc_pointer(self):
        """The report points at the migration documentation."""

        rendered = render_migration_report(MigrationReport(suites=()))

        assert "docs/gut-migration.md" in rendered

    def test_summary_counts_dirty_and_clean_suites(self):
        """The footer summarizes how much work remains."""

        report = MigrationReport(suites=(_dirty_suite(), _clean_suite()))
        rendered = render_migration_report(report)

        assert "1 suite needs migration, 1 suite is ready" in rendered

    def test_gutconfig_rendered_when_present(self):
        """A present .gutconfig.json gets a classification section."""

        report = MigrationReport(
            suites=(),
            gutconfig_path="res://.gutconfig.json",
        )
        translation = translate_gutconfig(
            {
                "dirs": ["res://test/"],
                "should_exit": True,
                "pre_run_script": "res://hooks/pre.gd",
                "log_level": 1,
            }
        )

        rendered = render_migration_report(report, translation=translation)

        assert "res://.gutconfig.json" in rendered
        assert "dirs -> test.test_dirs" in rendered
        assert "should_exit (handled automatically)" in rendered
        assert "pre_run_script (no equivalent, file preserved)" in rendered
        assert "log_level (not in the migration inventory)" in rendered

    def test_gutconfig_absent_renders_no_section(self):
        """No .gutconfig.json means no config section."""

        rendered = render_migration_report(MigrationReport(suites=()))

        assert "gutconfig" not in rendered.lower().replace(
            "docs/gut-migration.md", ""
        )

    def test_no_bridge_suites_message(self):
        """A project without bridge suites renders an explicit message."""

        rendered = render_migration_report(MigrationReport(suites=()))

        assert "No GUT suites found" in rendered
