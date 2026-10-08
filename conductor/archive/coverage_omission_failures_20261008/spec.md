# Spec: Native coverage instrumentation failures — Variant-inference compile errors & zero-point plan targets

**Type:** Bug fix
**Status:** Approved
**Source:** Adoption bug report from a 0.7.0 consumer (Godot 4.7.2, Windows 11, build-and-race project), verified against this repo.

## Overview

Native coverage instrumentation (`gd-tools test --coverage`) deterministically fails to instrument plan targets in two ways:

1. **Variant-inference compile error (Class 1).** `hit_ret`/`hit_bool` return `Variant`; wrapping an operand of a ternary/boolop expression makes the whole expression statically `Variant`. When that expression initializes a project `var x := …`, the `:=` infers from Variant → `INFERENCE_ON_VARIANT` (error by default in Godot 4.x — verified with Godot 4.7.2 `--check-only`) → injected source fails `GDScript.reload(true)` → file omitted with the misleading hint *"Fix the script's own syntax."* The offending declaration is the **user's** `:=` statement, not injected code (injected lines contain no declarations).
2. **Zero-point plan targets (Class 2).** Files with no trackable points (pure `const` data modules, definition-only classes) are included in the plan with `lines=[]`. The collector's `lines.is_empty()` early return (`gd_tools_native_coverage.gd` ~line 189) is its only silent skip path — no omission record, no engine output — and Python-side reconcile falls back to the generic *"the runtime did not report why"* reason. The reporter's dependency-blocked-reload hypothesis is not supported by evidence: every reload-failure path records an omission and emits a `push_warning` (which the reporter did observe for Class 1 but not Class 2). Phase 4 of the plan settles the hypothesis with an explicit fixture.
3. **Diagnostics gaps.** Reload-failure omissions omit the `reload()` error code; `artifacts.json`'s top-level `omitted` array reflects only one suite's omissions (the coverage shard merge in `native_test/orchestrator.py::_merge_coverage_shards` already unions correctly).

4. **Lint ignores gdlintrc (second report, same adoption).** `run_lint` (`src/gd_tools/lint_runner.py`) calls `gdtoolkit.linter.lint_code(code)` without a config, so a `disable:` list in the project's `gdlintrc` is honored by bare `gdlint` but not by `gd-tools lint`. `lint_code` accepts a config mapping (verified against the installed gdtoolkit).

## Functional requirements

- **R1 — Exclude zero-point files from the plan.** `generate_plan` skips discovered files that yield zero points, emitting a visible stderr warning per skipped file (style of the existing syntax-error skip). `PLAN_VERSION` bumps 7→8.
- **R2 — Annotate Variant-inference sites.** The plan generator detects `:=` statements whose initializer contains a wrapped operand span and records the statement line per file (per-file `warning_ignores` field). The collector inserts `@warning_ignore("inference_on_variant")` inline at those statements, preserving line counts. Wrapping behavior itself is unchanged (full branch fidelity retained).
- **R3 — Accurate omission diagnostics.** Reload-failure omission records carry the `reload()` error code; cause/fix text describes the actual mechanism instead of blaming the script's own syntax.
- **R4 — artifacts.json omitted union.** The run index's top-level `omitted` is the deduplicated union across all suites, matching `_merge_coverage_shards` behavior.
- **R5 — Repro fixture.** An e2e fixture covering: a `:=` wrapping a ternary/boolop operand (Class 1), a pure-const file (Class 2), and a dependency-graph case instrumenting scripts whose dependents are already loaded — settling the dependency-reload hypothesis with evidence.
- **R6 — Lint honors `gdlintrc`.** `run_lint` loads the project's `gdlintrc` (with an optional explicit config path on the CLI) and passes the parsed config through to `lint_code`. TOML `[lint] exclude` path discovery remains the file-source layer.

## Acceptance criteria

- A project with a pure-const class produces a plan without it; a skip warning appears on stderr.
- A file containing `var x := cond ? a : b` instruments, reloads cleanly, and records distinct hits for both arms — no `INFERENCE_ON_VARIANT` parse error in suite logs.
- A genuine reload failure produces an omission record including the error code and an accurate cause/fix.
- `artifacts.json` `omitted` equals the union across suites.
- With `disable: [- class-definitions-order]` in `gdlintrc`, `gd-tools lint` matches bare `gdlint` (no violations); without the disable, violations surface.
- `CI=true pytest` green; quality gates met (>80% line / >70% branch on `src/gd_tools`).

## Out of scope

- Dependency-ordering / pre-load instrumentation schemes (only the R5 evidence check).
- `@warning_ignore` handling for other injected-line warning classes unless discovered during R5.
- Release/tagging (per decision: no release yet).
