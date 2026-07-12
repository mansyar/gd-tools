<protect>
# Track: CI/CD Pipeline

**Track ID:** cicd_pipeline_20260712
**Type:** Feature
**Phase:** 4 — Polish
**Status:** New
**Created:** 2026-07-12

---

## Overview

Set up a GitHub Actions CI/CD pipeline for the `gd-tools` project with staged test gating, cross-platform testing, coverage reporting, and a release workflow skeleton. This track implements the CI/CD infrastructure described in `docs/ROADMAP.md` §Track 15, `docs/TESTING_STRATEGY.md` §9, and `conductor/tech-stack.md` §8.

## Context

- **Dependencies:** Track 14 (Test Suite) — ✅ completed. 630 tests (572 unit + 50 integration + 8 E2E). 99.49% line, 98% branch coverage.
- **Project status:** Phase 4 (Polish & Release). All MVP1 (Tracks 4-8) and MVP2 (Tracks 9-13) tracks completed.
- **Current test infrastructure:** `conftest.py` with `find_godot_binary()`, `.env` loading via `python-dotenv`, `pyproject.toml` pytest config with `--cov=gd_tools`, `--cov-branch`, `--cov-fail-under=80`.

## Functional Requirements

### FR-1: CI Workflow (`.github/workflows/ci.yml`)

**FR-1.1:** The CI pipeline triggers on push to `main` and on all pull requests.

**FR-1.2:** The pipeline uses staged gating with three sequential stages:

| Stage | Name | Runs | Depends On | Timeout |
|-------|------|------|------------|---------|
| 1 | `lint-format-unit` | ruff check, black --check, unit tests | — | 5 min |
| 2 | `integration` | Integration tests (requires Godot binary) | Stage 1 | 10 min |
| 3 | `e2e` | E2E tests (requires Godot + sample project) | Stage 2 | 10 min |

**FR-1.3:** Stage 1 runs on `ubuntu-latest` with Python 3.12.
- Lint: `ruff check src/ tests/`
- Format check: `black --check src/ tests/`
- Unit tests: `CI=true pytest tests/unit/ -m unit --cov=gd_tools --cov-report=xml`
- Upload coverage XML to codecov.io via `codecov-action@v4`

**FR-1.4:** Stage 1 also runs a cross-platform matrix job (Ubuntu + Windows, Python 3.10, 3.11, 3.12) running unit tests only. This verifies cross-platform compatibility without the slower integration tests.

**FR-1.5:** Stage 2 (integration tests) runs on `ubuntu-latest` with Python 3.12. It installs the latest stable Godot binary from GitHub releases, sets `GODOT_BIN` env var, and runs `CI=true pytest tests/integration/ -m integration`.

**FR-1.6:** Stage 3 (E2E tests) runs on `ubuntu-latest` with Python 3.12. It installs Godot, sets `GODOT_BIN`, and runs `CI=true pytest tests/e2e/ -m e2e`.

**FR-1.7:** Each stage uses `needs:` to enforce ordering — a failing stage blocks downstream stages.

**FR-1.8:** Job-level timeouts are set per stage to prevent hung CI.

**FR-1.9:** Test results (JUnit XML) are uploaded as GitHub Actions artifacts for debugging failures.

### FR-2: Godot Installation in CI

**FR-2.1:** Godot binary is downloaded from the official GitHub releases page (`https://github.com/godotengine/godot/releases`).

**FR-2.2:** The latest stable Godot release is used (currently 4.6.x). The download URL pattern is: `Godot_v{VERSION}-stable_linux.x86_64.zip`.

**FR-2.3:** The binary is placed on PATH as `godot` and made executable (`chmod +x`).

**FR-2.4:** The `GODOT_BIN` environment variable is set to the absolute path of the installed binary, ensuring the project's `find_godot_binary()` conftest helper detects it.

**FR-2.5:** Godot version is verified by running `godot --version` before tests start.

### FR-3: Coverage Reporting

**FR-3.1:** Coverage XML is generated during Stage 1 unit tests: `--cov-report=xml`.

**FR-3.2:** Coverage is uploaded to codecov.io using `codecov/codecov-action@v4` with the `CODECOV_TOKEN` secret.

**FR-3.3:** Coverage artifacts (XML + HTML) are also uploaded as GitHub Actions artifacts for local download.

### FR-4: Release Workflow (`.github/workflows/release.yml`)

**FR-4.1:** The release workflow triggers on tag push matching pattern `v*` (e.g., `v0.1.0`).

**FR-4.2:** The workflow builds the package: `python -m build` (produces sdist + wheel).

**FR-4.3:** The workflow verifies the package: `twine check dist/*`.

**FR-4.4:** The workflow uploads to TestPyPI using `twine upload --repository testpypi dist/*` with `TEST_PYPI_API_TOKEN` secret.

**FR-4.5:** The release workflow is a skeleton — production PyPI publish is deferred to Track 17 (PyPI Release).

### FR-5: Caching

**FR-5.1:** Python dependencies are cached using `actions/setup-python@v5` with `cache: pip` to speed up subsequent runs.

## Non-Functional Requirements

### NFR-1: Pipeline Duration
The full CI pipeline (all 3 stages) must complete in under 10 minutes total. Stages run sequentially, so this is the sum of all stage durations.

### NFR-2: Non-Interactive
All CI jobs run with `CI=true` environment variable to ensure single-execution mode (no watch mode, no interactive prompts).

### NFR-3: Fail-Fast
A failing job in any stage immediately fails the pipeline. Downstream stages are skipped (via `needs:` dependency).

### NFR-4: Secrets
- `CODECOV_TOKEN` — required for codecov.io upload (Stage 1)
- `TEST_PYPI_API_TOKEN` — TestPyPI API token (release workflow)

### NFR-5: Concurrency
The CI workflow uses `concurrency` groups to cancel superseded runs on the same branch/PR, saving CI minutes.

## Acceptance Criteria

1. **AC-1:** Pushing to a PR branch triggers the CI pipeline automatically.
2. **AC-2:** All 3 stages (lint-format-unit → integration → e2e) run in the correct order, with each stage depending on the previous via `needs:`.
3. **AC-3:** Stage 1 passes when ruff, black, and all unit tests pass (572 tests, ~10s).
4. **AC-4:** Stage 2 passes when all integration tests pass (50 tests, requires Godot binary installed in CI).
5. **AC-5:** Stage 3 passes when all E2E tests pass (8 tests, requires Godot + sample project).
6. **AC-6:** A failing stage blocks downstream stages from running.
7. **AC-7:** Coverage XML is uploaded to codecov.io successfully (visible in codecov dashboard).
8. **AC-8:** JUnit XML test results are uploaded as GitHub Actions artifacts.
9. **AC-9:** Pushing a tag (`v0.1.0`) triggers the release workflow, which builds the package and uploads to TestPyPI.
10. **AC-10:** The cross-platform matrix (Ubuntu + Windows, Python 3.10/3.11/3.12) runs unit tests successfully on all combinations.
11. **AC-11:** Pipeline completes in under 10 minutes total.
12. **AC-12:** The `release.yml` workflow is functional but publishes only to TestPyPI (not production PyPI — deferred to Track 17).

## Out of Scope

1. **Production PyPI publish** — Track 17 (PyPI Release) handles the final production publish.
2. **Branch protection rules** — These are GitHub repository settings (not workflow files). Documented as a recommendation but not automated.
3. **GitHub release creation** — Tagged release with release notes is Track 17's scope.
4. **Pre-commit hooks** — Listed in PRD §17 (Future Roadmap). Not part of CI/CD pipeline.
5. **macOS CI** — Deferred to future iteration (budget consideration per ROADMAP).
6. **Docker-based CI** — Not needed; GitHub Actions runners are sufficient.

## References

- `docs/ROADMAP.md` §Track 15 (lines 1292-1325)
- `docs/TESTING_STRATEGY.md` §9 (CI/CD Test Pipeline, lines 1162-1217)
- `docs/PRD.md` §15 (CI/CD Integration, lines 762-802)
- `conductor/tech-stack.md` §8 (CI/CD Stack)
- `conductor/product.md` §8 (Success Criteria — CI pipeline <10 min)
- `conductor/workflow.md` (Phase Completion Verification Protocol)
</protect>
