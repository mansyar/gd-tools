# Specification: macOS CI Matrix

## Overview

CI currently verifies gd-tools on Ubuntu and Windows only, while
`conductor/product.md` targets Windows/macOS/Linux users. The roadmap's
compatibility matrix (`docs/ROADMAP.md` §8) explicitly documents "macOS is
not covered" and defers it to this track (Roadmap Track 36). This track adds
`macos-latest` to the CI test matrix at full parity — unit (Python
3.10–3.12), integration, and e2e stages (Godot 4.5.2/4.6.1/4.7.1) — running
on every push/PR, and fixes any macOS-specific issues that surface.

## Functional Requirements

1. **Unit-test matrix:** the `matrix-unit` job in
   `.github/workflows/ci.yml` gains `macos-latest` in the `os` axis
   (3 Python versions → 3 new macOS jobs).
2. **Integration stage:** the `integration` job gains `macos-latest`
   (3 Godot versions → 3 new macOS jobs).
3. **E2E stage:** the `e2e` job gains `macos-latest` (3 Godot versions →
   3 new macOS jobs).
4. **Shared install-godot action:**
   `.github/actions/install-godot/action.yml` gains a macOS branch: correct
   release asset naming (`Godot_v{v}-stable_macos.universal.zip`),
   appropriate binary handling (POSIX path export — no Windows-specific
   `cygpath`; macOS arm64 runners run the universal binary), and validation
   that the binary executes (`godot --version`).
5. **Issue fixes:** any macOS-specific path handling, binary detection, or
   subprocess behavior issues in `src/gd_tools/godot.py` (and related
   modules) that surface during macOS runs are fixed.

## Non-Functional Requirements

- macOS jobs run on every push/PR (same triggers as the existing OSes).
- Existing per-job `timeout-minutes` budgets must accommodate macOS runner
  speed; raise with justification if a budget is exceeded.
- Pipeline duration must not regress for Linux/Windows jobs.

## Acceptance Criteria

1. macOS appears in all 3 CI stages and runs every combination
   (3 Pythons; 3 Godot versions × 2 stages).
2. All unit tests pass on macOS.
3. All integration tests pass on macOS with Godot installed.
4. All E2E smoke tests pass on macOS.
5. No Linux/Windows CI regressions introduced.
6. `docs/ROADMAP.md` §8 compatibility matrix updated to include macOS; the
   "macOS is not covered" limitation notes removed or rewritten; README
   platform wording consistent with the new verified state.

## Out of Scope

- Windowed-suite display server support (xvfb/dummy audio) — a separate,
  known matrix limit.
- Nightly scheduling restructuring or pipeline duration optimization.
- GUT bridge verification on macOS (bridge is deprecated; removal targeted
  for v0.6.0).
- New user-facing CLI functionality.
