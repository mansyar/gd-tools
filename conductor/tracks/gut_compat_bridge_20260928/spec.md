# GUT Compatibility Bridge (Native Migration Phase 3)

- **Track ID:** `gut_compat_bridge_20260928`
- **Type:** Feature
- **Status:** Draft
- **Branch:** `feature/gut-compat-bridge-20260928`
- **Origin:** ROADMAP §8 Phase 3; `conductor/product.md` §Migration boundary.
  Unblocked by `native_assertion_parity_skip_test_20260927`, which added
  runtime skipping and the ten GUT-core assertions the shim can reuse.

---

## 1. Overview

The native `GdToolsTest` runtime is the default test path, but existing GUT
suites still have no supported way to run under it. This track builds the
**GUT Compatibility Bridge**: a `GutTest`-compatible shim base class shipped
inside the `gd-tools-test` addon, so legacy GUT suites run through the native
protocol with the same user-facing result contract — **without the GUT addon
installed**. The legacy GUT subprocess execution path is removed in this
track, with deprecation/migration diagnostics pointing users at the bridge
and the migration path. Phase 4 (migration tooling) and Phase 5
(hardening/release) build on this.

## 2. Functional Requirements

**FR-1 — Shim base class.** A new GDScript file in
`src/gd_tools/addons/gd-tools-test/` provides `class_name GutTest`, backed by
the same runtime machinery as `GdToolsTest` (runner, protocol, preflight,
context). A suite declaring `extends GutTest` runs with no GUT addon present.

**FR-2 — Documented core subset** (per product.md):

- *Lifecycle hooks (all six):* `before_all`, `after_all`, `before_each`,
  `after_each`, `prerun_setup`, `postrun_teardown`.
- *Core assertions:* the GUT value/comparison family (`assert_true/false`,
  `assert_eq/ne`, `assert_gt/gte/lt/lte`, `assert_almost_eq/ne`,
  `assert_between/not_between`, `assert_null/not_null`,
  `assert_has/does_not_have`, `assert_is`, `assert_typeof/not_typeof`,
  `assert_has_method`, `assert_file_*`, string contains/starts/ends,
  `assert_same/not_same`, `assert_eq_deep/ne_deep`) — reusing the native
  assertions added in the parity track where equivalent.
- *Signal family:* `watch_signals`, `assert_signal_emitted`,
  `assert_signal_not_emitted`, `assert_signal_emitted_with_parameters`,
  `assert_signal_emit_count`, `assert_has_signal`, `assert_connected`,
  `assert_not_connected`.
- *Async helpers:* `wait_seconds`, `wait_for_signal` (bounded), `wait_frames`,
  `wait_physics_frames`, `wait_idle_frames`, `wait_process_frames`,
  `wait_until`, `wait_while`, plus legacy `yield_*` names mapped to the
  bounded implementations.
- *Skipping:* `skip_test`, `skip_if_godot_version_lt`, `skip_if_godot_version_ne`.

**FR-3 — Unsupported constructs fail with migration guidance.** A preflight
static scan of each bridge suite detects calls to unsupported GUT helpers
(mocking: `double`, `partial_double`, `stub`; parameterization:
`parameterize`, `use_parameters`; mock assertions: `assert_called*`,
`assert_call_count`; property/orphan/interactive: `assert_setget`,
`assert_accessors`, `assert_exports`, `assert_property*`, `assert_freed`,
`assert_no_new_orphans`, `pause_before_teardown`; `assert_engine_error*` /
`assert_push_*`). The run fails before any test executes with a per-file list
of unsupported constructs and pointers to the migration guidance.

**FR-4 — Auto-detection routing.** Discovery classifies each test file:
`extends GdToolsTest` → native path (unchanged), `extends GutTest` → bridge,
neither/unknown base → explicit error naming the file. Per-suite routing with
no CLI changes needed to adopt the bridge. The existing `_GUT_EXTENDS_RE` in
`native_test/discovery.py` already detects GUT suites — routing builds on it.

**FR-5 — GUT-free bridge rule.** The bridge conflicts with a real GUT install
(duplicate `class_name GutTest`). When `addons/gut` is present, preflight
fails with actionable guidance ("remove `addons/gut` to run through the
bridge; see docs/gut-migration.md").

**FR-6 — Legacy subprocess path removed.** The GUT subprocess execution path
is deleted from `test_runner.py` and its orchestration. The `--runtime gut`
CLI value and `test.runtime = "gut"` config value are rejected with a
migration-guidance error (not silently remapped). `init --with-gut` and
standalone GUT usage remain outside gd-tools' execution path.

**FR-7 — Result normalization.** Bridge suite results normalize into the
native protocol result model (statuses passed/failed/skipped/error/timeout),
producing the same user-facing output, JUnit XML, exit codes 0/1/2, and
artifact index entries as native suites. Mixed native+bridge suites run in
one invocation.

**FR-8 — Coverage in scope.** Bridge suites work with
`gd-tools test --coverage`: instrumented by the same coverage tracker,
reusing coverage plan schema v1, no GUT autoload involved.

**FR-9 — Deprecation & migration diagnostics.** Bridge runs emit a notice
that the suite runs through the compatibility bridge (temporary, one-release
migration path). `gd-tools doctor` reflects the new reality: GUT-install and
GUT-version checks no longer treat GUT as required for any runtime, and GUT
suites present in the project are reported as bridge-eligible.

## 3. Non-Functional Requirements

- Same exit-code contract (0 success / 1 test failure / 2 config or preflight
  error).
- TDD per workflow.md; unit tests for discovery routing, preflight scan,
  normalization, and CLI/config changes; coverage gate ≥80% line / ≥70%
  branch maintained (current: 95.2%).
- Godot 4.5+ supported (the bridge removes the GUT-9.6.0-refuses-4.5
  limitation for legacy suites).
- `docs/gut-migration.md` written in this track: supported subset, failing
  constructs, how to migrate to `GdToolsTest`; referenced by all migration
  diagnostics.
- ROADMAP §8 Phase 3 checkboxes marked delivered at completion;
  ARCHITECTURE.md Known Limitations updated (GUT compatibility section
  rewritten to describe the bridge).

## 4. Acceptance Criteria

1. A representative GUT-style suite (six hooks, core assertions, signal
   family, async waits) runs via plain `gd-tools test` with no GUT addon
   installed and produces the native result contract.
2. A project mixing `GdToolsTest` and `GutTest` suites runs in one
   invocation; each suite takes its route automatically.
3. A suite using `double()` or `parameterize()` fails at preflight with the
   construct named per file, and no tests execute.
4. `--runtime gut` and `runtime = "gut"` are rejected with migration
   guidance.
5. `gd-tools test --coverage` reports line/branch coverage for bridge suites
   identical in format to native suites.
6. Bridge runs emit the migration notice; `docs/gut-migration.md` exists and
   is linked from diagnostics.
7. Full unit suite passes; ruff/black clean; coverage gate holds.

## 5. Out of Scope

- Phase 4: dry-run migration reports, opt-in rewrites, `.gutconfig.json`
  translation.
- Phase 5: parallel execution, caching, bridge removal.
- Supporting doubles/stubs or parameterized tests in the shim (they fail with
  guidance by design).
- Changes to `init --with-gut` behaviour beyond what FR-9 requires.
