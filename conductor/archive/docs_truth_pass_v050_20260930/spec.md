# Specification — Docs Truth Pass v0.5.0

- **Track ID:** `docs_truth_pass_v050_20260930`
- **Type:** Chore (documentation-only; no code changes, no tests required per workflow.md)
- **Branch:** `feature/docs-truth-pass-20260930`
- **Status:** Approved by user 2026-09-30

## Overview

The native parallel suites track (merged in v0.5.0) closed several documented
limitations — parallel suite execution, `parameterize()` support, suite-level
`skip_test()` — but user-facing documentation was not swept afterward.
README.md still states *"Suites run sequentially; parallel execution is planned
but not yet available"*, CHANGELOG v0.5.0 Known Limitations repeats it, and the
bridge capability table still marks `parameterize()` as unsupported (preflight
rejects it). This track makes every documentation claim match shipped v0.5.0
reality.

## Functional Requirements

1. **Open-ended sweep:** Grep all project markdown (`README.md`,
   `CHANGELOG.md`, `ARCHITECTURE.md`, `docs/ROADMAP.md`, and any other `.md`
   reachable from those) for claims made stale by v0.5.0 features: parallel
   execution (`--parallel`), native runtime `parameterize()`, suite-level
   `skip_test()`, watch mode, coverage baseline/diff, `# gd-tools: no cover`
   exclusions, GUT bridge deprecation/removal timeline.
2. **Fix only false claims:** Rewrite stale statements to describe shipped
   behavior. Do not touch accurate rows/claims (e.g., editor plugin = "Not
   yet", roadmap pointers for unstarted tracks).
3. **Verify each claim:** For every rewritten statement, confirm against the
   implementation first (e.g., `--parallel` flag in `test_runner.py`,
   parameterize handling in the native runtime, preflight behavior) so no new
   drift is introduced.
4. **Changelog handling:** Rewrite the v0.5.0 "Known Limitations" bullets in
   place and add a `Fixed` bullet noting the documentation correction.
5. **Roadmap:** Update `docs/ROADMAP.md` Phase 5 status markers — mark
   "optional parallel execution (deferred)" as delivered; note the remaining
   deferred items (native runtime caching, v0.5.0 publication, bridge removal
   v0.6.0) as still open.

## Acceptance Criteria

- [ ] No `.md` file reachable from README/CHANGELOG/ARCHITECTURE/ROADMAP
      claims suites run sequentially or that parallel execution is unavailable.
- [ ] Bridge capability table no longer lists `parameterize()` as unsupported
      by the native runtime.
- [ ] CHANGELOG v0.5.0 Known Limitations describe only limitations that still
      exist; a Fixed entry records the correction.
- [ ] ROADMAP Phase 5 reflects parallel execution as delivered.
- [ ] Every rewritten claim is backed by a cited code location noted in the
      plan (grep evidence, not code changes).
- [ ] No code, config, or test files are modified.

## Out of Scope

- Editor plugin, pre-commit hooks, clean command, GH Actions annotations
  (separate tracks).
- Rewriting docs for features not yet implemented.
- Restructuring any document; wording polish of accurate claims.

## Decisions (user-confirmed 2026-09-30)

- Classification: **Chore** (not Bug).
- Sweep breadth: **Open-ended** — implementation greps all reachable markdown;
  spec states the goal rather than an exhaustive list.
- Changelog: **Edit v0.5.0 Known Limitations in place + add Fixed note**.
- Accurate claims: **Fix only false claims**; no wording polish of accurate rows.
- Claim backing: **Verify each rewritten claim against the implementation**.
