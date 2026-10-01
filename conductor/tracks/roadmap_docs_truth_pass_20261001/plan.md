# Implementation Plan: Roadmap & Docs Truth Pass (2026-10)

Note: documentation files are exempt from tests per workflow.md (Task
Workflow step 3). Verification is via search checks and diff inspection.

## Phase 1: Fold Migration Roadmap §8 into the Main Roadmap

- [ ] Task: Inventory §8 anchors and dependencies
  - [ ] Search the repo for all links to `ROADMAP.md#8-...` and record target files/lines (expected: `ARCHITECTURE.md`, `conductor/product.md`, `docs/gut-migration.md`)
  - [ ] Identify "durable decisions" in §8 (runtime model, migration boundary, success criteria) vs. transient phase-checklist content
- [ ] Task: Fold durable content into main roadmap sections
  - [ ] Move/merge durable decisions into the appropriate main roadmap sections (Native Runtime Transition overview + remaining Phase 5 items)
  - [ ] Record remaining Phase 5 items with "removal targeted for v0.6.0" framing preserved
  - [ ] Delete §8 entirely (no tombstone)
- [ ] Task: Rewrite all §8 anchor links to the new anchors
- [ ] Task: Verify no dangling `#8-...` anchors remain repo-wide (search check)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Refresh ARCHITECTURE.md Known Limitations

- [ ] Task: Cross-check every stated limitation against shipped tracks
  - [ ] Mark/remove closed limitations (parameterized tests, suite-level skip, signal assertions, editor plugin)
  - [ ] Keep true remaining limitations (headless-only runtime, bridge core-subset constraint, etc.) with accurate wording
- [ ] Task: Verify bridge-deprecation notes keep "deprecated v0.5.0 / removed v0.6.0" framing (NFR-3)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Reconcile README, USER_GUIDE, and PRD with Shipped Reality

- [ ] Task: Verify README feature table and capability claims against v0.5.0 + Unreleased feature set (`--changed`, signal assertions, preflight cache, `coverage run` playtest)
- [ ] Task: Verify USER_GUIDE command documentation matches actual CLI surface (flags, subcommands, defaults)
- [ ] Task: Apply factual corrections only to PRD (stale "planned/deferred" claims, outdated §8 references); no editorial rewrites of vision/positioning
- [ ] Task: Confirm zero `src/` or `tests/` changes in diff (NFR-1) and no CHANGELOG edit (NFR-2)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
