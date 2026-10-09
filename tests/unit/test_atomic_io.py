"""Unit tests for the shared crash-safe file-write helpers.

The native test runtime and the coverage reporter both write artifacts
that a user or a CI system reads back later; a process killed mid-write
used to leave a truncated file behind. Durable writes go through
:mod:`gd_tools.atomic_io`, and these tests pin the guarantees: replace
semantics, no leftover temporaries, and an untouched destination when
the final rename fails.
"""

import json
import os
from pathlib import Path

import pytest

from gd_tools.atomic_io import (
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
)

pytestmark = pytest.mark.unit


def test_atomic_write_json_writes_sorted_indented_document(tmp_path):
    """JSON is written indent=2, key-sorted, with a trailing newline."""
    path = tmp_path / "out.json"
    payload = {"b": 2, "a": {"y": [1, 2], "x": True}}

    atomic_write_json(path, payload)

    expected = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert path.read_text(encoding="utf-8") == expected


def test_atomic_write_json_replaces_existing_file(tmp_path):
    """A rewrite replaces the destination and leaves no temporaries."""
    path = tmp_path / "out.json"
    path.write_text('{"old": true}', encoding="utf-8")

    atomic_write_json(path, {"new": 1})

    assert path.read_text(encoding="utf-8") == '{\n  "new": 1\n}\n'
    assert sorted(item.name for item in tmp_path.iterdir()) == ["out.json"]


def test_atomic_write_json_creates_missing_parents(tmp_path):
    """Missing parent directories are created, not an error."""
    path = tmp_path / "nested" / "deep" / "out.json"

    atomic_write_json(path, {"ok": True})

    assert path.is_file()


def test_atomic_write_json_preserves_insertion_order_when_unsorted(tmp_path):
    """``sort_keys=False`` keeps the payload's insertion order."""
    path = tmp_path / "out.json"
    payload = {"z": 1, "a": 2}

    atomic_write_json(path, payload, sort_keys=False)

    assert path.read_text(encoding="utf-8") == '{\n  "z": 1,\n  "a": 2\n}\n'


def test_atomic_write_json_rejects_non_serializable_payload(tmp_path):
    """A payload JSON cannot encode raises and leaves no file behind."""
    path = tmp_path / "out.json"

    with pytest.raises(TypeError):
        atomic_write_json(path, {"path": Path(".")})

    assert not path.exists()
    assert sorted(item.name for item in tmp_path.iterdir()) == []


def test_failed_json_replace_keeps_original_and_cleans_up(
    tmp_path, monkeypatch
):
    """A failed final rename must neither clobber the file nor litter."""
    path = tmp_path / "out.json"
    path.write_text('{"original": true}', encoding="utf-8")

    def boom(src, dst):
        raise OSError("disk on fire")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError, match="disk on fire"):
        atomic_write_json(path, {"new": 1})

    assert path.read_text(encoding="utf-8") == '{"original": true}'
    assert sorted(item.name for item in tmp_path.iterdir()) == ["out.json"]


def test_atomic_write_text_replaces_existing_file(tmp_path):
    """A rewrite replaces the destination and leaves no temporaries."""
    path = tmp_path / "out.txt"
    path.write_text("old", encoding="utf-8")

    atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "new"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["out.txt"]


def test_atomic_write_text_creates_missing_parents(tmp_path):
    """Missing parent directories are created, not an error."""
    path = tmp_path / "nested" / "out.txt"

    atomic_write_text(path, "x")

    assert path.read_text(encoding="utf-8") == "x"


def test_atomic_write_text_accepts_empty_content(tmp_path):
    """An empty write still produces the destination file."""
    path = tmp_path / "marker"

    atomic_write_text(path, "")

    assert path.is_file()
    assert path.read_text(encoding="utf-8") == ""


def test_atomic_write_bytes_round_trips_raw_bytes(tmp_path):
    """Bytes are written verbatim, including non-UTF-8 sequences."""
    path = tmp_path / "out.bin"
    payload = b"\xff\xfe<?xml?>"

    atomic_write_bytes(path, payload)

    assert path.read_bytes() == payload


def test_failed_replace_keeps_original_and_cleans_up(tmp_path, monkeypatch):
    """A failed final rename must neither clobber the file nor litter."""
    path = tmp_path / "out.txt"
    path.write_text("original", encoding="utf-8")

    def boom(src, dst):
        raise OSError("disk on fire")

    monkeypatch.setattr(os, "replace", boom)

    with pytest.raises(OSError, match="disk on fire"):
        atomic_write_text(path, "new")

    assert path.read_text(encoding="utf-8") == "original"
    assert sorted(item.name for item in tmp_path.iterdir()) == ["out.txt"]
