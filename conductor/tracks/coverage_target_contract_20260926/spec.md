# Coverage Target Contract: Skip or Fail Uninstrumentable Files

- **Track ID:** coverage_target_contract_20260926
- **Type:** Feature
- **Status:** Draft — awaiting a decision on the behavior below
- **Origin:** Found during the Conductor review of `native_scene_integration_20260925`
  (see the review remediation commit `c00d048` git note).

## Problem

The coverage addon skips a file it cannot instrument, but the process still
fails. The two signals contradict each other, and neither is documented.

`src/gd_tools/addons/gd-tools-coverage/coverage.gd`:

```gdscript
var script = load(path) as GDScript
if script == null:
    _log_error(                      # coverage.gd:279 → push_error()
        "Failed to instrument script.",
        "Cannot load script: " + path,
        "Verify the path in the plan exists and compiles."
    )
    return false                     # the function skips
```

`push_error` escalates, so Godot exits non-zero, and
`src/gd_tools/test_runner.py:484` turns any `returncode > 1` into a hard
failure:

```python
if result.returncode > 1:
    raise GdToolsError(
        f"Godot exited with code {result.returncode}: "
        f"{result.stderr.strip()}"
    )
```

So the net behavior is: **the whole test run fails with exit 2.** The
`return false` and the "Verify the path..." text both imply a graceful skip.

The native runtime has the same structure —
`src/gd_tools/addons/gd-tools-test/gd_tools_native_coverage.gd:92-95` loads,
`push_error`s, and returns `false` — and the native runner maps the resulting
engine error to an `<engine>` error test, which is also exit 2.

**This is one decision, not two.** Fixing only the legacy path would leave the
two runtimes inconsistent, and native is now the default runtime.

## Scope of the real trigger

Verified while reviewing, so the trigger is narrower than it first appears:

- `src/gd_tools/coverage/plan_generator.py:501` computes
  `deleted = len(cached_paths - current_paths)` and forces plan regeneration, so
  **deleting a file does invalidate the plan cache**.
- `src/gd_tools/coverage/plan_generator.py:138` raises `CoveragePlanError` if a
  file is missing at generation time, so **a generated plan cannot reference a
  nonexistent file**.

The realistic triggers are therefore narrow:

1. A file deleted in the window between plan generation and the run.
2. `load()` failing for a reason other than "not found" — a real parse error, a
   cyclic dependency, or an engine-version-specific script feature.

Case 2 is the important one: a file that exists but does not compile is a real
defect, and skipping it silently makes coverage under-report.

## Options

| Option | Behavior | Cost |
| --- | --- | --- |
| **A. Fail (today, implicitly)** | Run stops, exit 2, error names the path | One uncompilable script blocks all testing in the project |
| **B. Skip** | Run continues, file excluded | Coverage silently under-reports; a broken script looks unexercised rather than broken |
| **C. Warn and continue** (recommended) | Run continues, file excluded, and the omission is recorded — in the run diagnostics, the terminal report, and the artifact index — plus a note that `--min` should be evaluated against the instrumented set | More work; needs an "uninstrumented targets" field threaded from plan through runner to report |

**Recommendation: option C.** It is what pytest-cov effectively does. It makes
`return false` honest and moves the information the error was trying to carry
somewhere durable instead of losing it in a process exit code. Silently
under-reported coverage is the more dangerous failure mode, because it survives
review and keeps looking complete.

If the smallest possible change is preferred, **option A is defensible** — but
then the `return false` and the "Verify the path..." text should stop implying
that the file is skipped.

## Why this is a separate track

`native_scene_integration_20260925` scoped itself to native scene/resource
integration. This changes the coverage contract for both runtimes, which is a
behavior change to the legacy path that track did not authorize.

## Open questions for the decision

- Does the omission belong in the run diagnostics, the terminal report, the
  artifact index, or all three?
- Should `--min` compare against the total plan or only the instrumented set?
  Comparing against the total makes a missing file depress the percentage;
  comparing only against the instrumented set hides it.
- Should a *nonexistent* path be treated differently from an *uncompilable* one?
  A nonexistent path indicates a stale plan; an uncompilable file indicates a
  broken script. They currently share one code path.
- Does the native and legacy coverage data schema need a new field, and if so
  is that a schema version bump?

## Notes for the implementer

- The plan should be written only after the option above is chosen, since the
  option determines the scope.
- `tests/integration/test_coverage_hooks.py::test_hooks_nonexistent_script_in_plan`
  currently depends on this behavior and is the natural place to pin the new
  contract. See the flakiness caveat in
  [the known-flakes note](./known_flakes.md) before trusting it as a gate.
