# Specification — Clean Command (Roadmap Track 39)

- **Track ID:** `clean_command_20260930` *(provisional; finalized at artifact creation)*
- **Type:** Feature
- **Phase:** 9 — Robustness & Quality
- **Branch:** `feature/clean-command-20260930`
- **Roadmap reference:** `docs/ROADMAP.md` §Track 39 (0.25 day, LOW risk)
- **Modules:** `src/gd_tools/clean.py` (new), `src/gd_tools/cli.py`, `tests/unit/test_clean.py` (new), `docs/USER_GUIDE.md`, `docs/ROADMAP.md`

## Overview

Add a `gd-tools clean` command that removes generated `.gd-tools/` artifacts so
users never have to hand-delete directories they may not fully understand.
The command is flag-driven and conservative: it never touches project files
(`addons/`, `gd-tools.toml`, `.gutconfig.json`), never touches the per-user
home cache (`~/.gd-tools` used by the update checker), and with no flags it
deletes nothing — it prints an inventory plus a hint.

The roadmap was written before several artifact categories existed; the flag
set is extended accordingly, with every target verified against the current
source layout:

| Flag | Target (verified in source) | Notes |
|---|---|---|
| `--coverage` | `.gd-tools/coverage/` | Includes `plan.json` (the Track 37 plan cache), `coverage.json`, reports, and `baseline.json` |
| `--baselines` | `<coverage output_dir>/baseline.json` | Single file; redundant (silently subsumed) when `--coverage` is also given |
| `--artifacts` | `.gd-tools/artifacts/` | Per-run test artifacts (`artifacts/<run_id>/`) and the run index |
| `--cache` | `.gd-tools/native/` | Native runtime worker scratch/work dir (the only standalone cache-like dir) |
| `--all` | entire `.gd-tools/` | Subsumes all of the above |
| `--dry-run` | (modifier) | Print exactly what would be removed; delete nothing |

## Functional Requirements

1. **FR-1 — Command surface.** `gd-tools clean` registered in `cli.py` with
   flags `--coverage`, `--artifacts`, `--baselines`, `--cache`, `--all`,
   `--dry-run`. `--all` overrides the narrower flags (documented in help text).
2. **FR-2 — No-flag behavior.** With no flags: print an inventory of what
   exists under `.gd-tools/` (each known subdirectory with a one-line
   description and approximate size), then print a hint naming the available
   flags. Exit 0. Delete nothing.
3. **FR-3 — Deletion semantics.** Each flag removes its target directory (or
   file) if it exists; missing targets are reported as "nothing to remove"
   rather than errors. Removals are recursive.
4. **FR-4 — Dry run.** `--dry-run` performs FR-2-style listing for the
   selected flags and marks each item `would remove`; nothing is deleted.
   Composable with every flag including `--all`.
5. **FR-5 — Summary output.** After a real run, print a per-target summary
   (target path, removed / nothing-to-remove, and freed size when removal
   happened).
6. **FR-6 — Redundant flags.** `--baselines` together with `--coverage` (or
   `--all`) is silently subsumed — no error; the summary lists the baseline
   once under the covering target.
7. **FR-7 — Protected paths (hard guarantees).** The command must never delete
   or modify: `addons/**` (including `addons/*/.backups/`), `gd-tools.toml`,
   `.gutconfig.json`, project source files, or the home cache `~/.gd-tools`.
   Enforcement is structural (targets are fixed constant paths under the
   project `.gd-tools/` only), and unit tests assert the boundaries.
8. **FR-8 — Exit codes.** 0 on success (including no-op / dry-run);
   non-zero (2) on operational errors (e.g., a target exists but cannot be
   removed), surfacing the path in the error message.
9. **FR-9 — API shape.** `clean.py` exposes `run_clean(coverage, artifacts,
   baselines, cache, all, dry_run, project_root) -> CleanResult` with a
   structured result (per-target status + freed bytes) so the CLI layer stays
   thin and testable.
10. **FR-10 — Docs.** USER_GUIDE section for `clean` (flags, protected paths,
    inventory behavior); ROADMAP Track 39 status updated to Delivered.

## Non-Functional Requirements

- **NFR-1 — Style:** ruff + black clean; type hints and docstrings per
  `code_styleguides/`.
- **NFR-2 — Testing:** unit tests with `tmp_path` project fixtures covering
  every flag, dry-run, no-flag inventory, missing targets, redundancy
  subsumption, and the protected-path guarantees. Coverage gates
  (>80% line / >70% branch) must hold.
- **NFR-3 — Safety:** default is delete-nothing; destructive action always
  requires an explicit flag; `--dry-run` never mutates.

## Acceptance Criteria

1. `gd-tools clean` (no flags) prints inventory + hint and exits 0 without
   deleting anything.
2. `gd-tools clean --coverage` removes `.gd-tools/coverage/` (including
   `plan.json` and `baseline.json`).
3. `gd-tools clean --artifacts` removes `.gd-tools/artifacts/`;
   `--cache` removes `.gd-tools/native/`; `--baselines` removes only
   `baseline.json`.
4. `gd-tools clean --all` removes the entire `.gd-tools/` directory.
5. `--dry-run` (alone or combined) deletes nothing and prints what would go.
6. `addons/`, `gd-tools.toml`, `.gutconfig.json`, and `~/.gd-tools` are never
   touched — asserted by tests.
7. Summary of removals (and freed sizes) printed on real runs.
8. Full suite passes with coverage gates met; ruff/black clean.
9. USER_GUIDE documents the command; ROADMAP marks Track 39 delivered.

## Out of Scope

- Cleaning directories other than project `.gd-tools/` (home cache, Godot
  `.godot/`, build exports).
- Interactive prompts (explicitly rejected in favor of inventory + hint).
- Deleting add-on `.backups/` directories (they live under the protected
  `addons/` tree and safeguard user modifications).
- Any config `[clean]` persistence section (flags only; can be added later).

## Decision Log

1. Type: **Feature** (user-confirmed).
2. No-flag behavior: **inventory + hint**, delete nothing (user-selected over
   interactive prompt and default-to-coverage).
3. Flag set: **extended** beyond roadmap — `--coverage`, `--artifacts`,
   `--baselines`, `--cache`, `--all`, `--dry-run` (user-selected; roadmap
   predated artifacts/baselines/native work dir).
4. `--cache` maps to `.gd-tools/native/` since the plan cache (`plan.json`)
   lives inside the coverage dir (user-confirmed).
5. Overlapping flags: **silently subsumed**, no error (user-confirmed).
