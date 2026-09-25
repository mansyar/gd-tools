"""Unit tests for native test discovery and selection."""

from pathlib import Path

import pytest

from gd_tools.native_test.discovery import (
    NativeDiscoveryError,
    discover_native_suites,
)

pytestmark = pytest.mark.unit


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _native_suite(path: Path) -> None:
    _write(
        path,
        """extends GdToolsTest
class_name ExampleSuite
const TAGS = [\"smoke\"]

func test_addition() -> void:
    pass

func test_async_wait() -> void:
    pass
""",
    )


def test_discovery_finds_native_suites_and_test_methods(tmp_path):
    """Native suites expose their class, tags, and test methods."""
    (tmp_path / "project.godot").touch()
    _native_suite(tmp_path / "test" / "example_test.gd")

    suites = discover_native_suites(tmp_path, test_dirs=["test"])

    assert len(suites) == 1
    assert suites[0].name == "ExampleSuite"
    assert suites[0].path == "res://test/example_test.gd"
    assert suites[0].tags == ["smoke"]
    assert [test.name for test in suites[0].tests] == [
        "test_addition",
        "test_async_wait",
    ]


def test_discovery_applies_configured_timeout_and_retries(tmp_path):
    """Configured execution defaults are carried into every manifest test."""
    (tmp_path / "project.godot").touch()
    _native_suite(tmp_path / "test" / "example_test.gd")

    suites = discover_native_suites(
        tmp_path,
        test_dirs=["test"],
        timeout_seconds=1.25,
        retries=2,
    )

    assert all(test.timeout_seconds == 1.25 for test in suites[0].tests)
    assert all(test.retries == 2 for test in suites[0].tests)


def test_discovery_applies_suite_and_test_filters(tmp_path):
    """Suite and exact test filters narrow the native manifest."""
    (tmp_path / "project.godot").touch()
    _native_suite(tmp_path / "test" / "example_test.gd")

    suite = discover_native_suites(
        tmp_path,
        test_dirs=["test"],
        suite="ExampleSuite",
        test="test_addition",
    )

    assert len(suite) == 1
    assert [test.name for test in suite[0].tests] == ["test_addition"]


def test_discovery_applies_tags_and_deduplicates_directories(tmp_path):
    """Tag selection and duplicate directories remain deterministic."""
    (tmp_path / "project.godot").touch()
    _native_suite(tmp_path / "test" / "example_test.gd")

    suites = discover_native_suites(
        tmp_path,
        test_dirs=["test", "test"],
        tags=["smoke"],
    )

    assert len(suites) == 1
    assert suites[0].tags == ["smoke"]


def test_discovery_ignores_non_native_scripts(tmp_path):
    """Production scripts and non-native suites are not collected."""
    (tmp_path / "project.godot").touch()
    _write(
        tmp_path / "test" / "not_a_suite.gd",
        "extends Node\n\nfunc test_helper() -> void:\n    pass\n",
    )

    assert discover_native_suites(tmp_path, test_dirs=["test"]) == []


def test_discovery_reports_gut_only_project_with_legacy_hint(tmp_path):
    """A GUT-only project gets an actionable migration error."""
    (tmp_path / "project.godot").touch()
    _write(
        tmp_path / "test" / "legacy_test.gd",
        "extends GutTest\n\nfunc test_legacy() -> void:\n    pass\n",
    )

    with pytest.raises(NativeDiscoveryError, match=r"--runtime gut"):
        discover_native_suites(tmp_path, test_dirs=["test"])
