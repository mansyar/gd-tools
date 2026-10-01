# Track: Native Runtime Caching (Preflight Cache)

**Track ID:** `native_runtime_caching_20261001` · **Type:** Chore (Performance) · **Status:** new

Closes the final deferred Migration Phase 5 item from ROADMAP.md.

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Summary

Content-hash cache for the native integration preflight under
`.gd-tools/native/preflight-cache/`: repeat `gd-tools test` runs on unchanged
projects skip the headless preflight Godot process. Keyed on test-file hashes,
`project.godot`, Godot binary version, and bundled addon hashes. `--no-cache`
escape hatch, verbose hit/miss reporting, fail-open on cache errors, cached
preflight artifacts copied into run artifacts, and a ≥30% repeat-run speedup
gate on the dogfood `spike/` project.
