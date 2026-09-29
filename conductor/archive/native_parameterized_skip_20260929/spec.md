# Spec: Native Parameterized Tests + Suite-Level Skip

**Track ID:** `native_parameterized_skip_20260929` · **Type:** Feature · **Status:** approved

## 1. Overview

The native `GdToolsTest` runtime currently discovers only zero-argument `test_*` methods, silently ignoring parameterized ones, and `skip_test()` called in `before_all` marks nothing because it executes on the suite instance rather than the per-test instance the runner reads. This track adds GUT-compatible parameterization (`parameterize`, `use_parameters`) and makes suite-level skipping work, closing 2 of the 4 Known Limitations in `docs/ARCHITECTURE.md` and removing the top migration blocker for GUT suites that use parameterization.

## 2. Goals

1. Parameterized test methods run as first-class, isolated test cases with full lifecycle semantics.
2. `skip_test()` in `before_all` skips every test in the suite with the recorded reason.
3. Legacy GUT suites using `parameterize` / `use_parameters` run through the compatibility bridge without preflight failure.
4. Results, JUnit XML, NDJSON events, and artifact indices identify each case deterministically (`test_foo[case-name]`).

## 3. Functional Requirements

### 3.1 Parameterization

- **FR-1** — `parameterize(params, values)` may be called in `before_all`: `params` is a list of parameter names, `values` a list of value sets (arrays). Test methods taking those parameters expand into one case per value set.
- **FR-2** — `use_parameters(values)` may be called inside a test body and resolves to the next value set per case (GUT legacy convention).
- **FR-3** — Each case is a first-class test: own `before_each`/`after_each`, own per-test timeout, own result entry, own retry/attempt records, own artifact records. Cases execute in declaration order.
- **FR-4** — Case names are pytest-style suffixes on the method name: single value → its string form (`test_foo[3]`, `test_foo[admin]`); multiple values → hyphen-joined (`test_foo[3-admin]`); unstable types (Objects, Dictionaries) fall back to the case index (`test_foo[2]`). Names are deterministic.
- **FR-5** — Async test methods parameterize identically to sync ones.
- **FR-6** — Selectors: `--test test_foo` matches **all** cases of the method; `--test "test_foo[admin]"` selects that single case; tag filters apply at method level (all cases share the method's tags).
- **FR-7** — Validation (preflight, exit `2` with suite path and expected shape, consistent with invalid-`INTEGRATION` handling): mismatched `params`/`values` lengths, non-array arguments, duplicate parameter names. An **empty values list** marks the test *skipped* with an explicit reason.
- **FR-8** — Coverage attribution aggregates cases back to the underlying method automatically (coverage operates on source lines, so no plan change is expected — verified during implementation).

### 3.2 Suite-Level Skip

- **FR-9** — `skip_test(reason)` called in `before_all` marks **every test in the suite** as `skipped` with the recorded reason; each test still produces a result entry.
- **FR-10** — Per-test `skip_test()` semantics are unchanged (no regression to the existing per-test path).
- **FR-11** — No protocol schema change: suite skip reuses the existing `skipped` status per test; summary counts count each skipped test.

### 3.3 Bridge

- **FR-12** — `parameterize` and `use_parameters` are removed from `_UNSUPPORTED_NAMES` in `bridge_scan.py`; bridge suites using them execute through the native machinery. The bridge inherits the same preflight validation (exit `2` on malformed declarations).

### 3.4 Reporting & Documentation

- **FR-13** — Each case counts as its own test in summary counts, JUnit XML, NDJSON progress events, and the artifact index.
- **FR-14** — Documentation pass: `ARCHITECTURE.md` Known Limitations (4 → 2), `USER_GUIDE.md` (parameterization + suite skip usage), `gut-migration.md` (constructs now supported), `CHANGELOG.md` entry.

## 4. Non-Functional Requirements

- Deterministic case naming (stable across runs for CI diffing).
- No new third-party dependency; no protocol version bump (v2 accommodates the expansion).
- Preflight remains one headless pass per command; expansion metadata flows through the existing suite manifest.
- gd-tools Python-side tests maintain ≥80% line / ≥70% branch coverage for touched modules.

## 5. Acceptance Criteria

1. A native suite with `parameterize` in `before_all` produces one result entry per value set, each with hooks, timeout, and artifacts.
2. A native suite using `use_parameters` inside a test body produces one case per value set.
3. `skip_test()` in `before_all` yields all-`skipped` results with the reason propagated.
4. A bridge (`extends GutTest`) suite using `parameterize` runs without preflight failure.
5. `--test` with a method name selects all cases; with a case name selects one case.
6. Invalid declarations exit `2` preflight with actionable messages; empty values list skips with reason.
7. JUnit XML and artifact index show per-case entries with `[name]` identifiers.
8. `CI=true pytest` passes; docs updated as in FR-14.

## 6. Out of Scope

- Parallel execution (Phase 5).
- Watch-mode-specific behavior (parameterized suites are ordinary suites to the watcher).
- Suite-level `skipped` status in the protocol schema.
- A native-specific (non-GUT) parameterization API.
- Bridge support for the remaining unsupported constructs (property/orphan assertions, engine-error diagnostics).

## 7. Decision Log

| # | Decision | Choice |
|---|----------|--------|
| 1 | Type | Feature (native runtime capability) |
| 2 | API | GUT-compatible `parameterize` / `use_parameters` |
| 3 | Case naming | pytest-style `test_foo[case-name]` suffix |
| 4 | Suite skip | `skip_test()` in `before_all` → all suite tests skipped with reason |
| 5 | Bridge scope | Included — remove from `_UNSUPPORTED_NAMES` once native supports it |
| 6 | Declaration | In `before_all` (GUT convention) |
| 7 | Lifecycle | Full per-case: own hooks, timeout, result entry, retry, artifacts |
| 8 | Edge cases | Preflight validation errors → exit 2; empty values list → skip with reason |
| 9 | Reporting & docs | Per-case counts everywhere; coverage aggregates back to method; docs pass |
| 10 | Constructs | Both `parameterize` (before_all) and `use_parameters` (in-test) |
| 11 | Case names | Stringified values + index fallback for unstable types |
| 12 | Selectors | Method match = all cases; case name = one; tags at method level |
| 13 | Non-goals | Declaration-order execution; no parallelism change; no watch-mode changes; async identical |
