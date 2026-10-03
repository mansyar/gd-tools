"""Unit tests for the shared crash-safe file-write helpers.

The native test runtime and the coverage reporter both write artifacts
that a user or a CI system reads back later; a process killed mid-write
used to leave a truncated file behind. Durable writes go through
:mod:`gd_tools.atomic_io`, and these tests pin the guarantees: replace
semantics, no leftover temporaries, and an untouched destination when
the final rename fails.
"""

import os

import pytest

from gd_tools.atomic_io import atomic_write_bytes, atomic_write_text

pytestmark = pytest.mark.unit


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
