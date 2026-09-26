# Architecture

This document describes the internal architecture of `gd-tools`. It covers two
subsystems, each documented in its own part:

| Part | Subsystem | Sections |
|------|-----------|----------|
| I | Coverage system --- the hybrid instrumentation architecture that fills the gap left by the absence of native GDScript coverage tooling in the Godot ecosystem | 1-7 |
| II | Native test runtime --- the Godot-native GDScript test runtime that replaced the GUT bridge | 8-13 |

For the full product specification, see [PRD Section
10](./PRD.md#10-coverage-architecture). For the original proof-of-concept
spike, see [SPIKE: Coverage
Instrumentation](./SPIKE_coverage_instrumentation.md). For the native runtime
migration roadmap, see [ROADMAP Section
8](./ROADMAP.md#8-temporary-native-test-runtime-migration-roadmap).

---

## Part I --- Coverage System

## 1. Overview

Godot 4 provides no built-in code coverage mechanism. GUT --- the
de facto GDScript test runner --- runs tests but does not track which
lines or branches were executed. `gd-tools` fills this gap with a
hybrid coverage system that combines Python-side static analysis with
GDScript-side runtime instrumentation.

The coverage system is the most technically complex component of
`gd-tools`. It spans two languages (Python and GDScript), three
execution phases, and four report formats. The architecture was
validated by a dedicated spike (see [SPIKE: Coverage
Instrumentation](./SPIKE_coverage_instrumentation.md)) before full
implementation.

### Why Coverage for GDScript Is Unique

GDScript coverage cannot reuse Python's `coverage.py` or JavaScript's
Istanbul. GDScript runs inside the Godot engine, not a standard
interpreter. The instrumentation must happen at the Godot runtime
level --- modifying `Script.source_code` and calling `Script.reload()`
--- because there is no bytecode hook API comparable to Python's
`sys.settrace`.

---

## 2. Architecture C (Hybrid)

The coverage system uses **Architecture C (Hybrid)** --- a three-phase
approach that splits work between Python (static analysis and
reporting) and GDScript (runtime instrumentation).

### Three Phases

| Phase | Language | Component | Responsibility |
|-------|----------|-----------|----------------|
| 1. Plan generation | Python | `coverage/plan_generator.py` | Parse GDScript via Lark AST, identify trackable lines and branches, emit `plan.json` |
| 2. Runtime instrumentation | GDScript | `coverage.gd`, `pre_run_hook.gd`, `post_run_hook.gd` | Inject tracker calls into source at runtime (via `coverage.gd._ready()`), activate tracker (via `pre_run_hook.gd`), execute tests, collect hit data, write `coverage.json` |
| 3. Report generation | Python | `coverage/reporter.py` | Cross-reference plan with hit data, compute metrics, emit reports (HTML, LCOV, Cobertura, text) |

### Comparison with Alternatives

Two alternative architectures were evaluated during the spike phase.
All three are documented in [SPIKE: Coverage Instrumentation Section
9](./SPIKE_coverage_instrumentation.md#9-fallback-plans).

**Architecture A --- Pure Python:**

Python generates instrumented copies of all `.gd` files in a temporary
directory, redirects GUT to run tests against the copies, then reads
coverage data. No GDScript addon is needed.

- Advantages: Simplest to implement; no dependency on Godot's
  `Script.source_code` API.
- Disadvantages: Most invasive. Class name resolution may break when
  scripts are moved. Test files need redirection to instrumented
  copies. `preload()` const references may not update.

**Architecture B --- Fork:**

Fork an existing Godot coverage project (e.g.,
`jamie-pate/godot-code-coverage`), update it for Godot 4.5, and use its
instrumentation mechanism while keeping the Python reporting layer.

- Advantages: Leverages existing work.
- Disadvantages: Depends on third-party code that may be unmaintained.
  Their instrumentation approach may be less robust than Lark-based
  parsing. Godot 4.5 compatibility is not guaranteed.

**Architecture C --- Hybrid (chosen):**

Python generates the plan; GDScript performs runtime instrumentation
via `Script.source_code` + `reload()`; Python generates reports.

- Advantages: Original source files on disk are never modified ---
  instrumentation happens in memory. Plan generation uses gdtoolkit's
  Lark parser for accurate AST traversal. The GDScript addon is small
  and self-contained.
- Disadvantages: Depends on Godot's `Script.reload()` working correctly
  in headless CLI mode. Source restoration after a crash is not
  handled (the process exits, discarding in-memory modifications).

### Why C Was Chosen

The spike (2026-07-09) validated all six success criteria for
Architecture C:

1. `Script.source_code` modification compiles via `reload()`.
2. Instrumented code executes and fires tracker calls.
3. Correct lines are recorded (hit counts match expected values).
4. Original test behavior is preserved (tests pass on instrumented
   code).
5. Coverage data is serializable as valid JSON.
6. The full flow works in CLI mode (`godot --headless -s ... -gexit`).

Since all criteria passed, no fallback was necessary. Architecture C
was confirmed for production implementation.

---

## 3. Full Flow

The following diagram shows the end-to-end flow of
`gd-tools test --coverage`:

```
User runs: gd-tools test --coverage --min 80

+---------------------------+
| CLI (cli.py)              |
|  load_config()            |
|  run_coverage_test()      |
+-----------+---------------+
            |
            v
+---------------------------+     +-----------------------+
| orchestrator.py           |     | plan_generator.py     |
|  run_coverage_test()      |---->|  generate_plan_cached()|
|                           |     |  cache check:         |
|  1. Generate/cached plan  |     |   compare file hashes |
|  2. Write plan.json       |<----|   hit: reuse cached   |
|     (skip on cache hit)   |     |   miss: generate_plan()|
|  3. Run tests w/ coverage |     +-----------------------+
|  4. Read coverage.json    |
|  5. Generate reports      |     plan.json written to:
+-----+---------------------+     .gd-tools/coverage/plan.json
      |
      | 3. Run tests
      v
+---------------------------+     +-----------------------+
| test_runner.py            |     | Godot subprocess      |
|  run_tests(coverage=True) |---->|  (headless)           |
|                           |     |                       |
|  Sets env vars:           |     |  _GDTCoverage._ready()|
|   GD_TOOLS_COVERAGE_      |     |   (first autoload)    |
|     PLAN=<plan.json>      |     |   load plan.json      |
|   GD_TOOLS_COVERAGE_      |     |   inject trackers     |
|     OUTPUT=<coverage.json>|     |   reload scripts      |
|                           |     |   (_active = false)   |
|  Builds GUT args with:   |     |   |                   |
|   -gpre_run_script=...   |     |   v                   |
|   -gpost_run_script=...   |     |  pre_run_hook.gd      |
+---------------------------+     |   set_active(true)    |
                                |   |                   |
                                |   v                   |
                                |  GUT runs tests       |
                                |   (instrumented code  |
                                |    fires tracker.hit) |
                                |   |                   |
                                |   v                   |
                                |  post_run_hook.gd     |
                                |   collect hits        |
                                |   write coverage.json  |
                                +-------+---------------+
                                        |
                                        v
                                .gd-tools/coverage/
                                  coverage.json

      |
      | 4. Read coverage data
      v
+---------------------------+     +-----------------------+
| orchestrator.py           |     | reporter.py           |
|  read coverage.json       |---->|  read_coverage_json() |
|  read plan.json           |     |  compute_summary()    |
|  generate_report()        |---->|  generate_report()    |
+---------------------------+     |                       |
                                  |  Dispatch to:        |
                                  |   html_reporter.py   |
                                  |   lcov_reporter.py   |
                                  |   cobertura_reporter |
                                  |   terminal_reporter  |
                                  +-----------+-----------+
                                              |
                                              v
                                  .gd-tools/coverage/
                                    (report files)
```

### Step-by-Step

1. **CLI entry:** `gd-tools test --coverage` calls
   `orchestrator.run_coverage_test()` with config and flags.

2. **Plan generation (with cache):** `plan_generator.generate_plan_cached()`
   checks if a cached `plan.json` exists and all source file hashes match.
   On a cache hit, the cached plan is reused without AST parsing. On a miss
   (file added/deleted/modified, corrupt plan, or `--no-cache` flag),
   `generate_plan()` discovers all `.gd` files in the project root (excluding
   `addons`, `.godot`, `.gd-tools`, `.git`, and test directories), parses
   each file via gdtoolkit's Lark parser, runs `CoverageVisitor` to identify
   trackable points, and assembles a `CoveragePlan`.

3. **Plan persistence:** The plan is serialized to
   `<output_dir>/plan.json` (skipped on cache hit — the file already
   exists and is unchanged).

4. **Test execution with coverage:** `test_runner.run_tests()` is
   called with `coverage=True`. This:
   - Sets two environment variables on the Godot subprocess.
   - Adds `-gpre_run_script` and `-gpost_run_script` GUT arguments
     pointing to the coverage addon hooks.
   - Launches Godot in headless mode with GUT.

5. **Autoload instrumentation (GDScript):** When Godot starts,
   `_GDTCoverage._ready()` runs as the first autoload (position 0),
   before any other autoload initializes. It:
   - Reads `plan.json` (path from `GD_TOOLS_COVERAGE_PLAN`).
   - Validates the plan structure.
   - For each file in the plan: loads the `GDScript` resource,
     injects `_GDTCoverage.hit(file_id, line_id)` calls before each
     trackable line, sets `script.source_code`, and calls
     `script.reload()`.
   - Leaves `_active = false` (tracker activation deferred to
     `pre_run_hook.gd`).

5b. **Tracker activation (GDScript):** GUT calls
   `pre_run_hook.gd.run()`, which calls `_GDTCoverage.set_active(true)`.
   This ensures hits are only recorded during test execution, not during
   autoload initialization.

6. **Test execution (instrumented):** GUT runs the tests. The
   instrumented code fires `_GDTCoverage.hit()` calls, which the
   tracker autoload records as hit counts in a nested dictionary
   keyed by `file_id` then `line_id`.

7. **Post-run collection (GDScript):** GUT calls
   `post_run_hook.gd.run()`. The hook:
   - Retrieves hits from the `_GDTCoverage` tracker.
   - Builds a JSON object with `version`, `generated_at`, and `files`.
   - Writes the result to `coverage.json` (path from
     `GD_TOOLS_COVERAGE_OUTPUT`).

8. **Report generation (Python):** `reporter.generate_report()` reads
   `coverage.json`, cross-references it with `plan.json` by
   `file_id`, computes line and branch coverage metrics, and
   dispatches to the format-specific reporter. If a `min_threshold`
   is set and not met, `CoverageThresholdError` is raised after the
   report file is written (the exception carries the `ReportResult`
   so the caller can display the coverage summary table without
   recomputation). `run_coverage_test()` prints the coverage summary
   table (Rich) to stdout on success, and before re-raising the
   threshold error.

---

## 4. Data Formats

### 4.1 Instrumentation Plan (`plan.json`)

The plan is generated by Python and consumed by the GDScript
pre-run hook. It identifies every trackable point in the project's
GDScript files.

```json
{
  "version": 1,
  "generated_by": "gd-tools",
  "files": [
    {
      "file_id": 0,
      "path": "res://scripts/calculator.gd",
      "source_hash": "sha256:abc123...",
      "lines": [
        {"line": 8, "id": 0, "type": "statement"},
        {"line": 9, "id": 1, "type": "branch", "branch_type": "if_true"},
        {"line": 11, "id": 2, "type": "branch", "branch_type": "if_false"}
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Schema version (currently 1) |
| `generated_by` | string | Tool name (`"gd-tools"`) |
| `files` | array | One entry per discovered `.gd` file |
| `files[].file_id` | int | Sequential 0-indexed identifier |
| `files[].path` | string | Godot resource path (`res://` prefix) |
| `files[].source_hash` | string | SHA-256 hash prefixed with `sha256:` |
| `files[].lines` | array | Trackable points in this file |
| `files[].lines[].line` | int | 1-indexed line number in source |
| `files[].lines[].id` | int | Unique identifier within the file (0-indexed) |
| `files[].lines[].type` | string | `"statement"` or `"branch"` |
| `files[].lines[].branch_type` | string\|null | Branch type if `type` is `"branch"`; `null` otherwise |

### Tracked Statement Types

The `CoverageVisitor` (Lark `Visitor`) identifies these statement
nodes in the GDScript AST:

| AST Node | GDScript Construct |
|----------|--------------------|
| `expr_stmt` | Expression statements |
| `return_stmt` | Return statements |
| `func_var_assigned` | Typed variable assignments |
| `func_var_typed_assgnd` | Typed variable assignments (explicit type) |
| `func_var_inf` | Inferred-type assignments (`:=`) |
| `break_stmt` | Break statements |
| `continue_stmt` | Continue statements |

### Tracked Branch Types

| AST Node | `branch_type` | GDScript Construct |
|----------|---------------|--------------------|
| `if_branch` | `if_true` | `if` block body |
| `elif_branch` | `elif_true` | `elif` block body |
| `else_branch` | `if_false` | `else` block body |
| `while_stmt` | `loop_body` | `while` loop body |
| `for_stmt` | `loop_body` | `for` loop body |
| `for_stmt_typed` | `loop_body` | Typed `for` loop body |
| `match_branch` | `match_case` | `match` case body |
| `test_expr` | `ternary_true`, `ternary_false` | Ternary expression (`a if cond else b`) — both value-branches |

### 4.2 Coverage Data (`coverage.json`)

The coverage data is produced by the GDScript post-run hook and
consumed by the Python reporter. It contains hit counts keyed by
`file_id` and `line_id`.

```json
{
  "version": 1,
  "generated_at": "2026-07-12T10:30:00Z",
  "files": [
    {
      "file_id": 0,
      "hits": {
        "0": 2,
        "1": 1,
        "2": 1
      }
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | int | Schema version (currently 1) |
| `generated_at` | string\|null | ISO 8601 timestamp from the runtime tracker |
| `files` | array | One entry per file with hits recorded |
| `files[].file_id` | int | Identifier matching the plan's `file_id` |
| `files[].hits` | object | Map of `line_id` (string) to hit count (int) |

Note: The coverage data does not include file paths --- path
resolution happens at report-generation time via the plan. Files in
the plan but absent from coverage data are treated as 0% covered.

---

## 5. Component Details

### 5.1 plan_generator.py

**Location:** `src/gd_tools/coverage/plan_generator.py`

**Responsibility:** Parses GDScript source files using gdtoolkit's
Lark parser, walks the resulting AST to identify trackable statements
and branch points, and emits an instrumentation plan.

**Key types:**

- `LinePlan` --- a single trackable point (line, id, type,
  branch_type).
- `FilePlan` --- per-file plan (file_id, path, source_hash, lines).
- `CoveragePlan` --- top-level container (version, generated_by,
  files).

**Key functions:**

- `generate_plan(project_root, exclude_dirs, test_dirs)`
  --- discovers `.gd` files, filters test directories, parses each
  file, runs `CoverageVisitor`, assembles a `CoveragePlan`.
- `generate_plan_cached(project_root, exclude_dirs, test_dirs,
  cache_path, use_cache)` --- wraps `generate_plan()` with hash-based
  cache check. Returns `tuple[CoveragePlan, CacheStatus]`. Cache hit:
  all file paths and source hashes match the cached plan. Cache miss:
  any file added/deleted/modified, corrupt plan, or `use_cache=False`.
- `CacheStatus` --- dataclass with `hit: bool` and `reason: str`,
  indicating whether the cached plan was reused.
- `write_plan_json(plan, output_path)` --- serializes a plan to JSON.
- `read_plan_json(path)` --- deserializes a plan from JSON with
  schema validation.
- `parse_gdscript(source)` --- wraps `gdtoolkit.parser.parser.parse()`
  with `gather_metadata=True` for line-number information.

**CoverageVisitor:** A Lark `Visitor` subclass. Each method
corresponds to a GDScript AST node name. When the visitor encounters
a node, it extracts the line number from `tree.meta.line`, assigns a
sequential `id`, and appends a `LinePlan` to `self.points`.

### 5.2 coverage.gd

**Location:** `src/gd_tools/addons/gd-tools-coverage/coverage.gd`

**Responsibility:** Autoload singleton registered as `_GDTCoverage`
in `project.godot` (first autoload, position 0). Instruments GDScript
files with coverage tracking calls in `_ready()`, then records line
hit counts during GUT test execution.

**Instrumentation:** In `_ready()`, the autoload checks the
`GD_TOOLS_COVERAGE_PLAN` environment variable. If set, it loads and
validates the plan JSON, then instruments each file by modifying
`script.source_code` and calling `script.reload()`. Because
`_GDTCoverage` is the first autoload, instrumentation happens before
any other autoload's `_ready()` creates instances --- eliminating
`ERR_ALREADY_IN_USE` errors.

**Activation:** After instrumentation, `_active` remains `false`. The
tracker is activated later by `pre_run_hook.gd.run()` calling
`set_active(true)`, ensuring hits are only recorded during test
execution. When inactive, the `hit()` method returns immediately ---
a single boolean check for minimal overhead.

**Data structure:** Hits are stored as a nested dictionary:
`_hits[file_id][line_id] = count`. The `hit(file_id, line_id)` method
increments the count for the given pair.

**Key methods:**

- `hit(file_id, line_id)` --- records a hit (no-op when inactive).
- `get_hits()` --- returns the full hits dictionary.
- `reset()` --- clears all recorded hits.
- `set_active(active)` --- programmatically activates/deactivates
  the tracker (used by `pre_run_hook.gd`).
- `is_active()` --- returns the current activation state.
- `_instrument_files(plan)` --- instruments all files in the plan
  (moved from `pre_run_hook.gd` in Track 24.5).
- `_instrument_file(file_entry)` --- instruments a single file via
  `load()` -> modify `source_code` -> `reload()`.
- `_inject_trackers(source, file_id, lines)` --- injects tracker calls
  bottom-to-top to preserve line numbers.

### 5.3 pre_run_hook.gd

**Location:** `src/gd_tools/addons/gd-tools-coverage/pre_run_hook.gd`

**Responsibility:** GUT pre-run hook. Activates the `_GDTCoverage`
tracker before tests are executed. Instrumentation was moved to
`coverage.gd._ready()` in Track 24.5.

**Base class:** `extends GutHookScript` (required by GUT 9.x). GUT
calls the `run()` method --- not `_init()` --- to execute the hook.

**Flow:**

1. Call `_GDTCoverage.set_active(true)` to activate the tracker.

By the time `pre_run_hook.gd.run()` is called, all autoloads
(including `_GDTCoverage`) have already initialized. The
instrumentation was performed in `_GDTCoverage._ready()`, so the
scripts are already instrumented. The pre-run hook only activates
hit recording, ensuring hits are captured only during test execution
--- not during autoload initialization.

**Note (Track 24.5):** All instrumentation logic (`_load_plan`,
`_validate_plan`, `_instrument_files`, `_instrument_file`,
`_inject_trackers`, `_extract_indent`, `_detect_body_indent`,
`_log_error`) was moved from `pre_run_hook.gd` to `coverage.gd`.
See Section 5.2 for details on the injection algorithm.

### 5.4 post_run_hook.gd

**Location:** `src/gd_tools/addons/gd-tools-coverage/post_run_hook.gd`

**Responsibility:** GUT post-run hook. Collects coverage data from
the `_GDTCoverage` tracker and writes it to a JSON file after tests
have executed.

**Base class:** `extends GutHookScript`. GUT calls the `run()`
method.

**Flow:**

1. Retrieve the `_GDTCoverage` autoload node from the scene tree.
2. Check that the tracker is active; if not, return silently.
3. Collect hits from the tracker via `get_hits()`.
4. Build the coverage JSON object (version, generated_at, files).
5. Write the JSON to the path from `GD_TOOLS_COVERAGE_OUTPUT`.
6. Print a summary line with file count and line count.

**JSON construction (`_build_coverage_json`):**

The hits dictionary uses integer keys internally
(`_hits[file_id][line_id]`). The post-run hook converts `line_id`
keys to strings for JSON serialization, since JSON object keys must
be strings.

### 5.5 reporter.py

**Location:** `src/gd_tools/coverage/reporter.py`

**Responsibility:** Reads the instrumentation plan and coverage data,
cross-references them by `file_id`, computes line and branch coverage
metrics, and dispatches to format-specific reporters.

**Key types:**

- `FileCoverage` --- per-file coverage data (file_id, hits).
- `CoverageData` --- top-level data (version, generated_at, files).
- `CoverageSummary` --- aggregated metrics (line_rate, branch_rate,
  covered/total counts).
- `FileSummary` --- per-file metrics with uncovered line and branch lists.
- `ReportResult` --- output of report generation (output_path,
  format, summary, file_summaries, threshold_met).

**Key functions:**

- `read_coverage_json(path)` --- deserializes coverage data with
  schema validation.
- `merge_coverage_data(files)` --- sums hit counts across multiple
  coverage files (for parallel CI shards).
- `write_coverage_json(data, path)` --- serializes coverage data.
- `compute_file_summary(file_plan, file_data)` --- per-file metrics.
- `compute_summary(plan, data)` --- overall metrics across all files.
- `render_uncovered_panels(file_summaries, plan)` --- renders Rich
  panels showing uncovered lines (as ranges) and branches (with type
  annotations) per file.
- `generate_report(plan, data, output_dir, format, min_threshold)`
  --- dispatches to the format-specific reporter and enforces the
  threshold.

**Supported formats:**

| Format | Output File | Reporter Module |
|--------|-------------|-----------------|
| `html` | `index.html` (in output dir) | `html_reporter.py` |
| `lcov` | `coverage.info` | `lcov_reporter.py` |
| `cobertura` | `cobertura.xml` | `cobertura_reporter.py` |
| `text` | `coverage_report.txt` | `terminal_reporter.py` |

**Threshold enforcement:** If `min_threshold` is set (0.0--1.0) and
`line_rate < min_threshold`, the report file is still written, then
`CoverageThresholdError` is raised (carrying the `ReportResult` so
the caller can display the coverage summary table before the error
propagates).

---

## 6. Design Decisions

### 6.1 Bottom-to-Top Injection

Tracker calls are inserted **before** the target line, which shifts
all subsequent lines down by one. To avoid line-number corruption,
line entries are sorted in descending order before insertion. This
ensures that inserting a tracker at line N does not affect the line
numbers of entries at lines > N, since those have already been
processed.

### 6.2 Environment Variable Activation

Two environment variables control the coverage system:

| Variable | Purpose |
|----------|---------|
| `GD_TOOLS_COVERAGE_PLAN` | Path to `plan.json` for `coverage.gd._ready()` instrumentation |
| `GD_TOOLS_COVERAGE_OUTPUT` | Path for `coverage.json` output |

These are set by `test_runner.run_tests()` when `coverage=True` is
passed. The same Godot/GUT project can run with or without coverage ---
no project configuration change is needed. When the plan env var is
absent, `_GDTCoverage._ready()` skips instrumentation and the tracker
remains inactive, so deploying the addon does not affect normal test
runs.

### 6.3 Source Restoration Approach

Source files on disk are **never modified**. Instrumentation happens
entirely in memory:

1. `script.source_code` is set to the instrumented version.
2. `script.reload()` recompiles the script in memory.
3. The original file on disk remains unchanged.

No backup or restore mechanism is needed because the instrumented
source exists only in the Godot process's memory. When the process
exits (after GUT finishes), the instrumented source is discarded.

The spike (see [SPIKE Section 13, Known Limitation
1](./SPIKE_coverage_instrumentation.md#13-spike-results-2026-07-09))
confirmed that source restoration after a crash is not needed for
the spike scope. In production, if `reload()` fails for a file, the
pre-run hook logs an error and skips that file --- the original
source remains in memory from the initial `load()`.

### 6.4 Error Precedence: TestFailureError Before CoverageThresholdError

When tests fail **and** coverage is below threshold,
`run_coverage_test()` re-raises `TestFailureError` first. This
ensures that CI pipelines report test failures as the primary issue
--- a coverage threshold violation is secondary when tests are already
failing. The coverage report is still generated (written to disk)
before either error is raised, so the report is available for
inspection regardless of the error.

In all cases (success, threshold failure, or test failure), the
coverage summary table (Rich, Lines/Branches: Found/Hit/Rate) is
printed to stdout before any error propagates. The table is rendered
by `_print_coverage_table()`, a shared helper extracted from
`show_coverage_summary()`.

### 6.5 Hook Base Class: GutHookScript

The pre-run and post-run hooks `extends GutHookScript` (not
`RefCounted`) and use the `run()` method (not `_init()`). This was
discovered during the spike --- GUT 9.x requires hook scripts to
inherit from `GutHookScript` and calls `run()` to execute them. See
[Spike Results, Key Deviation
1](./SPIKE_coverage_instrumentation.md#13-spike-results-2026-07-09).

### 6.6 Tracker Activation: Deferred to Pre-Run Hook (Track 24.5)

Instrumentation happens in `_GDTCoverage._ready()` (triggered by the
`GD_TOOLS_COVERAGE_PLAN` env var), but hit recording is activated
separately by `pre_run_hook.gd.run()` calling `set_active(true)`. This
separation ensures that hits are only recorded during test execution,
not during autoload initialization. When no plan env var is set,
instrumentation is skipped and the tracker stays inactive.

---

## 7. Cross-References

| Topic | Document | Section |
|-------|----------|---------|
| Full coverage specification | [PRD](./PRD.md) | Section 10 |
| Original spike proof-of-concept | [SPIKE](./SPIKE_coverage_instrumentation.md) | Full document |
| CLI command reference | [User Guide](./USER_GUIDE.md) | Command Reference |
| Coverage configuration keys | [User Guide](./USER_GUIDE.md) | Configuration |
| Contributing to the coverage system | [Contributing Guide](./CONTRIBUTING.md) | Project Structure |

---

## Part II --- Native Test Runtime

## 8. Overview

`gd-tools test` runs a GDScript test runtime that lives inside the Godot project
itself. A suite is an ordinary GDScript class extending `GdToolsTest`, which
extends `Node`. The test methods run in the real engine, against the real scene
tree, in the same project the code under test ships in.

The alternative --- driving an external framework over a subprocess boundary ---
cannot express assertions that need a live scene tree. A test that waits for a
signal from an animated `CharacterBody2D`, or that instantiates a scene and
inspects a child's exported state, has nothing to assert against unless the test
code is in the engine with the code under test.

The runtime is a **hybrid** design. Neither half is sufficient alone:

| Concern | Owner | Why |
|---------|-------|-----|
| Configuration, discovery, filtering, process orchestration, reporting, exit codes | Python | Pure logic, far easier to test and evolve off-engine |
| Test loading, lifecycle, assertions, async waits, scene-tree interaction, coverage activation | Godot | Requires a live engine and a live scene tree |

Python never parses GDScript to decide semantics. It reads *text* to find
candidate files (see [11.4](#114-discoverypy)), then delegates every semantic
question to Godot through a preflight process (see
[11.7](#117-gd_tools_test_preflightgd)).

### 8.1 Full Flow

```
gd-tools test
     |
     v
 +------------------+  discovery.py   find suites extending GdToolsTest
 |  Python          |  protocol.py    validate the version-2 contracts
 |                  |  command.py     import project, then preflight
 +------------------+
     |  writes suite-manifest.json
     v
 +------------------+  gd_tools_test_preflight.gd
 |  Godot           |  reads each suite's INTEGRATION constant
 |  (one preflight) |  through engine metadata, never text
 +------------------+
     |  preflight/result.json  (enriched, validated integration)
     v
 +------------------+  orchestrator.py  one process per suite
 |  Python          |  serial by default; merge coverage shards
 +------------------+
     |  GD_TOOLS_NATIVE_MANIFEST / _RESULT / _EVENTS / _LOG
     v
 +-----------------------------------------+
 |  Godot: gd_tools_test_runner.gd         |
 |    load suite -> before_all             |
 |    per test: context -> before_each     |
 |               -> test -> after_each     |
 |               -> failure evidence       |
 |    -> after_all -> write result         |
 +-----------------------------------------+
     |
     |  result.json + events.ndjson + coverage.json
     v
 +------------------+  reporter.py / terminal_reporter.py
 |  Python          |  JUnit XML, HTML/LCOV/Cobertura
 +------------------+  exit 0 pass, 1 failure, 2 environment
```

### 8.2 Isolation Model

Each suite runs in its **own Godot process**. This is not an optimization
detail --- it is what makes the run reproducible:

- A suite that leaks autoload state, adds nodes to the tree, or crashes the
  engine cannot affect any other suite.
- A crashed suite produces a distinguishable process outcome rather than
  corrupting the results of suites that already passed.
- Each process gets a fresh `ProjectSettings` load and a fresh engine, so
  ordering between suites cannot become a hidden dependency.

Suites run **sequentially** by default. Parallel execution is deliberately
deferred: concurrent Godot processes contend over the shared `.godot/` import
cache, and that contention is already a known source of intermittent failures
under load. The coverage shard merge ([11.2](#112-orchestratorpy)) is
order-independent, so it is already parallel-safe if that decision is revisited.

## 9. Data Formats

All cross-process data is versioned. `NATIVE_PROTOCOL_VERSION` is `2` in
`protocol.py`, mirrored by `PROTOCOL_VERSION := 2` in both GDScript entrypoints.
A mismatch is a protocol error, which surfaces as exit `2` --- never as a
silently mis-parsed result.

Every model is a Pydantic `BaseModel` with `extra='forbid'`, so an unknown key
is a hard error rather than a silently dropped field.

### 9.1 Suite Manifest (`preflight/suite-manifest.json`)

Written by Python, read by Godot. One file per suite.

| Field | Type | Meaning |
|-------|------|---------|
| `protocol_version` | `2` | Wire contract version |
| `project_root` | path | Absolute project root, for `res://` resolution |
| `runtime` | `native` \| `gut` | Runtime selector, echoed for clarity |
| `suite.name` | string | Class name, used for reporting and selection |
| `suite.path` | `res://` string | Suite script path |
| `suite.tests[]` | objects | `name`, `timeout_seconds`, `retries` |
| `suite.tags[]` | strings | Class-level tags, from `const TAGS` |
| `suite.integration` | object\|null | `scene`, `resources`, `mode` |

### 9.2 Integration Metadata

The result of merging suite defaults with per-test overrides. `null` for a
field means *remove an inherited entry*; an omitted field means *inherit*.

| Field | Type | Meaning |
|-------|------|---------|
| `integration.scene` | `res://` path\|null | At most one primary scene |
| `integration.resources` | map | Logical name to `res://` resource path |
| `integration.mode` | `headless` \| `windowed` | Execution mode for this suite |

`mode` is validated once per command, in the preflight, before any suite is
constructed. An invalid path, mode, or field is a **configuration** failure and
exits `2` naming the suite and the expected shape --- it is not left to fail
mid-test.

### 9.3 Preflight Result (`preflight/result.json`)

| Field | Type | Meaning |
|-------|------|---------|
| `status` | `ok` \| `error` | Whether validation succeeded |
| `suites[]` | objects | Enriched integration per suite, ready to execute |
| `error` | string\|null | Actionable failure message |

### 9.4 Per-Suite Result (`native/suite-NNNN.result.json`)

| Field | Type | Meaning |
|-------|------|---------|
| `status` | `passed` \| `failed` \| `error` | Suite outcome |
| `tests[]` | objects | `name`, `status`, `duration_seconds`, `attempts`, `message`, `diagnostics` |
| `coverage_data_path` | path\|null | Shard written by `GdToolsNativeCoverage` |
| `artifact_index_path` | path\|null | This run's artifact index |
| `engine_errors[]` | strings | Captured Godot errors |
| `engine_warnings[]` | strings | Captured Godot warnings |
| `started_at` / `finished_at` | ISO-8601 | Wall-clock bounds |

A test `status` may be `passed`, `failed`, `error`, `skipped`, or `pending`. The
protocol models `skipped` and `pending` and Python maps them
([11.1](#111-commandpy)), but the shipped assertion surface has no
`skip_test()` call yet, so no GDScript currently emits them.

### 9.5 Artifact Index (`artifacts.json`)

The machine-readable record of what a run produced. It lists only artifacts
that actually exist on disk, and `screenshots` lists only captures that were
realized.

| Field | Type | Meaning |
|-------|------|---------|
| `protocol_version` | `2` | Wire contract version |
| `run_id` | string | Run identifier |
| `status` | `passed` \| `failed` \| `error` \| `cancelled` | Terminal run status |
| `artifact_root` / `run_dir` | paths | Where the run wrote |
| `preflight` | map | Preflight artifact paths |
| `suites[]` | objects | Suite name plus its realized artifact paths |

### 9.6 Progress Events (`native/suite-NNNN.events.ndjson`)

One JSON object per line, appended as the run progresses. Streaming, so a run
can be observed while it executes.

### 9.7 Exit Codes

The exit code is the contract. It is stable across runtimes.

| Code | Meaning |
|------|---------|
| `0` | All selected tests passed, and any configured coverage threshold was met |
| `1` | A test failed, or coverage fell below `--min` |
| `2` | Environment, configuration, protocol, engine, or process failure |

Exit `2` is reserved for conditions where the run could not be trusted. A test
assertion failure is never exit `2` --- it is exit `1`. A windowed suite
requested on a headless renderer is exit `2`, because the suite did not run and
reporting it as a pass would be a lie.

## 10. Environment Contract

Python passes paths to Godot through the process environment rather than
command-line arguments, so long paths and `res://` values survive intact.

| Variable | Set by | Consumed by |
|----------|--------|-------------|
| `GD_TOOLS_NATIVE_MANIFEST` | orchestrator | runner --- manifest to execute |
| `GD_TOOLS_NATIVE_RESULT` | orchestrator | runner --- where to write the result |
| `GD_TOOLS_NATIVE_EVENTS` | orchestrator | runner --- NDJSON progress stream |
| `GD_TOOLS_NATIVE_LOG` | orchestrator | runner --- captured engine log |
| `GD_TOOLS_NATIVE_SCREENSHOT` | orchestrator | runner --- failure capture path |
| `GD_TOOLS_NATIVE_RUN_ID` | orchestrator | runner --- run identifier |
| `GD_TOOLS_NATIVE_PREFLIGHT_MANIFEST` | preflight | preflight script |
| `GD_TOOLS_NATIVE_PREFLIGHT_RESULT` | preflight | preflight script |

The preflight adapter clears every `_RUNNER_ENVIRONMENT_KEYS` entry before
launching. Without that, a preflight process would inherit a stale manifest
path from the environment and could execute the wrong suite.

## 11. Component Details

### 11.1 command.py

CLI-facing adapter. Owns the sequence Python controls end to end: resolve test
directories, discover suites, import the project, run the preflight, prepare
coverage, execute, then translate the run result into an exit code.

`run_native_test_command()` raises `ConfigError` when discovery finds nothing,
naming both remedies: add a suite extending `GdToolsTest`, or use
`--runtime gut` for a legacy project. The most useful error is the one that
tells you what to do next.

`_raise_for_native_error()` maps a terminal `error` status onto exit `2` before
any coverage threshold is evaluated --- an infrastructure failure must not be
reported as a coverage shortfall.

### 11.2 orchestrator.py

Runs one Godot process per suite, in a loop, and merges what comes back.

Per suite it writes a manifest, unlinks any stale shard before the run so a
crash cannot leave last run's coverage looking current, launches the process
with a bounded timeout, then reads the result file. A suite whose result file is
missing or unparseable becomes an `error` test result rather than a silent
omission.

`_merge_coverage_shards()` is order-independent by design, so coverage results
do not depend on suite order. That is also what makes the deferred parallelism
decision cheap to revisit.

`DEFAULT_RUNNER_SCRIPT` pins the runner to
`res://addons/gd-tools-test/gd_tools_test_runner.gd`.

### 11.3 preflight.py

Python adapter for the single headless preflight process. Writes a preflight
manifest, launches Godot once, and reads back the enriched result.

`_bounded_output()` truncates captured process output before it enters an error
message, so a Godot process that emits megabytes of diagnostics produces a
readable error instead of a wall of text.

### 11.4 discovery.py

Finds candidate suites. This is the one place where Python reads GDScript as
**text**, and it is deliberately limited to identifying *candidates*:

- `_EXTENDS_RE` matches a suite that extends `GdToolsTest`
- `_GUT_EXTENDS_RE` detects legacy `GutTest` suites so the error message can
  point at `--runtime gut`
- `_TEST_FUNC_RE` matches `test_*` methods with an empty parameter list
- `_TAG_RE` reads a class-level `const TAGS`

Anything semantic is deferred to the preflight. `NativeDiscoveryError` is a
`ConfigError`, so discovery problems exit `2` as configuration failures.

Because the test-method pattern requires no parameters, a parameterized test
method is not discovered as runnable. This is intentional, not an oversight ---
it is pinned by a test, because silently running a method that expects
arguments would be worse than not running it.

### 11.5 protocol.py

Every cross-process contract, as Pydantic models: `NativeSuite`, `NativeTest`,
`NativeSuiteIntegration`, `NativeTestIntegration`, `NativeCoverage`,
`NativeManifest`, `NativePreflightResult`, `NativeTestResult`, and
`NativeRunResult`.

`_ResourcePath` validates that a path is a `res://` path with no relative
segments, so a traversal attempt is rejected at the model boundary rather than
by a later filesystem call.

`write_json_atomic()` writes via a neighbouring temporary file and
`os.replace()`, so a reader never observes a half-written result.

### 11.6 artifacts.py

Run-scoped artifact layout and retention.

`NativeArtifactLayout` is a frozen dataclass and a **pure constructor** --- it
computes paths and touches no disk, which is what lets its behaviour be tested
without filesystem setup. `mark_run_started()` is the separate function that
creates the run directory and writes the marker.

Retention recognizes a run by a marker `gd-tools` itself wrote --- either
`.gdtools-run`, written the moment a run starts, or `artifacts.json`, the
published index. Everything else under the artifact root is left alone. Both
markers are required: the run-start marker means a run that dies before
publishing is still prunable, and accepting `artifacts.json` means runs from
earlier versions are not stranded forever.

The index is published **before** older runs are pruned. If publication fails,
nothing is deleted --- losing the ability to record a run is preferable to
losing a run's evidence.

### 11.7 gd_tools_test_preflight.gd

Headless entrypoint for validation. Loads each suite script through the engine
and reads its `INTEGRATION` constant as **metadata**, so integration
declarations are never parsed from source by Python.

It resolves suite-level defaults, merges per-test overrides field by field,
validates every `res://` path and the execution mode, and confirms that the
methods listed in the manifest actually exist on the loaded script
(`_test_method_names`). Method discovery uses `get_script_method_list()` ---
the engine's own view --- rather than a text pattern.

Any validation failure produces an `error` result, which Python turns into exit
`2` naming the suite and the expected shape. Because this runs once per command
before any suite is constructed, a bad declaration costs zero test execution.

### 11.8 gd_tools_test_runner.gd

The suite executor. One manifest, one suite, one process.

Per test, the order is fixed: build integration context, `before_each`, the test
body, `after_each`, then failure evidence, then teardown. Failure evidence is
captured *before* teardown, because after teardown the scene is gone and a
screenshot would be worthless.

Hooks are all optional, checked with `has_method`, so a suite defines only what
it needs. Retries rebuild the context from scratch per attempt, so a retry
cannot inherit mutated resources or a half-torn-down scene.

`_capture_engine_diagnostics()` collects Godot errors and warnings into the
result, so an engine-level complaint becomes structured test output instead of
a line in a log nobody reads. An engine error escalates the suite to `error`,
which is exit `2`.

### 11.9 gd_tools_test.gd

The base class a suite extends. It provides the assertion surface and the
engine-specific waits, and nothing else --- the runner owns lifecycle and
process management.

| Group | Functions |
|-------|-----------|
| Assertions | `assert_true`, `assert_false`, `assert_eq`, `assert_ne`, `assert_null`, `assert_not_null`, `fail` |
| Async waits | `wait_process_frame`, `wait_physics_frames`, `wait_seconds`, `wait_for_signal` |
| Context | `get_test_context()` |
| Suite state | suite-scoped storage for sharing fixtures across tests |

Assertions **record** failures rather than aborting, so one test reports every
assertion that failed instead of only the first. `_gd_tools_record_failure()`
attributes a failure to user code by skipping `gd_tools_test.gd` and
`gd_tools_test_runner.gd` stack frames --- a stack trace pointing at the
framework instead of the test is not a useful failure message.

### 11.10 gd_tools_test_context.gd

Explicit access to the scene tree and named resources for one test attempt.
Reached through `get_test_context()`.

| Method | Purpose |
|--------|---------|
| `get_scene_root()` | The instantiated primary scene |
| `find_node(relative_path)` | One node by relative path |
| `find_nodes(pattern)` | Nodes matching a name pattern |
| `get_resource(logical_name)` | A resource by its declared logical name |
| `get_integration()` | Effective resolved metadata for this test |
| `wait_for_signal(signal, timeout)` | Bounded wait |
| `capture_screenshot(path)` | Atomic capture |
| `clear()` | Release the scene and resources |

Resources are never assigned to nodes automatically. The context is a lookup
surface, not a proxy --- tests that want a node wired up wire it up
themselves, because a framework that silently mutates a scene tree makes test
setup invisible.

### 11.11 gd_tools_native_coverage.gd

Transient coverage collector for the native runner. It consumes the **same
version-1 instrumentation plan** the legacy path uses, so there is one plan
format rather than two.

Instrumentation happens in memory through the Script API. The tracker is reached
through a static callable, so instrumented code pays no lookup cost per hit.
On completion it writes the same `coverage.json` shape the Python reporter
already consumes.

This component is the bridge between the two halves of `gd-tools`: it is the
native runtime activating the coverage system described in Part I.

## 12. Design Decisions

### 12.1 Integration Metadata Is Read Through Godot, Never Parsed

Python reads `INTEGRATION` declarations by asking the engine for them
(`get_script_method_list()`, script constants) rather than by parsing GDScript
text. Parsing would make every formatting change, every syntax Godot adds, and
every conditional declaration a source of silent misreading. Asking the engine
cannot disagree with the engine.

The cost is one extra headless process per command, which is why validation
happens exactly once per command rather than once per suite.

### 12.2 Project Autoloads Run As In Production

The runtime installs **no test-only autoloads** and mutates no project
autoload. A suite that passes under a synthetic autoload the production build
does not have is a test that proves nothing.

This resolves in the opposite direction from the original roadmap item, which
contemplated an injectable autoload policy. The deciding argument was that
divergence between test and production autoloads is exactly the class of bug
this runtime exists to catch.

### 12.3 Windowed Execution Fails, It Does Not Fall Back

A `windowed` suite requires a real display. On a headless renderer it exits
`2` with no test executed, and never silently falls back to headless.

Automatic fallback would convert a configuration problem into a passing run
whose rendering was never exercised. Silence here is the failure mode that
matters most: the user believes they tested something they did not.

### 12.4 Per-Attempt Rebuild For Retry Isolation

Every attempt rebuilds the scene, context, and resources from scratch. A retry
that reused a mutated context would test state the first attempt had already
corrupted, and the second failure would say nothing about the code.

### 12.5 Run-Scoped Artifacts, Latest Run Only

Each run writes under `.gd-tools/artifacts/<run_id>/` with a machine-readable
index, and only the latest run is retained. The index is published before
pruning, so a failed publish never costs a run its evidence.

See [11.6](#116-artifactspy) for the retention marker rules, which exist to
make that guarantee true rather than merely intended.

### 12.6 One Godot Process Per Suite

Isolation over throughput. See [8.2](#82-isolation-model).

## 13. Cross-References

| Topic | Document | Section |
|-------|----------|---------|
| Coverage system architecture | This document | Part I, Sections 1-7 |
| Native runtime migration roadmap | [ROADMAP](./ROADMAP.md) | Section 8 |
| Native product decisions | [Conductor product definition](../conductor/product.md) | Section 9 |
| `gd-tools test` command reference | [User Guide](./USER_GUIDE.md) | Section 3.4 |
| Native runtime configuration keys | [User Guide](./USER_GUIDE.md) | Section 2.3 |
| Instrumentation plan and coverage data formats | This document | Sections 4.1, 4.2 |
| Runtime protocol and exit codes | This document | Sections 9, 11 |

### Known Limitations

Stated so they are not discovered by surprise:

- **No mocking or stubbing.** There is no double, spy, or stub facility.
- **No parameterized tests.** Test methods must take no parameters; a
  parameterized method is not discovered as runnable.
- **No parallel execution.** Suites run sequentially (see
  [8.2](#82-isolation-model)).
- **No `skip_test()`.** The protocol reserves `skipped` and `pending`, but the
  assertion surface cannot yet emit them.
- **Thin assertion surface.** Seven assertions (`gd_tools_test.gd`), which is
  considerably narrower than the GUT assertion set the migration bridge is
  being measured against.
- **No editor integration.** The runtime is headless and script-driven only.
