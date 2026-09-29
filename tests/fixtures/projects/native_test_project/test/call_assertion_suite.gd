extends GdToolsTest

# Phase 3 call-assertion family on GdToolsTest: `assert_called`,
# `assert_not_called`, `assert_call_count`, and `assert_call_arguments` must
# read the calls recorded on doubles produced by `double()` /
# `partial_double()`, with actionable expected-vs-actual diagnostics.
#
# Intentional-failure tests drive the assertion machinery, read the recorded
# failure via `get_failures()`, and finish with `clear_failures()` so the
# suite itself stays green once the assertions exist.

const SUBJECT := preload("res://scripts/mock_subject.gd")


func test_assert_called_passes_after_a_call() -> void:
	var d = double(SUBJECT)
	d.greet("world")
	assert_called(d, "greet")


func test_assert_not_called_passes_without_calls() -> void:
	var d = double(SUBJECT)
	assert_not_called(d, "greet")


func test_assert_call_count_matches_exact_number_of_calls() -> void:
	var d = double(SUBJECT)
	d.add(1, 2)
	d.add(3, 4)
	assert_call_count(d, "add", 2)


func test_assert_call_arguments_matches_recorded_arguments() -> void:
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", [2, 3])


func test_assert_call_arguments_checks_specific_call_index() -> void:
	# Index 0 is the first recorded call; -1 (the default) is the last.
	var d = double(SUBJECT)
	d.add(2, 3)
	d.add(4, 5)
	assert_call_arguments(d, "add", [4, 5], 1)


func test_assertions_count_methods_independently() -> void:
	var d = double(SUBJECT)
	d.greet("a")
	d.note("b")
	assert_call_count(d, "greet", 1)
	assert_call_count(d, "note", 1)
	assert_not_called(d, "pick")


func test_assert_called_failure_diagnostic_names_method() -> void:
	var d = double(SUBJECT)
	assert_called(d, "greet")
	var failures := get_failures()
	# Clear the recorder BEFORE verifying: if the assertion under test failed
	# to record anything, the verification below must fail the test for real.
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("greet" in message, "names the method: " + message)
		assert_true(
				"not" in message.to_lower() or "never" in message.to_lower(),
				"states the actual outcome: " + message
		)


func test_assert_not_called_failure_diagnostic_shows_count() -> void:
	var d = double(SUBJECT)
	d.greet("world")
	assert_not_called(d, "greet")
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("greet" in message, "names the method: " + message)
		assert_true("1" in message, "states the actual call count: " + message)


func test_assert_call_count_failure_diagnostic_shows_expected_and_actual() -> void:
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_count(d, "add", 3)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("add" in message, "names the method: " + message)
		assert_true("3" in message, "states the expected count: " + message)
		assert_true("1" in message, "states the actual count: " + message)


func test_assert_call_arguments_failure_diagnostic_shows_both_argument_sets() -> void:
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", [9, 9])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("add" in message, "names the method: " + message)
		assert_true("[9, 9]" in message, "shows expected arguments: " + message)
		assert_true("[2, 3]" in message, "shows actual arguments: " + message)


func test_assertions_read_the_call_recorder_not_script_state() -> void:
	# Calls recorded through a stubbed double must also be visible to the
	# assertion family: stubbed or not, every override records first.
	var d = double(SUBJECT)
	stub(d, "add").to_return(99)
	d.add(2, 3)
	assert_called(d, "add")
	assert_call_count(d, "add", 1)
	assert_call_arguments(d, "add", [2, 3])


func test_assertion_on_a_null_target_fails_cleanly() -> void:
	# A null target must record an actionable failure, not crash the suite
	# with a runtime error on a method call against null.
	assert_called(null, "greet")
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("double()" in message, "names the remedy: " + message)
