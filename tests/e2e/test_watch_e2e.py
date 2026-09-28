"""End-to-end watch session test on a real project with real file events.

Exercises the full watch stack in-process: the real watchdog observer on a
real filesystem, the real watch loop, and the real native runtime (a real
Godot binary per run). A background thread mutates the project between
runs, following the same scripted sequence as the acceptance criteria:

1. an initial full-suite run,
2. a save maps to exactly one affected suite,
3. a newly created suite is picked up without restarting,
4. an unmapped file falls back to an explicit full-suite run,
5. a clean shutdown exits 0 and leaves no orphan Godot processes.
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from gd_tools.config import load_config
from gd_tools.watch.observer import WatchdogEventSource
from gd_tools.watch.session import run_watch_mode

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.usefixtures("godot_bin"),
]

_RUN_TIMEOUT = 120.0


def _gd_tools_command() -> list[str]:
    """Use the installed CLI entry point when available."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _write_project(root: Path) -> None:
    """Create a minimal Godot project with two native suites."""
    (root / "src").mkdir()
    (root / "test").mkdir()
    (root / "tests").mkdir()
    (root / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="watch_e2e"\n',
        encoding="utf-8",
    )
    (root / "src" / "enemy.gd").write_text("extends Node\n", encoding="utf-8")
    (root / "src" / "player.gd").write_text("extends Node\n", encoding="utf-8")
    (root / "tests" / "test_enemy.gd").write_text(
        "extends GdToolsTest\n"
        "\n"
        "\n"
        "class_name EnemySuite\n"
        "\n"
        "\n"
        "func test_ok() -> void:\n"
        "\tassert_eq(1, 1)\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_player.gd").write_text(
        "extends GdToolsTest\n"
        "\n"
        "\n"
        "class_name PlayerSuite\n"
        "\n"
        "\n"
        "func test_ok() -> void:\n"
        "\tassert_eq(2, 2)\n",
        encoding="utf-8",
    )


class _OutputCollector:
    """Thread-safe output sink with run-marker waiting."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._lock = threading.Lock()

    def __call__(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)

    @property
    def lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def wait_for_run(self, number: int) -> bool:
        """Wait until "Run <number>:" has been reported."""
        marker = f"Run {number}:"
        deadline = time.monotonic() + _RUN_TIMEOUT
        while time.monotonic() < deadline:
            with self._lock:
                if any(line.startswith(marker) for line in self._lines):
                    return True
            time.sleep(0.1)
        return False


def _mutator(project, collector, stop, errors) -> None:
    """Script the file mutations between watch runs."""
    try:
        assert collector.wait_for_run(1), "initial run never reported"
        (project / "src" / "enemy.gd").write_text(
            "extends Node\n# touched\n", encoding="utf-8"
        )
        assert collector.wait_for_run(2), "mapped re-run never reported"
        (project / "tests" / "test_other.gd").write_text(
            "extends GdToolsTest\n"
            "\n"
            "\n"
            "class_name OtherSuite\n"
            "\n"
            "\n"
            "func test_ok() -> void:\n"
            "\tassert_eq(3, 3)\n",
            encoding="utf-8",
        )
        assert collector.wait_for_run(3), "new suite never picked up"
        (project / "src" / "helper.gd").write_text(
            "extends Node\n", encoding="utf-8"
        )
        assert collector.wait_for_run(4), "fallback run never reported"
    except Exception as exc:  # noqa: BLE001 - surfaced via errors list
        errors.append(exc)
    finally:
        stop.set()


class _TerminableSource:
    """Proxy that ends the event stream once the script completes."""

    def __init__(self, inner: WatchdogEventSource, stop) -> None:
        self._inner = inner
        self._stop = stop

    def events(self):
        for event in self._inner.events():
            if self._stop.is_set():
                break
            yield event
        self._inner.stop()

    def stop(self) -> None:
        self._inner.stop()


def _godot_process_count() -> int | None:
    """Count running Godot processes; None when no probe is available."""
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq godot.exe"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.stdout.lower().count("godot.exe")
        result = subprocess.run(
            ["pgrep", "-f", "godot"],
            capture_output=True,
            text=True,
            check=False,
        )
        return len([line for line in result.stdout.split() if line.strip()])
    except OSError:
        return None


def test_watch_session_end_to_end(tmp_path, monkeypatch, godot_bin):
    """The full watch loop reacts to real file events and shuts down."""
    project = tmp_path / "watch_project"
    project.mkdir()
    _write_project(project)
    env = os.environ.copy()
    env.update(
        {
            "GODOT_BIN": godot_bin,
            "GD_TOOLS_NO_UPDATE_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    init = subprocess.run(
        [*_gd_tools_command(), "init", "--non-interactive"],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    assert init.returncode == 0, init.stdout + init.stderr

    before = _godot_process_count()
    monkeypatch.chdir(project)
    config = load_config(project)
    collector = _OutputCollector()
    stop = threading.Event()
    errors: list[Exception] = []
    worker = threading.Thread(
        target=_mutator,
        args=(project, collector, stop, errors),
        daemon=True,
    )
    worker.start()
    try:
        code = run_watch_mode(
            config,
            event_source=_TerminableSource(WatchdogEventSource(project), stop),
            output=collector,
        )
    finally:
        stop.set()
        worker.join(timeout=_RUN_TIMEOUT + 30)
    after = _godot_process_count()

    assert not errors, errors
    assert code == 0
    lines = collector.lines
    assert any("Watching" in line and "Ctrl+C" in line for line in lines)
    assert any(
        line.startswith("Run 1:") and "(2 tests)" in line for line in lines
    )
    assert any(
        line.startswith("Run 2:") and "(1 tests)" in line for line in lines
    )
    assert any(
        line.startswith("Run 3:") and "(1 tests)" in line for line in lines
    )
    assert any(
        line.startswith("Run 4:") and "(3 tests)" in line for line in lines
    )
    assert any("No suite mapped for 'src/helper.gd'" in line for line in lines)
    assert before is None or after is None or before == after
