"""Native Godot test runtime support."""

from gd_tools.native_test.protocol import (
    NATIVE_PROTOCOL_VERSION,
    NativeCoverage,
    NativeManifest,
    NativeRunResult,
    NativeSuite,
    NativeTest,
    NativeTestResult,
    RuntimeMode,
    write_json_atomic,
)

__all__ = [
    "NATIVE_PROTOCOL_VERSION",
    "NativeCoverage",
    "NativeManifest",
    "NativeRunResult",
    "NativeSuite",
    "NativeTest",
    "NativeTestResult",
    "RuntimeMode",
    "write_json_atomic",
]
