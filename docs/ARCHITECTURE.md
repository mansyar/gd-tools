# Architecture: Coverage System

This document describes the internal architecture of the `gd-tools`
code coverage system --- the component that fills the gap left by the
absence of native GDScript coverage tooling in the Godot ecosystem.

For the full product specification, see [PRD Section
10](./PRD.md#10-coverage-architecture). For the original proof-of-concept
spike, see [SPIKE: Coverage
Instrumentation](./SPIKE_coverage_instrumentation.md).

---

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
|  run_coverage_test()      |---->|  generate_plan()      |
|                           |     |  discover .gd files  |
|  1. Generate plan         |     |  parse via Lark AST   |
|  2. Write plan.json       |<----|  CoverageVisitor      |
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

2. **Plan generation:** `plan_generator.generate_plan()` discovers all
   `.gd` files in the project root (excluding `addons`, `.godot`,
   `.gd-tools`, `.git`, and test directories), parses each file via
   gdtoolkit's Lark parser, runs `CoverageVisitor` to identify
   trackable points, and assembles a `CoveragePlan`.

3. **Plan persistence:** The plan is serialized to
   `<output_dir>/plan.json`.

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
