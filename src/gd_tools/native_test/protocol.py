"""Versioned data contracts for the native Godot test runtime."""

from __future__ import annotations

import json
import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

NATIVE_PROTOCOL_VERSION = 2


def _reject_relative_segments(value: str) -> str:
    """Reject a resource path that walks out of the project root.

    Args:
        value: A ``res://`` path declared by a suite.

    Returns:
        The unchanged path when every segment is a real project segment.

    Raises:
        ValueError: If a segment is ``.`` or ``..``.
    """
    segments = value.removeprefix("res://").split("/")
    if any(segment in {".", ".."} for segment in segments):
        raise ValueError("path segments must not be '.' or '..': " f"{value!r}")
    return value


_ResourcePath = Annotated[
    str,
    StringConstraints(pattern=r"^res://.+$"),
    AfterValidator(_reject_relative_segments),
]


class RuntimeMode(str, Enum):
    """Supported test execution runtimes."""

    NATIVE = "native"
    GUT = "gut"


class NativeExecutionMode(str, Enum):
    """Display modes supported by one isolated native suite process."""

    HEADLESS = "headless"
    WINDOWED = "windowed"


class NativeSuiteIntegration(BaseModel):
    """Suite-level scene, resource, and display defaults."""

    model_config = ConfigDict(extra="forbid")

    scene: _ResourcePath | None = None
    resources: dict[str, _ResourcePath] = Field(default_factory=dict)
    mode: NativeExecutionMode = NativeExecutionMode.HEADLESS


class NativeTestIntegration(BaseModel):
    """Effective scene and resource metadata for one native test attempt."""

    model_config = ConfigDict(extra="forbid")

    scene: _ResourcePath | None = None
    resources: dict[str, _ResourcePath] = Field(default_factory=dict)


class NativeCoverage(BaseModel):
    """Coverage settings passed to a native test run."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    plan_path: Path | None = None
    output_path: Path | None = None


class NativeTest(BaseModel):
    """A single native test method in a suite manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str
    tags: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=5.0, gt=0)
    retries: int = Field(default=0, ge=0)
    integration: NativeTestIntegration | None = None


class NativeSuite(BaseModel):
    """A native test suite and its selected test methods."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    tests: list[NativeTest] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    integration: NativeSuiteIntegration | None = None


class NativeManifest(BaseModel):
    """The complete contract passed from Python to the Godot runner."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal[2] = NATIVE_PROTOCOL_VERSION
    project_root: Path
    runtime: RuntimeMode
    suites: list[NativeSuite] = Field(default_factory=list)
    coverage: NativeCoverage = Field(default_factory=NativeCoverage)


class NativePreflightResult(BaseModel):
    """Structured metadata resolved by the Godot integration preflight."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal[2] = NATIVE_PROTOCOL_VERSION
    status: Literal["ok", "error"]
    suites: list[NativeSuite] = Field(default_factory=list)
    error: str | None = None

    @model_validator(mode="after")
    def _validate_status_error(self) -> NativePreflightResult:
        """Keep preflight status and error text internally consistent."""
        if self.status == "ok" and self.error is not None:
            raise ValueError("successful preflight cannot include an error")
        if self.status == "error" and (
            self.error is None or not self.error.strip()
        ):
            raise ValueError("failed preflight requires actionable error text")
        return self


class NativeTestResult(BaseModel):
    """The result of one native test method."""

    model_config = ConfigDict(extra="forbid")

    suite: str
    name: str
    status: Literal[
        "passed",
        "failed",
        "skipped",
        "pending",
        "error",
        "timeout",
        "crashed",
    ]
    duration_seconds: float = Field(default=0.0, ge=0)
    attempts: int = Field(default=1, ge=1)
    message: str = ""
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    engine_errors: list[str] = Field(default_factory=list)
    engine_warnings: list[str] = Field(default_factory=list)


class NativeRunResult(BaseModel):
    """The final native result for a test command."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal[2] = NATIVE_PROTOCOL_VERSION
    run_id: str
    status: Literal["passed", "failed", "error", "cancelled"]
    tests: list[NativeTestResult] = Field(default_factory=list)
    coverage_data_path: Path | None = None
    artifact_index_path: Path | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    engine_errors: list[str] = Field(default_factory=list)
    engine_warnings: list[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""


def write_json_atomic(path: Path, value: BaseModel) -> Path:
    """Serialize a Pydantic model to JSON without leaving partial files.

    The temporary file is created beside the destination so the final
    ``os.replace`` is atomic on the supported local filesystems.

    Args:
        path: Destination JSON path.
        value: Pydantic model to serialize.

    Returns:
        The destination path.

    Raises:
        OSError: If the temporary file or final replacement cannot be written.
    """
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
            json.dump(
                value.model_dump(mode="json"),
                temporary_file,
                indent=2,
                sort_keys=True,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, path)
        return path
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
