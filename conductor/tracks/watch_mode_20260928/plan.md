# Implementation Plan: Watch Mode (`gd-tools test --watch`)

- **Track ID:** watch_mode_20260928
- **Type:** Feature
- **Status:** New
- **Specification:** [`spec.md`](./spec.md)

## Phase 1 — Watch domain logic (pure Python, no I/O) [checkpoint: 38156b1]

**Purpose:** Nail mapping, debounce, and scope rules as testable units before any watching or CLI work.

- [x] Task: Add failing tests for file→suite convention mapping [ced68b5]
  - [ ] Test `foo.gd` → `test_foo.gd` / `foo_test.gd` resolution.
  - [ ] Test suite self-mapping (a changed suite file maps to itself).
  - [ ] Test same-directory precedence and cross-directory stem match.
  - [ ] Test both naming conventions and their precedence.
  - [ ] Run the targeted tests and confirm the expected Red phase.
- [x] Task: Implement the mapping module [ced68b5]
  - [ ] Create the `src/gd_tools/watch/` package.
  - [ ] Implement convention-based mapping resolution.
  - [ ] Integrate with native discovery results (known suites).
  - [ ] Run the mapping tests to Green.
- [x] Task: Add failing tests for debounce & run-coalescing state machine [763b37b]
  - [ ] Test 500 ms coalescing of rapid saves into one run.
  - [ ] Test mid-run save → dirty flag → exactly one queued re-run.
  - [ ] Test no run pile-up under continuous saves.
  - [ ] Use an injectable fake clock; confirm the expected Red phase.
- [x] Task: Implement the debounce/coalescing state machine [763b37b]
  - [ ] Implement the state machine against the fake-clock tests.
  - [ ] Refactor pass if warranted.
  - [ ] Run the debounce tests to Green.
- [x] Task: Add failing tests for watched-scope resolution [8c37552]
  - [ ] Test project-root scan with standard excludes (`.godot/`, `.gd-tools/`, `addons/gd-tools-*`, artifact dirs).
  - [ ] Test event classification (modified/created/deleted → action).
  - [ ] Test new-file pickup semantics.
  - [ ] Confirm the expected Red phase.
- [x] Task: Implement watched-scope resolution [8c37552]
  - [ ] Implement scope enumeration reusing existing exclusion logic.
  - [ ] Implement event → action classification.
  - [ ] Run the scope tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run targeted unit tests and static checks.
  - [ ] Review the domain modules for forward compatibility with the observer layer.
  - [ ] Create the phase checkpoint commit and record its SHA.

## Phase 2 — Watchdog integration & watch loop

**Purpose:** Wire the domain logic to real file events and the existing native orchestrator.

- [ ] Task: Document the watchdog dependency in tech-stack.md
  - [ ] Add a dated note documenting the `watchdog` runtime dependency.
  - [ ] Add `watchdog` to `pyproject.toml` runtime dependencies.
- [ ] Task: Add failing tests for the event-source abstraction
  - [ ] Define the observer interface over file events.
  - [ ] Test create/modify/delete event mapping to domain actions with a fake event source.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement the watchdog observer adapter
  - [ ] Implement the watchdog-backed observer behind the abstraction.
  - [ ] Batch event delivery feeding the debouncer.
  - [ ] Run the observer tests to Green.
- [ ] Task: Add failing tests for the watch loop orchestration
  - [ ] Test initial full run → watch transition.
  - [ ] Test mapped re-run and fallback full run on no-match with explicit status.
  - [ ] Test dirty-flag re-run after an in-flight run completes.
  - [ ] Test KeyboardInterrupt → clean exit 0.
  - [ ] Test filters respected per run. Confirm the expected Red phase.
- [ ] Task: Implement the watch loop
  - [ ] Orchestrate observer + debouncer + mapping + native orchestrator invocation.
  - [ ] Reuse existing result reporting per run.
  - [ ] Run the watch-loop tests to Green.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run targeted unit tests and static checks.
  - [ ] Review observer/loop seams for e2e testability.
  - [ ] Create the phase checkpoint commit and record its SHA.

## Phase 3 — CLI integration & terminal UX

**Purpose:** Expose the feature through `gd-tools test` with the documented UX contract.

- [ ] Task: Add failing CLI tests for --watch flag handling
  - [ ] Test `--watch` + `--runtime gut` → exit 2 with a clear message.
  - [ ] Test `CI=true` + `--watch` → exit 2 with a clear message.
  - [ ] Test filters and `--coverage` pass through to the watch loop.
  - [ ] Confirm the expected Red phase.
- [ ] Task: Implement CLI wiring
  - [ ] Add the `--watch` flag to the `test` command.
  - [ ] Implement startup guards and error messages.
  - [ ] Print the banner (`Watching N files. Press Ctrl+C to stop.`).
  - [ ] Clear the screen between runs (Windows-safe implementation).
  - [ ] Emit per-run results via the existing reporter.
  - [ ] Run the CLI tests to Green.
- [ ] Task: Update documentation
  - [ ] Add a watch-mode section to `README.md`.
  - [ ] Add a CHANGELOG entry.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Run targeted unit tests and static checks.
  - [ ] Verify docs match actual behavior.
  - [ ] Create the phase checkpoint commit and record its SHA.

## Phase 4 — End-to-end verification & polish

**Purpose:** Prove the full loop on a real project with real file events.

- [ ] Task: Add integration/e2e watch-session test
  - [ ] Script a real-filesystem watch session on a fixture project.
  - [ ] Assert save → single mapped re-run.
  - [ ] Assert new suite file pickup without restart.
  - [ ] Assert fallback run and clean Ctrl+C shutdown with no orphan Godot processes.
- [ ] Task: Full quality gate
  - [ ] Run `ruff check src/ tests/` and `black --check src/ tests/`.
  - [ ] Run `CI=true pytest` with coverage thresholds on new source.
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`)
  - [ ] Execute the manual verification plan: install via `pip install -e .`, run `gd-tools test --watch` on the sample project, confirm each acceptance criterion.
  - [ ] Create the phase checkpoint commit and record its SHA.
