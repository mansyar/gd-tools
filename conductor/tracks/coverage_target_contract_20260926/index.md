# Track coverage_target_contract_20260926 Context

Decide and implement what a coverage target that cannot be instrumented should
do. **Resolved 2026-09-27: warn and continue**, recording the omission in all
three reporting surfaces.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Known Flaky Tests](./known_flakes.md)
- [Metadata](./metadata.json)

The four behavioral questions are answered in "Resolved decisions" in the
specification. The plan is a four-phase, TDD-ordered roadmap; **Phase 1
establishes the reporter baseline that spec R3's mechanism depends on**, and
Task 2.3 is explicitly conditional on that finding.
