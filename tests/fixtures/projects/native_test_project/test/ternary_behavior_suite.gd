extends GdToolsTest
class_name TernaryBehaviorSuite


func test_true_arm_evaluates_exactly_once() -> void:
	var subject := TernarySideEffects.new()
	assert_eq(subject.pick(true), 10)
	assert_eq(subject.true_calls, 1)
	assert_eq(subject.false_calls, 0)
	assert_eq(subject.cond_calls, 1)


func test_false_arm_evaluates_exactly_once() -> void:
	var subject := TernarySideEffects.new()
	assert_eq(subject.pick(false), 20)
	assert_eq(subject.false_calls, 1)
	assert_eq(subject.true_calls, 0)
	assert_eq(subject.cond_calls, 1)


func test_repeated_calls_track_each_evaluation() -> void:
	var subject := TernarySideEffects.new()
	assert_eq(subject.pick(true), 10)
	assert_eq(subject.pick(false), 20)
	assert_eq(subject.pick(true), 10)
	assert_eq(subject.true_calls, 2)
	assert_eq(subject.false_calls, 1)
	assert_eq(subject.cond_calls, 3)
