# Track 13: Coverage CLI Integration

## Overview

Track 13 wires the existing coverage components — plan generator (Track 9), coverage hooks (Track 11), and reporter (Track 12) — into the `gd-tools` CLI. It implements four user-facing capabilities:

1. **`gd-tools test --coverage`** — Full coverage flow: generate plan → set env vars → run tests with GUT hooks → read coverage data → generate reports → apply threshold → print summary.
2. **`gd-tools coverage report`** — Regenerate reports (HTML/LCOV/Cobertura/terminal) from existing coverage data without re-running tests.
3. **`gd-tools coverage merge`** — Merge multiple coverage data files (sharded runs) into a single file.
4. **`gd-tools coverage show`** — Print a terminal summary table of the last coverage run.

This track also implements `[coverage]` config section loading from `gd-tools.toml`, with resolution: CLI flags > config file > defaults.

## Context & Dependencies

| Dependency | Track | Status |
|------------|-------|--------|
| Test runner (`test_runner.py`) | Track 6 | ✅ Completed |
| Plan generator (`coverage/plan_generator.py`) | Track 9 | ✅ Completed |
| Coverage hooks (`pre_run_hook.gd`, `post_run_hook.gd`) | Track 11 | ✅ Completed |
| Reporter (`coverage/reporter.py` + sub-reporters) | Track 12 | ✅ Completed |
| Config loader (`config.py`) | Track 4 | ✅ Completed |

**Modules to create/modify:**
- `src/gd_tools/cli.py` (update) — Wire `--coverage` flag to `test` command; implement `coverage` command group with `report`, `merge`, `show` subcommands.
- `src/gd_tools/coverage/orchestrator.py` (new) — Orchestration logic coordinating plan_generator → test_runner → reporter.
- `src/gd_tools/coverage/__init__.py` (update) — Re-export orchestrator functions.
- `src/gd_tools/config.py` (update) — Add `[coverage]` config section parsing.

## Functional Requirements

### FR-1: `gd-tools test --coverage`

The `test` command gains a `--coverage` boolean flag. When enabled:

1. Generate coverage plan via `plan_generator.generate_plan()` using config `[coverage]` source_dirs, exclude_dirs, test_dirs.
2. Write plan to `.gd-tools/coverage/plan.json` via `plan_generator.write_plan_json()`.
3. Set environment variables:
   - `GD_TOOLS_COVERAGE_ACTIVE=1`
   - `GD_TOOLS_COVERAGE_PLAN=<abs_path>/.gd-tools/coverage/plan.json`
   - `GD_TOOLS_COVERAGE_OUTPUT=<abs_path>/.gd-tools/coverage/coverage.json`
4. Run Godot+GUT with hooks via `test_runner.run_tests()` (adds `-gpre_run_script` / `-gpost_run_script` args).
5. After tests complete, read coverage JSON + plan JSON.
6. Generate reports via `reporter.generate_report(plan, data, output_dir, format, min_threshold)`.
7. Apply `--min N` threshold check (raises `CoverageThresholdError` if below).
8. Print terminal summary (test results + coverage summary).

**Flags:** `--coverage`, `--min N` (int, threshold %), `--suite NAME`, `--test NAME`, `--junit-xml PATH`, `--no-exit-code`

**Config overrides:** `--min` overrides `[coverage] min_percent`; `--format` overrides `[coverage] format`.

### FR-2: `gd-tools coverage report`

Regenerates reports from existing `.gd-tools/coverage/coverage.json` + `plan.json` without re-running tests.

1. Read plan JSON via `plan_generator.read_plan_json()`.
2. Read coverage JSON via `reporter.read_coverage_json()`.
3. Generate reports via `reporter.generate_report()`.
4. Print output path summary.

**Flags:** `--format html|lcov|cobertura|text` (default: from config or `html`), `--output-dir PATH` (default: from config or `.gd-tools/coverage`)

### FR-3: `gd-tools coverage merge`

Merges multiple coverage data files into one.

1. Read each input file via `reporter.read_coverage_json()`.
2. Merge via `reporter.merge_coverage_data()`.
3. Write merged JSON to `--output` path (default: `.gd-tools/coverage/coverage.json`).
4. Print merge summary (file count, total hits).

**Args:** `files` (variadic, at least 1). **Flags:** `--output PATH`

### FR-4: `gd-tools coverage show`

Prints a terminal summary table of existing coverage data.

1. Read plan JSON + coverage JSON from `.gd-tools/coverage/`.
2. Compute summary via `reporter.compute_summary()`.
3. Print Rich table (file, lines found/hit/%, branches found/hit/%, overall).
4. If `--min N` specified, exit 1 if coverage below threshold.

**Flags:** `--min N` (int, threshold %)

### FR-5: Config Integration (`[coverage]` section)

Load coverage settings from `gd-tools.toml`:

```toml
[coverage]
enabled = true
min_percent = 80
format = "html"
output_dir = ".gd-tools/coverage"
exclude = ["addons", ".godot", ".gd-tools", ".git"]
test_dirs = ["test", "tests"]
```

Resolution order: **CLI flags > config file > hardcoded defaults**.

- If `[coverage]` section is missing, use defaults (enabled=false, min_percent=0, format="html", output_dir=".gd-tools/coverage", exclude=[...], test_dirs=[]).
- If `--coverage` flag is passed, it overrides `enabled=false` in config.

## Non-Functional Requirements

| ID | Requirement |
|----|------------|
| NFR-1 | Orchestration logic in `src/gd_tools/coverage/orchestrator.py`, not in `cli.py` or `__init__.py`. CLI commands are thin wrappers calling orchestrator functions. |
| NFR-2 | Error precedence: when both `TestFailureError` and `CoverageThresholdError` occur, test failures are reported first in output. Both summaries printed. Exit code 1 (TestFailureError precedence). |
| NFR-3 | All error messages follow Cause/Fix format per product-guidelines §4. |
| NFR-4 | Exit codes: 0 = pass, 1 = test failures / coverage below threshold, 2 = environment/config error (CoveragePlanError, ConfigError, GodotNotFoundError). |
| NFR-5 | Coverage data saved to `.gd-tools/coverage/` (plan.json, coverage.json, html/, lcov.info, cobertura.xml). |
| NFR-6 | JUnit XML produced alongside coverage at `.gd-tools/results.xml` (both available simultaneously). |
| NFR-7 | Cross-platform: works on Windows, macOS, Linux (no OS-specific path assumptions; use `pathlib.Path`). |
| NFR-8 | Type hints on all new functions. Docstrings on all new public functions. |

## Acceptance Criteria

1. **AC-1:** `gd-tools test --coverage` runs tests, collects coverage data, and generates an HTML report in `.gd-tools/coverage/html/`.
2. **AC-2:** `gd-tools test --coverage --min 80` exits with code 1 when overall line coverage is below 80%, exits 0 when ≥80%.
3. **AC-3:** `gd-tools coverage report` reads existing `.gd-tools/coverage/coverage.json` + `plan.json` and regenerates reports without re-running tests.
4. **AC-4:** `gd-tools coverage merge file1.json file2.json --output merged.json` correctly combines hit counts per file_id/line_id.
5. **AC-5:** `gd-tools coverage show` prints a readable Rich summary table with per-file and overall coverage metrics.
6. **AC-6:** Coverage data (plan.json, coverage.json) saved to `.gd-tools/coverage/` directory.
7. **AC-7:** JUnit XML (`.gd-tools/results.xml`) is produced alongside coverage data when running `test --coverage`.
8. **AC-8:** Full end-to-end `gd-tools test --coverage` flow works on the development OS (Windows).
9. **AC-9:** `[coverage]` config section loaded from `gd-tools.toml`; CLI flags override config values, config overrides defaults.
10. **AC-10:** When tests fail AND coverage is below threshold, test failure summary is printed first, followed by coverage summary. Exit code is 1.
11. **AC-11:** Unit tests pass with `CI=true pytest -m unit` (<5s, no Godot required).
12. **AC-12:** `ruff check src/ tests/` and `black --check src/ tests/` pass with no errors.

## Out of Scope

- HTML source code display in reports (deferred known limitation from Track 12; line numbers shown but source not populated).
- Coverage of addon files (excluded entirely per TDD §12 Q2).
- Concurrent/parallel test run support (GDScript is single-threaded; not a v1 concern per TDD §12 Q5).
- CI/CD pipeline setup (Track 15).
- Full test suite implementation (Track 14).
- User documentation (Track 16).

## Technical References

- **ROADMAP.md** §Track 13 (lines 1130-1179) — Scope, success criteria, deliverables.
- **TDD.md** §3.4 — cli.py module spec (command groups, flags).
- **TDD.md** §3.7 — test_runner.py `run_gut_with_coverage()` function spec.
- **TDD.md** §5 — Data contracts (plan JSON, coverage JSON, env vars).
- **TDD.md** §6 — 15-step end-to-end coverage flow.
- **TDD.md** §8 — Error handling strategy (exit codes, exception flow).
- **PRD.md** §5 — CLI command surface specification.
- **PRD.md** §10 — Coverage architecture overview.
- **product-guidelines.md** §4 — Error message format (Cause/Fix).
