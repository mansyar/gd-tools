# Track: Coverage During Playtesting

**Track ID:** `playtest_coverage_20260930`
**Type:** Feature
**Status:** New
**Branch:** `feature/playtest-coverage-20260930`

`gd-tools coverage run` launches the game windowed and instrumented, collects
coverage during live gameplay via an env-activated playtest mode in the coverage
autoload (periodic + exit flush), and reports through the existing reporter
suite with `--timeout` and `--min` gating. Source: `docs/ROADMAP.md` Track 34.

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Context

- Product Definition: [conductor/product.md](../../product.md)
- Tech Stack: [conductor/tech-stack.md](../../tech-stack.md)
- Workflow: [conductor/workflow.md](../../workflow.md)
- Source roadmap item: `docs/ROADMAP.md` — Track 34
