# Track gut_compat_bridge_20260928 Context

Builds the GUT Compatibility Bridge (ROADMAP §8 Migration Phase 3): a
GutTest-compatible shim base class shipped inside the `gd-tools-test` addon so
legacy GUT suites run through the native protocol with the same user-facing
result contract, without the GUT addon installed. Suites are auto-routed per
file (`extends GdToolsTest` → native, `extends GutTest` → bridge, unknown
base → explicit error); a preflight static scan fails unsupported GUT
constructs (mocking, parameterization, mock assertions, property/orphan
checks) before execution with actionable migration guidance. The legacy GUT
subprocess path is removed in this track, bridge results normalize into the
native protocol, coverage works through the same tracker, and
`docs/gut-migration.md` documents the subset. Phase 4 migration tooling and
Phase 5 hardening are out of scope.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
