<protect>
# Track 17: PyPI Release - Implementation Plan

## Phase 1: Package Metadata Finalization [checkpoint: 98a3ca1]

- [x] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [x] Task: Update `pyproject.toml` metadata [6ce43dc]
    - [x] Change Development Status classifier from `"Development Status :: 3 - Alpha"` to `"Development Status :: 4 - Beta"`
    - [x] Add `[project.urls]` section with Homepage, Repository, Documentation, and Bug Tracker URLs
    - [x] Verify `readme = "README.md"` is present and correct
    - [x] Run `ruff check` and `black --check` to ensure no style violations introduced
    - [x] Commit: `chore(pyproject): Update package metadata for PyPI release`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Package Metadata Finalization' (Protocol in workflow.md)

## Phase 2: Release Workflow and Secrets Documentation

- [ ] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [ ] Task: Extend `.github/workflows/release.yml` for production PyPI
    - [ ] Add a `publish-pypi` job that depends on the existing `build-and-publish` (TestPyPI) job
    - [ ] Configure the PyPI upload step with `TWINE_USERNAME: __token__` and `TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}`
    - [ ] Ensure the TestPyPI upload step remains as a pre-production safety net
    - [ ] Update job/step names to reflect both TestPyPI and PyPI publishing
    - [ ] Commit: `ci(release): Add production PyPI upload to release workflow`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA
- [ ] Task: Update `.github/SECRETS.md`
    - [ ] Add `PYPI_API_TOKEN` secret documentation (Used by, Purpose, Required for, How to obtain, How to add)
    - [ ] Remove the "Production PyPI publishing is deferred to Track 17" note from the notes section
    - [ ] Commit: `docs(secrets): Document PYPI_API_TOKEN secret for production PyPI`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Release Workflow and Secrets Documentation' (Protocol in workflow.md)

## Phase 3: Package Build and Local Validation

- [ ] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [ ] Task: Build and validate package locally
    - [ ] Run `python -m build` to produce sdist (`.tar.gz`) and wheel (`.whl`) in `dist/`
    - [ ] Run `twine check dist/*` to validate package metadata and README rendering
    - [ ] Verify combined package size (sdist + wheel) is under 500KB
    - [ ] Inspect `dist/` contents to confirm both artifacts present
    - [ ] Commit: `chore(build): Verify package build and twine check pass`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Package Build and Local Validation' (Protocol in workflow.md)

## Phase 4: TestPyPI Publication and Validation

- [ ] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [ ] Task: Publish to TestPyPI and verify installation
    - [ ] Upload built package to TestPyPI: `twine upload --repository testpypi dist/*`
    - [ ] Create a clean virtual environment
    - [ ] Install from TestPyPI: `pip install -i https://test.pypi.org/simple/ gd-tools`
    - [ ] Verify `gd-tools --version` prints `0.1.0`
    - [ ] Verify `gd-tools --help` shows all command groups (test, lint, format, coverage, init, doctor)
    - [ ] Commit: `chore(release): Verify TestPyPI publication and installation`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'TestPyPI Publication and Validation' (Protocol in workflow.md)

## Phase 5: Production PyPI Publication

- [ ] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [ ] Task: Publish to production PyPI and verify installation
    - [ ] Upload built package to PyPI: `twine upload dist/*`
    - [ ] Create a clean virtual environment
    - [ ] Install from PyPI: `pip install gd-tools`
    - [ ] Verify `gd-tools --version` prints `0.1.0`
    - [ ] Verify all CLI commands appear in `--help` output (test, lint, format, coverage, init, doctor)
    - [ ] Verify package metadata on PyPI project page (name, version, description, author, license, classifiers, URLs)
    - [ ] Verify README renders correctly on the PyPI project page
    - [ ] Commit: `chore(release): Publish gd-tools 0.1.0 to PyPI`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Production PyPI Publication' (Protocol in workflow.md)

## Phase 6: Git Tag and GitHub Release

- [ ] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [ ] Task: Create git tag and GitHub release
    - [ ] Create git tag `v0.1.0` on the release commit
    - [ ] Push tag to remote: `git push origin v0.1.0`
    - [ ] Create GitHub Release tied to `v0.1.0` tag with release notes summarizing features delivered across all 17 tracks
    - [ ] Commit: `chore(release): Tag v0.1.0 and create GitHub release`
    - [ ] Attach git note with task summary
    - [ ] Update plan.md: mark task `[x]` with commit SHA
- [ ] Task: Conductor - User Manual Verification 'Git Tag and GitHub Release' (Protocol in workflow.md)
</protect>
