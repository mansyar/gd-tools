"""Unit tests for import-freshness gating in the native test pipeline."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.errors import GdToolsError
from gd_tools.native_test.command import (
    _ensure_project_imported,
    run_native_test_command,
)
from gd_tools.native_test.import_cache import (
    compute_import_cache_key,
    store_import_freshness,
)
from gd_tools.native_test.protocol import (
    NativeRunResult,
    NativeSuite,
    NativeTestResult,
)
from gd_tools.test_runner import TestResult
from gd_tools.verbosity import Verbosity, set_verbosity

pytestmark = pytest.mark.unit


def _write_project(root):
    """Create a minimal Godot project with one import-relevant file."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "project.godot").write_text("[application]\n", encoding="utf-8")
    (root / "src" / "player.gd").write_text("# player\n", encoding="utf-8")


def _godot(version: str = "4.5.2") -> SimpleNamespace:
    return SimpleNamespace(path="godot", version=version, is_valid=True)


def _cache_state(project_root):
    return project_root / ".gd-tools" / "native" / "import-cache" / "state.json"


def test_first_run_imports_and_records_freshness(tmp_path):
    """A cold project runs the import and stores the freshness entry."""
    _write_project(tmp_path)
    mock = MagicMock()
    with patch("gd_tools.native_test.command._import_project", mock):
        _ensure_project_imported(_godot(), tmp_path, None)
    mock.assert_called_once()
    assert _cache_state(tmp_path).exists()


def test_unchanged_second_run_skips_import(tmp_path):
    """A warm rerun on an unchanged project never spawns the import."""
    _write_project(tmp_path)
    mock = MagicMock()
    with patch("gd_tools.native_test.command._import_project", mock):
        _ensure_project_imported(_godot(), tmp_path, None)
        _ensure_project_imported(_godot(), tmp_path, None)
    mock.assert_called_once()


def test_changed_project_imports_again(tmp_path):
    """A project change between runs triggers a fresh import."""
    _write_project(tmp_path)
    mock = MagicMock()
    with patch("gd_tools.native_test.command._import_project", mock):
        _ensure_project_imported(_godot(), tmp_path, None)
        (tmp_path / "src" / "player.gd").write_text(
            "# player v2\n", encoding="utf-8"
        )
        _ensure_project_imported(_godot(), tmp_path, None)
    assert mock.call_count == 2


def test_changed_godot_version_imports_again(tmp_path):
    """Switching the resolved Godot binary triggers a fresh import."""
    _write_project(tmp_path)
    mock = MagicMock()
    with patch("gd_tools.native_test.command._import_project", mock):
        _ensure_project_imported(_godot("4.5.2"), tmp_path, None)
        _ensure_project_imported(_godot("4.6.1"), tmp_path, None)
    assert mock.call_count == 2


def test_no_cache_always_imports_and_stores_nothing(tmp_path):
    """--no-cache bypasses both the cache lookup and the store."""
    _write_project(tmp_path)
    mock = MagicMock()
    with patch("gd_tools.native_test.command._import_project", mock):
        _ensure_project_imported(_godot(), tmp_path, None, no_cache=True)
        _ensure_project_imported(_godot(), tmp_path, None, no_cache=True)
    assert mock.call_count == 2
    assert not _cache_state(tmp_path).exists()


def test_no_cache_ignores_a_seeded_cache(tmp_path):
    """A stored freshness entry cannot suppress a --no-cache import."""
    _write_project(tmp_path)
    key = compute_import_cache_key(tmp_path, godot_version="4.5.2")
    assert store_import_freshness(
        tmp_path / ".gd-tools" / "native" / "import-cache", key
    )
    mock = MagicMock()
    with patch("gd_tools.native_test.command._import_project", mock):
        _ensure_project_imported(_godot(), tmp_path, None, no_cache=True)
    mock.assert_called_once()


def test_failed_import_does_not_update_cache(tmp_path):
    """A failed import leaves no freshness entry behind."""
    _write_project(tmp_path)
    mock = MagicMock(side_effect=GdToolsError("import crashed"))
    with (
        patch("gd_tools.native_test.command._import_project", mock),
        pytest.raises(GdToolsError),
    ):
        _ensure_project_imported(_godot(), tmp_path, None)
    assert not _cache_state(tmp_path).exists()


def test_cache_errors_fail_open(tmp_path):
    """Cache hashing failures degrade to a normal unconditional import."""
    _write_project(tmp_path)
    mock = MagicMock()
    with (
        patch("gd_tools.native_test.command._import_project", mock),
        patch(
            "gd_tools.native_test.command.compute_import_cache_key",
            side_effect=OSError("hash failed"),
        ),
    ):
        _ensure_project_imported(_godot(), tmp_path, None)
    mock.assert_called_once()


def test_verbose_reports_miss_then_hit(tmp_path, capsys):
    """Hit/miss reasons are reported under --verbose, cache or not."""
    _write_project(tmp_path)
    set_verbosity(Verbosity.VERBOSE)
    try:
        with patch("gd_tools.native_test.command._import_project"):
            _ensure_project_imported(_godot(), tmp_path, None)
            _ensure_project_imported(_godot(), tmp_path, None)
    finally:
        set_verbosity(Verbosity.DEFAULT)
    captured = capsys.readouterr().out
    assert "Import cache miss" in captured
    assert "Import cache hit" in captured


def test_run_native_command_passes_no_cache_to_the_import_gate(tmp_path):
    """The pipeline forwards the --no-cache flag to the import gate."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = NativeRunResult(
        run_id="run-1",
        status="passed",
        tests=[
            NativeTestResult(
                suite="ExampleSuite", name="test_ok", status="passed"
            )
        ],
    )
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=_godot(),
        ),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight_result(suite),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch("gd_tools.native_test.command._ensure_project_imported") as gate,
    ):
        run_native_test_command(_pipeline_config(), no_cache=True)

    assert gate.call_args.kwargs["no_cache"] is True


def test_warm_pipeline_rerun_skips_the_import_process(tmp_path):
    """Two identical pipeline invocations import the project only once."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = NativeRunResult(
        run_id="run-1",
        status="passed",
        tests=[
            NativeTestResult(
                suite="ExampleSuite", name="test_ok", status="passed"
            )
        ],
    )

    def _run_once() -> TestResult:
        with (
            patch(
                "gd_tools.native_test.command.find_project_root",
                return_value=tmp_path,
            ),
            patch(
                "gd_tools.native_test.command.find_godot",
                return_value=_godot(),
            ),
            patch(
                "gd_tools.native_test.command.discover_native_suites",
                return_value=[suite],
            ),
            patch(
                "gd_tools.native_test.command._prepare_coverage",
                return_value=(None, None),
            ),
            patch(
                "gd_tools.native_test.command.run_preflight_cached",
                return_value=_preflight_result(suite),
            ),
            patch(
                "gd_tools.native_test.command.run_native_tests",
                return_value=native,
            ),
            patch("gd_tools.native_test.command._generate_native_report"),
            patch("gd_tools.native_test.command.format_test_results"),
        ):
            return run_native_test_command(_pipeline_config())

    _write_project(tmp_path)
    (tmp_path / "test").mkdir(exist_ok=True)
    (tmp_path / "test" / "example.gd").write_text(
        "extends GdToolsTest\n", encoding="utf-8"
    )
    with patch("gd_tools.native_test.command._import_project") as import_mock:
        cold = _run_once()
        warm = _run_once()
    import_mock.assert_called_once()
    assert (cold.total, cold.passed, cold.failed, cold.skipped) == (
        warm.total,
        warm.passed,
        warm.failed,
        warm.skipped,
    )
    assert cold.junit_xml_path == warm.junit_xml_path


def _pipeline_config() -> SimpleNamespace:
    """A minimal config satisfying the native test pipeline."""
    return SimpleNamespace(
        godot=SimpleNamespace(),
        test=SimpleNamespace(
            test_dirs=["test"],
            timeout_seconds=5.0,
            retries=0,
            tags=[],
        ),
        coverage=SimpleNamespace(
            output_dir=".gd-tools/coverage",
            exclude=[],
            test_dirs=["test"],
            format="text",
        ),
    )


def _preflight_result(suite: NativeSuite):
    from gd_tools.native_test.protocol import NativePreflightResult

    return NativePreflightResult(status="ok", suites=[suite])
