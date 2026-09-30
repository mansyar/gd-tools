# Track: Coverage Exclusion Annotations

**Track ID:** `coverage_exclusions_20260930`
**Type:** Feature
**Status:** New
**Branch:** `feat/coverage-exclusions-20260930`

Support `# gd-tools: no cover` annotations (single-line, block `start`/`end`, and
func-line exclusion) so users can exclude lines from coverage instrumentation.
Excluded lines are recorded in the plan JSON, removed from coverage percentage
math, styled distinctly in the HTML report, and summarized in the terminal report.

## Documents

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

## Context

- Product Definition: [conductor/product.md](../../product.md)
- Tech Stack: [conductor/tech-stack.md](../../tech-stack.md)
- Workflow: [conductor/workflow.md](../../workflow.md)
- Source roadmap item: `docs/ROADMAP.md` § Track 30
