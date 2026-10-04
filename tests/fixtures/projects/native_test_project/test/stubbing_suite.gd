extends GdToolsTest

class_name NativeStubbingSuite

# Phase 2 semantics for stubbing: `stub()` chains with `to_return()` and
# `to_call_super()`, match by exact arguments, the "any" wildcard, and a
# no-arguments default fallback. Every stub is registered against a specific
# double instance, so fresh doubles are never affected by earlier stubs.
# Fail-fast validation of invalid targets arrives in a later phase.

const SUBJECT := preload("res://scripts/mock_subject.gd")


func test_stub_to_return_overrides_double() -> void:
	var d = double(SUBJECT)
	stub(d, "add").to_return(99)
	assert_eq(d.add(2, 3), 99)


func test_stub_to_return_on_partial_double() -> void:
	var p = partial_double(SUBJECT)
	stub(p, "greet").to_return("overridden")
	assert_eq(p.greet("world"), "overridden")


func test_stub_to_call_super_on_full_double() -> void:
	var d = double(SUBJECT)
	stub(d, "add").to_call_super()
	assert_eq(d.add(2, 3), 5)


func test_stub_to_call_super_on_partial_runs_real() -> void:
	var p = partial_double(SUBJECT)
	stub(p, "add").to_call_super()
	assert_eq(p.add(2, 3), 5)


func test_stub_with_exact_arguments_matches_only_those() -> void:
	var d = double(SUBJECT)
	stub(d, "add", [2, 3]).to_return(99)
	assert_eq(d.add(2, 3), 99)
	# Any other call is unstubbed and answers the typed zero value.
	assert_eq(d.add(5, 5), 0)


func test_stub_with_any_wildcard_matches_any_value() -> void:
	var d = double(SUBJECT)
	stub(d, "add", ["any", 3]).to_return(7)
	assert_eq(d.add(100, 3), 7)
	# A call that does not match the pattern stays unstubbed.
	assert_eq(d.add(1, 4), 0)


func test_stub_without_arguments_is_default_fallback() -> void:
	var d = double(SUBJECT)
	stub(d, "add").to_return(-1)
	stub(d, "add", [1, 1]).to_return(2)
	# An exact-argument stub takes precedence over the default fallback.
	assert_eq(d.add(1, 1), 2)
	assert_eq(d.add(4, 4), -1)


func test_stub_to_return_null_on_untyped_method() -> void:
	var d = double(SUBJECT)
	stub(d, "pick").to_return(null)
	assert_null(d.pick("x"))


func test_stub_to_return_typed_value_on_typed_method() -> void:
	var d = double(SUBJECT)
	stub(d, "greet").to_return("hi")
	assert_eq(d.greet("x"), "hi")


func test_stub_applies_only_to_its_own_double() -> void:
	var first = double(SUBJECT)
	stub(first, "add").to_return(99)
	# A different double of the same script carries no stubs.
	var second = double(SUBJECT)
	assert_eq(second.add(1, 1), 0)
	# The stubbed double keeps its behaviour.
	assert_eq(first.add(1, 1), 99)


func test_stubs_do_not_leak_into_the_next_test() -> void:
	# The previous test registered a stub on one of its doubles; this test
	# creates a fresh double and must see pristine unstubbed behaviour.
	var d = double(SUBJECT)
	assert_eq(d.add(1, 1), 0)
	assert_eq(d.greet("x"), "")


func test_double_records_calls_with_arguments() -> void:
	# Phase 2 proving test for the call recorder: Phase 3 replaces the
	# internals read with public call-count assertions.
	var d = double(SUBJECT)
	d.add(2, 3)
	d.greet("world")
	d.add(4, 5)
	assert_eq(d.__gd_tools.calls.size(), 3)
	assert_eq(d.__gd_tools.calls[0]["method"], "add")
	assert_eq(d.__gd_tools.calls[0]["args"], [2, 3])
	assert_eq(d.__gd_tools.calls[1]["method"], "greet")
	assert_eq(d.__gd_tools.calls[2]["args"], [4, 5])


func test_to_return_seq_returns_values_in_order() -> void:
	# A sequenced stub answers successive matching calls with its values
	# in registration order.
	var d = double(SUBJECT)
	stub(d, "add", [2, 3]).to_return_seq([10, 20, 30])
	assert_eq(d.add(2, 3), 10)
	assert_eq(d.add(2, 3), 20)
	assert_eq(d.add(2, 3), 30)


func test_to_return_seq_repeats_final_value_on_exhaustion() -> void:
	# Once the sequence is exhausted, its final value repeats so late
	# calls never fail the script under test.
	var d = double(SUBJECT)
	stub(d, "add", [2, 3]).to_return_seq([10, 20])
	assert_eq(d.add(2, 3), 10)
	assert_eq(d.add(2, 3), 20)
	assert_eq(d.add(2, 3), 20)
	assert_eq(d.add(2, 3), 20)


func test_to_return_seq_composes_with_specificity_tiers() -> void:
	# Sequenced stubs participate in normal matching: an exact-argument
	# stub outranks the default fallback, and each double tracks its own
	# sequence position.
	var d = double(SUBJECT)
	stub(d, "add").to_return_seq([7, 8])
	stub(d, "add", [1, 1]).to_return(2)
	assert_eq(d.add(1, 1), 2)
	assert_eq(d.add(4, 4), 7)
	assert_eq(d.add(4, 4), 8)
	# The exact stub is unaffected by the fallback's sequence position.
	assert_eq(d.add(1, 1), 2)


func test_to_fail_records_a_failure_at_call_time() -> void:
	# A fail stub records a test failure through the normal failure path
	# when a matching call happens, naming the method and the given
	# message.
	var d = double(SUBJECT)
	stub(d, "add", [2, 3]).to_fail("boom")
	assert_eq(d.add(2, 3), 0)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "the fail stub recorded exactly one failure")
	if failures.size() == 1:
		var message := str(failures[0]["message"])
		assert_true("boom" in message, "carries the stub message: " + message)
		assert_true('"add"' in message, "names the stubbed method: " + message)


func test_to_fail_zero_value_lets_execution_continue() -> void:
	# GDScript has no exceptions: after a fail stub fires, the call still
	# answers the return type's zero value and the script under test keeps
	# executing (subsequent calls still land on the recorder).
	var d = double(SUBJECT)
	stub(d, "note").to_fail("nope")
	d.note("x")
	assert_call_count(d, "note", 1)
	d.add(2, 3)
	assert_call_count(d, "add", 1)
	var failures := get_failures()
	clear_failures()
	assert_eq(failures.size(), 1, "only the fail stub recorded a failure")
