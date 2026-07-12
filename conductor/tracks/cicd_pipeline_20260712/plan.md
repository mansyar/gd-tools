<protect>
# Implementation Plan: CI/CD Pipeline

**Track ID:** cicd_pipeline_20260712
**Spec:** [./spec.md](./spec.md)
**Created:** 2026-07-12

> **Note:** This track creates configuration files (`.github/workflows/*.yml`). Per `workflow.md`, config files do NOT require TDD tests. Verification is done via YAML validation and GitHub Actions execution.

---

## Phase 1: CI Workflow Foundation (ci.yml) [checkpoint: 3038ec1]

- [x] Task: Read [spec.md](./spec.md) and [workflow.md](../../workflow.md) to review requirements and TDD protocol before starting this phase

- [x] Task: Create `.github/workflows/` directory and `ci.yml` file skeleton [7c486f7]
    - [x] Create `.github/workflows/` directory
    - [x] Create `ci.yml` with workflow name, trigger definitions (push to `main`, pull requests)
    - [x] Add `concurrency` group to cancel superseded runs on same branch/PR

- [x] Task: Implement Stage 1 — `lint-format-unit` job [7c486f7]
    - [x] Define job `lint-format-unit` on `ubuntu-latest` with Python 3.12
    - [x] Add `actions/checkout@v4` step
    - [x] Add `actions/setup-python@v5` step with `cache: pip`
    - [x] Add `pip install -e ".[dev]"` step (install project + dev dependencies)
    - [x] Add `ruff check src/ tests/` step
    - [x] Add `black --check src/ tests/` step
    - [x] Add `CI=true pytest tests/unit/ -m unit --cov=gd_tools --cov-report=xml --cov-report=html` step
    - [x] Add `codecov/codecov-action@v4` upload step with `CODECOV_TOKEN` secret
    - [x] Add `actions/upload-artifact@v4` step for coverage XML/HTML reports
    - [x] Set job timeout to 5 minutes

- [x] Task: Implement cross-platform matrix job [7c486f7]
    - [x] Define job `matrix-unit` with `needs: lint-format-unit`
    - [x] Set strategy matrix: OS `[ubuntu-latest, windows-latest]` × Python `[3.10, 3.11, 3.12]`
    - [x] Add checkout, setup-python (with cache), pip install steps
    - [x] Add `CI=true pytest tests/unit/ -m unit` step (no coverage in matrix)
    - [x] Set job timeout to 5 minutes

- [x] Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)

## Phase 2: Godot Integration & Stages 2-3 (ci.yml) [checkpoint: be67452]

- [x] Task: Read [spec.md](./spec.md) and [workflow.md](../../workflow.md) to review requirements and TDD protocol before starting this phase

- [x] Task: Implement Stage 2 — `integration` job [bff9221]
    - [x] Define job `integration` with `needs: lint-format-unit` (Stage 1)
    - [x] Run on `ubuntu-latest` with Python 3.12
    - [x] Add checkout, setup-python (with cache), pip install steps
    - [x] Add Godot installation step (download latest stable from GitHub releases)
    - [x] Add `chmod +x` and move binary to PATH as `godot`
    - [x] Set `GODOT_BIN` environment variable to absolute path of binary
    - [x] Add `godot --version` verification step
    - [x] Add `CI=true pytest tests/integration/ -m integration` step
    - [x] Set job timeout to 10 minutes

- [x] Task: Implement Stage 3 — `e2e` job [bff9221]
    - [x] Define job `e2e` with `needs: integration` (Stage 2)
    - [x] Run on `ubuntu-latest` with Python 3.12
    - [x] Add checkout, setup-python (with cache), pip install steps
    - [x] Add Godot installation step (reuse same installation logic as Stage 2)
    - [x] Set `GODOT_BIN` environment variable to absolute path
    - [x] Add `godot --version` verification step
    - [x] Add `CI=true pytest tests/e2e/ -m e2e` step
    - [x] Set job timeout to 10 minutes

- [x] Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)

## Phase 3: Release Workflow Skeleton (release.yml) [checkpoint: 94bc573]

- [x] Task: Read [spec.md](./spec.md) and [workflow.md](../../workflow.md) to review requirements and TDD protocol before starting this phase

- [x] Task: Create `.github/workflows/release.yml` file [406fa6c]
    - [x] Define workflow with trigger on tag push matching `v*` (e.g., `v0.1.0`)
    - [x] Define job `build-and-publish` on `ubuntu-latest` with Python 3.12
    - [x] Add `actions/checkout@v4` step
    - [x] Add `actions/setup-python@v5` step with `cache: pip`
    - [x] Install `build` and `twine` packages
    - [x] Add `python -m build` step (produces sdist + wheel in `dist/`)
    - [x] Add `twine check dist/*` step (verify package metadata)
    - [x] Add `twine upload --repository testpypi dist/*` step with `TEST_PYPI_API_TOKEN` secret
    - [x] Set job timeout to 10 minutes

- [x] Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)

## Phase 4: Validation & Documentation

- [x] Task: Read [spec.md](./spec.md) and [workflow.md](../../workflow.md) to review requirements and TDD protocol before starting this phase

- [x] Task: Validate workflow YAML files
    - [x] Verify YAML syntax and structure of `ci.yml` and `release.yml`
    - [x] Verify `needs:` dependency chain: `lint-format-unit` → `integration` → `e2e`
    - [x] Verify all `actions/*` version references are current
    - [x] Verify env var `CI=true` is set in all test steps
    - [x] Verify `GODOT_BIN` is set in Stages 2 and 3

- [x] Task: Document required GitHub secrets
    - [x] Create documentation listing required secrets: `CODECOV_TOKEN`, `TEST_PYPI_API_TOKEN`
    - [x] Add setup instructions for each secret in GitHub repository settings
    - [x] Add note that `CODECOV_TOKEN` is optional for public repos but recommended

- [x] Task: Final commit and verification [1f0fe69]
    - [x] Stage all workflow files and documentation
    - [x] Commit with message: `feat(ci): Add CI/CD pipeline with staged gating and release skeleton`
    - [ ] Verify pipeline triggers on next push/PR

- [ ] Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)
</protect>
