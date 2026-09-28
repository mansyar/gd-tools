"""Unit tests for the bridge preflight static scan."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.native_test import command
from gd_tools.native_test.bridge_scan import BridgeScanError, scan_bridge_suites
from gd_tools.native_test.protocol import NativeSuite, NativeTest, RuntimeMode

pytestmark = pytest.mark.unit


def _bridge_suite(path: Path, source: str) -> NativeSuite:
    suite_file = path / "test" / "legacy_test.gd"
    suite_file.parent.mkdir(parents=True, exist_ok=True)
    suite_file.write_text(source, encoding="utf-8")
    return NativeSuite(
        name="LegacySuite",
        path="res://test/legacy_test.gd",
        runtime=RuntimeMode.GUT,
        tests=[NativeTest(name="test_example")],
    )


def _supported_suite(path: Path) -> NativeSuite:
    return _bridge_suite(
        path,
        """extends GutTest

func test_supported_constructs() -> void:
    watch_signals(get_tree())
    assert_eq(1 + 1, 2)
    assert_signal_emitted(node, "fired")
    await wait_for_signal(node.fired, 1.0)
    await wait_seconds(0.1)
    skip_if_godot_version_lt("4.5")
""",
    )


def _assert_no_findings(project_root: Path, suite: NativeSuite) -> None:
    assert scan_bridge_suites(project_root, [suite]) is None


def test_scan_ignores_native_suites(tmp_path):
    """The scan only inspects suites routed through the bridge."""
    suite_file = tmp_path / "test" / "native_test.gd"
    suite_file.parent.mkdir(parents=True, exist_ok=True)
    suite_file.write_text(
        "extends GdToolsTest\n\nfunc test_native() -> void:\n"
        '    double("res://thing.gd")\n',
        encoding="utf-8",
    )
    suite = NativeSuite(
        name="NativeSuite",
        path="res://test/native_test.gd",
        runtime=RuntimeMode.NATIVE,
        tests=[NativeTest(name="test_native")],
    )

    _assert_no_findings(tmp_path, suite)


def test_scan_passes_supported_bridge_constructs(tmp_path):
    """The documented core subset does not fail the scan."""
    _assert_no_findings(tmp_path, _supported_suite(tmp_path))


@pytest.mark.parametrize(
    ("category", "constructs"),
    [
        ("mocking", ["double", "partial_double", "stub"]),
        ("parameterization", ["parameterize", "use_parameters"]),
        ("mock-assertions", ["assert_called_with", "assert_call_count"]),
        (
            "property-orphan-interactive",
            [
                "assert_setget",
                "assert_accessors",
                "assert_exports",
                "assert_property_with_backing_variable",
                "assert_freed",
                "assert_no_new_orphans",
                "pause_before_teardown",
            ],
        ),
        (
            "engine-error-asserts",
            [
                "assert_engine_error",
                "assert_engine_error_count",
                "assert_push_error",
                "assert_push_warning_count",
            ],
        ),
    ],
)
def test_scan_detects_unsupported_construct_categories(
    tmp_path, category, constructs
):
    """Every unsupported GUT helper category is named in the error."""
    calls = "\n".join(f"    {name}(something)" for name in constructs)
    suite = _bridge_suite(
        tmp_path,
        f"extends GutTest\n\nfunc test_unsupported() -> void:\n{calls}\n",
    )

    with pytest.raises(BridgeScanError) as excinfo:
        scan_bridge_suites(tmp_path, [suite])

    message = str(excinfo.value)
    assert "res://test/legacy_test.gd" in message
    for name in constructs:
        assert name in message
    assert "docs/gut-migration.md" in message


def test_scan_reports_line_numbers_and_deduplicates(tmp_path):
    """A construct used repeatedly is reported once, with its first line."""
    suite = _bridge_suite(
        tmp_path,
        """extends GutTest

func test_repeated() -> void:
    double("res://a.gd")
    double("res://b.gd")
""",
    )

    with pytest.raises(BridgeScanError) as excinfo:
        scan_bridge_suites(tmp_path, [suite])

    message = str(excinfo.value)
    assert message.count("double") == 1
    assert "line 4" in message


def test_scan_ignores_member_calls_on_objects(tmp_path):
    """A method call like ``foo.double()`` is not a GUT helper call."""
    suite = _bridge_suite(
        tmp_path,
        """extends GutTest

func test_member_calls() -> void:
    var helper = MyHelper.new()
    helper.double()
    helper.stub()
""",
    )

    _assert_no_findings(tmp_path, suite)


def test_scan_groups_findings_per_file(tmp_path):
    """Findings from multiple bridge suites are grouped per file."""
    first = _bridge_suite(
        tmp_path,
        'extends GutTest\n\nfunc test_one() -> void:\n    double("a")\n',
    )
    second_file = tmp_path / "test" / "other_test.gd"
    second_file.write_text(
        "extends GutTest\n\nfunc test_two() -> void:\n    stub(b)\n",
        encoding="utf-8",
    )
    second = NativeSuite(
        name="OtherSuite",
        path="res://test/other_test.gd",
        runtime=RuntimeMode.GUT,
        tests=[NativeTest(name="test_two")],
    )

    with pytest.raises(BridgeScanError) as excinfo:
        scan_bridge_suites(tmp_path, [first, second])

    message = str(excinfo.value)
    assert "res://test/legacy_test.gd" in message
    assert "res://test/other_test.gd" in message
    assert "2 bridge suites" in message


def test_command_runs_bridge_scan_before_preflight(tmp_path, monkeypatch):
    """The static scan fails the run before any Godot process spawns."""
    (tmp_path / "project.godot").touch()
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "legacy_test.gd").write_text(
        "extends GutTest\n\nfunc test_x() -> void:\n    double(obj)\n",
        encoding="utf-8",
    )
    godot_info = SimpleNamespace(is_valid=True, path="godot", version="4.5")
    monkeypatch.setattr(command, "find_project_root", lambda: tmp_path)
    monkeypatch.setattr(command, "find_godot", lambda config: godot_info)
    monkeypatch.setattr(
        command, "_test_directories", lambda *args, **kwargs: ["test"]
    )

    def _fail_import(*args, **kwargs):
        pytest.fail("Godot import ran before the bridge static scan")

    monkeypatch.setattr(command, "_import_project", _fail_import)

    with pytest.raises(BridgeScanError, match="double"):
        command.run_native_test_command(GdToolsConfig())
