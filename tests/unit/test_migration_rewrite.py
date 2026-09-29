"""Unit tests for the conservative GUT base-class rewriter."""

import pytest

from gd_tools.migration.rewrite import generate_diff, rewrite_suite

pytestmark = pytest.mark.unit

_SIMPLE = "extends GutTest\n\n\nfunc test_it() -> void:\n\tassert_true(true)\n"
_RENAMED = (
    "extends GdToolsTest\n\n\nfunc test_it() -> void:\n\tassert_true(true)\n"
)


class TestRewriteSuite:
    def test_renames_the_extends_declaration(self):
        """`extends GutTest` becomes `extends GdToolsTest`."""

        result = rewrite_suite(_SIMPLE)

        assert result.new_source == _RENAMED

    def test_change_records_the_line_number(self):
        """The rewrite records which line changed."""

        result = rewrite_suite(_SIMPLE)

        assert result.changed_lines == (1,)
        assert result.changes[0].old == "extends GutTest"

    def test_comment_after_extends_is_preserved(self):
        """Trailing comments on the extends line survive the rename."""

        result = rewrite_suite("extends GutTest  # base\n")

        assert result.new_source == "extends GdToolsTest  # base\n"
        assert result.changed_lines == (1,)

    def test_indented_extends_is_not_rewritten(self):
        """Only real declarations are rewritten, never indented text."""

        source = '\tvar x = "extends GutTest"\n'

        result = rewrite_suite(source)

        assert result.new_source == source
        assert result.changed_lines == ()

    def test_gdtools_test_suite_is_left_alone(self):
        """Already-native suites produce no changes."""

        result = rewrite_suite("extends GdToolsTest\n")

        assert result.new_source == "extends GdToolsTest\n"
        assert result.changed_lines == ()

    def test_unknown_base_is_left_alone(self):
        """Suites extending other bases are untouched."""

        source = "extends Node\n"

        result = rewrite_suite(source)

        assert result.new_source == source
        assert result.changed_lines == ()


class TestGenerateDiff:
    def test_diff_shows_the_rename(self):
        """The diff marks the extends line as changed."""

        diff = generate_diff("res://test/legacy.gd", _SIMPLE, _RENAMED)

        assert "-extends GutTest" in diff
        assert "+extends GdToolsTest" in diff

    def test_diff_names_the_suite_path(self):
        """The diff header carries the res:// path."""

        diff = generate_diff("res://test/legacy.gd", _SIMPLE, _RENAMED)

        assert "res://test/legacy.gd" in diff

    def test_no_changes_produce_empty_diff(self):
        """Clean suites yield an empty diff string."""

        diff = generate_diff("res://test/clean.gd", _SIMPLE, _SIMPLE)

        assert diff == ""
