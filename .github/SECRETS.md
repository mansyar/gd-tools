# Required GitHub Secrets

This document lists the GitHub repository secrets required by the CI/CD
pipeline workflows defined in `.github/workflows/`.

## Secrets

### `CODECOV_TOKEN`

- **Used by:** `.github/workflows/ci.yml` — Stage 1 (`lint-format-unit` job)
- **Purpose:** Authenticates uploads to [codecov.io](https://codecov.io) for
  coverage reporting.
- **Required for:** Public repos — optional but recommended. Private repos —
  required.
- **How to obtain:**
  1. Sign in to [codecov.io](https://codecov.io) with your GitHub account.
  2. Enable the repository.
  3. Copy the repository upload token from Settings → Token.
- **How to add:**
  1. Go to the GitHub repository → **Settings** → **Secrets and variables** →
     **Actions**.
  2. Click **New repository secret**.
  3. Name: `CODECOV_TOKEN`
  4. Value: paste the token from codecov.io.
  5. Click **Add secret**.

### `TEST_PYPI_API_TOKEN`

- **Used by:** `.github/workflows/release.yml` — `build-and-publish` job
- **Purpose:** Authenticates package uploads to
  [TestPyPI](https://test.pypi.org).
- **Required for:** Yes — the release workflow cannot publish without it.
- **How to obtain:**
  1. Create an account on [test.pypi.org](https://test.pypi.org/account/register/).
  2. Go to Account Settings → **API tokens**.
  3. Click **Add API token**.
  4. Scope: **Entire account** (or limit to the project once created).
  5. Copy the token (starts with `pypi-`).
- **How to add:**
  1. Go to the GitHub repository → **Settings** → **Secrets and variables** →
     **Actions**.
  2. Click **New repository secret**.
  3. Name: `TEST_PYPI_API_TOKEN`
  4. Value: paste the TestPyPI API token.
  5. Click **Add secret**.

## Notes

- `CODECOV_TOKEN` is **optional for public repositories** — codecov-action
  can work without it on public repos, but setting it ensures reliable
  uploads and avoids rate limits. It is **recommended** for all repositories.
- `TEST_PYPI_API_TOKEN` is **required** for the release workflow. Without it,
  tag pushes (`v*`) will fail at the upload step.
- Production PyPI publishing is deferred to Track 17 (PyPI Release) and will
  require an additional `PYPI_API_TOKEN` secret at that time.
