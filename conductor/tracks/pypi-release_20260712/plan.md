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

## Phase 2: Release Workflow and Secrets Documentation [checkpoint: 59cc2db]

- [x] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [x] Task: Extend `.github/workflows/release.yml` for production PyPI [6ee4b81]
    - [x] Add a `publish-pypi` job that depends on the existing `build-and-publish` (TestPyPI) job
    - [x] Configure the PyPI upload step with `TWINE_USERNAME: __token__` and `TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}`
    - [x] Ensure the TestPyPI upload step remains as a pre-production safety net
    - [x] Update job/step names to reflect both TestPyPI and PyPI publishing
    - [x] Commit: `ci(release): Add production PyPI upload to release workflow`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Update `.github/SECRETS.md` [99a1f9d]
    - [x] Add `PYPI_API_TOKEN` secret documentation (Used by, Purpose, Required for, How to obtain, How to add)
    - [x] Remove the "Production PyPI publishing is deferred to Track 17" note from the notes section
    - [x] Commit: `docs(secrets): Document PYPI_API_TOKEN secret for production PyPI`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Release Workflow and Secrets Documentation' (Protocol in workflow.md)

## Phase 3: Package Build and Local Validation [checkpoint: f80e4a3]

- [x] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [x] Task: Build and validate package locally [af832af]
    - [x] Run `python -m build` to produce sdist (`.tar.gz`) and wheel (`.whl`) in `dist/`
    - [x] Run `twine check dist/*` to validate package metadata and README rendering
    - [x] Verify combined package size (sdist + wheel) is under 500KB
    - [x] Inspect `dist/` contents to confirm both artifacts present
    - [x] Commit: `chore(build): Verify package build and twine check pass`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Package Build and Local Validation' (Protocol in workflow.md)

## Phase 4: TestPyPI Publication and Validation [checkpoint: 34a9af9]

- [x] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [x] Task: Publish to TestPyPI and verify installation [e2754f8]
    - [x] Upload built package to TestPyPI: `twine upload --repository testpypi dist/*`
    - [x] Create a clean virtual environment
    - [x] Install from TestPyPI: `pip install -i https://test.pypi.org/simple/ gd-tools`
    - [x] Verify `gd-tools --version` prints `0.1.0`
    - [x] Verify `gd-tools --help` shows all command groups (test, lint, format, coverage, init, doctor)
    - [x] Commit: `chore(release): Verify TestPyPI publication and installation`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Conductor - User Manual Verification 'TestPyPI Publication and Validation' (Protocol in workflow.md)

## Phase 5: Production PyPI Publication [checkpoint: 88acad2]

- [x] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [x] Task: Publish to production PyPI and verify installation [cb82521]
    - [x] Upload built package to PyPI: `twine upload dist/*`
    - [x] Create a clean virtual environment
    - [x] Install from PyPI: `pip install gd-tools-cli` (renamed from gd-tools due to PyPI name conflict with existing 'gdtools' project)
    - [x] Verify `gd-tools --version` prints `0.1.0`
    - [x] Verify all CLI commands appear in `--help` output (test, lint, format, coverage, init, doctor)
    - [x] Verify package metadata on PyPI project page (name, version, description, author, license, classifiers, URLs)
    - [x] Verify README renders correctly on the PyPI project page
    - [x] Commit: `chore(release): Rename to gd-tools-cli and publish 0.1.0 to PyPI`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Production PyPI Publication' (Protocol in workflow.md)

## Phase 6: Git Tag and GitHub Release [checkpoint: cc5423d]

- [x] Task: Read `spec.md` and `../workflow.md` to review requirements and workflow protocols for this phase
- [x] Task: Create git tag and GitHub release [0947c0b]
    - [x] Create git tag `v0.1.0` on the release commit
    - [x] Push tag to remote: `git push origin v0.1.0`
    - [x] Create GitHub Release tied to `v0.1.0` tag with release notes summarizing features delivered across all 17 tracks
    - [x] Commit: `chore(release): Tag v0.1.0 and create GitHub release`
    - [x] Attach git note with task summary
    - [x] Update plan.md: mark task `[x]` with commit SHA
- [x] Task: Conductor - User Manual Verification 'Git Tag and GitHub Release' (Protocol in workflow.md)
</protect>
