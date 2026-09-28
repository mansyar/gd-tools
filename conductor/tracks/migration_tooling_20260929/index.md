# Track migration_tooling_20260929 Context

Builds the guided Migration Tooling (ROADMAP §8 Migration Phase 4): a
`gd-tools migrate` command that produces a read-only, per-file migration
report (base class, supported/unsupported constructs with file:line guidance
reusing the bridge preflight scanner, bridge-only aliases listed as "works
now, rename later"), translates `.gutconfig.json` into `gd-tools.toml`
(merge, never clobber; unmapped options reported), and — behind `--apply` —
performs conservative rewrites: `extends GutTest` → `extends GdToolsTest`
base-class rename plus config translation, shown as unified diffs, written
atomically, and never applied to files with unsupported constructs. Exit
codes: 0 nothing to migrate, 1 findings, 2 infrastructure error. Fulfills
the documented promise in `docs/gut-migration.md` §6 and `product.md`'s
migration boundary. Phase 5 hardening, call-site alias rewrites, and doctor
changes are out of scope.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
