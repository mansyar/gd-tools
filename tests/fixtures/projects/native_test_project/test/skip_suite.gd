extends GdToolsTest
class_name NativeSkipSuite

# Skips with a reason; the runner reports `skipped` and carries the reason.
func test_skips_with_reason() -> void:
	skip_test("no network in sandbox")

# An argument-less skip must still yield a non-blank reason.
func test_skips_without_reason() -> void:
	skip_test()

# An assertion after a skip is discarded, not recorded as a failure.
func test_assertion_after_skip_is_discarded() -> void:
	skip_test("guard")
	assert_eq(1, 2, "must not be recorded")

# fail() after a skip is discarded on the same guard.
func test_fail_after_skip_is_discarded() -> void:
	skip_test("guard")
	fail("must not be recorded")

# A failure recorded before a skip still fails the test; a skip never masks it.
func test_failure_before_skip_still_fails() -> void:
	assert_eq(1, 2, "real failure")
	skip_test("too late")

# pending_test() is an alias for skip_test() and reports the same status.
func test_pending_test_alias() -> void:
	pending_test("alias path")
