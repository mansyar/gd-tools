extends GdToolsTest

# Phase 4 fail-fast validation: invalid mocking usage must fail the test
# immediately with a diagnostic naming the method and the target, not fail
# later (or silently do nothing) when the stub never matches.
#
# Every test here drives an intentional failure, captures the recorded
# failures, clears the recorder BEFORE verifying, and then checks the
# captured copy. Clearing first means a broken implementation (one that
# records nothing) makes the verification itself fail the test for real.

const SUBJECT := preload("res://scripts/mock_subject.gd")


func test_stub_on_nonexistent_method_fails_the_test() -> void:
	var d = double(SUBJECT)
	stub(d, "nonexistent").to_return(1)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "stub() must fail the test on a missing method")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("nonexistent" in message, "names the method: " + message)
		assert_true(
				"mock_subject" in message, "names the target script: " + message
		)


func test_stub_on_a_partial_double_missing_method_fails_the_test() -> void:
	var p = partial_double(SUBJECT)
	stub(p, "also_missing").to_call_super()
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "stub() must fail the test on a missing method")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("also_missing" in message, "names the method: " + message)


func test_stub_requires_a_double() -> void:
	var subject = SUBJECT.new()
	stub(subject, "add").to_return(1)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "stub() must fail the test on a non-double")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("double" in message, "explains the requirement: " + message)


func test_double_on_a_non_script_value_fails_the_test() -> void:
	double(42)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "double() must fail the test on a non-script")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("script" in message.to_lower(), "names the requirement: " + message)
		assert_true("42" in message, "names the offending value: " + message)


func test_partial_double_on_a_non_script_value_fails_the_test() -> void:
	partial_double([1, 2, 3])
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "partial_double() must fail the test on a non-script")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("script" in message.to_lower(), "names the requirement: " + message)
		assert_true("[1, 2, 3]" in message, "names the offending value: " + message)
