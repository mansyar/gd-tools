extends GdToolsTest

class_name NativeMockingSuite

# Phase 1 semantics for the double engine: `double()` and `partial_double()`
# follow GUT behaviour for UNSTUBBED calls. Stubbing itself is Phase 2; every
# method here must pass once the double engine exists.

const SUBJECT := preload("res://scripts/mock_subject.gd")


func test_double_returns_instance_extending_target() -> void:
	# The double is a real instance whose generated script extends the target,
	# so `is` checks against the original class still hold.
	var d = double(SUBJECT)
	assert_not_null(d)
	assert_true(d is NativeMockSubject)


func test_double_accepts_path_string() -> void:
	# A path is accepted alongside a preloaded script resource.
	var d = double("res://scripts/mock_subject.gd")
	assert_not_null(d)
	assert_true(d is NativeMockSubject)


func test_double_unstubbed_variant_method_returns_null() -> void:
	# GUT semantics hold wherever null is a legal value: Variant-returning
	# and object-returning methods answer null until stubbed.
	var d = double(SUBJECT)
	assert_null(d.pick("anything"))


func test_double_unstubbed_typed_method_returns_type_default() -> void:
	# Godot forbids returning null from typed primitive functions, so the
	# double answers with the return type's zero value instead.
	var d = double(SUBJECT)
	assert_eq(d.add(2, 3), 0)
	assert_eq(d.greet("world"), "")


func test_double_does_not_run_real_implementation() -> void:
	# The real body must not execute for a full double: no side effects, no
	# mutation of inherited state.
	var d = double(SUBJECT)
	d.note("hello")
	assert_eq(d.events.size(), 0)


func test_double_returns_fresh_instance_per_call() -> void:
	# Each double() call yields an independent instance so tests cannot leak
	# state into each other through a shared double.
	var first = double(SUBJECT)
	var second = double(SUBJECT)
	assert_false(is_same(first, second))


func test_partial_double_runs_real_implementation() -> void:
	# A partial double runs the REAL implementation while nothing is stubbed.
	var p = partial_double(SUBJECT)
	assert_eq(p.add(2, 3), 5)
	assert_eq(p.greet("world"), "Hello, world!")


func test_partial_double_keeps_side_effects() -> void:
	# Real side effects survive: the partial records into the subject's state.
	var p = partial_double(SUBJECT)
	p.note("hello")
	assert_eq(p.events.size(), 1)
	assert_eq(p.events[0], "hello")
