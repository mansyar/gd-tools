# Specification: Roadmap & Docs Truth Pass (2026-10)

## Type
Chore (Documentation)

## Overview
Consolidate the temporary native-test-runtime migration roadmap into the main
project documentation and bring all user-facing docs in line with the shipped
v0.5.0 feature set. This is an explicit Phase 5 leftover item ("Fold durable
decisions into the main roadmap and remove this section") and clears the path
for the v0.6.0 bridge-removal track.

## Functional Requirements

### FR-1 — Fold ROADMAP §8
The durable decisions in `docs/ROADMAP.md` §8 ("Temporary: Native Test
Runtime Migration Roadmap") are absorbed into the main roadmap sections. The
temporary framing ("in progress", phase checklists of completed work) is
collapsed into a concise record of delivered capability plus the remaining
Phase 5 items (v0.5.0 publish, bridge removal targeted for v0.6.0). §8 is
then removed, leaving no tombstone.

### FR-2 — Rewrite §8 anchor links
Every link to `ROADMAP.md#8-temporary-native-test-runtime-migration-roadmap`
(known occurrences: `ARCHITECTURE.md`, `conductor/product.md`,
`docs/gut-migration.md`) is updated to point at the new anchor(s) where the
content now lives. A repo-wide search confirms zero dangling `#8-...` anchors
remain.

### FR-3 — Refresh known limitations
`docs/ARCHITECTURE.md` "Known Limitations" sections are updated to reflect
reality: closed limitations (no parameterized tests, no suite-level skip, no
signal assertions, no editor plugin) are removed or marked resolved; remaining
true limitations (bridge core-subset constraint, headless-only runtime, etc.)
stay, with the bridge-deprecation note preserving the "removed in v0.6.0"
framing.

### FR-4 — Reconcile README / USER_GUIDE / PRD
Factual claims in `README.md`, `docs/USER_GUIDE.md`, and `docs/PRD.md` are
verified against the shipped feature set (v0.5.0 + Unreleased: `--changed`,
signal assertions, preflight cache, `coverage run` playtest). Stale claims
are corrected. The PRD gets **factual corrections only** — vision/positioning
prose and the Native Test Runtime Direction section are not editorially
rewritten.

## Non-Functional Requirements
- **NFR-1:** No runtime code changes — `src/`, `tests/`, and CI workflows are
  untouched.
- **NFR-2:** No CHANGELOG entry (docs truth work is not user-facing feature
  news).
- **NFR-3:** Bridge removal remains framed as "targeted for v0.6.0" everywhere
  it appears.

## Acceptance Criteria
1. §8 no longer exists in `docs/ROADMAP.md`; its durable decisions are present
   in the main roadmap body.
2. Zero links to `ROADMAP.md#8-...` remain anywhere in the repo (verified by
   search).
3. ARCHITECTURE.md lists no limitation that shipped tracks have closed.
4. No factual claim in README/USER_GUIDE/PRD contradicts shipped behavior
   (spot-check of every feature table row and capability claim).
5. Working tree diff touches only `docs/*.md`, `README.md`, and
   `conductor/*.md`.

## Out of Scope
- `doctor` / `init` messaging updates and any `src/` string changes (deferred
  to the v0.6.0 bridge-removal track).
- GUT bridge removal itself.
- Rewriting PRD vision/positioning sections or rewriting USER_GUIDE structure.
- CHANGELOG edits.
