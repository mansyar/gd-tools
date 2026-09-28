"""Unit tests for the watch-mode event source abstraction and watchdog adapter."""

import os
import time
from types import SimpleNamespace

import pytest

from gd_tools.watch.observer import (
    FileEvent,
    WatchdogEventSource,
    _relative_posix,
)
from gd_tools.watch.scope import is_watched_path

pytestmark = pytest.mark.unit


def _write(root, relative: str, content: str = "extends Node\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _collect(source, predicate, timeout=3.0):
    """Poll the event source until predicate holds or the timeout elapses."""
    deadline = time.monotonic() + timeout
    collected: list[FileEvent] = []
    generator = source.events()
    while time.monotonic() < deadline:
        event = next(generator)
        if event is not None:
            collected.append(event)
            if predicate(collected):
                return collected
    return collected


def test_is_watched_path_accepts_scope_files():
    """Plain .gd paths inside the project are watched."""
    assert is_watched_path("src/enemy.gd") is True
    assert is_watched_path("addons/my_addon/custom.gd") is True


def test_is_watched_path_rejects_non_gd_and_excluded():
    """Non-.gd files and standard excludes are not watched."""
    assert is_watched_path("src/enemy.tscn") is False
    assert is_watched_path(".godot/imported/cache.gd") is False
    assert is_watched_path(".gd-tools/artifacts/run/cover.gd") is False
    assert is_watched_path("addons/gd-tools-coverage/coverage.gd") is False


def test_adapter_reports_created_gd_file(tmp_path):
    """Creating a watched .gd file yields a created FileEvent."""
    source = WatchdogEventSource(tmp_path)
    try:
        _write(tmp_path, "src/enemy.gd")
        events = _collect(
            source, lambda evs: any(e.event_type == "created" for e in evs)
        )
        created = [e for e in events if e.event_type == "created"]
        assert created and created[0].path == "src/enemy.gd"
    finally:
        source.stop()


def test_adapter_reports_modified_gd_file(tmp_path):
    """Modifying a watched .gd file yields a modified FileEvent."""
    _write(tmp_path, "src/enemy.gd")
    source = WatchdogEventSource(tmp_path)
    try:
        time.sleep(0.3)
        path = tmp_path / "src" / "enemy.gd"
        path.write_text("extends Node\n# touched\n", encoding="utf-8")
        events = _collect(
            source, lambda evs: any(e.event_type == "modified" for e in evs)
        )
        modified = [e for e in events if e.event_type == "modified"]
        assert modified and modified[0].path == "src/enemy.gd"
    finally:
        source.stop()


def test_adapter_reports_deleted_gd_file(tmp_path):
    """Deleting a watched .gd file yields a deleted FileEvent."""
    _write(tmp_path, "src/enemy.gd")
    source = WatchdogEventSource(tmp_path)
    try:
        time.sleep(0.3)
        (tmp_path / "src" / "enemy.gd").unlink()
        events = _collect(
            source, lambda evs: any(e.event_type == "deleted" for e in evs)
        )
        deleted = [e for e in events if e.event_type == "deleted"]
        assert deleted and deleted[0].path == "src/enemy.gd"
    finally:
        source.stop()


def test_adapter_ignores_non_gd_files(tmp_path):
    """Non-.gd file activity produces no events."""
    source = WatchdogEventSource(tmp_path)
    try:
        _write(tmp_path, "src/scene.tscn")
        _write(tmp_path, "notes.txt", content="hello\n")
        events = _collect(source, lambda evs: len(evs) > 0, timeout=1.0)
        assert events == []
    finally:
        source.stop()


def test_adapter_ignores_excluded_directories(tmp_path):
    """Events inside standard excludes are filtered out."""
    source = WatchdogEventSource(tmp_path)
    try:
        _write(tmp_path, ".godot/imported/cache.gd")
        _write(tmp_path, "addons/gd-tools-test/gd_tools_test.gd")
        events = _collect(source, lambda evs: len(evs) > 0, timeout=1.0)
        assert events == []
    finally:
        source.stop()


def test_adapter_stop_terminates_event_stream(tmp_path):
    """After stop(), the events generator finishes instead of blocking."""
    source = WatchdogEventSource(tmp_path)
    generator = source.events()
    next(generator, None)
    source.stop()
    assert next(generator, None) is None


@pytest.mark.skipif(os.name != "nt", reason="Windows path prefix")
def test_relative_posix_handles_extended_length_prefix(tmp_path):
    """Windows \\?\ paths resolve to project-relative posix paths."""
    extended = "\\\\?\\" + str(tmp_path / "src" / "enemy.gd")
    assert _relative_posix(extended, tmp_path) == "src/enemy.gd"


def test_relative_posix_outside_root_returns_none(tmp_path):
    """Paths outside the project root resolve to None."""
    outside = tmp_path.parent / "elsewhere.gd"
    assert _relative_posix(str(outside), tmp_path) is None


def test_enqueue_survives_unresolvable_paths(tmp_path):
    """Out-of-scope watchdog events are dropped without raising."""
    handler = WatchdogEventSource(tmp_path)._handler()
    stranger = SimpleNamespace(
        event_type="modified",
        src_path=str(tmp_path.parent / "elsewhere.gd"),
    )
    handler.on_any_event(stranger)
