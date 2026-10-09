# Specification: CLI Core Refactor

*Track ID: `cli_core_refactor_20261009` · Type: Chore (Refactor) · Created: 2026-10-09*

## Overview

`src/gd_tools/cli.py` has grown into a 1,790-line monolith holding all 12 CLI commands, rendering helpers, and ~18 hand-written pairwise flag-conflict checks. Additionally, the atomic-JSON-write pattern is implemented four times across the codebase, and the repo carries dead artifacts from the GUT-bridge removal era. This track restructures the CLI layer for maintainability without changing any external behavior: the CLI contract (commands, flags, output, exit codes) is frozen; the internal module layout is freed.

## Functional Requirements

- **FR-1 — Full command decomposition.** All 12 commands (`init`, `doctor`, `version`, `test`, `migrate`, `lint`, `format`, `coverage {report,merge,show,save-baseline,diff,run}`, `config {show,validate,schema}`, `completion`, `install-hooks`, `clean`) move into per-command modules under `src/gd_tools/commands/`. `cli.py` remains the thin dispatcher and retains: `GdToolsGroup` (pre-dispatch update/addon checks, `NotImplementedError` → exit 2), PowerShell completion, Windows UTF-8 setup, and the command-tree registration.
- **FR-2 — Shared-state access.** Extracted command modules import existing shared modules directly (`config`, `output`, `verbosity`, `errors`, etc.). No new context/abstraction layer is introduced.
- **FR-3 — Declarative conflict table.** The `test` command's hand-written flag-conflict checks (cli.py:800–873) are replaced by a data-driven conflict table in a dedicated module (e.g., `commands/test_validation.py`) with its own unit tests. Rules cover the existing pairwise constraints (`--base` requires `--changed`; `--shard`/`--changed`/`--watch`/CI incompatibilities, etc.) with unchanged error messages and exit-code-2 semantics.
- **FR-4 — Atomic-write consolidation.** The four implementations (`atomic_io.py:16/61`, `native_test/artifacts.py:234`, `native_test/orchestrator.py` inline, `native_test/protocol.py` inline) consolidate onto `atomic_io.py`. Call sites are updated; `atomic_io` API gains whatever thin JSON helper is needed (e.g., `atomic_write_json`).
- **FR-5 — Repo hygiene.** Remove: stray `out.json` at repo root, stale `__pycache__/test_runner.cpython-313*.pyc`, duplicate `gd_tools_cli.egg-info/`, one-off `tools/verify_watch_phase2.py` dev script (if truly unreferenced — verify before deleting).
- **FR-6 — Un-hardcode `config validate`.** The "Sections validated: 5 (…)" string derives from the config model rather than a hardcoded literal.

## Non-Functional Requirements

- **NFR-1 — Behavior frozen:** identical commands, flags, help-text semantics, output, and exit codes (0/1/2). The `gd-tools` console script and `python -m gd_tools` entry points are unchanged.
- **NFR-2 — Test safety net:** the full suite (`CI=true pytest`, ~1,825 tests) passes before and after every phase; no test is modified to accommodate the refactor except where it imports `cli.py` internals (updates limited to mechanical import-path changes).
- **NFR-3 — Coverage non-regression:** `pytest --cov=gd_tools --cov-branch` line ≥80% / branch ≥70% overall, and per-module coverage of new `commands/` modules ≥ the coverage of the code they replaced.
- **NFR-4 — Style:** conforms to `conductor/code_styleguides/python.md`; `ruff check` and `black --check` clean.
- **NFR-5 — Import hygiene:** no circular imports introduced (verified by import smoke test).

## Acceptance Criteria

1. `src/gd_tools/cli.py` contains no command implementation bodies beyond the dispatcher/`GdToolsGroup`/completion/UTF-8 setup.
2. Every command lives in exactly one module under `commands/`; no cross-command logic duplication introduced.
3. Exactly one atomic-write implementation exists; all call sites delegate to it.
4. Flag-conflict behavior is table-driven, unit-tested independently, and produces byte-identical error messages.
5. Repo contains none of the FR-5 artifacts.
6. Full suite green; coverage gates met; ruff/black clean.

## Out of Scope

- Any user-visible change (new flags, changed output, improved error wording)
- Refactors of `native_test/`, `coverage/`, or `watch/` internals beyond FR-4 call-site updates
- Removing the deprecated `--format` alias or the `--runtime gut` rejection choice (public surface frozen)
- Renaming the package or changing packaging metadata (egg-info *deletion* is hygiene; the canonical `gd_tools.egg-info` stays)
