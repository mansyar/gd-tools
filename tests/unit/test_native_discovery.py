"""Unit tests for native test discovery and selection."""

from pathlib import Path

import pytest

from gd_tools.native_test.discovery import (
    NativeDiscoveryError,
    discover_native_suites,
)
from gd_tools.native_test.protocol import RuntimeMode

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


def _gut_suite(path: Path) -> None:
    _write(
        path,
        """extends GutTest
class_name LegacySuite
const TAGS = [\"legacy\"]

func test_legacy_assertion() -> void:
    pass

func test_legacy_signal() -> void:
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


def test_discovery_preserves_explicit_file_selector(tmp_path):
    """An explicit file selector does not broaden to sibling suites."""
    (tmp_path / "project.godot").touch()
    selected = tmp_path / "test" / "selected.gd"
    _native_suite(selected)
    _native_suite(tmp_path / "test" / "sibling.gd")

    suites = discover_native_suites(tmp_path, test_dirs=[str(selected)])

    assert [suite.name for suite in suites] == ["ExampleSuite"]
    assert suites[0].path == "res://test/selected.gd"


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


def test_discovery_ignores_non_suite_helper_scripts(tmp_path):
    """Scripts without test methods in test dirs are not collected."""
    (tmp_path / "project.godot").touch()
    _write(
        tmp_path / "test" / "helper.gd",
        "extends Node\n\nfunc collect_value() -> int:\n    return 4\n",
    )

    assert discover_native_suites(tmp_path, test_dirs=["test"]) == []


def test_discovery_rejects_guttest_suite_with_removal_guidance(tmp_path):
    """A GutTest suite fails discovery: the bridge was removed in v0.6.0."""
    (tmp_path / "project.godot").touch()
    _gut_suite(tmp_path / "test" / "legacy_test.gd")

    with pytest.raises(NativeDiscoveryError, match=r"legacy_test\.gd"):
        discover_native_suites(tmp_path, test_dirs=["test"])


def test_discovery_marks_native_suites_with_native_runtime(tmp_path):
    """Native suites carry the native runtime explicitly."""
    (tmp_path / "project.godot").touch()
    _native_suite(tmp_path / "test" / "example_test.gd")

    suites = discover_native_suites(tmp_path, test_dirs=["test"])

    assert len(suites) == 1
    assert suites[0].runtime is RuntimeMode.NATIVE


def test_discovery_keeps_stable_path_order(tmp_path):
    """Discovered suites are ordered by path, not discovery timing."""
    (tmp_path / "project.godot").touch()
    _native_suite(tmp_path / "test" / "zeta_example_test.gd")
    _native_suite(tmp_path / "test" / "alpha_example_test.gd")
    _native_suite(tmp_path / "test" / "mid_example_test.gd")

    suites = discover_native_suites(tmp_path, test_dirs=["test"])

    assert [suite.path for suite in suites] == [
        "res://test/alpha_example_test.gd",
        "res://test/mid_example_test.gd",
        "res://test/zeta_example_test.gd",
    ]


def test_discovery_errors_when_test_file_extends_unknown_base(tmp_path):
    """A test file with test methods and an unknown base fails discovery."""
    (tmp_path / "project.godot").touch()
    _write(
        tmp_path / "test" / "stray_test.gd",
        "extends Node\n\nfunc test_thing() -> void:\n    pass\n",
    )

    with pytest.raises(NativeDiscoveryError, match=r"stray_test\.gd.*Node"):
        discover_native_suites(tmp_path, test_dirs=["test"])


def _parameterized_suite(path: Path) -> None:
    _write(
        path,
        """extends GdToolsTest
class_name ParameterizedSuite

func before_all() -> void:
    parameterize(["value", "label"], [[1, "admin"], [2, "user"]])

func test_ranked(value: int, label: String) -> void:
    pass

func test_plain() -> void:
    pass
""",
    )


def test_discovery_includes_parameterized_test_methods(tmp_path):
    """Parameterized methods are discovered alongside zero-arg methods."""
    (tmp_path / "project.godot").touch()
    _parameterized_suite(tmp_path / "test" / "parameterized_test.gd")

    suites = discover_native_suites(tmp_path, test_dirs=["test"])

    assert len(suites) == 1
    assert [test.name for test in suites[0].tests] == [
        "test_ranked",
        "test_plain",
    ]


def test_discovery_finds_suite_with_only_parameterized_methods(tmp_path):
    """A suite whose tests are all parameterized is still discovered."""
    (tmp_path / "project.godot").touch()
    _write(
        tmp_path / "test" / "only_parameterized_test.gd",
        """extends GdToolsTest
class_name OnlyParameterizedSuite

func before_all() -> void:
    parameterize(["value"], [["a"], ["b"]])

func test_value(value: String) -> void:
    pass
""",
    )

    suites = discover_native_suites(tmp_path, test_dirs=["test"])

    assert len(suites) == 1
    assert [test.name for test in suites[0].tests] == ["test_value"]


def test_discovery_case_selector_matches_parameterized_method(tmp_path):
    """A ``name[case]`` selector selects the method owning that case."""
    (tmp_path / "project.godot").touch()
    _parameterized_suite(tmp_path / "test" / "parameterized_test.gd")

    suites = discover_native_suites(
        tmp_path,
        test_dirs=["test"],
        test="test_ranked[admin]",
    )

    assert len(suites) == 1
    assert [test.name for test in suites[0].tests] == ["test_ranked[admin]"]


def test_discovery_case_selector_defers_case_existence_to_preflight(tmp_path):
    """A ``name[case]`` selector keeps the method; preflight resolves cases."""
    (tmp_path / "project.godot").touch()
    _parameterized_suite(tmp_path / "test" / "parameterized_test.gd")

    suites = discover_native_suites(
        tmp_path,
        test_dirs=["test"],
        test="test_plain[admin]",
    )

    # Discovery is textual: whether ``test_plain`` has cases is only known
    # after preflight resolves parameterization, so the selector survives
    # verbatim for preflight to validate.
    assert len(suites) == 1
    assert [test.name for test in suites[0].tests] == ["test_plain[admin]"]


def test_discovery_case_selector_requires_bracket_suffix(tmp_path):
    """A selector without brackets keeps exact method-name matching."""
    (tmp_path / "project.godot").touch()
    _parameterized_suite(tmp_path / "test" / "parameterized_test.gd")

    suites = discover_native_suites(
        tmp_path,
        test_dirs=["test"],
        test="test_rankedx",
    )

    assert suites == []
