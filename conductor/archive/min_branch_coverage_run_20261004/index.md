# Track: Min-Branch Gate on `coverage run` + Zero-Branch Exemption

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)

Wire `--min-branch` into `gd-tools coverage run` (closing the PR #39 gap)
and define the zero-branch-point rule consistently: exempt with an explicit
console note rather than a failure.
