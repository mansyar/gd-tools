# Specification: Instrumentation Hygiene Sweep (`instrumentation_hygiene_20261003`)

## Overview

Four independently verified defects plus accumulated GUT-removal residue,
folded into one track because each item is small and none justifies its own
cycle. The largest item is an instrumentation-correctness bug in the same
family as the ternary anchoring fix (`ternary_instrumentation_20261003`):
tracked points recorded on lines where GDScript permits no statement, so the
collector injects a tracker call that makes the whole file unparseable.

## Phase 1 — Class-body instrumentation correctness (bug fix)

### Root cause

A tracked point whose recorded line is a **class-body line** causes the
collector (`gd_tools_native_coverage.gd`) to inject
`GdToolsNativeCoverage.hit(...)` into the class body. GDScript class bodies
accept only member declarations, never statements, so the instrumented source
fails to parse (`Unexpected identifier in class body`). `_instrument_file`
catches the failed reload and records the file as an omission, so the file
silently drops out of coverage and `--min` escalates to exit 2.

Confirmed defect cases (verified with the plan generator, Godot 4.7.2):

| Source | Recorded point | Injection site |
|---|---|---|
| `class Inner:` / `var F = func(): return 2` | statement at the `var F` line | class body — **broken** |
| `class Inner:` / `var F = func(): print(1)` | statement at the `var F` line | class body — **broken** |
| `static var S = func(): return 2` (class level) | statement at the `static var` line | class body — **broken** |
| `@export var v = func(): print(1)` | statement at the `@export var` line | class body — **broken** |

The same defect class is expected for lambda bodies inside **default
parameter values** (tracker inside a function signature); this must be
confirmed during implementation and covered if real.

### Verified constraint: multi-line lambda bodies are instrumentable

A tracker inserted inside a multi-line lambda body parses cleanly:

```gdscript
class Inner:
	var F = func():
		GdToolsNativeCoverage.hit(0, 1)   # verified OK against Godot 4.7.2
		print(1)
		return 2
```

Their statements record on their own lines, which are legal statement lines.
The fix must therefore be **line-precise**: drop only points whose recorded
line is a class-body or signature line; keep points that record on legal
statement lines inside lambda bodies.

### Functional requirements

- **FR-1**: No planned point may record on a line where a statement cannot
  begin: class-member declaration lines at any class nesting level
  (`var`/`const`/`static var`/`@export`/`signal`/`enum`/inner-class headers),
  their multi-line continuation spans, and function signature lines. The
  mechanism is an implementation detail (extending the anchor pre-pass in
  `plan_generator.py`); the outcome is pinned by tests.
- **FR-2**: Statements inside multi-line lambda bodies whose own line is a
  legal statement line must remain tracked (verified instrumentable above).
- **FR-3**: Disallowed points are dropped silently, documented — same policy
  as the ternary track. No stderr noise.
- **FR-4**: `PLAN_VERSION` bumps 3 → 4. Cached v3 plans hold the now-dropped
  points and would keep producing broken instrumented output until they
  happen to miss; the bump forces one regeneration. Version tests and all
  golden plan fixtures updated.
- **FR-5**: The real-Godot integration parse suite
  (`tests/integration/test_coverage_instrumentation_parses.py`) gains these
  cases with per-case expected-point assertions (a zero-point plan compiles
  trivially — that gap is how the header-ternary drop shipped): single-line
  class lambdas (`var`, `static var`, `@export`, nested class), multi-line
  class lambdas (points kept), and a default-parameter lambda if confirmed.
- **FR-6**: Existing behaviour is preserved everywhere else: the ternary
  anchoring from the previous track, statement tracking inside function
  bodies, func-level single-line lambdas (tracker lands before the `var`
  line inside the function — legal, mildly imprecise attribution, unchanged).

## Phase 2 — Coverage data fidelity and durable writes (bug fix)

- **FR-7**: `write_coverage_json` (`reporter.py`) serializes the `omitted`
  key when the data carries omissions. This is the write path for
  `coverage merge` (`orchestrator.py:134`), which currently produces a merged
  file that has silently lost real omission reasons (downgraded to
  `_UNKNOWN_REASON` on the next read). The addition must be verified additive
  against the reader (which already tolerates the key's absence); no
  coverage-data version bump is expected.
- **FR-8**: `write_coverage_json` writes atomically (temp file + `os.replace`).
- **FR-9**: `_write_junit_xml` (`native_test/command.py`) writes atomically.
  It currently ends in `ET.ElementTree(root).write(path, ...)`; a crash
  mid-write leaves a corrupt JUnit XML.
- **FR-10**: `mark_run_started` (`native_test/artifacts.py`) writes its run
  marker atomically.
- **FR-11**: The atomic-write pattern currently exists in at least three
  places (`write_json_atomic` in `protocol.py`, the coverage shard merge, the
  plan cache). These fixes must reuse or consolidate a single shared helper
  rather than adding a fourth or fifth copy.

## Phase 3 — Hygiene sweep (chore)

- **FR-12**: Delete `pre_run_hook.gd` and `post_run_hook.gd` — they
  `extends GutHookScript`, a base class removed by the GUT bridge removal;
  they can never load. Remove their entries from `init.py`'s deploy
  manifests and update every doc reference (ARCHITECTURE, AUDIT_REPORT,
  CONTRIBUTING, PRD, ROADMAP, ROADMAP_v1, SPIKE_coverage_instrumentation,
  TDD).
- **FR-13**: `gd-tools init` cleans up stale deploys: when run in a project
  whose `addons/gd-tools-coverage/` still contains the dead hook files,
  delete them and report the removal, so existing projects self-heal.
- **FR-14**: Remove the empty-but-wired `_DEPRECATED_FIELDS` machinery in
  `config.py` (`check_deprecated_settings` operates on an empty list — dead
  weight). Update or remove its tests.
- **FR-15**: Remove the accepted-but-never-used `non_interactive` parameter
  from `init` (verify the CLI wiring during implementation; if a CLI flag
  feeds it, remove both).
- **FR-16**: Rename `test_runner.py` — its `TestDetail`/`TestResult`/
  `format_test_results` exports are live (used by `native_test/command.py`
  and `watch/session.py`) but the module name is GUT-era. Rename and update
  imports.
- **FR-17**: Doc debt: correct the ARCHITECTURE §3 flow that still diagrams
  the removed `run_coverage_test()`; correct TESTING_STRATEGY §5's "GUT
  installation" wording; correct the "protocol v2" docstrings in
  `native_test/preflight.py` (the protocol is v3).

## Non-functional requirements

- **NFR-1**: No behaviour change beyond the specified fixes. Full test suite
  green; ruff and black clean.
- **NFR-2**: Phase 1 verified by the real-Godot integration suite with
  per-case expected points, using the established harness discipline
  (`class_name` stub, not autoload; `--import` per project; fresh `.godot`
  per check — a stale cache produces false passes).
- **NFR-3**: Coverage gates maintained (≥80% line, ≥70% branch).
- **NFR-4**: TDD ordering per `workflow.md`: failing tests before each
  implementation step.

## Acceptance criteria

1. A project containing class-level single-line lambdas instruments without
   parse errors; those files appear in coverage totals instead of omissions.
2. Multi-line class-level lambda bodies remain tracked and compile.
3. `PLAN_VERSION` is 4; a cached v3 plan regenerates with reason
   "cache plan version outdated (found 3, expected 4)".
4. `coverage merge` output preserves `omitted` reasons; all three formerly
   non-atomic writes are atomic and share one helper.
5. The dead hook files are absent from the repo, the deploy manifests, fresh
   `init` deploys, and stale copies are removed by `init`.
6. The doc debt items in FR-17 are corrected.

## Out of scope

- Ternary arm spans (`ternary_true`/`ternary_false` co-anchored) — a plan
  format change rippling through every consumer; separate track.
- Multi-line `match` patterns — gdtoolkit cannot parse them at all; upstream.
- New coverage features of any kind.
