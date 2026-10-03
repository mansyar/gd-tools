# Track: Ternary Branch Separation

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

Make ternary branch coverage measurable by instrumenting each ternary arm at
its operand expression with value-preserving wrapper calls, closing the
documented known limitation from the `ternary_instrumentation_20261003` track.
