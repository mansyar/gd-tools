"""Versioned data contracts for the native Godot test runtime."""

from __future__ import annotations

import json
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

from gd_tools.atomic_io import atomic_write_text

NATIVE_PROTOCOL_VERSION = 3


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


class NativeTestParameters(BaseModel):
    """A parameterization declaration resolved by integration preflight.

    ``names`` lists the parameter names a test method receives per case and
    ``values`` holds one value set per expanded case. An empty ``values``
    list is a valid declaration: the runtime reports the test as skipped.
    """

    model_config = ConfigDict(extra="forbid")

    names: list[str] = Field(min_length=1)
    values: list[list[Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_shape(self) -> NativeTestParameters:
        """Keep parameter names non-empty, unique, and row-consistent."""
        if any(not name.strip() for name in self.names):
            raise ValueError("parameter names must be non-empty strings")
        if len(set(self.names)) != len(self.names):
            raise ValueError("parameter names must be unique")
        for index, row in enumerate(self.values):
            if len(row) != len(self.names):
                raise ValueError(
                    "parameter value set "
                    f"{index} has {len(row)} values; expected {len(self.names)}"
                )
        return self


class NativeTest(BaseModel):
    """A single native test method in a suite manifest."""

    model_config = ConfigDict(extra="forbid")

    name: str
    tags: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=5.0, gt=0)
    retries: int = Field(default=0, ge=0)
    integration: NativeTestIntegration | None = None
    parameters: NativeTestParameters | None = None


class NativeSuite(BaseModel):
    """A native test suite and its selected test methods."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    tests: list[NativeTest] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    integration: NativeSuiteIntegration | None = None
    runtime: RuntimeMode = RuntimeMode.NATIVE


class NativeManifest(BaseModel):
    """The complete contract passed from Python to the Godot runner."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal[3] = NATIVE_PROTOCOL_VERSION
    project_root: Path
    runtime: RuntimeMode
    suites: list[NativeSuite] = Field(default_factory=list)
    coverage: NativeCoverage = Field(default_factory=NativeCoverage)


class NativePreflightResult(BaseModel):
    """Structured metadata resolved by the Godot integration preflight."""

    model_config = ConfigDict(extra="forbid")

    protocol_version: Literal[3] = NATIVE_PROTOCOL_VERSION
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

    protocol_version: Literal[3] = NATIVE_PROTOCOL_VERSION
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
    payload = (
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n"
    )
    return atomic_write_text(path, payload)
