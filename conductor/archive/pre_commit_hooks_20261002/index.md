# Track: Pre-commit Hook Integration

**Track ID:** `pre_commit_hooks_20261002`
**Status:** new
**Type:** Feature
**Branch:** `feature/pre-commit-hooks-20261002`

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Add a `gd-tools install-hooks` command that wires gd-tools into the pre-commit
framework: generate `.pre-commit-hooks.yaml`, write/merge a `repos: local:`
entry into `.pre-commit-config.yaml` (merge-by-id, never clobber foreign
hooks), offer format/lint/test hooks with an interactive prompt plus
`--all`/`--hooks`/`--non-interactive` flags, and document the integration in
README and USER_GUIDE.
