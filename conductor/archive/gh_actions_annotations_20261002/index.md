# Track: GitHub Actions Annotations (`gh_actions_annotations_20261002`)

- **Type:** Feature
- **Status:** new
- **Branch:** `feature/gh-actions-annotations-20261002`
- **Created:** 2026-10-02

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Implement Roadmap Track 31: add a `github-actions` report format to
`lint`, `coverage report`, and `coverage run`, emitting official GitHub
Actions workflow log commands (`::error` / `::warning`) so lint
violations and coverage threshold failures surface as native PR
annotations. Includes lint annotation formatting with spec-compliant
escaping, a coverage annotation reporter (summary gate error + per-file
warnings), CLI choice wiring, `[coverage].format` config alignment, and
USER_GUIDE/CHANGELOG documentation. SARIF and other CI log formats are
out of scope.
