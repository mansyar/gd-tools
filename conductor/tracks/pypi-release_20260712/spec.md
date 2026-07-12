<protect>
# Track 17: PyPI Release

## 1. Overview

Package and publish `gd-tools` to PyPI, completing the v1.0 milestone (M4).
This is the final track in Phase 4 (Polish & Release). The tool has been
fully implemented (Tracks 0-16), tested (99.49% line coverage, 98% branch),
documented (README, User Guide, Contributing Guide, Architecture doc), and
has a CI/CD pipeline with staged gating. This track finalizes package
metadata, extends the release workflow to production PyPI, and performs the
actual release.

**Track Type:** Release/Chore
**Phase:** 4 - Polish & Release
**Dependencies:** Track 14 (tests), Track 15 (CI/CD), Track 16 (docs)
**Estimated Effort:** 0.5 day
**Risk:** LOW

---

## 2. Functional Requirements

### FR-1: Finalize `pyproject.toml` Metadata

- **FR-1.1:** Update the `Development Status` classifier from
  `"Development Status :: 3 - Alpha"` to
  `"Development Status :: 4 - Beta"`.
- **FR-1.2:** Add `[project.urls]` section with the following keys:
  - `Homepage` = `https://github.com/mansyar/gd-tools`
  - `Repository` = `https://github.com/mansyar/gd-tools`
  - `Documentation` = `https://github.com/mansyar/gd-tools#readme`
  - `Bug Tracker` = `https://github.com/mansyar/gd-tools/issues`
- **FR-1.3:** Verify that `readme = "README.md"` correctly renders as the
  PyPI long description (via `twine check`).

### FR-2: Extend Release Workflow for Production PyPI

- **FR-2.1:** Extend `.github/workflows/release.yml` to add a production
  PyPI upload step **after** the TestPyPI upload succeeds.
- **FR-2.2:** The production PyPI upload step must use the `PYPI_API_TOKEN`
  secret (with `TWINE_USERNAME: __token__` and
  `TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}`).
- **FR-2.3:** The TestPyPI upload step must remain as a pre-production
  safety net.
- **FR-2.4:** Update the job name from `"Build & Publish to TestPyPI"` to
  reflect that it now publishes to both TestPyPI and PyPI, or split into
  two jobs with the PyPI job depending on the TestPyPI job.

### FR-3: Update Secrets Documentation

- **FR-3.1:** Update `.github/SECRETS.md` to document the `PYPI_API_TOKEN`
  secret with the same format as existing entries (Used by, Purpose,
  Required for, How to obtain, How to add).
- **FR-3.2:** Update the notes section to reflect that production PyPI
  publishing is now active (remove the "deferred to Track 17" note).

### FR-4: Package Build and Validation

- **FR-4.1:** Run `python -m build` to produce both sdist (`.tar.gz`) and
  wheel (`.whl`) artifacts.
- **FR-4.2:** Run `twine check dist/*` to validate package metadata and
  README rendering.
- **FR-4.3:** Verify package size is under 500KB (per ROADMAP section 7
  success metric).

### FR-5: TestPyPI Validation

- **FR-5.1:** Upload the built package to TestPyPI.
- **FR-5.2:** Verify installation from TestPyPI in a clean virtual
  environment: `pip install -i https://test.pypi.org/simple/ gd-tools`.
- **FR-5.3:** Verify `gd-tools --version` prints `0.1.0` from the
  TestPyPI install.
- **FR-5.4:** Verify `gd-tools --help` shows all command groups from the
  TestPyPI install.

### FR-6: Production PyPI Release

- **FR-6.1:** Upload the built package to production PyPI.
- **FR-6.2:** Verify installation from PyPI in a clean virtual
  environment: `pip install gd-tools`.
- **FR-6.3:** Verify `gd-tools --version` prints `0.1.0` from the PyPI
  install.
- **FR-6.4:** Verify all CLI command groups appear in `--help` output.

### FR-7: Git Tag and GitHub Release

- **FR-7.1:** Create git tag `v0.1.0` on the release commit.
- **FR-7.2:** Push the tag to the remote repository.
- **FR-7.3:** Create a GitHub Release tied to the `v0.1.0` tag with
  release notes summarizing the features delivered across all 17 tracks.

---

## 3. Non-Functional Requirements

- **NFR-1:** Package size under 500KB (sdist + wheel combined).
- **NFR-2:** README renders correctly on PyPI (no broken markdown, no
  missing badges).
- **NFR-3:** All CLI commands work after a non-editable `pip install`
  (not just `pip install -e .`).
- **NFR-4:** The release workflow must not publish to production PyPI if
  the TestPyPI upload or `twine check` fails.
- **NFR-5:** ASCII-only in all modified files (per product-guidelines
  section 7).

---

## 4. Acceptance Criteria

1. `pip install gd-tools` works on a clean virtual environment.
2. `gd-tools --version` prints `0.1.0`.
3. All CLI commands (`test`, `lint`, `format`, `coverage`, `init`,
   `doctor`) appear in `--help` and respond (not just from editable
   install).
4. Package metadata on PyPI is correct (name, version, description,
   author, license, classifiers, URLs).
5. README renders correctly on the PyPI project page.
6. `python -m build` produces both sdist and wheel.
7. `twine check dist/*` passes without warnings.
8. Git tag `v0.1.0` is created and pushed.
9. GitHub Release `v0.1.0` is created with release notes.
10. `release.yml` workflow uploads to both TestPyPI and production PyPI.

---

## 5. Out of Scope

- Post-release monitoring (PyPI download stats, issue triage) - covered
  by workflow.md Deployment Workflow > Post-Release.
- Automated version bumping or changelog generation tooling.
- Pre-commit hook setup (future work per PRD section 17).
- HTML source view in coverage reports (deferred from Track 12).
- Yanking or re-pulling releases (emergency procedure only, documented
  in workflow.md).

---

## 6. References

- [PRD section 15](../../docs/PRD.md) - CI/CD Integration, exit codes
- [ROADMAP section 4 - Track 17](../../docs/ROADMAP.md) - Track scope
  and success criteria
- [Product Definition section 8](../product.md) - Success criteria
  (PyPI publish is the primary release gate)
- [Tech Stack section 8](../tech-stack.md) - CI/CD stack (build, twine,
  PyPI, TestPyPI)
- [Workflow - Deployment Workflow](../workflow.md) - Pre-Release
  Checklist, Release Steps, Post-Release
- `.github/workflows/release.yml` - Existing release workflow (TestPyPI
  only)
- `.github/SECRETS.md` - Secret documentation (PYPI_API_TOKEN to be
  added)
</protect>
