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


func test_assert_call_arguments_wildcard_matches_any_value() -> void:
	# The string "any" acts as a per-element wildcard, mirroring stub()
	# semantics: the wildcard position accepts any recorded argument.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", ["any", 3])


func test_assert_call_arguments_wildcard_matches_in_any_position() -> void:
	# Wildcards work in every argument position, not just the first.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", [2, "any"])


func test_assert_call_arguments_wildcard_still_checks_other_arguments() -> void:
	# A wildcard only lifts its own position: a concrete argument that
	# mismatches the recorded call still fails the assertion.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", ["any", 4])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "mismatched concrete argument must fail")


func test_assert_call_arguments_wildcard_requires_same_arity() -> void:
	# A pattern must have the same element count as the recorded call,
	# even when every element is a wildcard.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", ["any"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "arity mismatch must fail even with wildcards")


func test_assert_call_count_failure_lists_recorded_calls() -> void:
	# A count failure should show what actually happened: the recorded
	# calls with their indexes and arguments.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_count(d, "add", 2)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("call 0: [2, 3]" in message, "lists the recorded call: " + message)


func test_assert_not_called_failure_lists_recorded_calls() -> void:
	# The same call listing applies when assert_not_called fails.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_not_called(d, "add")
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("call 0: [2, 3]" in message, "lists the recorded call: " + message)


func test_assert_call_arguments_failure_shows_per_argument_diff() -> void:
	# An argument failure should pinpoint each mismatched position instead
	# of only showing two flat arrays.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", [9, 9])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true(
			"argument 0: expected 9, but was 2" in message,
			"diffs argument 0: " + message
		)
		assert_true(
			"argument 1: expected 9, but was 3" in message,
			"diffs argument 1: " + message
		)


func test_assert_call_arguments_failure_diff_skips_wildcard_positions() -> void:
	# Wildcard positions never mismatch, so the diff only covers concrete
	# arguments that failed to match.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_arguments(d, "add", ["any", 9])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true(
			"argument 1: expected 9, but was 3" in message,
			"diffs the concrete mismatch: " + message
		)
		assert_true(
			not ("argument 0:" in message),
			"does not diff the wildcard position: " + message
		)


func test_failure_call_list_is_bounded() -> void:
	# Diagnostics must stay readable: the recorded call list is capped,
	# with a summary line for the omitted calls.
	var d = double(SUBJECT)
	for i in range(12):
		d.add(i, i)
	assert_not_called(d, "add")
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("more call(s)" in message, "summarizes the tail: " + message)
		assert_true(not ("call 8:" in message), "caps the listing: " + message)


func test_assert_call_order_passes_in_order() -> void:
	# Calls recorded in the expected order satisfy the assertion.
	var d = double(SUBJECT)
	d.add(2, 3)
	d.greet("world")
	assert_call_order(d, ["add", "greet"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 0, "the expected order passes: " + str(failures))


func test_assert_call_order_ignores_unlisted_methods() -> void:
	# Order checking is subsequence-based: calls to methods that are not
	# listed do not break the expected ordering.
	var d = double(SUBJECT)
	d.add(2, 3)
	d.note("mid")
	d.greet("world")
	assert_call_order(d, ["add", "greet"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 0, "interleaved calls keep the order: " + str(failures))


func test_assert_call_order_handles_repeated_calls() -> void:
	# Repeated calls of the same method are consumed first-match: the first
	# expected "add" consumes the first recorded add, the second the next.
	var d = double(SUBJECT)
	d.add(1, 1)
	d.greet("mid")
	d.add(2, 2)
	assert_call_order(d, ["add", "greet", "add"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 0, "repeated methods match across interleaving: " + str(failures))


func test_assert_call_order_fails_when_order_is_reversed() -> void:
	# Out-of-order calls fail and the message shows the actual recorded
	# order so the user can see what happened.
	var d = double(SUBJECT)
	d.greet("world")
	d.add(2, 3)
	assert_call_order(d, ["add", "greet"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "the reversed order failed exactly once")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("actual order" in message, "shows the actual order: " + message)
		assert_true("greet" in message and "add" in message, "names both methods: " + message)


func test_assert_call_order_fails_when_method_never_called() -> void:
	# An expected method that never ran is named in the failure alongside
	# the actual recorded order.
	var d = double(SUBJECT)
	d.add(2, 3)
	assert_call_order(d, ["add", "pick"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "the missing method failed exactly once")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true('"pick"' in message, "names the missing method: " + message)
		assert_true("never called" in message, "says it never ran: " + message)


func test_assert_call_order_requires_a_double() -> void:
	# The assertion only accepts doubles, like the other spy assertions.
	assert_call_order(SUBJECT.new(), ["greet"])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1)
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("double()" in message, "explains the double requirement: " + message)
