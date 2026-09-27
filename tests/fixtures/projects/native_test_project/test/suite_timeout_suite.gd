extends GdToolsTest
class_name NativeSuiteTimeoutSuite

# Set only once `before_all` runs to completion. When the suite budget is
# too small, the runner abandons the hook mid-await and this stays false,
# which is how the Python side observes the budget rather than inferring it
# from a status.
var before_all_completed := false

const MARKER_PATH := "res://suite_timeout_completed.log"

func before_all() -> void:
	await wait_seconds(0.6)
	before_all_completed = true
	# A file marker as well as the instance flag: an empty suite produces no
	# test results to assert on, so the flag alone would be unobservable.
	var marker = FileAccess.open(MARKER_PATH, FileAccess.WRITE)
	if marker != null:
		marker.store_line("completed")
		marker.close()

func test_first_short_budget() -> void:
	assert_true(true)

func test_second_long_budget() -> void:
	assert_true(true)

func test_before_all_really_completed() -> void:
	assert_true(before_all_completed, "before_all did not run to completion")
