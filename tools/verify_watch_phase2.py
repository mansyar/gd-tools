"""Manual Phase 2 verification for the Watch Mode track (watch_mode_20260928).

Validates the real watchdog stack on the live filesystem:

1. WatchdogEventSource surfaces .gd modifications as FileEvents and ignores
   non-.gd files.
2. watch_loop driven by the real adapter performs the initial full run, then
   exactly one debounced mapped re-run after a real on-disk save.

Run with: .venv\\Scripts\\python.exe tools\\verify_watch_phase2.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gd_tools.native_test.protocol import NativeRunResult, NativeSuite, NativeTest
from gd_tools.watch.loop import watch_loop
from gd_tools.watch.observer import FileEvent, WatchdogEventSource

RESULTS: list[str] = []


def record(label: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(f"{'PASS' if ok else 'FAIL'} {label}" + (f" ({detail})" if detail else ""))


def collect_events(source: WatchdogEventSource, deadline_seconds: float) -> list[FileEvent]:
    """Poll the adapter until the deadline, returning only real FileEvents."""
    events: list[FileEvent] = []
    deadline = time.monotonic() + deadline_seconds
    for event in source.events():
        if event is not None:
            events.append(event)
        if time.monotonic() > deadline:
            break
    return events


def verify_adapter(project_root: Path) -> None:
    """Part 1: real adapter reports .gd changes, ignores other files."""
    source = WatchdogEventSource(project_root)
    time.sleep(0.5)  # let the watchdog observer schedule

    target = project_root / "src" / "enemy.gd"
    target.write_text("# touched\n", encoding="utf-8")

    events = collect_events(source, deadline_seconds=3.0)
    gd_events = [e for e in events if e.path.replace("\\", "/") == "src/enemy.gd"]
    record(
        "adapter reports .gd modification",
        bool(gd_events) and gd_events[0].event_type in ("modified", "created"),
        f"events={events}",
    )

    (project_root / "notes.txt").write_text("ignored\n", encoding="utf-8")
    extra = collect_events(source, deadline_seconds=1.0)
    record(
        "adapter ignores non-.gd files",
        not any(e.path.endswith(".txt") for e in events + extra),
        f"txt_events={[e for e in extra if e.path.endswith('.txt')]}",
    )
    source.stop()


def verify_loop(project_root: Path) -> None:
    """Part 2: real adapter + watch_loop performs initial run + mapped re-run."""
    suite = NativeSuite(
        name="test_enemy",
        path="res://tests/test_enemy.gd",
        tests=[NativeTest(name="test_health")],
    )
    calls: list[list[str]] = []

    def runner(suites: list[NativeSuite]) -> NativeRunResult:
        calls.append([s.path for s in suites])
        if len(calls) >= 2:
            # Second call is the mapped re-run: end the watch session cleanly.
            raise KeyboardInterrupt
        return NativeRunResult(run_id=f"r{len(calls)}", status="passed")

    output: list[str] = []
    source = WatchdogEventSource(project_root)

    def drive() -> None:
        code = watch_loop(
            project_root,
            discover=lambda: [suite],
            runner=runner,
            event_source=source,
            clock=time.monotonic,
            output=output.append,
        )
        record("loop exits 0 on clean stop", code == 0, f"code={code}")

    thread = threading.Thread(target=drive, daemon=True)
    thread.start()

    time.sleep(1.0)  # initial full run settles
    target = project_root / "src" / "enemy.gd"
    target.write_text("# saved by watcher test\n", encoding="utf-8")

    thread.join(timeout=15.0)
    record("loop finishes within timeout", not thread.is_alive())

    record(
        "initial full run executed",
        len(calls) >= 1 and calls[0] == ["res://tests/test_enemy.gd"],
        f"calls={calls}",
    )
    record(
        "exactly one debounced mapped re-run after real save",
        len(calls) == 2 and calls[1] == ["res://tests/test_enemy.gd"],
        f"calls={calls}",
    )
    record(
        "fallback/status lines present",
        any("Run 1: passed" in line for line in output),
        f"output={output}",
    )
    source.stop()


def main() -> int:
    project_root = Path(tempfile.mkdtemp(prefix="gd_tools_watch_verify_"))
    (project_root / "src").mkdir()
    (project_root / "tests").mkdir()
    (project_root / "src" / "enemy.gd").write_text("extends Node\n", encoding="utf-8")
    (project_root / "tests" / "test_enemy.gd").write_text("extends Node\n", encoding="utf-8")
    try:
        verify_adapter(project_root)
        verify_loop(project_root)
    finally:
        shutil.rmtree(project_root, ignore_errors=True)

    print("\n".join(RESULTS))
    failures = [line for line in RESULTS if line.startswith("FAIL")]
    print(f"\n{len(RESULTS) - len(failures)}/{len(RESULTS)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())