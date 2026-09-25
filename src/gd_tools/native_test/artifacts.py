"""Run-scoped artifact layout and retention for native test execution."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gd_tools.native_test.protocol import NATIVE_PROTOCOL_VERSION

_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VALID_STATUSES = {"passed", "failed", "error", "cancelled"}


class ArtifactPublishError(RuntimeError):
    """Raised when a native artifact index cannot be safely published."""


@dataclass(frozen=True)
class NativeArtifactLayout:
    """Stable paths owned by one native test run."""

    project_root: Path
    run_id: str

    def __post_init__(self) -> None:
        """Validate and canonicalize the path-bearing layout fields."""
        if (
            not self.run_id
            or self.run_id in {".", ".."}
            or _SAFE_RUN_ID.fullmatch(self.run_id) is None
        ):
            raise ValueError(
                "run_id must be a safe path component containing only "
                "letters, digits, '.', '_', or '-'"
            )
        object.__setattr__(
            self, "project_root", Path(self.project_root).resolve()
        )

    @classmethod
    def create(cls, project_root: Path, run_id: str) -> NativeArtifactLayout:
        """Create a layout after validating the run ID path component."""
        return cls(project_root=project_root, run_id=run_id)

    @property
    def artifact_root(self) -> Path:
        """Return the fixed artifact root for the project."""
        return self.project_root / ".gd-tools" / "artifacts"

    @property
    def run_dir(self) -> Path:
        """Return the directory owned by this run."""
        return self.artifact_root / self.run_id

    @property
    def preflight_dir(self) -> Path:
        """Return the metadata preflight directory."""
        return self.run_dir / "preflight"

    @property
    def native_dir(self) -> Path:
        """Return the per-suite runner directory."""
        return self.run_dir / "native"

    @property
    def index_path(self) -> Path:
        """Return the machine-readable artifact index path."""
        return self.run_dir / "artifacts.json"

    def preflight_paths(self) -> dict[str, Path]:
        """Return stable preflight artifact paths."""
        return {
            "manifest": self.preflight_dir / "preflight.manifest.json",
            "result": self.preflight_dir / "preflight.result.json",
            "log": self.preflight_dir / "preflight.log",
        }

    def suite_paths(self, index: int) -> dict[str, Path]:
        """Return stable artifact paths for one suite process."""
        if index < 0:
            raise ValueError("suite artifact index must be non-negative")
        prefix = self.native_dir / f"suite-{index:04d}"
        return {
            "manifest": Path(f"{prefix}.manifest.json"),
            "result": Path(f"{prefix}.result.json"),
            "events": Path(f"{prefix}.events.ndjson"),
            "log": Path(f"{prefix}.log"),
            "coverage": Path(f"{prefix}.coverage.json"),
            "screenshot": Path(f"{prefix}.failure.png"),
        }


def publish_artifact_index(
    layout: NativeArtifactLayout,
    *,
    status: str,
    suite_names: list[str],
    suite_paths: list[dict[str, Path]],
    preflight_paths: dict[str, Path],
) -> Path:
    """Atomically publish one run index, then prune older run directories.

    The index is written before retention runs. If publication fails, the
    previous run remains available for diagnosis.

    Args:
        layout: Run-scoped artifact layout.
        status: Terminal native result status.
        suite_names: Suite names in process order.
        suite_paths: Stable artifact paths in the same order as suite_names.
        preflight_paths: Stable preflight artifact paths.

    Returns:
        The published artifact index path.

    Raises:
        ValueError: If the status or suite metadata is inconsistent.
        ArtifactPublishError: If publication or retention fails.
    """
    if status not in _VALID_STATUSES:
        raise ValueError(f"Unsupported native artifact status: {status}")
    if len(suite_names) != len(suite_paths):
        raise ValueError("suite_names and suite_paths must have equal length")

    suites: list[dict[str, Any]] = []
    for suite_name, paths in zip(suite_names, suite_paths):
        if not suite_name:
            raise ValueError("suite_names cannot contain empty names")
        suites.append(
            {
                "suite": suite_name,
                **{key: str(path) for key, path in paths.items()},
            }
        )

    payload = {
        "protocol_version": NATIVE_PROTOCOL_VERSION,
        "run_id": layout.run_id,
        "status": status,
        "artifact_root": str(layout.artifact_root),
        "run_dir": str(layout.run_dir),
        "preflight": {key: str(path) for key, path in preflight_paths.items()},
        "suites": suites,
    }
    try:
        _write_json_atomic(layout.index_path, payload)
    except (OSError, TypeError, ValueError) as exc:
        raise ArtifactPublishError(
            f"Could not publish native artifact index at {layout.index_path}"
        ) from exc

    try:
        _prune_old_runs(layout.artifact_root, layout.run_dir)
    except OSError as exc:
        raise ArtifactPublishError(
            f"Published native artifact index at {layout.index_path}, but "
            f"could not prune older runs under {layout.artifact_root}"
        ) from exc
    return layout.index_path


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON payload through a neighboring temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _prune_old_runs(artifact_root: Path, current_run_dir: Path) -> None:
    """Remove direct child run directories except the current run."""
    if not artifact_root.is_dir():
        return
    for child in artifact_root.iterdir():
        if child == current_run_dir or not child.is_dir() or child.is_symlink():
            continue
        shutil.rmtree(child)
