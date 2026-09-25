# Known Flaky Tests: Godot Under Load

Captured during the Conductor review of `native_scene_integration_20260925`.

## Symptom

Full-suite runs fail roughly one test out of ~1100, and it is a **different
test each run**. The failing test passes reliably in isolation.

| Run | Failing test | Passes alone? |
| --- | --- | --- |
| 1 | `tests/integration/test_test_runner_integration.py::test_run_tests_coverage_flag` | yes (12.5s) |
| 2 | `tests/e2e/test_native_integration_cli.py::test_native_cli_tag_selection_skips_unmatched_scene_tests` | yes (5.9s) |
| 3 | `tests/integration/test_coverage_hooks.py::test_hooks_nonexistent_script_in_plan` | yes (5/5, and 12/12 with its file) |

Run 3 produced this verbatim:

```
Godot exited with code 4294967295: ERROR: Attempt to open script
'res://scripts/nonexistent.gd' resulted in error 'File not found'.
  at: push_error (core/variant/variant_utility.cpp:1023)
  [0] _log_error (res://addons/gd-tools-coverage/coverage.gd:279)
```

The same fixture, plan, and code path produce exit 0 in isolation and `-1` under
load.

## Assessment

Not a defect in any individual test. Godot's process-level signals are
timing-sensitive under CPU contention — specifically whether a `push_error`
escalates the process exit code, and whether the error reaches the log before
teardown. The observation is solid; the precise escalation rule has not been
established and would need instrumentation to pin down.

Two distinct vectors:

- **Vector A — Godot's own process behavior** (exit code, error flush timing).
  Upstream; no change in our code makes it deterministic.
- **Vector B — our test helpers' assumptions** (hard `assert returncode == 0`,
  fixed timeouts). This vector was fixed once already: `import_godot_project` in
  the root `conftest.py` retries the Godot project import once, after
  reproducing the original failure verbatim (Godot printing
  `[ DONE ] first_scan_filesystem` and *then* exiting `-1`).

## Deliberately not done

A blanket retry around every Godot invocation was rejected: it would hide real
regressions, make the suite slower and noisier, and erase the ability to tell
"flaky" from "broken".

## Suggested next steps, in order of value

1. **Quarantine and label** the three tests above as known-flaky, so a random
   failure is triaged as noise rather than investigated from scratch.
2. **Experiment with serializing** the Godot-dependent tests. The suite already
   runs sequentially, and the contention is *within* the machine, so this may not
   help — worth one run to find out.
3. **Investigate the escalation rule** if it recurs, which would allow asserting
   on it instead of retrying around it.

Items 1 and 2 change how the suite reports failures, so they are the project's
call to make rather than an implementation detail.

## Related

- [Coverage target contract](./../coverage_target_contract_20260926/spec.md) —
  the underlying `push_error` escalation, treated as a product decision.
