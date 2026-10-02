# Spec: v0.6.0 Legacy Sweep

**Type:** Chore
**Branch:** `chore/legacy-sweep-20261002`
**Motivation:** The v0.6.0 GUT bridge removal (Track `gut_bridge_removal_20261001`) intentionally left some legacy scaffolding; this track completes the cleanup so the codebase reflects the native-runtime-only reality.

## Overview

Remove code and configuration orphaned by the GUT removal, and reconcile living documentation with shipped v0.6.0 behavior. No user-facing behavior changes beyond the removal of the dead `gutconfig` config key.

## Functional Requirements

- **FR-1 — Dead code removal:** Delete `GUT_VERSION_MAP` and `get_gut_version_for_godot` from `godot.py` (update its module docstring, which still advertises GUT version mapping).
- **FR-2 — GUT remnant audit:** Inventory every GUT reference in `src/gd_tools/`; classify each as **remove** (dead) or **keep** (intentional: doctor advisory, `migrate` command + gutconfig translation, v0.6.0 rejection error messages, `docs/gut-migration.md`). Known candidates to evaluate: `GUTNotInstalledError` (`errors.py`), `is_gut_installed` and legacy-runner display remnants (`test_runner.py`), the `gut` entry in `version.py`'s version report, stale module docstrings. Every removal must be backed by a grep-proven zero-reference check and a green test suite.
- **FR-3 — Config cleanup:** Remove the `[test] gutconfig` field from the Pydantic config model (`config.py`), regenerate the checked-in `docs/gd-tools.schema.json` snapshot, and keep its sync test green. **Keep** the `runtime` field (single-valued `"native"`) for GdUnit4 forward-compatibility. Existing TOMLs containing `gutconfig` will fail validation as an unknown key — accepted (consistent with v0.6.0's breaking-change posture).
- **FR-4 — Docs truth pass:** Sweep **living docs only** — `README.md`, `docs/USER_GUIDE.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` — for GUT-era claims contradicting shipped v0.6.0 behavior (e.g., USER_GUIDE's config table listing `gutconfig`, PRD config examples). Historical docs (`docs/TDD.md`, `docs/ROADMAP_v1.md`, `docs/SPIKE_*.md`) are **out of scope**.
- **FR-5 — Retire Roadmap Track 32:** Mark "Configurable Version Mapping" in `docs/ROADMAP.md` as obsolete (reason: its purpose was the GUT version map, removed in v0.6.0).

## Acceptance Criteria

1. `GUT_VERSION_MAP` and `get_gut_version_for_godot` no longer exist; `rg "GUT_VERSION_MAP|get_gut_version_for_godot"` over the repo returns only historical-doc hits.
2. Audit table (removed vs. kept, with rationale) recorded in the track; every removal compiles, and the full test suite (unit/integration/e2e) passes.
3. `gutconfig` absent from config model + JSON schema snapshot; schema sync test passes; a TOML containing `gutconfig` fails validation as an unknown key per existing config validation conventions.
4. `runtime` field retained and documented as native-only.
5. Living docs contain no claims that GUT is a runnable runtime or that `gutconfig` is a supported key.
6. ROADMAP Track 32 marked obsolete with rationale.
7. No CHANGELOG entry (explicitly out of scope).

## Out of Scope

- CHANGELOG updates
- GdUnit4 support
- Pre-commit hooks (Roadmap Track 29)
- GitHub Actions annotations (Roadmap Track 31)
- Editor plugin work
- Touching `docs/gut-migration.md` or the `migrate` command
- Removing `doctor`'s Legacy GUT advisory
