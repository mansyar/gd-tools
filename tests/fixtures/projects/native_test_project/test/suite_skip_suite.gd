extends GdToolsTest
class_name NativeSuiteSkipSuite

# `skip_test()` called in `before_all` must mark every test in the suite —
# including each expanded parameterized case — as `skipped` with the reason.
# The test bodies assert false on purpose: if a body ever runs, the run
# fails, which proves the suite-level skip failed to prevent execution.

func before_all() -> void:
	parameterize(["value"], [[1], [2]])
	skip_test("suite environment unavailable")

func before_each() -> void:
	# Hooks must not run for suite-skipped tests; the presence of this
	# file after a run is observable proof they did.
	var file := FileAccess.open("res://suite_skip_hook_ran.txt", FileAccess.WRITE)
	file.store_string("ran")
	file.close()

func test_skipped_by_suite() -> void:
	assert_true(false, "suite-skip must prevent test bodies from running")

func test_async_case(value: int) -> void:
	assert_true(false, "parameterized cases must be skipped by suite skip")
