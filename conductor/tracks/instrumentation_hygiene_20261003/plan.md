# Track Implementation Plan: Instrumentation Hygiene Sweep

Implements `conductor/tracks/instrumentation_hygiene_20261003/spec.md`
(Bug fix + chore). Six phases, TDD ordering throughout: every production
change is preceded by failing tests, and every phase ends with a
verification checkpoint per `conductor/workflow.md`.

The dominant risk in this track is the same one the ternary track hit:
plan-generator changes that alter which lines carry points require a
`PLAN_VERSION` bump, and the bump ripples through golden fixtures and
every hard-coded version assertion. Phases 1 and 2 are therefore sequenced
exactly like the proven ternary track (anchor first, bump second).

## Phase 1: Class-Body Anchor Resolution [complete: b9e3e31]

Goal: no planned point records on a class-body line or a function
signature line. Multi-line lambda body statements stay tracked (FR-2);
func-level single-line lambdas stay exactly as they are today (FR-6).

- [x] Task: Write failing unit tests for class-body anchoring (Red) [00e5537]
  - Extend `tests/unit/test_plan_generator_ternary.py` or add a sibling
    module covering, per spec FR-1: class-level `var F = func(): ...`
    records no point on the declaration line; `static var S = func(): ...`
    likewise; `@export var E = func(): ...` likewise.
  - Cover FR-2: a multi-line lambda body inside a class-level declaration
    keeps its body-statement points (they record on the body's own lines,
    which ARE legal insertion points).
  - Cover FR-6: func-level `var f = func(): return 2` still records its
    statement on the `var` line (unchanged behaviour).
  - Cover the signature-line rule: no point records on a `func f(a = ...):`
    line itself, including a default-parameter value expression.
  - Run `python -m pytest tests/unit -q` and confirm the new tests fail
    for the expected reason (points recorded on illegal lines).
- [x] Task: Implement anchor resolution (Green) [00e5537]
  - Generalize the ternary anchor pre-pass in
    `src/gd_tools/coverage/plan_generator.py` so statement points resolve
    an anchor line the same way `test_expr` does.
  - Class-member declaration lines and signature lines must yield no
    anchor (point dropped per FR-3), never a nearby unrelated statement.
  - Preserve bottom-up id ordering and the exclusion-check semantics
    (FR-5's `# gd-tools: no cover` evaluated against the final line).
- [x] Task: Refactor [00e5537]
  - Re-read the anchor code for duplication between the ternary path and
    the general statement path; collapse shared logic if it reads cleanly.
  - Run ruff and black; fix findings.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [b9e3e31]

## Phase 2: Plan Version Bump and Cache Invalidation [complete: 1e421fb]

Goal: cached v3 plans that still carry class-body points are rejected,
forcing one regeneration (`PLAN_VERSION` 3 → 4, spec FR-4).

- [x] Task: Write failing test for cache invalidation (Red) [8aefb93]
  - Add a v3-cache-accepted test asserting the cache regenerates with an
    outdated reason, mirroring `test_cache_v2_plan_is_regenerated_with_outdated_reason`.
  - Assert `read_plan_json`'s unsupported-version message mentions the
    current version.
- [x] Task: Bump the plan version (Green) [8aefb93]
  - `PLAN_VERSION = 3` → `4` in `src/gd_tools/coverage/plan_generator.py`
    with a docstring recording both prior bumps and this one's rationale.
  - Update golden fixtures in `tests/fixtures/plans/*.expected.json` via
    `tools/generate_expected_plans.py` and any hard-coded `3`s in tests
    (grep first; the ternary track missed several).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md) [1e421fb]

## Phase 3: Real-Godot Class-Body Regression Cases

Goal: the Godot parse suite proves instrumented output compiles for every
class-body scenario, with per-case expected-point assertions (FR-5) so a
silent drop cannot pass vacuously.

- [ ] Task: Add class-body cases to the Godot parse suite
  - Extend `tests/integration/test_coverage_instrumentation_parses.py`
    with the spec's defect table cases: class-level `var`/`static var`/
    `@export` single-line lambda bodies (now dropped - plan has no illegal
    points, output parses), multi-line class lambda bodies (tracked,
    output parses), func-level lambda (unchanged).
  - Each case declares its expected planned points, per the gap the
    ternary review exposed (a zero-point plan compiles trivially).
- [ ] Task: Verify the suite has teeth
  - Run the suite against the pre-Phase-1 generator
    (`git checkout` the file, run, restore) and confirm exactly the
    class-body cases fail.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Coverage Data Fidelity and Durable Writes

Goal: `coverage merge` stops losing omission reasons, and all remaining
non-atomic writes move onto one shared helper (spec FR-7 through FR-11).

- [ ] Task: Write failing tests for omission fidelity and atomic writes (Red)
  - Round-trip test: `CoverageData` with `omitted` entries written via
    `write_coverage_json` and read back preserves reasons (currently
    degrades to `_UNKNOWN_REASON`).
  - Atomicity tests: the shared helper writes via temp-file + `os.replace`
    in the destination directory; assert no partial file survives an
    interrupted write (simulate by patching the serializer to raise).
- [ ] Task: Implement fidelity and the shared atomic helper (Green)
  - `write_coverage_json` (`src/gd_tools/coverage/reporter.py`) includes
    the `omitted` list. Verify additivity against the reader before
    deciding whether the coverage-data version needs a bump; document the
    finding either way.
  - Introduce one shared atomic-write helper (extend or relocate
    `write_json_atomic` from `native_test/protocol.py`) and migrate
    `write_coverage_json`, `_write_junit_xml` (`native_test/command.py`),
    and `mark_run_started` (`native_test/artifacts.py`) onto it.
  - `mark_run_started` keeps its documented early-marker semantics; only
    the write mechanism changes.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [b9e3e31]

## Phase 5: Hygiene Sweep - Dead Code, Stale Deploys, Doc Debt

Goal: GUT-removal residue stops shipping; the small dead-code items are
removed; the known-stale docs are corrected (spec FR-12 through FR-17).

- [ ] Task: Remove the dead GUT hook files and their deployment
  - Delete `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd` and
    `post_run_hook.gd` (they extend the removed `GutHookScript` base).
  - Remove their entries from `init.py`'s deploy manifests; update the
    8 documents that reference them.
  - Implement init self-healing (FR-13): an `init` run detects hook files
    it no longer deploys in the target project, deletes them, and reports
    the cleanup. Write the test first.
- [ ] Task: Remove dead code
  - `_DEPRECATED_FIELDS` machinery in `config.py` (empty but wired).
  - The unused `non_interactive` parameter in `init.py` (verify CLI wiring
    first; if it is wired, record that and leave it).
  - Rename `test_runner.py` to reflect what it does (it renders test
    results; it does not run tests) and update importers
    (`native_test/command.py`, `watch/session.py`).
- [ ] Task: Correct the stale documentation
  - `docs/ARCHITECTURE.md` §3: remove the `run_coverage_test()` flow that
    no longer exists.
  - `docs/TESTING_STRATEGY.md` §5: replace the "GUT installation" wording.
  - `src/gd_tools/native_test/preflight.py`: protocol-v2 strings → v3.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [b9e3e31]

## Phase 6: Documentation and Final Validation

- [ ] Task: Update documentation for the shipped fixes
  - CHANGELOG Unreleased entries: class-body anchoring fix (user-visible:
    files with class-level lambdas stop silently vanishing from coverage),
    merge omission fidelity, `PLAN_VERSION` 4, init self-heal.
  - `docs/ARCHITECTURE.md` and `docs/TDD.md` entries for the anchoring
    generalization, mirroring the ternary track's documentation style.
- [ ] Task: Full-suite validation
  - `python -m pytest tests -q` green (unit + integration + e2e).
  - `ruff check src tests` and `black --check src tests` clean.
  - Coverage gates hold (>=80% line / >=70% branch).
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) [b9e3e31]
