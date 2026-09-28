"""Unit tests for watch-mode watched-scope resolution and event classification."""

import pytest

from gd_tools.watch.scope import (
    WatchAction,
    classify_event,
    resolve_watched_files,
)

pytestmark = pytest.mark.unit


def _write(root, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("extends Node\n", encoding="utf-8")


def test_resolves_gd_files_under_project_root(tmp_path):
    """Every .gd file under the project root is part of the watch scope."""
    _write(tmp_path, "src/enemy.gd")
    _write(tmp_path, "tests/test_enemy.gd")
    _write(tmp_path, "scripts/util/deep.gd")

    files = resolve_watched_files(tmp_path)

    names = sorted(f.replace("\\", "/") for f in files)
    assert names == [
        "scripts/util/deep.gd",
        "src/enemy.gd",
        "tests/test_enemy.gd",
    ]


def test_standard_directories_are_excluded(tmp_path):
    """Engine cache, tool state, and git internals are never watched."""
    _write(tmp_path, "src/keep.gd")
    _write(tmp_path, ".godot/imported/cached.gd")
    _write(tmp_path, ".gd-tools/artifacts/run-1/cover.gd")
    _write(tmp_path, ".git/hooks/hook.gd")

    files = resolve_watched_files(tmp_path)

    assert [f.replace("\\", "/") for f in files] == ["src/keep.gd"]


def test_gd_tools_addons_are_excluded_but_user_addons_watched(tmp_path):
    """Only the deployed gd-tools addons are excluded from the watch scope."""
    _write(tmp_path, "src/keep.gd")
    _write(tmp_path, "addons/gd-tools-coverage/coverage.gd")
    _write(tmp_path, "addons/gd-tools-test/gd_tools_test.gd")
    _write(tmp_path, "addons/my_addon/custom.gd")

    files = resolve_watched_files(tmp_path)

    names = sorted(f.replace("\\", "/") for f in files)
    assert names == ["addons/my_addon/custom.gd", "src/keep.gd"]


def test_newly_created_files_are_picked_up(tmp_path):
    """Re-resolving the scope sees files created after the first scan."""
    _write(tmp_path, "src/first.gd")
    assert len(resolve_watched_files(tmp_path)) == 1

    _write(tmp_path, "src/second.gd")

    files = resolve_watched_files(tmp_path)
    assert len(files) == 2


@pytest.mark.parametrize(
    ("event_type", "expected"),
    [
        ("modified", WatchAction.RUN),
        ("created", WatchAction.RUN),
        ("deleted", WatchAction.IGNORE),
        ("moved", WatchAction.IGNORE),
        ("unknown-event", WatchAction.IGNORE),
    ],
)
def test_events_are_classified_into_actions(event_type, expected):
    """Modified and created events trigger runs; the rest are ignored."""
    assert classify_event(event_type) is expected
