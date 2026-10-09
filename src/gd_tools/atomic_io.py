"""Crash-safe file writes for artifacts read back by users and CI.

Several components persist files that outlive the process writing them:
coverage data, JUnit XML, run markers. A process killed mid-write used
to leave a truncated file behind that downstream tooling then choked on.
The components that persist such files route their writes through
this module: the content is staged in a temporary file beside the destination, flushed
and fsynced, and moved into place with a single ``os.replace``.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_bytes(path: Path | str, payload: bytes) -> Path:
    """Write bytes to ``path`` without leaving partial files.

    The temporary file is created beside the destination so the final
    ``os.replace`` is atomic on the supported local filesystems. A
    failure at any point removes the temporary file and leaves any
    previous content at ``path`` untouched.

    Args:
        path: Destination file path (a :class:`~pathlib.Path` or a
            string, matching the tolerance of the writers it replaces).
        payload: Exact bytes to write.

    Returns:
        The destination path.

    Raises:
        OSError: If the temporary file or final replacement cannot be
            written.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, path)
        return path
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path | str, text: str) -> Path:
    """Write text to ``path`` as UTF-8 without leaving partial files.

    Convenience wrapper around :func:`atomic_write_bytes`.

    Args:
        path: Destination file path (a :class:`~pathlib.Path` or a
            string).
        text: Text to write, encoded as UTF-8.

    Returns:
        The destination path.

    Raises:
        OSError: If the temporary file or final replacement cannot be
            written.
    """
    return atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(
    path: Path | str,
    payload: Any,
    *,
    sort_keys: bool = True,
    indent: int | None = 2,
) -> Path:
    """Serialize ``payload`` as JSON and write it atomically as UTF-8.

    Convenience wrapper around :func:`atomic_write_text` for JSON
    documents. A trailing newline is appended so the file ends cleanly
    for diffing and line-oriented tooling.

    Args:
        path: Destination file path (a :class:`~pathlib.Path` or a
            string).
        payload: JSON-serializable value (dicts, lists, scalars).
        sort_keys: Sort dictionary keys; ``True`` matches the writers
            this helper consolidates.
        indent: JSON indentation depth, or ``None`` for compact output.

    Returns:
        The destination path.

    Raises:
        TypeError, ValueError: If ``payload`` is not JSON-serializable.
        OSError: If the temporary file or final replacement cannot be
            written.
    """
    text = json.dumps(payload, indent=indent, sort_keys=sort_keys) + "\n"
    return atomic_write_text(path, text)
