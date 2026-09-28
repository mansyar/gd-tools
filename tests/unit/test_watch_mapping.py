"""Unit tests for watch-mode file-to-suite convention mapping."""

from pathlib import Path

import pytest

from gd_tools.native_test.protocol import NativeSuite
from gd_tools.watch.mapping import map_changed_file

pytestmark = pytest.mark.unit


def _suite(relative_posix_path: str) -> NativeSuite:
    return NativeSuite(name=Path(relative_posix_path).stem, path=relative_posix_path)


def test_maps_source_file_to_test_prefix_suite(tmp_path):
    """foo.gd maps to a sibling test_foo.gd suite."""
    suites = [_suite("res://tests/test_enemy.gd")]

    result = map_changed_file(
        tmp_path / "src" / "enemy.gd", tmp_path, suites
    )

    assert result == "res://tests/test_enemy.gd"


def test_maps_source_file_to_suffix_suite(tmp_path):
    """foo.gd maps to a sibling foo_test.gd suite."""
    suites = [_suite("res://tests/enemy_test.gd")]

    result = map_changed_file(
        tmp_path / "src" / "enemy.gd", tmp_path, suites
    )

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

    result = map_changed_file(
        tmp_path / "src" / "player.gd", tmp_path, suites
    )

    assert result is None


def test_mapping_respects_active_suite_filter(tmp_path):
    """A sibling suite present on disk but absent from the selected set does not match."""
    suites: list[NativeSuite] = []

    result = map_changed_file(
        tmp_path / "src" / "enemy.gd", tmp_path, suites
    )

    assert result is None


def test_file_outside_project_root_maps_to_none(tmp_path):
    """A changed path outside the project root maps to nothing."""
    suites = [_suite("res://tests/test_enemy.gd")]

    result = map_changed_file(
        tmp_path.parent / "elsewhere" / "enemy.gd", tmp_path, suites
    )

    assert result is None