# Spec: Coverage Exclusion Annotations

**Track ID:** `coverage_exclusions_20260930`
**Type:** Feature
**Source:** ROADMAP Track 30 (`docs/ROADMAP.md` §Track 30), refined 2026-09-30
**Branch:** `feat/coverage-exclusions-20260930`

## Overview

`gd-tools` coverage currently counts every instrumentable line, so debug-only code, platform-specific branches, and noisy declarations artificially lower coverage percentages. This track adds user-controlled exclusions via GDScript comment annotations, interpreted by the Python plan generator during AST traversal. Excluded lines are never instrumented, are recorded transparently in the plan JSON, are excluded from coverage percentage math, and are visibly styled in the HTML report with a compact count in the terminal report.

## Functional Requirements

### FR1 — Annotation forms

The plan generator recognizes these comment annotations (exact token: `gd-tools: no cover`, case-sensitive, must be a GDScript comment — content inside string literals or docstrings is never treated as an annotation):

1. **Line exclusion:** `# gd-tools: no cover` on a line excludes that line only.
2. **Block exclusion:** `# gd-tools: no cover start` … `# gd-tools: no cover end` excludes all lines from the `start` annotation line through the `end` annotation line, inclusive.
3. **Function exclusion:** `# gd-tools: no cover` (or `... no cover start`) on a `func` definition line excludes the entire function body (all lines belonging to that function).

### FR2 — Edge-case semantics (flat, first-match)

- Nested `start` blocks are not supported: an inner `start` encountered while a block is open is ignored with a warning; the first matching `end` closes the open block.
- A `start` with no matching `end` warns and excludes to end of file.
- An `end` with no open `start` warns and is ignored (that line itself is not excluded).
- An annotation on a blank or comment-only line excludes that line only (no function inference applies).
- Only real comment tokens count; annotation-looking text inside strings is inert.

### FR3 — Malformed-annotation diagnostics

Warnings are emitted to **stderr** during plan generation (consistent with existing coverage diagnostics). They must not pollute machine-readable report files. Malformed annotations never abort plan generation (warn-and-continue, per the project's coverage-target-contract philosophy).

### FR4 — Plan JSON transparency

- The plan JSON records excluded lines per file (e.g. an `excluded_lines` field listing line numbers or ranges) so exclusions are machine-readable and auditable.
- The plan cache **version is bumped** so any plan generated before this feature is regenerated — a stale cached plan cannot silently drop exclusions.
- Files without annotations produce plans byte-compatible with the previous format's existing fields (existing coverage results unchanged).

### FR5 — Reporting

- **HTML report:** excluded lines are rendered in a distinct style (gray/strikethrough per ROADMAP) and are not shown as uncovered.
- **Terminal report:** a compact per-file excluded-lines count (or single summary line such as "Excluded: N lines across M files") appears **only when exclusions exist** — no noise when annotations aren't used.
- **Percentage math:** excluded lines are removed from the countable total (denominator) before percentages are computed and before the `--min` threshold gate evaluates. Excluding noisy lines therefore genuinely raises measured coverage.
- **LCOV/Cobertura/diff:** no changes in this track; baselines recorded before this feature get no special handling in `coverage diff`.

## Non-Functional Requirements

- NFR1: Follows `conductor/code_styleguides/python.md`; typed, documented public functions.
- NFR2: Plan generation performance must not regress measurably for files without annotations (single-pass comment scan integrated with existing Lark traversal).
- NFR3: Exit-code semantics unchanged (exclusions are not errors; malformed annotations are warnings, exit still 0/1 by coverage outcome only).
- NFR4: TDD per `conductor/workflow.md`; unit tests cover all annotation forms, edge cases, and percentage math; fixture `.gd` files exercise each form.

## Acceptance Criteria

1. `# gd-tools: no cover` excludes a single line from instrumentation and from the denominator.
2. `start`/`end` excludes an inclusive block; func-line annotation excludes the whole function body.
3. Malformed annotations warn on stderr and follow the flat semantics above; plan generation never fails because of them.
4. Excluded lines are recorded in the plan JSON; the cache version bump guarantees regeneration.
5. HTML shows excluded lines distinctly; terminal shows a compact count only when exclusions exist.
6. Files without annotations produce unchanged results.
7. `--min` evaluates against the post-exclusion denominator.
8. USER_GUIDE documents all forms; README gains a one-liner under coverage features. ROADMAP is not edited in this track.

## Out of Scope

- `# pragma: no cover` alias syntax.
- `--show-excluded` CLI flag.
- LCOV/Cobertura/diff reporter changes; stale-baseline notices.
- Nested block regions with stack semantics.
- ROADMAP status edits (separate docs-truth-pass candidate).
- Excluding entire files via config (potential follow-up track).
