# Track Specification — Native Release Readiness (v0.5.0)

**Track ID:** `native_release_readiness_20260930` · **Type:** Chore/Release

## Overview

The GUT migration arc (roadmap Phases 0–4) is functionally complete, but the project has accumulated a fat "Unreleased" changelog, stale migration-era documentation, and one bounded robustness gap (Phase 5's crash-recovery item). This track closes the migration story: it makes the documentation tell the truth about the current state, hardens the native runtime's failure paths to a releasable standard, formally deprecates the GUT bridge, and prepares the v0.5.0 release for publication.

## Functional Requirements

### FR1 — Documentation truth pass (all user-facing docs)
- `docs/ROADMAP.md`: fix the stale "Phases 3–5 outstanding" header; check off delivered Phase 4 checkboxes; rewrite Phase 5 status to reflect what this track delivers vs. what remains (parallel execution, runtime caching deferred).
- `README.md`: update the known-limitations table (parameterized tests now supported; bridge status changes to *Deprecated*); verify all CLI examples still produce current output.
- `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md`: remove/reword bridge-era statements that describe GUT as the default path or the bridge as active-new rather than deprecated.
- `doctor` command output and `gd-tools init` messaging: align bridge status wording with the deprecation.
- `CHANGELOG.md`: finalize the Unreleased section into v0.5.0 format with accurate Known Limitations.

### FR2 — Crash-recovery & diagnostics hardening (bounded)
- **Orphan cleanup:** interrupting `gd-tools test` (Ctrl+C / SIGTERM) kills spawned Godot child processes; no orphans remain after an interrupted run.
- **Crash-safe artifacts:** a run terminated before completion still leaves artifacts under `.gd-tools/artifacts/<run_id>/` clearly marked as incomplete (machine-readable marker + human notice in terminal output), so a crashed run is never mistaken for a passing one.
- **Exit-2 diagnostics:** environment/config/protocol/engine failures produce structured, actionable diagnostics (what failed, expected vs. found, the fix to try) — extending existing exit-2 paths, not redesigning them.
- **No resume capability:** shards already passed are NOT reused across runs; a re-run executes everything.

### FR3 — GUT bridge deprecation
- Bridge remains fully functional (no behavior change), but emits a one-time deprecation notice when a GUT-style suite runs, stating that removal is planned for v0.6.0.
- Docs state the removal timeline consistently (product.md's "one-release migration period" honored: deprecated in 0.5, removed in 0.6).

### FR4 — Release preparation (v0.5.0)
- Version bump to `0.5.0` in `pyproject.toml` (and any version-displayed surfaces).
- CHANGELOG finalized per FR1.
- Pre-release gate per workflow: full test suite, coverage targets met, `ruff check` + `black --check` clean, `python -m build`, `twine check` on the produced distributions.

## Non-Functional Requirements
- TDD per `workflow.md`: tests precede implementation for all FR2/FR3 code changes.
- Coverage targets maintained: ≥80% line / ≥70% branch on `src/gd_tools/*.py`.
- All CLI behavior remains non-interactive (`CI=true`).
- No behavior change to passing runs; hardening touches failure/interruption paths only.

## Acceptance Criteria
1. ROADMAP header, checkboxes, and Phase 5 section match delivered reality; no doc claims a capability that doesn't exist (verified against actual CLI output).
2. Interrupted run: no orphan Godot processes remain; artifact directory marked incomplete; exit code is 130 (or 2, per chosen convention — decided in plan).
3. Simulated engine/protocol/config failure prints actionable diagnostics naming the failing suite and remedy.
4. Running a GUT-style suite shows the deprecation notice exactly once; native suites show nothing new.
5. `python -m build` produces a clean 0.5.0 wheel+tarball passing `twine check`.
6. Full CI-equivalent check passes locally (`ruff`, `black`, `CI=true pytest`, coverage gates).

## Out of Scope
- PyPI/GitHub release publication (short follow-up after merge approval).
- Optional parallel suite execution and native runtime caching (deferred Phase 5 items).
- Crash *resume* from partially completed runs.
- Tracks 29–36, 39 items (exclusion annotations, GH Actions annotations, pre-commit hooks, playtest coverage, editor plugin, macOS matrix, clean command).
