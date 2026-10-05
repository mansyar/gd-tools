# Track: Expression-Level Branch Coverage

- **Track ID:** `expression_branch_coverage_20261005`
- **Type:** Feature
- **Status:** new
- **Branch:** `feature/expression-branch-coverage-20261005`

Extend hybrid branch coverage beyond ternaries: `and`/`or` short-circuit
operators (per-operator branch points with right/short arms) and `assert`
conditions (`assert_true`/`assert_false` arms) become first-class, fully
gated branch points. `PLAN_VERSION` 6→7 with cache invalidation and a loud
old-addon handshake.

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
