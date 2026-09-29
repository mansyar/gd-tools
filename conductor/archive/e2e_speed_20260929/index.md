# Track e2e_speed_20260929 Context

Speeds up the E2E test stage — the CI wall-time bottleneck (5-10.5 min per
job, Windows dominating) that pushes PR CI to ~13 min against the documented
10-min target. Three levers, no product behavior change: (1) duration
measurement via `--durations=20` in the CI E2E and integration pytest steps;
(2) elimination of real-time waits in watch/migration e2e by injecting fast
timing values through the existing config/fixture seams (the watch coalescer
already accepts `debounce_seconds` and an injectable clock); (3) a
marker-selected smoke subset (`e2e_smoke`, 3-5 critical-path tests, <= ~2 min
per job) that runs on the unchanged 6-job PR matrix, with the full E2E suite
moving to a nightly schedule plus `workflow_dispatch`. Acceptance: PR CI wall
time <= 10 min. Out of scope: pytest-xdist, Godot import/binary caching,
matrix trimming, persistent Godot worker process, CI step retry logic.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
