# Implementation Plan: Roadmap & Docs Truth Pass (2026-10)

Note: documentation files are exempt from tests per workflow.md (Task
Workflow step 3). Verification is via search checks and diff inspection.

## Phase 1: Fold Migration Roadmap §8 into the Main Roadmap

- [x] Task: Inventory §8 anchors and dependencies
  - [x] Search the repo for all links to `ROADMAP.md#8-...` and record target files/lines (expected: `ARCHITECTURE.md`, `conductor/product.md`, `docs/gut-migration.md`)
  - [x] Identify "durable decisions" in §8 (runtime model, migration boundary, success criteria) vs. transient phase-checklist content
- [x] Task: Fold durable content into main roadmap sections
  - [x] Move/merge durable decisions into the appropriate main roadmap sections (Native Runtime Transition overview + remaining Phase 5 items)
  - [x] Record remaining Phase 5 items with "removal targeted for v0.6.0" framing preserved
  - [x] Delete §8 entirely (no tombstone)
- [x] Task: Rewrite all §8 anchor links to the new anchors
- [x] Task: Verify no dangling `#8-...` anchors remain repo-wide (search check)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

[checkpoint: 456c258]

## Phase 2: Refresh ARCHITECTURE.md Known Limitations

- [x] Task: Cross-check every stated limitation against shipped tracks
  - [x] Mark/remove closed limitations (parameterized tests, suite-level skip, signal assertions, editor plugin)
  - [x] Keep true remaining limitations (headless-only runtime, bridge core-subset constraint, etc.) with accurate wording
- [x] Task: Verify bridge-deprecation notes keep "deprecated v0.5.0 / removed v0.6.0" framing (NFR-3)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

[checkpoint: f656e37]

## Phase 3: Reconcile README, USER_GUIDE, and PRD with Shipped Reality

- [x] Task: Verify README feature table and capability claims against v0.5.0 + Unreleased feature set (`--changed`, signal assertions, preflight cache, `coverage run` playtest)
- [x] Task: Verify USER_GUIDE command documentation matches actual CLI surface (flags, subcommands, defaults)
- [x] Task: Apply factual corrections only to PRD (stale "planned/deferred" claims, outdated §8 references); no editorial rewrites of vision/positioning
- [x] Task: Confirm zero `src/` or `tests/` changes in diff (NFR-1) and no CHANGELOG edit (NFR-2)
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

[checkpoint: 362543d]
