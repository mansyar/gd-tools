extends GdToolsTest
class_name BoolopBehaviorSuite


func test_and_right_evaluates_only_when_left_true() -> void:
	var subject := BoolopSideEffects.new()
	assert_eq(subject.and_pick(true, true), true)
	assert_eq(subject.cond_calls, 1)
	assert_eq(subject.right_calls, 1)


func test_and_right_skipped_when_left_false() -> void:
	var subject := BoolopSideEffects.new()
	assert_eq(subject.and_pick(false, true), false)
	assert_eq(subject.cond_calls, 1)
	assert_eq(subject.right_calls, 0)


func test_or_right_skipped_when_left_true() -> void:
	var subject := BoolopSideEffects.new()
	assert_eq(subject.or_pick(true, true), true)
	assert_eq(subject.cond_calls, 1)
	assert_eq(subject.right_calls, 0)


func test_or_right_evaluates_when_left_false() -> void:
	var subject := BoolopSideEffects.new()
	assert_eq(subject.or_pick(false, true), true)
	assert_eq(subject.cond_calls, 1)
	assert_eq(subject.right_calls, 1)


func test_return_values_unchanged() -> void:
	var subject := BoolopCoverageSubject.new()
	assert_eq(subject.both(true, false), false)
	assert_eq(subject.both(false, false), false)
	assert_eq(subject.either(false, false), false)
	assert_eq(subject.either(true, true), true)
	assert_eq(subject.chain(true, true, false), false)
	assert_eq(subject.chain(true, true, true), true)
