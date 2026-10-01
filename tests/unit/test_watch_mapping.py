"""Unit tests for watch-mode file-to-suite convention mapping."""

from pathlib import Path

import pytest

from gd_tools.native_test.protocol import NativeSuite
from gd_tools.watch.mapping import map_changed_file, select_suites_for_changes

pytestmark = pytest.mark.unit


def _suite(relative_posix_path: str) -> NativeSuite:
    return NativeSuite(
        name=Path(relative_posix_path).stem, path=relative_posix_path
    )


def test_maps_source_file_to_test_prefix_suite(tmp_path):
    """foo.gd maps to a sibling test_foo.gd suite."""
    suites = [_suite("res://tests/test_enemy.gd")]

    result = map_changed_file(tmp_path / "src" / "enemy.gd", tmp_path, suites)

    assert result == "res://tests/test_enemy.gd"


def test_maps_source_file_to_suffix_suite(tmp_path):
    """foo.gd maps to a sibling foo_test.gd suite."""
    suites = [_suite("res://tests/enemy_test.gd")]

    result = map_changed_file(tmp_path / "src" / "enemy.gd", tmp_path, suites)

    assert result == "res://tests/enemy_test.gd"


def test_prefix_convention_wins_when_both_exist(tmp_path):
    """test_foo.gd takes precedence over foo_test.gd."""
    suites = [
        _suite("res://tests/foo_test.gd"),
        _suite("res://tests/test_foo.gd"),
    ]

    result = map_changed_file(tmp_path / "src" / "foo.gd", tmp_path, suites)

    assert result == "res://tests/test_foo.gd"


def test_changed_suite_file_maps_to_itself(tmp_path):
    """Editing a suite file re-runs that suite."""
    suites = [_suite("res://tests/test_enemy.gd")]

    result = map_changed_file(
        tmp_path / "tests" / "test_enemy.gd", tmp_path, suites
    )

    assert result == "res://tests/test_enemy.gd"


def test_same_directory_match_is_preferred_over_cross_directory(tmp_path):
    """A same-directory suite wins over a cross-directory stem match."""
    suites = [
        _suite("res://tests/test_enemy.gd"),
        _suite("res://src/test_enemy.gd"),
    ]

    result = map_changed_file(tmp_path / "src" / "enemy.gd", tmp_path, suites)

    assert result == "res://src/test_enemy.gd"


def test_no_match_returns_none(tmp_path):
    """A changed file with no convention sibling maps to nothing."""
    suites = [_suite("res://tests/test_enemy.gd")]

    result = map_changed_file(tmp_path / "src" / "player.gd", tmp_path, suites)

    assert result is None


def test_mapping_respects_active_suite_filter(tmp_path):
    """A sibling suite present on disk but absent from the selected set does not match."""
    suites: list[NativeSuite] = []

    result = map_changed_file(tmp_path / "src" / "enemy.gd", tmp_path, suites)

    assert result is None


def test_file_outside_project_root_maps_to_none(tmp_path):
    """A changed path outside the project root maps to nothing."""
    suites = [_suite("res://tests/test_enemy.gd")]

    result = map_changed_file(
        tmp_path.parent / "elsewhere" / "enemy.gd", tmp_path, suites
    )

    assert result is None


class TestSelectSuitesForChanges:
    """select_suites_for_changes partitions changed files into selected
    suites and unmapped paths (shared by watch mode and test --changed)."""

    def test_selects_only_mapped_suites(self, tmp_path):
        """Changed sources narrow the suite list to their mapped suites."""
        suites = [
            _suite("res://tests/test_enemy.gd"),
            _suite("res://tests/test_player.gd"),
        ]

        selected, unmapped = select_suites_for_changes(
            ["src/enemy.gd"], tmp_path, suites
        )

        assert [suite.path for suite in selected] == [
            "res://tests/test_enemy.gd"
        ]
        assert unmapped == []

    def test_preserves_discovery_order(self, tmp_path):
        """Selected suites keep discovery order regardless of change order."""
        suites = [
            _suite("res://tests/test_enemy.gd"),
            _suite("res://tests/test_player.gd"),
        ]

        selected, _ = select_suites_for_changes(
            ["src/player.gd", "src/enemy.gd"], tmp_path, suites
        )

        assert [suite.path for suite in selected] == [
            "res://tests/test_enemy.gd",
            "res://tests/test_player.gd",
        ]

    def test_unmapped_paths_are_partitioned_for_fallback(self, tmp_path):
        """Unmapped changed paths are returned so callers can fall back."""
        suites = [_suite("res://tests/test_enemy.gd")]

        selected, unmapped = select_suites_for_changes(
            ["src/enemy.gd", "src/unknown.gd"], tmp_path, suites
        )

        assert [suite.path for suite in selected] == [
            "res://tests/test_enemy.gd"
        ]
        assert unmapped == ["src/unknown.gd"]

    def test_deleted_path_maps_by_name(self, tmp_path):
        """A deleted source file still maps via the naming convention."""
        suites = [_suite("res://tests/test_enemy.gd")]

        selected, unmapped = select_suites_for_changes(
            ["src/enemy.gd"], tmp_path, suites
        )

        assert [suite.path for suite in selected] == [
            "res://tests/test_enemy.gd"
        ]
        assert unmapped == []

    def test_respects_already_filtered_suites(self, tmp_path):
        """Mapping only considers the suites passed in (active filters)."""
        suites = [_suite("res://tests/test_player.gd")]

        selected, unmapped = select_suites_for_changes(
            ["src/enemy.gd"], tmp_path, suites
        )

        assert selected == []
        assert unmapped == ["src/enemy.gd"]

    def test_changed_suite_maps_to_itself(self, tmp_path):
        """A changed path that is itself a selected suite maps to itself."""
        suites = [_suite("res://tests/test_enemy.gd")]

        selected, unmapped = select_suites_for_changes(
            ["tests/test_enemy.gd"], tmp_path, suites
        )

        assert [suite.path for suite in selected] == [
            "res://tests/test_enemy.gd"
        ]
        assert unmapped == []

    def test_duplicate_mappings_are_deduplicated(self, tmp_path):
        """Two changed paths mapping to the same suite select it once."""
        suites = [
            _suite("res://tests/test_enemy.gd"),
            _suite("res://tests/test_player.gd"),
        ]

        selected, unmapped = select_suites_for_changes(
            ["src/enemy.gd", "src/other/enemy.gd"], tmp_path, suites
        )

        assert [suite.path for suite in selected] == [
            "res://tests/test_enemy.gd"
        ]
        assert unmapped == []
