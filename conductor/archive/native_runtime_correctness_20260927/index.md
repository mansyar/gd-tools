# Track native_runtime_correctness_20260927 Context

Fixes three defects in the native test runtime, which is the default execution
path for `gd-tools test` and therefore the path every project runs. The
base-class `GdToolsTest.wait_for_signal` is typed `-> bool` but can only return
true, while `GdToolsTestContext.wait_for_signal` carries the same name with
opposite semantics, so a bounded wait cannot be written against the obvious
method. Separately, `gd_tools_test_runner.gd::_suite_timeout` returns on the
first iteration of its loop, making the first test's declared timeout the
`before_all` and `after_all` budget. And per-test timeout cancellation is
maintained by hand at three sites with no enforcement, so a forgotten increment
leaks a timer that fires into the following test as a spurious result. A fourth
task collapses the duplicated invoke-and-await bodies without merging two
genuinely different shapes. The work is confined to two shipped GDScript files
with no Python source change, and is delivered in four independently
checkpointable phases.

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Metadata](./metadata.json)
- [Known Flaky Tests](../coverage_target_contract_20260926/known_flakes.md)
